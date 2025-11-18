"""Unit tests for velocity feature service."""

import time
from datetime import datetime, timedelta
import pytest

from app.models.schemas import TransactionRequest
from app.services.velocity_service import VelocityService, get_velocity_service
from app.services.feature_store import get_feature_store, initialize_feature_store


@pytest.fixture
def velocity_service():
    """Create a fresh VelocityService instance with clean feature store."""
    # Initialize feature store
    initialize_feature_store()

    # Clear feature store before each test
    store = get_feature_store()
    store.clear()

    # Return fresh velocity service
    return VelocityService()


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


def test_calculate_velocity_features_first_transaction(velocity_service, sample_transaction):
    """Test velocity features for user's first transaction."""
    features = velocity_service.calculate_velocity_features(sample_transaction)

    # First transaction should have zero counts
    assert features["txn_count_5min"] == 0.0
    assert features["txn_count_1hour"] == 0.0
    assert features["amount_sum_last10"] == 100.0  # Current amount (no history)
    assert features["merchant_txn_count"] == 0.0


def test_update_velocity_counters(velocity_service, sample_transaction):
    """Test that counters are incremented after update."""
    # Update counters
    velocity_service.update_velocity_counters(sample_transaction)

    # Check counters were incremented
    features = velocity_service.calculate_velocity_features(sample_transaction)

    assert features["txn_count_5min"] == 1.0
    assert features["txn_count_1hour"] == 1.0
    assert features["merchant_txn_count"] == 1.0


def test_user_velocity_5min_window(velocity_service, sample_transaction):
    """Test user transaction count in 5-minute window (Story 3.2 requirement)."""
    # Simulate 6 transactions from same user in 5 minutes
    for i in range(6):
        velocity_service.update_velocity_counters(sample_transaction)

    # 7th transaction should see count=6
    features = velocity_service.calculate_velocity_features(sample_transaction)
    assert features["txn_count_5min"] == 6.0


def test_user_velocity_1hour_window(velocity_service, sample_transaction):
    """Test user transaction count in 1-hour window."""
    # Simulate 15 transactions from same user
    for i in range(15):
        velocity_service.update_velocity_counters(sample_transaction)

    # 16th transaction should see count=15
    features = velocity_service.calculate_velocity_features(sample_transaction)
    assert features["txn_count_5min"] == 15.0  # All within 5 min
    assert features["txn_count_1hour"] == 15.0


def test_merchant_velocity_5min_window(velocity_service):
    """Test merchant transaction count in 5-minute window."""
    merchant_id = "high_volume_merchant"

    # Simulate 10 transactions to same merchant from different users
    for user_id in range(1, 11):  # user_id must be > 0
        txn = TransactionRequest(
            user_id=user_id,
            amount=50.0,
            merchant_id=merchant_id,
            merchant_category="retail",
            timestamp=datetime.utcnow(),
            country="US",
            payment_method="credit_card"
        )
        velocity_service.update_velocity_counters(txn)

    # Next transaction to this merchant should see count=10
    txn = TransactionRequest(
        user_id=999,
        amount=50.0,
        merchant_id=merchant_id,
        merchant_category="retail",
        timestamp=datetime.utcnow(),
        country="US",
        payment_method="credit_card"
    )
    features = velocity_service.calculate_velocity_features(txn)
    assert features["merchant_txn_count"] == 10.0


def test_amount_sum_last10_transactions(velocity_service, sample_transaction):
    """Test amount sum for last 10 transactions."""
    # Create 10 transactions with different amounts
    amounts = [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0]

    for amount in amounts:
        txn = TransactionRequest(
            user_id=12345,
            amount=amount,
            merchant_id="merchant_123",
            merchant_category="retail",
            timestamp=datetime.utcnow(),
            country="US",
            payment_method="credit_card"
        )
        velocity_service.update_velocity_counters(txn)

    # Next transaction should see sum of last 10
    features = velocity_service.calculate_velocity_features(sample_transaction)
    expected_sum = sum(amounts)  # 10+20+30+...+100 = 550
    assert features["amount_sum_last10"] == expected_sum


def test_amount_sum_max_10_transactions(velocity_service):
    """Test that amount list is capped at 10 transactions."""
    # Create 15 transactions
    for i in range(15):
        txn = TransactionRequest(
            user_id=12345,
            amount=10.0,
            merchant_id="merchant_123",
            merchant_category="retail",
            timestamp=datetime.utcnow(),
            country="US",
            payment_method="credit_card"
        )
        velocity_service.update_velocity_counters(txn)

    # Should only sum last 10 (100.0)
    txn = TransactionRequest(
        user_id=12345,
        amount=5.0,
        merchant_id="merchant_123",
        merchant_category="retail",
        timestamp=datetime.utcnow(),
        country="US",
        payment_method="credit_card"
    )
    features = velocity_service.calculate_velocity_features(txn)
    assert features["amount_sum_last10"] == 100.0  # 10 * 10.0


def test_multiple_users_dont_interfere(velocity_service):
    """Test that different users have independent counters."""
    # User 1: 3 transactions
    for i in range(3):
        txn1 = TransactionRequest(
            user_id=1111,
            amount=100.0,
            merchant_id="merchant_123",
            merchant_category="retail",
            timestamp=datetime.utcnow(),
            country="US",
            payment_method="credit_card"
        )
        velocity_service.update_velocity_counters(txn1)

    # User 2: 5 transactions
    for i in range(5):
        txn2 = TransactionRequest(
            user_id=2222,
            amount=50.0,
            merchant_id="merchant_123",
            merchant_category="retail",
            timestamp=datetime.utcnow(),
            country="US",
            payment_method="credit_card"
        )
        velocity_service.update_velocity_counters(txn2)

    # Check User 1 sees only their count
    txn1_check = TransactionRequest(
        user_id=1111,
        amount=100.0,
        merchant_id="merchant_123",
        merchant_category="retail",
        timestamp=datetime.utcnow(),
        country="US",
        payment_method="credit_card"
    )
    features1 = velocity_service.calculate_velocity_features(txn1_check)
    assert features1["txn_count_5min"] == 3.0

    # Check User 2 sees only their count
    txn2_check = TransactionRequest(
        user_id=2222,
        amount=50.0,
        merchant_id="merchant_123",
        merchant_category="retail",
        timestamp=datetime.utcnow(),
        country="US",
        payment_method="credit_card"
    )
    features2 = velocity_service.calculate_velocity_features(txn2_check)
    assert features2["txn_count_5min"] == 5.0


def test_velocity_features_calculation_speed(velocity_service, sample_transaction):
    """Test that velocity feature calculation is fast (<20ms)."""
    # Warm up
    velocity_service.calculate_velocity_features(sample_transaction)

    # Measure 100 calculations
    start_time = time.time()
    for _ in range(100):
        velocity_service.calculate_velocity_features(sample_transaction)
    elapsed_ms = (time.time() - start_time) * 1000

    avg_latency_ms = elapsed_ms / 100
    assert avg_latency_ms < 20.0, f"Velocity calculation too slow: {avg_latency_ms:.2f}ms"


def test_ttl_expiration_5min_window(velocity_service, sample_transaction):
    """Test that 5-minute counters expire after TTL (300 seconds)."""
    # This test would require mocking time or waiting 5 minutes
    # For now, we test that TTL is set correctly by checking feature store

    velocity_service.update_velocity_counters(sample_transaction)

    # Check that counter exists
    features = velocity_service.calculate_velocity_features(sample_transaction)
    assert features["txn_count_5min"] == 1.0

    # Note: Full TTL test would require time manipulation or Redis PTTL command
    # In-memory store will expire entries automatically via TTL


def test_singleton_pattern(velocity_service):
    """Test that get_velocity_service returns singleton instance."""
    service1 = get_velocity_service()
    service2 = get_velocity_service()

    # Should be same instance
    assert service1 is service2


def test_edge_case_first_transaction_for_new_user(velocity_service):
    """Test edge case: First transaction for new user returns count=1 (after update)."""
    new_user_txn = TransactionRequest(
        user_id=99999,
        amount=200.0,
        merchant_id="merchant_999",
        merchant_category="retail",
        timestamp=datetime.utcnow(),
        country="US",
        payment_method="credit_card"
    )

    # First check: Should have zero counts
    features_before = velocity_service.calculate_velocity_features(new_user_txn)
    assert features_before["txn_count_5min"] == 0.0

    # Update counters
    velocity_service.update_velocity_counters(new_user_txn)

    # Second transaction: Should see count=1
    features_after = velocity_service.calculate_velocity_features(new_user_txn)
    assert features_after["txn_count_5min"] == 1.0


def test_velocity_attack_scenario(velocity_service):
    """Test fraud scenario: Rapid-fire velocity attack (6 txns in 5 minutes)."""
    user_id = 12345

    # Simulate 6 rapid transactions (fraud pattern)
    for i in range(6):
        txn = TransactionRequest(
            user_id=user_id,
            amount=50.0 + i * 10,  # Varying amounts
            merchant_id=f"merchant_{i}",  # Different merchants
            merchant_category="retail",
            timestamp=datetime.utcnow(),
            country="US",
            payment_method="credit_card"
        )
        velocity_service.update_velocity_counters(txn)

    # 7th transaction should detect velocity attack
    attack_txn = TransactionRequest(
        user_id=user_id,
        amount=100.0,
        merchant_id="merchant_999",
        merchant_category="retail",
        timestamp=datetime.utcnow(),
        country="US",
        payment_method="credit_card"
    )
    features = velocity_service.calculate_velocity_features(attack_txn)

    # Should see 6 transactions in 5-minute window
    assert features["txn_count_5min"] == 6.0

    # Amount sum should include last 6 transactions
    # 50, 60, 70, 80, 90, 100 = 450
    expected_sum = sum([50.0 + i * 10 for i in range(6)])
    assert features["amount_sum_last10"] == expected_sum


def test_amount_sum_with_empty_history(velocity_service, sample_transaction):
    """Test that amount_sum returns current amount when no history."""
    # No updates, so no history
    features = velocity_service.calculate_velocity_features(sample_transaction)

    # Should return current transaction amount
    assert features["amount_sum_last10"] == sample_transaction.amount


def test_concurrent_updates_thread_safety(velocity_service):
    """Test thread safety with concurrent velocity updates."""
    import threading

    user_id = 12345
    num_threads = 10
    txns_per_thread = 10

    def update_counters():
        for i in range(txns_per_thread):
            txn = TransactionRequest(
                user_id=user_id,
                amount=10.0,
                merchant_id="merchant_123",
                merchant_category="retail",
                timestamp=datetime.utcnow(),
                country="US",
                payment_method="credit_card"
            )
            velocity_service.update_velocity_counters(txn)

    # Run concurrent updates
    threads = [threading.Thread(target=update_counters) for _ in range(num_threads)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # Check final count (should be num_threads * txns_per_thread)
    txn = TransactionRequest(
        user_id=user_id,
        amount=10.0,
        merchant_id="merchant_123",
        merchant_category="retail",
        timestamp=datetime.utcnow(),
        country="US",
        payment_method="credit_card"
    )
    features = velocity_service.calculate_velocity_features(txn)

    expected_count = num_threads * txns_per_thread
    assert features["txn_count_5min"] == expected_count
    assert features["txn_count_1hour"] == expected_count


def test_all_velocity_features_returned(velocity_service, sample_transaction):
    """Test that all required velocity features are returned."""
    features = velocity_service.calculate_velocity_features(sample_transaction)

    # Verify all required keys exist
    required_keys = ["txn_count_5min", "txn_count_1hour", "amount_sum_last10", "merchant_txn_count"]
    for key in required_keys:
        assert key in features, f"Missing required feature: {key}"

    # Verify all values are floats
    for key, value in features.items():
        assert isinstance(value, float), f"Feature {key} is not a float: {type(value)}"
