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
from app.services.velocity_service import get_velocity_service
from app.services.behavioral_service import get_behavioral_service
from app.services.anomaly_service import get_anomaly_service

logger = logging.getLogger(__name__)


class ScoringService:
    """Score transactions for fraud using ML model."""

    def __init__(self, use_ml_model: bool = True):
        """
        Initialize scoring service.

        Args:
            use_ml_model: If True, uses ML model. If False, uses placeholder logic.
        """
        self.use_ml_model = use_ml_model

        self.threshold_flag = 0.5
        self.threshold_decline = 0.9

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
        Score transaction for fraud risk.

        Args:
            transaction: Transaction to score
            request_id: Unique request identifier

        Returns:
            TransactionResponse with score, decision, and SHAP explanation
        """
        try:
            if self.use_ml_model:
                score, model_info, shap_explanation = self._score_with_ml_model(transaction)
            else:
                score = self._calculate_placeholder_score(transaction)
                model_info = {"model_version": "placeholder_v1.0"}
                shap_explanation = []

            decision = self._make_decision(score)

            transaction_id = self._generate_transaction_id(transaction, request_id)

            explanation = {
                "top_features": shap_explanation,
                "threshold": self.threshold_flag,
                "model_version": model_info.get("model_version", "unknown"),
                "explanation_type": "shap"
            }

            response = TransactionResponse(
                transaction_id=transaction_id,
                score=score,
                decision=decision,
                explanation=explanation,
                timestamp=datetime.utcnow(),
                processing_time_ms=None
            )

            try:
                velocity_service = get_velocity_service()
                velocity_service.update_velocity_counters(transaction)

                behavioral_service = get_behavioral_service()
                behavioral_service.update_user_profile(transaction)

                anomaly_service = get_anomaly_service()
                anomaly_service.update_anomaly_counters(transaction)
            except Exception as e:
                logger.error(f"Failed to update feature store: {e}", exc_info=True)

            return response

        except Exception as e:
            logger.error(f"Scoring failed: {e}", exc_info=True)
            return TransactionResponse(
                transaction_id=self._generate_transaction_id(transaction, request_id),
                score=0.5,
                decision="FLAG",
                explanation={
                    "error": "Model prediction failed, flagged for manual review",
                    "top_features": [],
                    "model_version": "error_fallback"
                },
                timestamp=datetime.utcnow(),
                processing_time_ms=None
            )

    def _score_with_ml_model(self, transaction: TransactionRequest) -> tuple[float, Dict[str, Any], list]:
        """
        Score transaction using ML model and generate SHAP explanations.

        Args:
            transaction: Transaction to score

        Returns:
            Tuple of (score, model_info, shap_explanation)
        """
        try:
            model_service = get_model_service()

            features_df = model_service.extract_features(transaction)

            prediction_result = model_service.predict(transaction)
            score = prediction_result["score"]

            shap_explanation = model_service.generate_shap_explanation(
                features_df=features_df,
                top_n=5
            )

            model_info = {
                "model_version": prediction_result.get("model_version", "unknown"),
                "inference_time_ms": prediction_result.get("inference_time_ms", 0),
                "features_used": prediction_result.get("features_used", 0),
            }

            logger.debug(
                f"ML model prediction: score={score:.3f}, "
                f"inference_time={model_info['inference_time_ms']:.2f}ms, "
                f"SHAP features={len(shap_explanation)}"
            )

            return score, model_info, shap_explanation

        except RuntimeError as e:
            logger.error(f"Model service error: {e}")
            raise
        except Exception as e:
            logger.error(f"Model prediction failed: {e}", exc_info=True)
            raise

    def _calculate_placeholder_score(self, transaction: TransactionRequest) -> float:
        """
        Calculate placeholder fraud score based on simple heuristics.

        Args:
            transaction: Transaction data

        Returns:
            Fraud score between 0.0 and 1.0
        """
        score = 0.0
        if transaction.amount > 1000:
            score += 0.3
        elif transaction.amount > 500:
            score += 0.2
        elif transaction.amount > 100:
            score += 0.1

        risky_categories = ["online_gambling", "crypto", "foreign_exchange"]
        medium_risk_categories = ["electronics", "jewelry", "travel"]

        if transaction.merchant_category in risky_categories:
            score += 0.4
        elif transaction.merchant_category in medium_risk_categories:
            score += 0.2

        user_seed = transaction.user_id % 100 / 100.0
        score += user_seed * 0.3

        score = max(0.0, min(1.0, score))

        return round(score, 2)

    def _make_decision(self, score: float) -> str:
        """
        Make decision based on fraud score.

        Args:
            score: Fraud probability (0.0 to 1.0)

        Returns:
            "ALLOW", "FLAG", or "DECLINE"
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
        """Generate unique transaction ID."""
        content = f"{transaction.user_id}_{transaction.amount}_{transaction.merchant_id}_{request_id}"
        hash_value = hashlib.sha256(content.encode()).hexdigest()[:12]
        return f"txn_{hash_value}"

    def _generate_placeholder_explanation(
        self,
        transaction: TransactionRequest,
        score: float
    ) -> Dict[str, Any]:
        """Generate placeholder SHAP-style explanation."""
        top_features = []
        if transaction.amount > 500:
            top_features.append({
                "feature_name": "transaction_amount",
                "feature_value": transaction.amount,
                "shap_value": round(0.3 * score, 3),
                "contribution": "fraud"
            })

        if transaction.merchant_category:
            top_features.append({
                "feature_name": "merchant_category",
                "feature_value": transaction.merchant_category,
                "shap_value": round(0.2 * score, 3),
                "contribution": "fraud" if score > 0.5 else "legitimate"
            })

        top_features.append({
            "feature_name": "user_velocity_5min",
            "feature_value": 1.0,
            "shap_value": round(0.1 * score, 3),
            "contribution": "legitimate"
        })

        if transaction.country:
            risky_countries = ["NG", "RU", "CN"]
            is_risky = transaction.country in risky_countries

            top_features.append({
                "feature_name": "country_risk",
                "feature_value": transaction.country,
                "shap_value": round((0.2 if is_risky else -0.1) * score, 3),
                "contribution": "fraud" if is_risky else "legitimate"
            })

        if transaction.payment_method:
            top_features.append({
                "feature_name": "payment_method",
                "feature_value": transaction.payment_method,
                "shap_value": round(0.05 * score, 3),
                "contribution": "legitimate"
            })

        top_features.sort(key=lambda x: abs(x["shap_value"]), reverse=True)
        top_features = top_features[:5]

        return {
            "top_features": top_features,
            "threshold": self.threshold_flag,
            "model_version": "placeholder_v1.0",
            "explanation_type": "mock_shap"
        }
