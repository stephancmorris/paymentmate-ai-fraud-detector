"""In-memory feature store for real-time velocity and behavioral features."""

import logging
import time
import threading
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from collections import defaultdict
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class FeatureValue:
    """Feature value with expiration timestamp."""
    value: Any
    expires_at: float  # Unix timestamp


class FeatureStore:
    """
    Thread-safe in-memory feature store with TTL support.

    Stores velocity features (transaction counts, amounts) with automatic expiration.
    Uses Python dict for <5ms get/set operations.
    """

    def __init__(self):
        """Initialize feature store with thread-safe dict."""
        self._store: Dict[str, FeatureValue] = {}
        self._lock = threading.RLock()  # Reentrant lock for nested operations
        self._cleanup_interval = 60  # Cleanup every 60 seconds
        self._last_cleanup = time.time()
        logger.info("FeatureStore initialized")

    def set(self, key: str, value: Any, ttl_seconds: int = 300) -> None:
        """
        Set feature value with TTL.

        Args:
            key: Feature key (e.g., "user:12345:txn_count_5m")
            value: Feature value (int, float, str, dict, list)
            ttl_seconds: Time-to-live in seconds (default: 300 = 5 minutes)
        """
        expires_at = time.time() + ttl_seconds

        with self._lock:
            self._store[key] = FeatureValue(value=value, expires_at=expires_at)
            self._maybe_cleanup()

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get feature value (returns None if expired or missing).

        Args:
            key: Feature key
            default: Default value if key missing/expired

        Returns:
            Feature value or default
        """
        with self._lock:
            feature = self._store.get(key)

            if feature is None:
                return default

            # Check if expired
            if time.time() > feature.expires_at:
                del self._store[key]  # Clean up expired entry
                return default

            return feature.value

    def increment(self, key: str, amount: int = 1, ttl_seconds: int = 300) -> int:
        """
        Atomically increment counter (creates if missing).

        Args:
            key: Feature key
            amount: Increment amount (default: 1)
            ttl_seconds: TTL for new keys

        Returns:
            New counter value
        """
        with self._lock:
            current = self.get(key, default=0)
            new_value = current + amount
            self.set(key, new_value, ttl_seconds)
            return new_value

    def add_to_list(self, key: str, value: Any, max_length: int = 100, ttl_seconds: int = 3600) -> List:
        """
        Append value to list (creates if missing).

        Args:
            key: Feature key
            value: Value to append
            max_length: Max list size (oldest removed if exceeded)
            ttl_seconds: TTL for list

        Returns:
            Updated list
        """
        with self._lock:
            current_list = self.get(key, default=[])
            if not isinstance(current_list, list):
                current_list = []

            current_list.append(value)

            # Trim to max length (keep most recent)
            if len(current_list) > max_length:
                current_list = current_list[-max_length:]

            self.set(key, current_list, ttl_seconds)
            return current_list

    def delete(self, key: str) -> bool:
        """
        Delete feature.

        Args:
            key: Feature key

        Returns:
            True if deleted, False if not found
        """
        with self._lock:
            if key in self._store:
                del self._store[key]
                return True
            return False

    def get_many(self, keys: List[str]) -> Dict[str, Any]:
        """
        Get multiple features at once.

        Args:
            keys: List of feature keys

        Returns:
            Dict mapping keys to values (missing keys omitted)
        """
        result = {}
        for key in keys:
            value = self.get(key)
            if value is not None:
                result[key] = value
        return result

    def get_stats(self) -> Dict[str, Any]:
        """Return feature store statistics."""
        with self._lock:
            total_keys = len(self._store)
            expired_count = sum(1 for f in self._store.values() if time.time() > f.expires_at)

            return {
                "total_keys": total_keys,
                "active_keys": total_keys - expired_count,
                "expired_keys": expired_count,
                "memory_bytes": self._estimate_memory(),
            }

    def clear(self) -> int:
        """Clear all features (for testing). Returns count of deleted keys."""
        with self._lock:
            count = len(self._store)
            self._store.clear()
            logger.info(f"FeatureStore cleared ({count} keys deleted)")
            return count

    def _maybe_cleanup(self) -> None:
        """Cleanup expired entries if interval elapsed (non-blocking)."""
        current_time = time.time()

        # Check if cleanup needed (without blocking)
        if current_time - self._last_cleanup < self._cleanup_interval:
            return

        # Run cleanup
        self._last_cleanup = current_time
        expired_keys = [
            key for key, feature in self._store.items()
            if current_time > feature.expires_at
        ]

        for key in expired_keys:
            del self._store[key]

        if expired_keys:
            logger.debug(f"Cleaned up {len(expired_keys)} expired features")

    def _estimate_memory(self) -> int:
        """Rough memory estimate in bytes."""
        import sys
        total = sys.getsizeof(self._store)
        for key, feature in self._store.items():
            total += sys.getsizeof(key) + sys.getsizeof(feature.value)
        return total


# Feature key builders for consistent naming
class FeatureKeys:
    """
    Feature key builders following pattern: {entity}:{id}:{feature}:{window}

    Examples:
        user:12345:txn_count:5m
        user:12345:amount_sum:1h
        merchant:merch_123:txn_count:5m
    """

    @staticmethod
    def user_txn_count(user_id: int, window_minutes: int = 5) -> str:
        """User transaction count key (e.g., user:12345:txn_count:5m)."""
        return f"user:{user_id}:txn_count:{window_minutes}m"

    @staticmethod
    def user_amount_sum(user_id: int, window_minutes: int = 60) -> str:
        """User amount sum key (e.g., user:12345:amount_sum:60m)."""
        return f"user:{user_id}:amount_sum:{window_minutes}m"

    @staticmethod
    def user_amount_list(user_id: int, window_minutes: int = 60) -> str:
        """User amount list key (e.g., user:12345:amount_list:60m)."""
        return f"user:{user_id}:amount_list:{window_minutes}m"

    @staticmethod
    def user_transactions(user_id: int) -> str:
        """User transaction history key (e.g., user:12345:transactions)."""
        return f"user:{user_id}:transactions"

    @staticmethod
    def merchant_txn_count(merchant_id: str, window_minutes: int = 5) -> str:
        """Merchant transaction count key (e.g., merchant:merch_123:txn_count:5m)."""
        return f"merchant:{merchant_id}:txn_count:{window_minutes}m"

    @staticmethod
    def user_profile(user_id: int) -> str:
        """User profile key (e.g., user:12345:profile)."""
        return f"user:{user_id}:profile"

    @staticmethod
    def user_avg_amount(user_id: int) -> str:
        """User average amount key (e.g., user:12345:avg_amount)."""
        return f"user:{user_id}:avg_amount"

    @staticmethod
    def user_countries_24h(user_id: int) -> str:
        """User countries set (24h window) key (e.g., user:12345:countries:24h)."""
        return f"user:{user_id}:countries:24h"

    @staticmethod
    def user_merchants_1h(user_id: int) -> str:
        """User merchants set (1h window) key (e.g., user:12345:merchants:1h)."""
        return f"user:{user_id}:merchants:1h"

    @staticmethod
    def user_merchant_history(user_id: int) -> str:
        """User all-time merchant history key (e.g., user:12345:merchant_history)."""
        return f"user:{user_id}:merchant_history"


# Global singleton instance
_feature_store: Optional[FeatureStore] = None


def get_feature_store() -> FeatureStore:
    """Get global FeatureStore instance (must be initialized first)."""
    if _feature_store is None:
        raise RuntimeError("FeatureStore not initialized. Call initialize_feature_store() at startup.")
    return _feature_store


def initialize_feature_store() -> None:
    """Initialize and load feature store (call once at startup)."""
    global _feature_store

    if _feature_store is not None:
        logger.warning("FeatureStore already initialized")
        return

    logger.info("Initializing feature store...")
    _feature_store = FeatureStore()
    logger.info("✓ FeatureStore initialized")
