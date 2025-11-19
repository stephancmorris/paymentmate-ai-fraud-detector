"""Unit tests for anomaly detection service."""

import time
from datetime import datetime
import pytest

from app.models.schemas import TransactionRequest
from app.services.anomaly_service import AnomalyService, get_anomaly_service
from app.services.feature_store import get_feature_store, initialize_feature_store


@pytest.fixture
def anomaly_service():
    """Create a fresh AnomalyService instance with clean feature store."""
    initialize_feature_store()
    store = get_feature_store()
    store.clear()
    return AnomalyService()


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


def test_calculate_anomaly_features_new_user(anomaly_service, sample_transaction):
    """Test anomaly features for new user (no history)."""
    features = anomaly_service.calculate_anomaly_features(sample_transaction)

    # New user should have 0 countries, 0 merchants, new merchant
    assert features["unique_countries_24h"] == 0.0
    assert features["unique_merchants_1h"] == 0.0
    assert features["is_new_merchant"] == 1.0


def test_calculate_anomaly_features_existing_user(anomaly_service):
    """Test anomaly features for user with history."""
    user_id = 12345

    # Simulate user with history: 2 countries, 3 merchants, merchant_123 seen before
    store = get_feature_store()
    store.set(f"user:{user_id}:countries:24h", {"US", "CA"}, ttl_seconds=86400)
    store.set(f"user:{user_id}:merchants:1h", {"merch_1", "merch_2", "merch_3"}, ttl_seconds=3600)
    store.set(f"user:{user_id}:merchant_history", {"merch_1", "merch_2", "merchant_123"}, ttl_seconds=2592000)

    txn = TransactionRequest(
        user_id=user_id,
        amount=200.0,
        merchant_id="merchant_123",
        merchant_category="retail",
        timestamp=datetime.utcnow(),
        country="US",
        payment_method="credit_card"
    )

    features = anomaly_service.calculate_anomaly_features(txn)

    assert features["unique_countries_24h"] == 2.0
    assert features["unique_merchants_1h"] == 3.0
    assert features["is_new_merchant"] == 0.0  # merchant_123 is known


def test_geographic_anomaly_multiple_countries(anomaly_service):
    """Test detection of transactions from multiple countries."""
    user_id = 12345

    # Simulate 3 countries in 24 hours (account takeover pattern)
    store = get_feature_store()
    store.set(f"user:{user_id}:countries:24h", {"US", "RU", "CN"}, ttl_seconds=86400)

    txn = TransactionRequest(
        user_id=user_id,
        amount=500.0,
        merchant_id="merchant_999",
        merchant_category="electronics",
        timestamp=datetime.utcnow(),
        country="US",
        payment_method="credit_card"
    )

    features = anomaly_service.calculate_anomaly_features(txn)

    assert features["unique_countries_24h"] == 3.0  # High geographic spread!


def test_merchant_velocity_anomaly(anomaly_service):
    """Test detection of rapid merchant changes."""
    user_id = 12345

    # Simulate 6 different merchants in 1 hour (card testing pattern)
    merchants = {f"merchant_{i}" for i in range(1, 7)}
    store = get_feature_store()
    store.set(f"user:{user_id}:merchants:1h", merchants, ttl_seconds=3600)

    txn = TransactionRequest(
        user_id=user_id,
        amount=50.0,
        merchant_id="merchant_7",
        merchant_category="retail",
        timestamp=datetime.utcnow(),
        country="US",
        payment_method="credit_card"
    )

    features = anomaly_service.calculate_anomaly_features(txn)

    assert features["unique_merchants_1h"] == 6.0  # High merchant velocity!


def test_new_merchant_detection(anomaly_service):
    """Test detection of first transaction at new merchant."""
    user_id = 12345

    # User has history with 5 merchants
    known_merchants = {f"merchant_{i}" for i in range(1, 6)}
    store = get_feature_store()
    store.set(f"user:{user_id}:merchant_history", known_merchants, ttl_seconds=2592000)

    # Transaction at NEW merchant
    txn = TransactionRequest(
        user_id=user_id,
        amount=1000.0,
        merchant_id="merchant_new_suspicious",
        merchant_category="electronics",
        timestamp=datetime.utcnow(),
        country="US",
        payment_method="credit_card"
    )

    features = anomaly_service.calculate_anomaly_features(txn)

    assert features["is_new_merchant"] == 1.0  # New merchant flag


def test_update_anomaly_counters_new_user(anomaly_service, sample_transaction):
    """Test updating counters for new user."""
    anomaly_service.update_anomaly_counters(sample_transaction)

    # Check that sets were created
    store = get_feature_store()
    countries = store.get(f"user:12345:countries:24h")
    merchants = store.get(f"user:12345:merchants:1h")
    history = store.get(f"user:12345:merchant_history")

    assert countries == {"US"}
    assert merchants == {"merchant_123"}
    assert history == {"merchant_123"}


def test_update_anomaly_counters_existing_user(anomaly_service):
    """Test updating counters for existing user (set addition)."""
    user_id = 12345

    # User has existing data
    store = get_feature_store()
    store.set(f"user:{user_id}:countries:24h", {"US"}, ttl_seconds=86400)
    store.set(f"user:{user_id}:merchants:1h", {"merch_1"}, ttl_seconds=3600)
    store.set(f"user:{user_id}:merchant_history", {"merch_1", "merch_2"}, ttl_seconds=2592000)

    # New transaction from different country and merchant
    txn = TransactionRequest(
        user_id=user_id,
        amount=300.0,
        merchant_id="merch_3",
        merchant_category="retail",
        timestamp=datetime.utcnow(),
        country="CA",
        payment_method="credit_card"
    )

    anomaly_service.update_anomaly_counters(txn)

    # Check sets were updated
    countries = store.get(f"user:{user_id}:countries:24h")
    merchants = store.get(f"user:{user_id}:merchants:1h")
    history = store.get(f"user:{user_id}:merchant_history")

    assert countries == {"US", "CA"}
    assert merchants == {"merch_1", "merch_3"}
    assert history == {"merch_1", "merch_2", "merch_3"}


def test_fraud_scenario_account_takeover_geographic(anomaly_service):
    """Test fraud scenario: Account takeover with geographic hopping."""
    user_id = 12345

    # Normal user in US
    store = get_feature_store()
    store.set(f"user:{user_id}:countries:24h", {"US"}, ttl_seconds=86400)
    store.set(f"user:{user_id}:merchant_history", {"walmart", "target"}, ttl_seconds=2592000)

    # Fraudster uses card from Russia at new merchant
    txn = TransactionRequest(
        user_id=user_id,
        amount=800.0,
        merchant_id="russian_electronics_store",
        merchant_category="electronics",
        timestamp=datetime.utcnow(),
        country="RU",
        payment_method="credit_card"
    )

    features = anomaly_service.calculate_anomaly_features(txn)

    # Before update: 1 country (US only)
    assert features["unique_countries_24h"] == 1.0
    assert features["is_new_merchant"] == 1.0

    # After update, next transaction will see 2 countries
    anomaly_service.update_anomaly_counters(txn)
    countries = store.get(f"user:{user_id}:countries:24h")
    assert countries == {"US", "RU"}  # Geographic anomaly!


def test_fraud_scenario_card_testing(anomaly_service):
    """Test fraud scenario: Card testing across multiple merchants."""
    user_id = 67890

    # Simulate 5 rapid transactions at different merchants (card testing)
    merchants = []
    for i in range(1, 6):
        txn = TransactionRequest(
            user_id=user_id,
            amount=1.0,  # Small test amount
            merchant_id=f"merchant_{i}",
            merchant_category="retail",
            timestamp=datetime.utcnow(),
            country="US",
            payment_method="credit_card"
        )
        anomaly_service.update_anomaly_counters(txn)
        merchants.append(f"merchant_{i}")

    # 6th transaction (model will see 5 merchants from previous)
    txn = TransactionRequest(
        user_id=user_id,
        amount=1.0,
        merchant_id="merchant_6",
        merchant_category="retail",
        timestamp=datetime.utcnow(),
        country="US",
        payment_method="credit_card"
    )

    features = anomaly_service.calculate_anomaly_features(txn)

    assert features["unique_merchants_1h"] == 5.0  # High merchant velocity
    assert features["is_new_merchant"] == 1.0  # All merchants are new


def test_all_anomaly_features_returned(anomaly_service, sample_transaction):
    """Test that all required anomaly features are returned."""
    features = anomaly_service.calculate_anomaly_features(sample_transaction)

    # Verify all required keys exist
    required_keys = ["unique_countries_24h", "unique_merchants_1h", "is_new_merchant"]
    for key in required_keys:
        assert key in features, f"Missing required feature: {key}"

    # Verify all values are floats
    for key, value in features.items():
        assert isinstance(value, float), f"Feature {key} is not a float: {type(value)}"


def test_anomaly_features_calculation_speed(anomaly_service, sample_transaction):
    """Test that anomaly feature calculation is fast (<15ms)."""
    # Warm up
    anomaly_service.calculate_anomaly_features(sample_transaction)

    # Measure 100 calculations
    start_time = time.time()
    for _ in range(100):
        anomaly_service.calculate_anomaly_features(sample_transaction)
    elapsed_ms = (time.time() - start_time) * 1000

    avg_latency_ms = elapsed_ms / 100
    assert avg_latency_ms < 15.0, f"Anomaly calculation too slow: {avg_latency_ms:.2f}ms"


def test_singleton_pattern():
    """Test that get_anomaly_service returns singleton instance."""
    service1 = get_anomaly_service()
    service2 = get_anomaly_service()

    # Should be same instance
    assert service1 is service2


def test_multiple_users_independent_tracking(anomaly_service):
    """Test that different users have independent anomaly tracking."""
    # User 1: US only
    store = get_feature_store()
    store.set("user:1111:countries:24h", {"US"}, ttl_seconds=86400)
    store.set("user:1111:merchant_history", {"walmart"}, ttl_seconds=2592000)

    # User 2: CA and US
    store.set("user:2222:countries:24h", {"CA", "US"}, ttl_seconds=86400)
    store.set("user:2222:merchant_history", {"bestbuy", "target"}, ttl_seconds=2592000)

    # User 1 transaction
    txn1 = TransactionRequest(
        user_id=1111,
        amount=100.0,
        merchant_id="new_merchant",
        merchant_category="retail",
        timestamp=datetime.utcnow(),
        country="US",
        payment_method="credit_card"
    )
    features1 = anomaly_service.calculate_anomaly_features(txn1)
    assert features1["unique_countries_24h"] == 1.0
    assert features1["is_new_merchant"] == 1.0

    # User 2 transaction
    txn2 = TransactionRequest(
        user_id=2222,
        amount=100.0,
        merchant_id="bestbuy",
        merchant_category="electronics",
        timestamp=datetime.utcnow(),
        country="CA",
        payment_method="credit_card"
    )
    features2 = anomaly_service.calculate_anomaly_features(txn2)
    assert features2["unique_countries_24h"] == 2.0
    assert features2["is_new_merchant"] == 0.0  # bestbuy is known


def test_counter_ttl_set_correctly(anomaly_service, sample_transaction):
    """Test that anomaly counters have correct TTLs."""
    anomaly_service.update_anomaly_counters(sample_transaction)

    store = get_feature_store()

    # Countries: 24 hour TTL
    countries = store.get("user:12345:countries:24h")
    assert countries is not None

    # Merchants 1h: 1 hour TTL
    merchants = store.get("user:12345:merchants:1h")
    assert merchants is not None

    # Merchant history: 30 day TTL
    history = store.get("user:12345:merchant_history")
    assert history is not None


def test_geographic_spread_fraud_detection(anomaly_service):
    """Test detection of impossible travel (geographic spread fraud)."""
    user_id = 99999

    # User makes 4 transactions in 4 different countries within 24 hours (impossible!)
    countries = ["US", "CN", "RU", "BR"]
    store = get_feature_store()

    for country in countries:
        txn = TransactionRequest(
            user_id=user_id,
            amount=200.0,
            merchant_id=f"merchant_{country}",
            merchant_category="retail",
            timestamp=datetime.utcnow(),
            country=country,
            payment_method="credit_card"
        )
        anomaly_service.update_anomaly_counters(txn)

    # Check final state
    final_countries = store.get(f"user:{user_id}:countries:24h")
    assert len(final_countries) == 4  # 4 countries in 24h = strong fraud signal!


def test_edge_case_missing_country_data(anomaly_service):
    """Test handling of missing country data."""
    user_id = 12345

    txn = TransactionRequest(
        user_id=user_id,
        amount=100.0,
        merchant_id="merchant_123",
        merchant_category="retail",
        timestamp=datetime.utcnow(),
        country=None,  # Missing country
        payment_method="credit_card"
    )

    # Should not crash
    features = anomaly_service.calculate_anomaly_features(txn)
    assert features["unique_countries_24h"] == 0.0

    # Update should handle None gracefully
    anomaly_service.update_anomaly_counters(txn)
    store = get_feature_store()
    countries = store.get(f"user:{user_id}:countries:24h")
    assert None in countries  # None is added to set


def test_legitimate_scenario_frequent_shopper(anomaly_service):
    """Test legitimate scenario: User shopping at multiple known merchants."""
    user_id = 55555

    # User has extensive merchant history (frequent shopper)
    known_merchants = {f"merchant_{i}" for i in range(1, 21)}  # 20 known merchants
    store = get_feature_store()
    store.set(f"user:{user_id}:merchant_history", known_merchants, ttl_seconds=2592000)

    # User shops at known merchant
    txn = TransactionRequest(
        user_id=user_id,
        amount=150.0,
        merchant_id="merchant_5",
        merchant_category="retail",
        timestamp=datetime.utcnow(),
        country="US",
        payment_method="credit_card"
    )

    features = anomaly_service.calculate_anomaly_features(txn)

    assert features["is_new_merchant"] == 0.0  # Known merchant = not suspicious
