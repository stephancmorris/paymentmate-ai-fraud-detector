"""Velocity feature calculation service for fraud detection."""

import logging
from typing import Dict, Any

from app.models.schemas import TransactionRequest
from app.services.feature_store import get_feature_store, FeatureKeys

logger = logging.getLogger(__name__)


class VelocityService:
    """Calculate real-time velocity features using feature store."""

    def __init__(self):
        """Initialize velocity service."""
        self.feature_store = get_feature_store()
        logger.info("VelocityService initialized")

    def calculate_velocity_features(self, transaction: TransactionRequest) -> Dict[str, float]:
        """
        Calculate all velocity features for a transaction.

        Returns dict with:
            - txn_count_5min: Transaction count in last 5 minutes (user)
            - txn_count_1hour: Transaction count in last 1 hour (user)
            - amount_sum_last10: Sum of last 10 transaction amounts (user)
            - merchant_txn_count: Transaction count in last 5 minutes (merchant)
        """
        user_id = transaction.user_id
        merchant_id = transaction.merchant_id
        amount = float(transaction.amount)

        # User transaction count (5 minute window)
        txn_5min_key = FeatureKeys.user_txn_count(user_id=user_id, window_minutes=5)
        txn_count_5min = self.feature_store.get(txn_5min_key, default=0)

        # User transaction count (1 hour window)
        txn_1hour_key = FeatureKeys.user_txn_count(user_id=user_id, window_minutes=60)
        txn_count_1hour = self.feature_store.get(txn_1hour_key, default=0)

        # User amount sum (last 10 transactions, 1 hour window)
        amount_list_key = FeatureKeys.user_amount_list(user_id=user_id, window_minutes=60)
        amount_list = self.feature_store.get(amount_list_key, default=[])
        amount_sum_last10 = sum(amount_list) if amount_list else amount

        # Merchant transaction count (5 minute window)
        merchant_5min_key = FeatureKeys.merchant_txn_count(merchant_id=merchant_id, window_minutes=5)
        merchant_txn_count = self.feature_store.get(merchant_5min_key, default=0)

        logger.debug(
            f"Velocity features for user {user_id}: "
            f"5min={txn_count_5min}, 1hour={txn_count_1hour}, "
            f"amount_sum={amount_sum_last10:.2f}, merchant_5min={merchant_txn_count}"
        )

        return {
            "txn_count_5min": float(txn_count_5min),
            "txn_count_1hour": float(txn_count_1hour),
            "amount_sum_last10": float(amount_sum_last10),
            "merchant_txn_count": float(merchant_txn_count),
        }

    def update_velocity_counters(self, transaction: TransactionRequest) -> None:
        """
        Update feature store counters after processing a transaction.

        Call this AFTER scoring to increment counters for next transaction.
        """
        user_id = transaction.user_id
        merchant_id = transaction.merchant_id
        amount = float(transaction.amount)

        # Increment user transaction count (5 minute window, 300s TTL)
        txn_5min_key = FeatureKeys.user_txn_count(user_id=user_id, window_minutes=5)
        self.feature_store.increment(txn_5min_key, amount=1, ttl_seconds=300)

        # Increment user transaction count (1 hour window, 3600s TTL)
        txn_1hour_key = FeatureKeys.user_txn_count(user_id=user_id, window_minutes=60)
        self.feature_store.increment(txn_1hour_key, amount=1, ttl_seconds=3600)

        # Add amount to user's transaction history (last 10, 1 hour window)
        amount_list_key = FeatureKeys.user_amount_list(user_id=user_id, window_minutes=60)
        self.feature_store.add_to_list(amount_list_key, value=amount, ttl_seconds=3600, max_length=10)

        # Increment merchant transaction count (5 minute window, 300s TTL)
        merchant_5min_key = FeatureKeys.merchant_txn_count(merchant_id=merchant_id, window_minutes=5)
        self.feature_store.increment(merchant_5min_key, amount=1, ttl_seconds=300)

        logger.debug(f"Updated velocity counters for user {user_id}, merchant {merchant_id}")


# Global singleton instance
_velocity_service = None


def get_velocity_service() -> VelocityService:
    """Get global VelocityService instance."""
    global _velocity_service
    if _velocity_service is None:
        _velocity_service = VelocityService()
    return _velocity_service
