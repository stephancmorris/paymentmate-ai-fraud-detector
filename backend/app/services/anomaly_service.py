"""Anomaly detection feature service for fraud detection."""

import logging
from typing import Dict, Set
from datetime import datetime

from app.models.schemas import TransactionRequest
from app.services.feature_store import get_feature_store, FeatureKeys

logger = logging.getLogger(__name__)


class AnomalyService:
    """Calculate anomaly detection features for geographic and merchant patterns."""

    def __init__(self):
        """Initialize anomaly service."""
        self.feature_store = get_feature_store()
        logger.info("AnomalyService initialized")

    def calculate_anomaly_features(self, transaction: TransactionRequest) -> Dict[str, float]:
        """
        Calculate anomaly features for a transaction.

        Returns dict with:
            - unique_countries_24h: Number of unique countries in last 24 hours
            - unique_merchants_1h: Number of unique merchants in last hour
            - is_new_merchant: 1.0 if merchant is new to user, 0.0 otherwise
        """
        user_id = transaction.user_id
        current_country = transaction.country
        current_merchant = transaction.merchant_id

        # Get unique countries in last 24 hours
        countries_key = FeatureKeys.user_countries_24h(user_id)
        countries_set = self.feature_store.get(countries_key, default=set())
        unique_countries = float(len(countries_set))

        # Get unique merchants in last hour
        merchants_key = FeatureKeys.user_merchants_1h(user_id)
        merchants_set = self.feature_store.get(merchants_key, default=set())
        unique_merchants = float(len(merchants_set))

        # Check if this is a new merchant for the user
        merchant_history_key = FeatureKeys.user_merchant_history(user_id)
        merchant_history = self.feature_store.get(merchant_history_key, default=set())
        is_new_merchant = 1.0 if current_merchant not in merchant_history else 0.0

        logger.debug(
            f"Anomaly features for user {user_id}: "
            f"countries_24h={unique_countries}, merchants_1h={unique_merchants}, "
            f"new_merchant={is_new_merchant}"
        )

        return {
            "unique_countries_24h": unique_countries,
            "unique_merchants_1h": unique_merchants,
            "is_new_merchant": is_new_merchant,
        }

    def update_anomaly_counters(self, transaction: TransactionRequest) -> None:
        """
        Update anomaly tracking counters after a transaction.

        Tracks:
        - Countries used in last 24 hours (for geographic anomalies)
        - Merchants used in last hour (for rapid merchant changes)
        - All-time merchant history (for new merchant detection)

        Call this AFTER scoring to prevent current transaction from
        affecting its own anomaly features.
        """
        user_id = transaction.user_id
        current_country = transaction.country
        current_merchant = transaction.merchant_id

        # Update countries set (24-hour window)
        countries_key = FeatureKeys.user_countries_24h(user_id)
        countries_set = self.feature_store.get(countries_key, default=set())
        if not isinstance(countries_set, set):
            countries_set = set()
        countries_set.add(current_country)
        self.feature_store.set(
            countries_key,
            countries_set,
            ttl_seconds=24 * 3600  # 24 hours
        )

        # Update merchants set (1-hour window)
        merchants_key = FeatureKeys.user_merchants_1h(user_id)
        merchants_set = self.feature_store.get(merchants_key, default=set())
        if not isinstance(merchants_set, set):
            merchants_set = set()
        merchants_set.add(current_merchant)
        self.feature_store.set(
            merchants_key,
            merchants_set,
            ttl_seconds=3600  # 1 hour
        )

        # Update all-time merchant history (30-day window for consistency)
        merchant_history_key = FeatureKeys.user_merchant_history(user_id)
        merchant_history = self.feature_store.get(merchant_history_key, default=set())
        if not isinstance(merchant_history, set):
            merchant_history = set()
        merchant_history.add(current_merchant)
        self.feature_store.set(
            merchant_history_key,
            merchant_history,
            ttl_seconds=30 * 24 * 3600  # 30 days
        )

        logger.debug(
            f"Updated anomaly counters for user {user_id}: "
            f"countries={len(countries_set)}, merchants_1h={len(merchants_set)}, "
            f"total_merchants={len(merchant_history)}"
        )


_anomaly_service = None


def get_anomaly_service() -> AnomalyService:
    """Get global AnomalyService instance."""
    global _anomaly_service
    if _anomaly_service is None:
        _anomaly_service = AnomalyService()
    return _anomaly_service
