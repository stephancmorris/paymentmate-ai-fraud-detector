"""
Scoring service for fraud detection.
Implements the core logic for scoring transactions using ML model.
"""

import logging
import hashlib
from datetime import datetime
from typing import Dict, Any

from app.models.schemas import TransactionRequest, TransactionResponse
from app.services.model_service import get_model_service

logger = logging.getLogger(__name__)


class ScoringService:
    """
    Service for scoring transactions for fraud using ML model.

    This service uses the trained XGBoost model to generate fraud scores
    and make decisions based on configurable thresholds.
    """

    def __init__(self, use_ml_model: bool = True):
        """
        Initialize the scoring service.

        Args:
            use_ml_model: If True, uses ML model for scoring. If False, uses placeholder logic.
        """
        self.use_ml_model = use_ml_model

        # Decision thresholds (from model training)
        self.threshold_flag = 0.5  # Default threshold from training
        self.threshold_decline = 0.9  # Very high confidence for auto-decline

        # Alternative: Use F1-optimal threshold from model metadata
        # self.threshold_flag = 0.737  # F1-optimal from training report

        if self.use_ml_model:
            logger.info(
                f"ScoringService initialized with ML model\n"
                f"  FLAG threshold: {self.threshold_flag}\n"
                f"  DECLINE threshold: {self.threshold_decline}"
            )
        else:
            logger.info("ScoringService initialized with placeholder logic (ML disabled)")

    async def score_transaction(
        self,
        transaction: TransactionRequest,
        request_id: str
    ) -> TransactionResponse:
        """
        Score a transaction for fraud risk using ML model.

        This method:
        1. Uses the trained XGBoost model to predict fraud probability
        2. Makes a decision based on configured thresholds
        3. Generates explanations (placeholder until SHAP integration in Story 2.4)

        Args:
            transaction: The transaction to score
            request_id: Unique request identifier

        Returns:
            TransactionResponse with score, decision, and explanation
        """
        try:
            # Use ML model for scoring
            if self.use_ml_model:
                score, model_info = self._score_with_ml_model(transaction)
            else:
                # Fallback to placeholder logic if ML is disabled
                score = self._calculate_placeholder_score(transaction)
                model_info = {"model_version": "placeholder_v1.0"}

            # Determine decision based on thresholds
            decision = self._make_decision(score)

            # Generate transaction ID
            transaction_id = self._generate_transaction_id(transaction, request_id)

            # Generate explanation (placeholder until Story 2.4 - SHAP integration)
            explanation = self._generate_placeholder_explanation(transaction, score)
            explanation["model_version"] = model_info.get("model_version", "unknown")

            return TransactionResponse(
                transaction_id=transaction_id,
                score=score,
                decision=decision,
                explanation=explanation,
                timestamp=datetime.utcnow(),
                processing_time_ms=None  # Will be set by the endpoint
            )

        except Exception as e:
            logger.error(f"Scoring failed: {e}", exc_info=True)
            # Fallback to safe decision on error
            return TransactionResponse(
                transaction_id=self._generate_transaction_id(transaction, request_id),
                score=0.5,  # Neutral score on error
                decision="FLAG",  # Conservative: flag for manual review on error
                explanation={
                    "error": "Model prediction failed, flagged for manual review",
                    "top_features": [],
                    "model_version": "error_fallback"
                },
                timestamp=datetime.utcnow(),
                processing_time_ms=None
            )

    def _score_with_ml_model(self, transaction: TransactionRequest) -> tuple[float, Dict[str, Any]]:
        """
        Score a transaction using the ML model.

        Args:
            transaction: The transaction to score

        Returns:
            Tuple of (score, model_info)

        Raises:
            Exception: If model prediction fails
        """
        try:
            model_service = get_model_service()
            prediction_result = model_service.predict(transaction)

            score = prediction_result["score"]
            model_info = {
                "model_version": prediction_result.get("model_version", "unknown"),
                "inference_time_ms": prediction_result.get("inference_time_ms", 0),
                "features_used": prediction_result.get("features_used", 0),
            }

            logger.debug(
                f"ML model prediction: score={score:.3f}, "
                f"inference_time={model_info['inference_time_ms']:.2f}ms"
            )

            return score, model_info

        except RuntimeError as e:
            logger.error(f"Model service error: {e}")
            raise
        except Exception as e:
            logger.error(f"Model prediction failed: {e}", exc_info=True)
            raise

    def _calculate_placeholder_score(self, transaction: TransactionRequest) -> float:
        """
        Calculate a placeholder fraud score based on simple heuristics.

        This uses rule-based logic to simulate fraud scoring until the
        ML model is integrated:
        - High amounts are more suspicious
        - Certain merchant categories are riskier
        - Add some randomness to simulate real-world variance

        Args:
            transaction: The transaction data

        Returns:
            Fraud score between 0.0 and 1.0
        """
        score = 0.0

        # Base score from amount (higher amounts = higher risk)
        if transaction.amount > 1000:
            score += 0.3
        elif transaction.amount > 500:
            score += 0.2
        elif transaction.amount > 100:
            score += 0.1

        # Merchant category risk
        risky_categories = ["online_gambling", "crypto", "foreign_exchange"]
        medium_risk_categories = ["electronics", "jewelry", "travel"]

        if transaction.merchant_category in risky_categories:
            score += 0.4
        elif transaction.merchant_category in medium_risk_categories:
            score += 0.2

        # Add some deterministic "randomness" based on user_id
        # This ensures the same user gets consistent scores
        user_seed = transaction.user_id % 100 / 100.0
        score += user_seed * 0.3

        # Ensure score is in valid range [0, 1]
        score = max(0.0, min(1.0, score))

        # Round to 2 decimal places
        return round(score, 2)

    def _make_decision(self, score: float) -> str:
        """
        Make a decision based on the fraud score.

        Args:
            score: Fraud probability score (0.0 to 1.0)

        Returns:
            Decision: "ALLOW", "FLAG", or "DECLINE"
        """
        if score >= self.threshold_decline:
            return "DECLINE"
        elif score >= self.threshold_flag:
            return "FLAG"
        else:
            return "ALLOW"

    def _generate_transaction_id(
        self,
        transaction: TransactionRequest,
        request_id: str
    ) -> str:
        """
        Generate a unique transaction ID.

        Args:
            transaction: Transaction data
            request_id: Request ID

        Returns:
            Unique transaction identifier
        """
        # Create a hash-based ID from transaction attributes
        content = f"{transaction.user_id}_{transaction.amount}_{transaction.merchant_id}_{request_id}"
        hash_value = hashlib.sha256(content.encode()).hexdigest()[:12]
        return f"txn_{hash_value}"

    def _generate_placeholder_explanation(
        self,
        transaction: TransactionRequest,
        score: float
    ) -> Dict[str, Any]:
        """
        Generate a placeholder SHAP-style explanation.

        This creates a mock explanation structure that will be replaced
        with actual SHAP values when the ML model is integrated.

        Args:
            transaction: Transaction data
            score: Calculated fraud score

        Returns:
            Explanation dictionary with top features
        """
        # Create placeholder feature explanations
        top_features = []

        # Amount feature
        if transaction.amount > 500:
            top_features.append({
                "feature_name": "transaction_amount",
                "feature_value": transaction.amount,
                "shap_value": round(0.3 * score, 3),
                "contribution": "fraud"
            })

        # Merchant category feature
        if transaction.merchant_category:
            top_features.append({
                "feature_name": "merchant_category",
                "feature_value": transaction.merchant_category,
                "shap_value": round(0.2 * score, 3),
                "contribution": "fraud" if score > 0.5 else "legitimate"
            })

        # User history feature (placeholder)
        top_features.append({
            "feature_name": "user_velocity_5min",
            "feature_value": 1.0,  # Placeholder - would come from feature store
            "shap_value": round(0.1 * score, 3),
            "contribution": "legitimate"
        })

        # Country risk feature
        if transaction.country:
            risky_countries = ["NG", "RU", "CN"]  # Example high-risk countries
            is_risky = transaction.country in risky_countries

            top_features.append({
                "feature_name": "country_risk",
                "feature_value": transaction.country,
                "shap_value": round((0.2 if is_risky else -0.1) * score, 3),
                "contribution": "fraud" if is_risky else "legitimate"
            })

        # Payment method feature
        if transaction.payment_method:
            top_features.append({
                "feature_name": "payment_method",
                "feature_value": transaction.payment_method,
                "shap_value": round(0.05 * score, 3),
                "contribution": "legitimate"
            })

        # Sort by absolute SHAP value and take top 5
        top_features.sort(key=lambda x: abs(x["shap_value"]), reverse=True)
        top_features = top_features[:5]

        return {
            "top_features": top_features,
            "threshold": self.threshold_flag,
            "model_version": "placeholder_v1.0",
            "explanation_type": "mock_shap"
        }
