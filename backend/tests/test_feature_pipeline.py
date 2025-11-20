"""Integration tests for complete feature pipeline (Story 3.5)."""

import time
from datetime import datetime
import pytest
import pandas as pd

from app.models.schemas import TransactionRequest
from app.services.model_service import ModelService, get_model_service, initialize_model_service
from app.services.feature_store import get_feature_store, initialize_feature_store


@pytest.fixture(scope="module")
def model_service():
    """Create ModelService instance with loaded model."""
    initialize_feature_store()
    initialize_model_service()
    service = get_model_service()
    service.load_model()
    return service


@pytest.fixture(autouse=True)
def clear_feature_store():
    """Clear feature store between tests."""
    store = get_feature_store()
    store.clear()
    yield
    store.clear()


@pytest.fixture
def sample_transaction():
    """Create sample transaction for testing."""
    return TransactionRequest(
        user_id=12345,
        amount=100.0,
        merchant_id="merchant_123",
        merchant_category="retail",
        timestamp=datetime.utcnow(),
        country="US",
        payment_method="credit_card"
    )


def test_complete_pipeline_all_features_extracted(model_service, sample_transaction):
    """Test that all feature types are extracted in pipeline."""
    features_df = model_service.extract_features(sample_transaction)

    # Verify DataFrame structure
    assert isinstance(features_df, pd.DataFrame)
    assert len(features_df) == 1  # Single row
    assert len(features_df.columns) == 13  # 13 features

    # Verify all expected features present
    expected_features = [
        "amount", "amount_vs_avg_ratio", "amount_sum_last10", "user_avg_amount",
        "txn_count_5min", "txn_count_1hour", "hour_of_day", "day_of_week",
        "is_weekend", "is_night", "is_high_risk_category", "is_foreign_country",
        "merchant_txn_count"
    ]
    for feature in expected_features:
        assert feature in features_df.columns, f"Missing feature: {feature}"


def test_pipeline_feature_types_represented(model_service, sample_transaction):
    """Test that all feature types (velocity, behavioral, anomaly, temporal, categorical) are present."""
    features_df = model_service.extract_features(sample_transaction)
    features = features_df.iloc[0].to_dict()

    # Velocity features
    assert "txn_count_5min" in features  # Velocity
    assert "txn_count_1hour" in features  # Velocity
    assert "amount_sum_last10" in features  # Velocity
    assert "merchant_txn_count" in features  # Velocity

    # Behavioral features
    assert "user_avg_amount" in features  # Behavioral
    assert "amount_vs_avg_ratio" in features  # Behavioral

    # Temporal features
    assert "hour_of_day" in features  # Temporal
    assert "day_of_week" in features  # Temporal
    assert "is_weekend" in features  # Temporal
    assert "is_night" in features  # Temporal

    # Categorical features
    assert "is_high_risk_category" in features  # Categorical
    assert "is_foreign_country" in features  # Categorical

    # Note: Anomaly features calculated but not yet in model (waiting for retraining)


def test_pipeline_performance_under_100ms(model_service):
    """Test that complete pipeline (feature extraction + inference) completes in <100ms."""
    # Create test transaction
    txn = TransactionRequest(
        user_id=99999,
        amount=500.0,
        merchant_id="test_merchant",
        merchant_category="electronics",
        timestamp=datetime.utcnow(),
        country="US",
        payment_method="credit_card"
    )

    # Warm up (first run loads model)
    model_service.extract_features(txn)
    model_service.predict(txn)

    # Measure 10 runs
    times = []
    for _ in range(10):
        start = time.time()

        # Complete pipeline: feature extraction + model inference
        features_df = model_service.extract_features(txn)
        prediction = model_service.predict(txn)

        elapsed_ms = (time.time() - start) * 1000
        times.append(elapsed_ms)

    avg_time = sum(times) / len(times)
    assert avg_time < 100.0, f"Pipeline too slow: {avg_time:.2f}ms (target: <100ms)"


def test_pipeline_handles_missing_data_gracefully(model_service):
    """Test that pipeline handles missing/None values gracefully."""
    # Transaction with None country (edge case)
    txn = TransactionRequest(
        user_id=11111,
        amount=200.0,
        merchant_id="merchant_abc",
        merchant_category="retail",
        timestamp=datetime.utcnow(),
        country=None,  # Missing country
        payment_method="credit_card"
    )

    # Should not crash
    features_df = model_service.extract_features(txn)

    # Verify features extracted
    assert features_df is not None
    assert len(features_df) == 1

    # Check that is_foreign_country handles None gracefully
    assert "is_foreign_country" in features_df.columns


def test_pipeline_feature_vector_no_nan_values(model_service, sample_transaction):
    """Test that feature vector contains no NaN values."""
    features_df = model_service.extract_features(sample_transaction)

    # Check for NaN values
    assert not features_df.isnull().any().any(), "Feature vector contains NaN values"


def test_pipeline_feature_vector_no_infinity_values(model_service, sample_transaction):
    """Test that feature vector contains no infinity values."""
    features_df = model_service.extract_features(sample_transaction)

    # Check for infinity values
    assert not (features_df == float('inf')).any().any(), "Feature vector contains +inf"
    assert not (features_df == float('-inf')).any().any(), "Feature vector contains -inf"


def test_pipeline_feature_dimensionality_correct(model_service, sample_transaction):
    """Test that feature vector has correct dimensionality for model."""
    features_df = model_service.extract_features(sample_transaction)

    # Model expects 13 features
    assert features_df.shape == (1, 13), f"Incorrect shape: {features_df.shape}, expected (1, 13)"


def test_pipeline_end_to_end_with_real_data(model_service):
    """End-to-end test: transaction → features → prediction → response."""
    # Create realistic transaction
    txn = TransactionRequest(
        user_id=55555,
        amount=1250.0,
        merchant_id="walmart",
        merchant_category="retail",
        timestamp=datetime.utcnow(),
        country="US",
        payment_method="credit_card"
    )

    # Step 1: Extract features
    features_df = model_service.extract_features(txn)
    assert features_df is not None
    assert features_df.shape == (1, 13)

    # Step 2: Make prediction
    prediction = model_service.predict(txn)
    assert "score" in prediction
    assert "inference_time_ms" in prediction
    assert "model_version" in prediction
    assert "features_used" in prediction

    # Verify prediction values
    assert 0.0 <= prediction["score"] <= 1.0, "Score out of range [0, 1]"
    assert prediction["inference_time_ms"] >= 0, "Negative inference time"
    assert prediction["features_used"] == 13, f"Wrong feature count: {prediction['features_used']}"


def test_pipeline_velocity_features_update_over_time(model_service):
    """Test that velocity features update correctly over multiple transactions."""
    user_id = 77777

    # Transaction 1
    txn1 = TransactionRequest(
        user_id=user_id,
        amount=100.0,
        merchant_id="merch_1",
        merchant_category="retail",
        timestamp=datetime.utcnow(),
        country="US",
        payment_method="credit_card"
    )
    features1 = model_service.extract_features(txn1)

    # First transaction: should have 0 velocity
    assert features1.iloc[0]["txn_count_5min"] == 0.0
    assert features1.iloc[0]["txn_count_1hour"] == 0.0

    # Update velocity counters (normally done by scoring service)
    from app.services.velocity_service import get_velocity_service
    velocity_service = get_velocity_service()
    velocity_service.update_velocity_counters(txn1)

    # Transaction 2 (same user)
    txn2 = TransactionRequest(
        user_id=user_id,
        amount=150.0,
        merchant_id="merch_2",
        merchant_category="retail",
        timestamp=datetime.utcnow(),
        country="US",
        payment_method="credit_card"
    )
    features2 = model_service.extract_features(txn2)

    # Second transaction: should see first transaction in velocity
    assert features2.iloc[0]["txn_count_5min"] == 1.0  # Sees txn1
    assert features2.iloc[0]["txn_count_1hour"] == 1.0


def test_pipeline_behavioral_features_update_over_time(model_service):
    """Test that behavioral features update correctly over multiple transactions."""
    user_id = 88888

    # Transaction 1: $100
    txn1 = TransactionRequest(
        user_id=user_id,
        amount=100.0,
        merchant_id="merch_1",
        merchant_category="retail",
        timestamp=datetime.utcnow(),
        country="US",
        payment_method="credit_card"
    )
    features1 = model_service.extract_features(txn1)

    # First transaction: default average ($100)
    assert features1.iloc[0]["user_avg_amount"] == 100.0
    assert features1.iloc[0]["amount_vs_avg_ratio"] == 1.0  # 100 / 100

    # Update behavioral profile
    from app.services.behavioral_service import get_behavioral_service
    behavioral_service = get_behavioral_service()
    behavioral_service.update_user_profile(txn1)

    # Transaction 2: $200 (2x higher)
    txn2 = TransactionRequest(
        user_id=user_id,
        amount=200.0,
        merchant_id="merch_2",
        merchant_category="retail",
        timestamp=datetime.utcnow(),
        country="US",
        payment_method="credit_card"
    )
    features2 = model_service.extract_features(txn2)

    # Second transaction: should see updated average
    assert features2.iloc[0]["user_avg_amount"] == 100.0  # EMA: still 100 (updated after txn1)
    assert features2.iloc[0]["amount_vs_avg_ratio"] == 2.0  # 200 / 100


def test_pipeline_temporal_features_correct_values(model_service):
    """Test that temporal features are correctly calculated."""
    # Create transaction at specific time (past date to avoid validation error)
    test_time = datetime(2024, 11, 20, 14, 30, 0)  # Wednesday, 2:30 PM

    txn = TransactionRequest(
        user_id=99999,
        amount=100.0,
        merchant_id="merch_1",
        merchant_category="retail",
        timestamp=test_time,
        country="US",
        payment_method="credit_card"
    )

    features = model_service.extract_features(txn)

    # Verify temporal features
    assert features.iloc[0]["hour_of_day"] == 14.0  # 2 PM
    assert features.iloc[0]["day_of_week"] == 2.0  # Wednesday (0=Monday)
    assert features.iloc[0]["is_weekend"] == 0.0  # Wednesday is not weekend
    assert features.iloc[0]["is_night"] == 0.0  # 2 PM is not night


def test_pipeline_categorical_features_risk_detection(model_service):
    """Test that categorical features correctly identify risk."""
    # High-risk transaction
    high_risk_txn = TransactionRequest(
        user_id=11111,
        amount=1000.0,
        merchant_id="crypto_exchange",
        merchant_category="crypto",  # High-risk category
        timestamp=datetime.utcnow(),
        country="NG",  # High-risk country (Nigeria)
        payment_method="credit_card"
    )

    features = model_service.extract_features(high_risk_txn)

    # Should flag high-risk category and foreign country
    assert features.iloc[0]["is_high_risk_category"] == 1.0
    assert features.iloc[0]["is_foreign_country"] == 1.0

    # Low-risk transaction
    low_risk_txn = TransactionRequest(
        user_id=22222,
        amount=50.0,
        merchant_id="walmart",
        merchant_category="retail",  # Low-risk category
        timestamp=datetime.utcnow(),
        country="US",  # Low-risk country
        payment_method="credit_card"
    )

    features = model_service.extract_features(low_risk_txn)

    # Should not flag low-risk
    assert features.iloc[0]["is_high_risk_category"] == 0.0
    assert features.iloc[0]["is_foreign_country"] == 0.0


def test_pipeline_feature_extraction_timing_breakdown(model_service, sample_transaction, caplog):
    """Test that timing breakdown is logged correctly."""
    import logging
    caplog.set_level(logging.DEBUG)

    # Extract features (triggers timing logs)
    model_service.extract_features(sample_transaction)

    # Check that timing log was emitted
    timing_logs = [record for record in caplog.records if "Feature extraction timing" in record.message]
    assert len(timing_logs) > 0, "No timing breakdown logged"

    # Verify timing components are present
    timing_msg = timing_logs[0].message
    assert "velocity=" in timing_msg
    assert "behavioral=" in timing_msg
    assert "anomaly=" in timing_msg
    assert "temporal=" in timing_msg
    assert "categorical=" in timing_msg
    assert "total=" in timing_msg


def test_pipeline_feature_values_logged(model_service, sample_transaction, caplog):
    """Test that feature values are logged for debugging."""
    import logging
    caplog.set_level(logging.DEBUG)

    # Extract features (triggers feature value logs)
    model_service.extract_features(sample_transaction)

    # Check that feature values log was emitted
    feature_logs = [record for record in caplog.records if "Feature values:" in record.message]
    assert len(feature_logs) > 0, "No feature values logged"


def test_pipeline_concurrent_users_independent(model_service):
    """Test that multiple users have independent feature calculations."""
    # User 1: Regular shopper
    txn1 = TransactionRequest(
        user_id=111,
        amount=50.0,
        merchant_id="walmart",
        merchant_category="retail",
        timestamp=datetime.utcnow(),
        country="US",
        payment_method="credit_card"
    )

    # User 2: High spender
    txn2 = TransactionRequest(
        user_id=222,
        amount=5000.0,
        merchant_id="luxury_store",
        merchant_category="jewelry",
        timestamp=datetime.utcnow(),
        country="US",
        payment_method="credit_card"
    )

    # Extract features for both
    features1 = model_service.extract_features(txn1)
    features2 = model_service.extract_features(txn2)

    # Verify amounts are different (users are independent)
    assert features1.iloc[0]["amount"] == 50.0
    assert features2.iloc[0]["amount"] == 5000.0

    # Verify averages are independent
    assert features1.iloc[0]["user_avg_amount"] == 100.0  # Default
    assert features2.iloc[0]["user_avg_amount"] == 100.0  # Default (different user)
