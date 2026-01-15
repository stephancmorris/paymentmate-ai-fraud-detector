"""Behavioral feature calculation service for fraud detection."""

import logging
from typing import Dict, Any
from datetime import datetime

from app.models.schemas import TransactionRequest
from app.services.feature_store import get_feature_store, FeatureKeys

logger = logging.getLogger(__name__)


class BehavioralService:
    """Calculate behavioral deviation features using user profiles."""

    def __init__(self):
        self.feature_store = get_feature_store()
        logger.info("BehavioralService initialized")

    def calculate_behavioral_features(self, transaction: TransactionRequest) -> Dict[str, float]:
        """
        Calculate behavioral features for a transaction.

        Returns dict with:
            - user_avg_amount: User's average transaction amount (7-day window)
            - amount_vs_avg_ratio: Current amount / user average
        """
        user_id = transaction.user_id
        current_amount = float(transaction.amount)

        user_avg = self.feature_store.get(
            FeatureKeys.user_avg_amount(user_id),
            default=100.0
        )

        amount_ratio = current_amount / user_avg if user_avg > 0 else 1.0

        logger.debug(
            f"Behavioral features for user {user_id}: "
            f"avg_amount={user_avg:.2f}, ratio={amount_ratio:.2f}"
        )

        return {
            "user_avg_amount": float(user_avg),
            "amount_vs_avg_ratio": float(amount_ratio),
        }

    def update_user_profile(self, transaction: TransactionRequest) -> None:
        """
        Update user profile with transaction data.

        Uses exponential moving average: new_avg = (old_avg * 0.9) + (current_amount * 0.1)
        Call AFTER scoring to prevent current transaction from affecting its own features.
        """
        user_id = transaction.user_id
        current_amount = float(transaction.amount)

        current_avg = self.feature_store.get(
            FeatureKeys.user_avg_amount(user_id),
            default=100.0
        )

        alpha = 0.1
        new_avg = (current_avg * (1 - alpha)) + (current_amount * alpha)

        self.feature_store.set(
            FeatureKeys.user_avg_amount(user_id),
            new_avg,
            ttl_seconds=30 * 24 * 3600
        )

        logger.debug(
            f"Updated user {user_id} profile: "
            f"avg_amount {current_avg:.2f} → {new_avg:.2f}"
        )


_behavioral_service = None


def get_behavioral_service() -> BehavioralService:
    """Get global BehavioralService instance."""
    global _behavioral_service
    if _behavioral_service is None:
        _behavioral_service = BehavioralService()
    return _behavioral_service
