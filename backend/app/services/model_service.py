"""XGBoost model service for fraud detection with SHAP explanations."""

import logging
import time
from pathlib import Path
from typing import Optional, Dict, Any, List

import joblib
import numpy as np
import pandas as pd
from xgboost import XGBClassifier
import shap

from app.models.schemas import TransactionRequest
from app.services.velocity_service import get_velocity_service
from app.services.behavioral_service import get_behavioral_service
from app.services.anomaly_service import get_anomaly_service

logger = logging.getLogger(__name__)


class ModelService:
    """Loads XGBoost model and generates fraud predictions with SHAP explanations."""

    def __init__(self, model_path: Optional[str] = None):
        """Initialize with optional custom model path."""
        self.model: Optional[XGBClassifier] = None
        self.model_metadata: Optional[Dict[str, Any]] = None
        self.feature_names: List[str] = []
        self.is_loaded = False
        self.shap_explainer: Optional[shap.TreeExplainer] = None

        if model_path is None:
            backend_dir = Path(__file__).parent.parent.parent
            model_path = backend_dir.parent / "ml" / "models" / "fraud_detector_v1.joblib"

        self.model_path = Path(model_path)
        logger.info(f"ModelService initialized with model path: {self.model_path}")

    def load_model(self) -> None:
        """Load XGBoost model and initialize SHAP TreeExplainer."""
        try:
            start_time = time.time()

            if not self.model_path.exists():
                raise FileNotFoundError(
                    f"Model file not found at {self.model_path}. "
                    "Run ml/training/train_model.py first."
                )

            logger.info(f"Loading model from {self.model_path}")
            artifact = joblib.load(self.model_path)

            self.model = artifact["model"]
            self.model_metadata = artifact["metadata"]
            self.feature_names = self.model_metadata["features"]
            load_time = (time.time() - start_time) * 1000

            if not isinstance(self.model, XGBClassifier):
                raise ValueError("Loaded model is not an XGBClassifier")

            self.is_loaded = True

            # Initialize SHAP explainer (one-time ~36ms cost)
            logger.info("Initializing SHAP TreeExplainer...")
            shap_start_time = time.time()
            self.shap_explainer = shap.TreeExplainer(self.model)
            shap_init_time = (time.time() - shap_start_time) * 1000

            logger.info(
                f"✓ Model loaded in {load_time:.2f}ms\n"
                f"  Version: {self.model_metadata.get('version', 'unknown')}\n"
                f"  Training date: {self.model_metadata.get('training_date', 'unknown')}\n"
                f"  Features: {len(self.feature_names)}\n"
                f"  Precision: {self.model_metadata.get('test_precision', 0):.3f}\n"
                f"  Recall: {self.model_metadata.get('test_recall', 0):.3f}\n"
                f"✓ SHAP explainer initialized in {shap_init_time:.2f}ms"
            )

        except FileNotFoundError as e:
            logger.error(f"Model file not found: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to load model: {e}", exc_info=True)
            raise

    def extract_features(self, transaction: TransactionRequest) -> pd.DataFrame:
        """Transform transaction into 13 model features (matches training format)."""
        if not self.is_loaded:
            raise RuntimeError("Model not loaded. Call load_model() first.")

        try:
            # Get real-time velocity features from feature store
            velocity_service = get_velocity_service()
            velocity_features = velocity_service.calculate_velocity_features(transaction)

            # Get behavioral features (user spending profile)
            behavioral_service = get_behavioral_service()
            behavioral_features = behavioral_service.calculate_behavioral_features(transaction)

            # Get anomaly features (geographic and merchant patterns)
            anomaly_service = get_anomaly_service()
            anomaly_features = anomaly_service.calculate_anomaly_features(transaction)

            features = {
                "amount": float(transaction.amount),
                "amount_vs_avg_ratio": behavioral_features["amount_vs_avg_ratio"],
                "amount_sum_last10": velocity_features["amount_sum_last10"],
                "user_avg_amount": behavioral_features["user_avg_amount"],
                "txn_count_5min": velocity_features["txn_count_5min"],
                "txn_count_1hour": velocity_features["txn_count_1hour"],
                "hour_of_day": float(transaction.timestamp.hour),
                "day_of_week": float(transaction.timestamp.weekday()),
                "is_weekend": float(transaction.timestamp.weekday() >= 5),
                "is_night": float(transaction.timestamp.hour < 6 or transaction.timestamp.hour >= 22),
                "is_high_risk_category": self._is_high_risk_category(transaction.merchant_category),
                "is_foreign_country": self._is_foreign_country(transaction.country),
                "merchant_txn_count": velocity_features["merchant_txn_count"],
            }

            df = pd.DataFrame([features], columns=self.feature_names)

            missing_features = set(self.feature_names) - set(df.columns)
            if missing_features:
                raise ValueError(f"Missing required features: {missing_features}")

            return df

        except Exception as e:
            logger.error(f"Feature extraction failed: {e}", exc_info=True)
            raise ValueError(f"Failed to extract features: {e}")

    def predict(self, transaction: TransactionRequest) -> Dict[str, Any]:
        """Run fraud prediction, return score + inference time + version."""
        if not self.is_loaded:
            raise RuntimeError("Model not loaded. Call load_model() first.")

        try:
            start_time = time.time()

            features_df = self.extract_features(transaction)
            prediction_proba = self.model.predict_proba(features_df)[0, 1]  # Fraud probability
            inference_time = (time.time() - start_time) * 1000

            score = float(np.clip(prediction_proba, 0.0, 1.0))

            logger.debug(f"Prediction: score={score:.3f}, time={inference_time:.2f}ms")

            return {
                "score": round(score, 3),
                "inference_time_ms": round(inference_time, 2),
                "model_version": self.model_metadata.get("version", "unknown"),
                "features_used": len(self.feature_names),
            }

        except Exception as e:
            logger.error(f"Prediction failed: {e}", exc_info=True)
            raise

    def generate_shap_explanation(
        self,
        features_df: pd.DataFrame,
        top_n: int = 5
    ) -> List[Dict[str, Any]]:
        """Generate SHAP values for top N features (sorted by absolute contribution)."""
        if not self.is_loaded or self.shap_explainer is None:
            raise RuntimeError("SHAP explainer not initialized. Call load_model() first.")

        try:
            start_time = time.time()

            # Calculate SHAP values for fraud class
            shap_values = self.shap_explainer.shap_values(features_df)
            shap_values_single = shap_values[0] if len(shap_values.shape) > 1 else shap_values
            shap_time = (time.time() - start_time) * 1000

            explanations = []
            for i, feature_name in enumerate(self.feature_names):
                feature_value = float(features_df.iloc[0, i])
                shap_value = float(shap_values_single[i])

                # Positive SHAP → fraud, Negative SHAP → legitimate
                contribution = "fraud" if shap_value > 0 else "legitimate"

                explanations.append({
                    "feature_name": feature_name,
                    "feature_value": feature_value,
                    "shap_value": round(shap_value, 4),
                    "contribution": contribution,
                    "abs_shap_value": abs(shap_value)  # For sorting
                })

            # Sort by impact (largest absolute value first)
            explanations.sort(key=lambda x: x["abs_shap_value"], reverse=True)
            top_explanations = explanations[:top_n]

            # Clean up sorting helper
            for exp in top_explanations:
                del exp["abs_shap_value"]

            logger.debug(
                f"SHAP generated in {shap_time:.2f}ms, "
                f"top: {top_explanations[0]['feature_name']} ({top_explanations[0]['shap_value']:.4f})"
            )

            return top_explanations

        except Exception as e:
            logger.error(f"SHAP generation failed: {e}", exc_info=True)
            logger.warning("Returning empty SHAP explanation")
            return []  # Don't crash prediction on SHAP failure

    def get_model_info(self) -> Dict[str, Any]:
        """Return model metadata (version, metrics, features)."""
        if not self.is_loaded:
            return {"is_loaded": False, "error": "Model not loaded"}

        return {
            "is_loaded": True,
            "version": self.model_metadata.get("version", "unknown"),
            "training_date": self.model_metadata.get("training_date", "unknown"),
            "features": len(self.feature_names),
            "test_precision": self.model_metadata.get("test_precision", 0),
            "test_recall": self.model_metadata.get("test_recall", 0),
            "test_f1": self.model_metadata.get("test_f1", 0),
            "test_roc_auc": self.model_metadata.get("test_roc_auc", 0),
            "optimal_threshold": self.model_metadata.get("optimal_threshold", 0.5),
        }

    # ============================================================================
    # Feature engineering helpers
    # ============================================================================

    def _is_high_risk_category(self, category: str) -> float:
        """Return 1.0 if category in high-risk list, else 0.0."""
        high_risk = ["online_gambling", "crypto", "foreign_exchange", "money_transfer", "prepaid_cards"]
        return 1.0 if category.lower() in high_risk else 0.0

    def _is_foreign_country(self, country: str) -> float:
        """Return 1.0 if not US, else 0.0 (assumes US domestic)."""
        return 0.0 if country.upper() == "US" else 1.0


# Global singleton instance
model_service: Optional[ModelService] = None


def get_model_service() -> ModelService:
    """Get global ModelService instance (must be initialized first)."""
    if model_service is None:
        raise RuntimeError("Model service not initialized. Call initialize_model_service() at startup.")
    return model_service


def initialize_model_service(model_path: Optional[str] = None) -> None:
    """Initialize and load model (call once at startup)."""
    global model_service

    if model_service is not None:
        logger.warning("Model service already initialized")
        return

    logger.info("Initializing model service...")
    model_service = ModelService(model_path)
    model_service.load_model()
    logger.info("✓ Model service initialized")
