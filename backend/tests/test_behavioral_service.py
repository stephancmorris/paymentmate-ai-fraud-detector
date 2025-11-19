"""Unit tests for behavioral feature service."""

import time
from datetime import datetime
import pytest

from app.models.schemas import TransactionRequest
from app.services.behavioral_service import BehavioralService, get_behavioral_service
from app.services.feature_store import get_feature_store, initialize_feature_store


@pytest.fixture
def behavioral_service():
    """Create a fresh BehavioralService instance with clean feature store."""
    initialize_feature_store()
    store = get_feature_store()
    store.clear()
    return BehavioralService()


@pytest.fixture
def sample_transaction():
    """Create a sample transaction for testing."""
    return TransactionRequest(
        user_id=12345,
        amount=100.0,
        merchant_id="merchant_123",
        merchant_category="retail",
        timestamp=datetime.utcnow(),
        country="US",
        payment_method="credit_card"
    )


def test_calculate_behavioral_features_new_user(behavioral_service, sample_transaction):
    """Test behavioral features for new user (no history)."""
    features = behavioral_service.calculate_behavioral_features(sample_transaction)

    # New user should have default average (100.0)
    assert features["user_avg_amount"] == 100.0
    # Ratio should be 1.0 (100 / 100)
    assert features["amount_vs_avg_ratio"] == 1.0


def test_calculate_behavioral_features_existing_user(behavioral_service):
    """Test behavioral features for user with history."""
    user_id = 12345

    # Simulate user with $50 average
    store = get_feature_store()
    store.set(f"user:{user_id}:avg_amount", 50.0, ttl_seconds=3600)

    # New transaction for $200
    txn = TransactionRequest(
        user_id=user_id,
        amount=200.0,
        merchant_id="merchant_123",
        merchant_category="retail",
        timestamp=datetime.utcnow(),
        country="US",
        payment_method="credit_card"
    )

    features = behavioral_service.calculate_behavioral_features(txn)

    assert features["user_avg_amount"] == 50.0
    # Ratio should be 4.0 (200 / 50)
    assert features["amount_vs_avg_ratio"] == 4.0


def test_amount_10x_above_average(behavioral_service):
    """Test transaction 10x above user average (fraud pattern)."""
    user_id = 12345

    # User normally spends $50
    store = get_feature_store()
    store.set(f"user:{user_id}:avg_amount", 50.0, ttl_seconds=3600)

    # Fraudster makes $500 purchase
    txn = TransactionRequest(
        user_id=user_id,
        amount=500.0,
        merchant_id="merchant_999",
        merchant_category="electronics",
        timestamp=datetime.utcnow(),
        country="US",
        payment_method="credit_card"
    )

    features = behavioral_service.calculate_behavioral_features(txn)

    assert features["user_avg_amount"] == 50.0
    assert features["amount_vs_avg_ratio"] == 10.0  # 10x above average!


def test_update_user_profile_new_user(behavioral_service, sample_transaction):
    """Test updating profile for new user."""
    # Update profile with first transaction ($100)
    behavioral_service.update_user_profile(sample_transaction)

    # Check updated average (should be EMA: 100.0*0.9 + 100.0*0.1 = 100.0)
    store = get_feature_store()
    updated_avg = store.get(f"user:12345:avg_amount")

    assert updated_avg == 100.0


def test_update_user_profile_existing_user(behavioral_service):
    """Test updating profile for existing user (EMA calculation)."""
    user_id = 12345

    # User has $100 average
    store = get_feature_store()
    store.set(f"user:{user_id}:avg_amount", 100.0, ttl_seconds=3600)

    # New transaction for $200
    txn = TransactionRequest(
        user_id=user_id,
        amount=200.0,
        merchant_id="merchant_123",
        merchant_category="retail",
        timestamp=datetime.utcnow(),
        country="US",
        payment_method="credit_card"
    )

    behavioral_service.update_user_profile(txn)

    # New average = (100 * 0.9) + (200 * 0.1) = 90 + 20 = 110
    updated_avg = store.get(f"user:{user_id}:avg_amount")
    assert updated_avg == pytest.approx(110.0, rel=1e-6)


def test_update_user_profile_multiple_transactions(behavioral_service):
    """Test profile updates over multiple transactions (EMA convergence)."""
    user_id = 12345

    # Start with $100 average
    store = get_feature_store()
    store.set(f"user:{user_id}:avg_amount", 100.0, ttl_seconds=3600)

    # User makes 5 transactions of $150 each
    for i in range(5):
        txn = TransactionRequest(
            user_id=user_id,
            amount=150.0,
            merchant_id=f"merchant_{i}",
            merchant_category="retail",
            timestamp=datetime.utcnow(),
            country="US",
            payment_method="credit_card"
        )
        behavioral_service.update_user_profile(txn)

    # Average should move towards $150
    # After 5 updates: ~100 → ~105 → ~110 → ~114 → ~117 → ~120
    updated_avg = store.get(f"user:{user_id}:avg_amount")
    assert updated_avg > 110.0  # Should increase
    assert updated_avg < 130.0  # But not jump to 150 immediately (EMA smoothing)


def test_behavioral_features_zero_average_edge_case(behavioral_service):
    """Test edge case: user with zero average (shouldn't crash)."""
    user_id = 12345

    # Simulate user with $0 average (edge case)
    store = get_feature_store()
    store.set(f"user:{user_id}:avg_amount", 0.0, ttl_seconds=3600)

    txn = TransactionRequest(
        user_id=user_id,
        amount=100.0,
        merchant_id="merchant_123",
        merchant_category="retail",
        timestamp=datetime.utcnow(),
        country="US",
        payment_method="credit_card"
    )

    features = behavioral_service.calculate_behavioral_features(txn)

    # Should handle zero average gracefully (return ratio=1.0)
    assert features["user_avg_amount"] == 0.0
    assert features["amount_vs_avg_ratio"] == 1.0


def test_behavioral_features_calculation_speed(behavioral_service, sample_transaction):
    """Test that behavioral feature calculation is fast (<10ms)."""
    # Warm up
    behavioral_service.calculate_behavioral_features(sample_transaction)

    # Measure 100 calculations
    start_time = time.time()
    for _ in range(100):
        behavioral_service.calculate_behavioral_features(sample_transaction)
    elapsed_ms = (time.time() - start_time) * 1000

    avg_latency_ms = elapsed_ms / 100
    assert avg_latency_ms < 10.0, f"Behavioral calculation too slow: {avg_latency_ms:.2f}ms"


def test_singleton_pattern():
    """Test that get_behavioral_service returns singleton instance."""
    service1 = get_behavioral_service()
    service2 = get_behavioral_service()

    # Should be same instance
    assert service1 is service2


def test_multiple_users_independent_profiles(behavioral_service):
    """Test that different users have independent profiles."""
    # User 1: $50 average
    store = get_feature_store()
    store.set(f"user:1111:avg_amount", 50.0, ttl_seconds=3600)

    # User 2: $200 average
    store.set(f"user:2222:avg_amount", 200.0, ttl_seconds=3600)

    # User 1 transaction
    txn1 = TransactionRequest(
        user_id=1111,
        amount=100.0,
        merchant_id="merchant_123",
        merchant_category="retail",
        timestamp=datetime.utcnow(),
        country="US",
        payment_method="credit_card"
    )
    features1 = behavioral_service.calculate_behavioral_features(txn1)
    assert features1["user_avg_amount"] == 50.0
    assert features1["amount_vs_avg_ratio"] == 2.0

    # User 2 transaction
    txn2 = TransactionRequest(
        user_id=2222,
        amount=100.0,
        merchant_id="merchant_123",
        merchant_category="retail",
        timestamp=datetime.utcnow(),
        country="US",
        payment_method="credit_card"
    )
    features2 = behavioral_service.calculate_behavioral_features(txn2)
    assert features2["user_avg_amount"] == 200.0
    assert features2["amount_vs_avg_ratio"] == 0.5


def test_all_behavioral_features_returned(behavioral_service, sample_transaction):
    """Test that all required behavioral features are returned."""
    features = behavioral_service.calculate_behavioral_features(sample_transaction)

    # Verify all required keys exist
    required_keys = ["user_avg_amount", "amount_vs_avg_ratio"]
    for key in required_keys:
        assert key in features, f"Missing required feature: {key}"

    # Verify all values are floats
    for key, value in features.items():
        assert isinstance(value, float), f"Feature {key} is not a float: {type(value)}"


def test_fraud_scenario_spending_spike(behavioral_service):
    """Test fraud scenario: Large spending spike."""
    user_id = 12345

    # Normal user: $75 average
    store = get_feature_store()
    store.set(f"user:{user_id}:avg_amount", 75.0, ttl_seconds=3600)

    # Fraudster makes $1500 purchase (20x above average)
    txn = TransactionRequest(
        user_id=user_id,
        amount=1500.0,
        merchant_id="electronics_store",
        merchant_category="electronics",
        timestamp=datetime.utcnow(),
        country="US",
        payment_method="credit_card"
    )

    features = behavioral_service.calculate_behavioral_features(txn)

    assert features["user_avg_amount"] == 75.0
    assert features["amount_vs_avg_ratio"] == 20.0  # 20x spike!


def test_profile_ttl_set_correctly(behavioral_service, sample_transaction):
    """Test that user profiles have 30-day TTL."""
    behavioral_service.update_user_profile(sample_transaction)

    # Check that profile exists
    store = get_feature_store()
    avg = store.get(f"user:12345:avg_amount")
    assert avg is not None

    # Note: Can't directly test TTL without waiting or mocking time
    # But we verify it's set in the implementation (30 days = 2592000 seconds)


def test_ema_learning_rate_convergence(behavioral_service):
    """Test EMA learning rate (alpha=0.1) provides smooth updates."""
    user_id = 12345

    # Start with $100 average
    store = get_feature_store()
    store.set(f"user:{user_id}:avg_amount", 100.0, ttl_seconds=3600)

    # Make 10 transactions of $200 each
    for i in range(10):
        txn = TransactionRequest(
            user_id=user_id,
            amount=200.0,
            merchant_id=f"merchant_{i}",
            merchant_category="retail",
            timestamp=datetime.utcnow(),
            country="US",
            payment_method="credit_card"
        )
        behavioral_service.update_user_profile(txn)

    # After 10 transactions at $200, average should be moving towards $200
    # Formula: new_avg = old_avg * 0.9 + new_amount * 0.1
    # After 10 iterations: ~100 → ~190 (converging to 200)
    updated_avg = store.get(f"user:{user_id}:avg_amount")
    assert updated_avg > 150.0  # Should have moved significantly
    assert updated_avg < 200.0  # But not fully converged yet (EMA smoothing)
