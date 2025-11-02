"""Unit tests for in-memory feature store."""

import pytest
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

from app.services.feature_store import FeatureStore, FeatureKeys


@pytest.fixture
def store():
    """Create fresh feature store for each test."""
    return FeatureStore()


# ============================================================================
# Basic Operations Tests
# ============================================================================


def test_set_and_get(store):
    """Test basic set/get operations."""
    store.set("test_key", "test_value", ttl_seconds=60)
    assert store.get("test_key") == "test_value"


def test_get_missing_key(store):
    """Test getting missing key returns default."""
    assert store.get("missing_key") is None
    assert store.get("missing_key", default="default") == "default"


def test_get_expired_key(store):
    """Test that expired keys return None."""
    store.set("expiring_key", "value", ttl_seconds=1)
    assert store.get("expiring_key") == "value"

    time.sleep(1.1)  # Wait for expiration

    assert store.get("expiring_key") is None


def test_set_overwrites_existing(store):
    """Test that set overwrites existing value."""
    store.set("key", "value1", ttl_seconds=60)
    store.set("key", "value2", ttl_seconds=60)
    assert store.get("key") == "value2"


def test_delete_key(store):
    """Test deleting a key."""
    store.set("key", "value", ttl_seconds=60)
    assert store.delete("key") is True
    assert store.get("key") is None
    assert store.delete("key") is False  # Already deleted


def test_clear_all(store):
    """Test clearing all keys."""
    store.set("key1", "value1", ttl_seconds=60)
    store.set("key2", "value2", ttl_seconds=60)

    count = store.clear()

    assert count == 2
    assert store.get("key1") is None
    assert store.get("key2") is None


# ============================================================================
# Data Type Tests
# ============================================================================


def test_store_different_types(store):
    """Test storing different data types."""
    store.set("int_key", 42, ttl_seconds=60)
    store.set("float_key", 3.14, ttl_seconds=60)
    store.set("str_key", "hello", ttl_seconds=60)
    store.set("dict_key", {"a": 1, "b": 2}, ttl_seconds=60)
    store.set("list_key", [1, 2, 3], ttl_seconds=60)

    assert store.get("int_key") == 42
    assert store.get("float_key") == 3.14
    assert store.get("str_key") == "hello"
    assert store.get("dict_key") == {"a": 1, "b": 2}
    assert store.get("list_key") == [1, 2, 3]


# ============================================================================
# Increment Operation Tests
# ============================================================================


def test_increment_creates_if_missing(store):
    """Test increment creates counter if missing."""
    result = store.increment("counter")
    assert result == 1
    assert store.get("counter") == 1


def test_increment_existing_counter(store):
    """Test incrementing existing counter."""
    store.set("counter", 5, ttl_seconds=60)
    result = store.increment("counter")
    assert result == 6
    assert store.get("counter") == 6


def test_increment_by_amount(store):
    """Test incrementing by custom amount."""
    store.increment("counter", amount=10)
    assert store.get("counter") == 10

    store.increment("counter", amount=5)
    assert store.get("counter") == 15


def test_increment_expired_key(store):
    """Test increment on expired key creates new counter."""
    store.set("counter", 5, ttl_seconds=1)
    time.sleep(1.1)

    result = store.increment("counter")
    assert result == 1  # Starts fresh


# ============================================================================
# List Operations Tests
# ============================================================================


def test_add_to_list_creates_if_missing(store):
    """Test adding to non-existent list creates it."""
    result = store.add_to_list("list_key", "value1")
    assert result == ["value1"]
    assert store.get("list_key") == ["value1"]


def test_add_to_list_appends(store):
    """Test adding to existing list appends."""
    store.add_to_list("list_key", "value1")
    store.add_to_list("list_key", "value2")
    store.add_to_list("list_key", "value3")

    result = store.get("list_key")
    assert result == ["value1", "value2", "value3"]


def test_add_to_list_max_length(store):
    """Test list trimming when max_length exceeded."""
    for i in range(10):
        store.add_to_list("list_key", i, max_length=5)

    result = store.get("list_key")
    assert len(result) == 5
    assert result == [5, 6, 7, 8, 9]  # Keeps most recent


def test_add_to_list_non_list_value(store):
    """Test adding to key with non-list value resets as list."""
    store.set("key", "not_a_list", ttl_seconds=60)
    result = store.add_to_list("key", "value")
    assert result == ["value"]


# ============================================================================
# Get Many Tests
# ============================================================================


def test_get_many(store):
    """Test getting multiple keys at once."""
    store.set("key1", "value1", ttl_seconds=60)
    store.set("key2", "value2", ttl_seconds=60)
    store.set("key3", "value3", ttl_seconds=60)

    result = store.get_many(["key1", "key2", "key3", "missing_key"])

    assert result == {
        "key1": "value1",
        "key2": "value2",
        "key3": "value3"
    }  # missing_key not included


def test_get_many_empty_list(store):
    """Test get_many with empty list."""
    result = store.get_many([])
    assert result == {}


# ============================================================================
# TTL and Expiration Tests
# ============================================================================


def test_different_ttls(store):
    """Test keys with different TTLs expire independently."""
    store.set("key1", "value1", ttl_seconds=1)
    store.set("key2", "value2", ttl_seconds=3)

    assert store.get("key1") == "value1"
    assert store.get("key2") == "value2"

    time.sleep(1.5)

    assert store.get("key1") is None  # Expired
    assert store.get("key2") == "value2"  # Still valid


def test_automatic_cleanup(store):
    """Test automatic cleanup of expired keys."""
    # Set many keys with short TTL
    for i in range(50):
        store.set(f"key_{i}", f"value_{i}", ttl_seconds=1)

    stats_before = store.get_stats()
    assert stats_before["total_keys"] == 50

    time.sleep(1.1)  # Wait for expiration

    # Trigger cleanup by setting new key
    store.set("trigger", "cleanup", ttl_seconds=60)

    stats_after = store.get_stats()
    assert stats_after["active_keys"] < stats_before["total_keys"]


# ============================================================================
# Statistics Tests
# ============================================================================


def test_get_stats(store):
    """Test getting feature store statistics."""
    store.set("key1", "value1", ttl_seconds=60)
    store.set("key2", "value2", ttl_seconds=1)

    stats = store.get_stats()

    assert "total_keys" in stats
    assert "active_keys" in stats
    assert "expired_keys" in stats
    assert "memory_bytes" in stats

    assert stats["total_keys"] == 2

    time.sleep(1.1)

    stats2 = store.get_stats()
    assert stats2["expired_keys"] == 1  # key2 expired


# ============================================================================
# Feature Key Builders Tests
# ============================================================================


def test_feature_key_user_txn_count():
    """Test user transaction count key builder."""
    key = FeatureKeys.user_txn_count(12345, window_minutes=5)
    assert key == "user:12345:txn_count:5m"


def test_feature_key_user_amount_sum():
    """Test user amount sum key builder."""
    key = FeatureKeys.user_amount_sum(12345, window_minutes=60)
    assert key == "user:12345:amount_sum:60m"


def test_feature_key_user_transactions():
    """Test user transactions key builder."""
    key = FeatureKeys.user_transactions(12345)
    assert key == "user:12345:transactions"


def test_feature_key_merchant_txn_count():
    """Test merchant transaction count key builder."""
    key = FeatureKeys.merchant_txn_count("merch_123", window_minutes=5)
    assert key == "merchant:merch_123:txn_count:5m"


def test_feature_key_user_profile():
    """Test user profile key builder."""
    key = FeatureKeys.user_profile(12345)
    assert key == "user:12345:profile"


# ============================================================================
# Concurrency Tests
# ============================================================================


def test_concurrent_increments(store):
    """Test concurrent increments are thread-safe."""
    key = "concurrent_counter"
    num_threads = 10
    increments_per_thread = 100

    def increment_many():
        for _ in range(increments_per_thread):
            store.increment(key)

    threads = [threading.Thread(target=increment_many) for _ in range(num_threads)]

    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join()

    expected = num_threads * increments_per_thread
    actual = store.get(key)
    assert actual == expected, f"Expected {expected}, got {actual}"


def test_concurrent_reads_and_writes(store):
    """Test concurrent reads and writes don't cause errors."""
    num_operations = 200
    errors = []

    def random_operations():
        try:
            for i in range(100):
                operation = i % 4
                if operation == 0:
                    store.set(f"key_{i}", f"value_{i}", ttl_seconds=60)
                elif operation == 1:
                    store.get(f"key_{i}")
                elif operation == 2:
                    store.increment(f"counter_{i}")
                else:
                    store.add_to_list(f"list_{i}", i)
        except Exception as e:
            errors.append(str(e))

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(random_operations) for _ in range(10)]
        for future in as_completed(futures):
            future.result()

    assert len(errors) == 0, f"Concurrent operations had errors: {errors}"


def test_high_throughput(store):
    """Test handling 1000+ concurrent operations."""
    num_requests = 1000

    def single_operation(i):
        store.set(f"key_{i}", i, ttl_seconds=60)
        return store.get(f"key_{i}")

    start_time = time.time()

    with ThreadPoolExecutor(max_workers=50) as executor:
        futures = [executor.submit(single_operation, i) for i in range(num_requests)]
        results = [future.result() for future in as_completed(futures)]

    elapsed_ms = (time.time() - start_time) * 1000

    # Verify all operations succeeded
    assert len(results) == num_requests
    assert None not in results

    # Calculate average latency
    avg_latency_ms = elapsed_ms / num_requests

    print(f"\nThroughput test: {num_requests} operations in {elapsed_ms:.2f}ms")
    print(f"Average latency: {avg_latency_ms:.4f}ms per operation")

    # Should be well under 5ms per operation
    assert avg_latency_ms < 5


# ============================================================================
# Performance Tests
# ============================================================================


def test_get_performance(store):
    """Test that get operations complete in <5ms."""
    store.set("perf_key", "value", ttl_seconds=60)

    start = time.time()
    for _ in range(1000):
        store.get("perf_key")
    elapsed_ms = (time.time() - start) * 1000

    avg_ms = elapsed_ms / 1000
    print(f"\nAverage GET latency: {avg_ms:.4f}ms")

    assert avg_ms < 0.1  # Should be sub-0.1ms


def test_set_performance(store):
    """Test that set operations complete in <5ms."""
    start = time.time()
    for i in range(1000):
        store.set(f"key_{i}", i, ttl_seconds=60)
    elapsed_ms = (time.time() - start) * 1000

    avg_ms = elapsed_ms / 1000
    print(f"\nAverage SET latency: {avg_ms:.4f}ms")

    assert avg_ms < 0.1  # Should be sub-0.1ms


def test_increment_performance(store):
    """Test that increment operations complete in <5ms."""
    start = time.time()
    for _ in range(1000):
        store.increment("counter")
    elapsed_ms = (time.time() - start) * 1000

    avg_ms = elapsed_ms / 1000
    print(f"\nAverage INCREMENT latency: {avg_ms:.4f}ms")

    assert avg_ms < 0.1  # Should be sub-0.1ms
