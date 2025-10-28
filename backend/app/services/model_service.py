"""
Model loading and inference service for fraud detection.

This service handles:
- Loading the trained XGBoost model at startup
- Model inference for transactions
- Feature extraction and transformation
- Error handling for model failures
"""

import logging
import time
from pathlib import Path
from typing import Optional, Dict, Any, List

import joblib
import numpy as np
import pandas as pd
from xgboost import XGBClassifier

from app.models.schemas import TransactionRequest

logger = logging.getLogger(__name__)


class ModelService:
    """
    Service for loading and executing the XGBoost fraud detection model.

    This service loads the trained model at application startup and provides
    methods for making predictions on transactions.
    """

    def __init__(self, model_path: Optional[str] = None):
        """
        Initialize the model service.

        Args:
            model_path: Path to the trained model file. If None, uses default path.
        """
        self.model: Optional[XGBClassifier] = None
        self.model_metadata: Optional[Dict[str, Any]] = None
        self.feature_names: List[str] = []
        self.is_loaded = False

        # Default model path (relative to backend directory)
        if model_path is None:
            backend_dir = Path(__file__).parent.parent.parent
            model_path = backend_dir.parent / "ml" / "models" / "fraud_detector_v1.joblib"

        self.model_path = Path(model_path)

        logger.info(f"ModelService initialized with model path: {self.model_path}")

    def load_model(self) -> None:
        """
        Load the trained XGBoost model from disk.

        This method loads the model artifact which contains:
        - The trained XGBoost classifier
        - Model metadata (version, features, performance metrics)

        Raises:
            FileNotFoundError: If model file doesn't exist
            Exception: If model loading fails
        """
        try:
            start_time = time.time()

            if not self.model_path.exists():
                raise FileNotFoundError(
                    f"Model file not found at {self.model_path}. "
                    "Please train the model first (Story 2.2)."
                )

            logger.info(f"Loading model from {self.model_path}")

            # Load model artifact
            artifact = joblib.load(self.model_path)

            # Extract model and metadata
            self.model = artifact["model"]
            self.model_metadata = artifact["metadata"]
            self.feature_names = self.model_metadata["features"]

            load_time = (time.time() - start_time) * 1000  # Convert to ms

            # Validate model
            if not isinstance(self.model, XGBClassifier):
                raise ValueError("Loaded model is not an XGBClassifier")

            self.is_loaded = True

            logger.info(
                f"✓ Model loaded successfully in {load_time:.2f}ms\n"
                f"  Version: {self.model_metadata.get('version', 'unknown')}\n"
                f"  Training date: {self.model_metadata.get('training_date', 'unknown')}\n"
                f"  Features: {len(self.feature_names)}\n"
                f"  Test precision: {self.model_metadata.get('test_precision', 0):.3f}\n"
                f"  Test recall: {self.model_metadata.get('test_recall', 0):.3f}\n"
                f"  Optimal threshold: {self.model_metadata.get('optimal_threshold', 0.5):.3f}"
            )

        except FileNotFoundError as e:
            logger.error(f"Model file not found: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to load model: {e}", exc_info=True)
            raise

    def extract_features(self, transaction: TransactionRequest) -> pd.DataFrame:
        """
        Extract features from a transaction request for model inference.

        This method transforms a TransactionRequest into the feature format
        expected by the XGBoost model. The features must match the order and
        format used during training.

        Args:
            transaction: The transaction to extract features from

        Returns:
            DataFrame with a single row containing all required features

        Raises:
            ValueError: If required features cannot be extracted
        """
        if not self.is_loaded:
            raise RuntimeError("Model not loaded. Call load_model() first.")

        try:
            # Note: In a full implementation, these features would come from:
            # 1. The transaction request (amount, etc.)
            # 2. A feature store (velocity features, user history)
            # 3. Real-time calculations (ratios, aggregations)
            #
            # For now, we'll create placeholder features that match the training format.
            # In Story 3.x, these will be replaced with real feature engineering.

            features = {
                # Amount features
                "amount": float(transaction.amount),
                "amount_vs_avg_ratio": self._calculate_amount_ratio(transaction),
                "amount_sum_last10": float(transaction.amount),  # Placeholder
                "user_avg_amount": 100.0,  # Placeholder - would come from feature store

                # Velocity features (would come from feature store in Story 3.2)
                "txn_count_5min": 0.0,  # Placeholder
                "txn_count_1hour": 0.0,  # Placeholder

                # Temporal features
                "hour_of_day": float(transaction.timestamp.hour),
                "day_of_week": float(transaction.timestamp.weekday()),
                "is_weekend": float(transaction.timestamp.weekday() >= 5),
                "is_night": float(transaction.timestamp.hour < 6 or transaction.timestamp.hour >= 22),

                # Categorical features
                "is_high_risk_category": self._is_high_risk_category(transaction.merchant_category),
                "is_foreign_country": self._is_foreign_country(transaction.country),
                "merchant_txn_count": 1.0,  # Placeholder - would come from feature store
            }

            # Create DataFrame with features in correct order
            df = pd.DataFrame([features], columns=self.feature_names)

            # Validate all features are present
            missing_features = set(self.feature_names) - set(df.columns)
            if missing_features:
                raise ValueError(f"Missing required features: {missing_features}")

            return df

        except Exception as e:
            logger.error(f"Feature extraction failed: {e}", exc_info=True)
            raise ValueError(f"Failed to extract features: {e}")

    def predict(self, transaction: TransactionRequest) -> Dict[str, Any]:
        """
        Make a fraud prediction for a transaction.

        This method:
        1. Extracts features from the transaction
        2. Runs model inference
        3. Returns the fraud probability score

        Args:
            transaction: The transaction to score

        Returns:
            Dictionary containing:
            - score: Fraud probability (0.0 to 1.0)
            - inference_time_ms: Time taken for inference
            - model_version: Version of the model used

        Raises:
            RuntimeError: If model is not loaded
            Exception: If prediction fails
        """
        if not self.is_loaded:
            raise RuntimeError("Model not loaded. Call load_model() first.")

        try:
            start_time = time.time()

            # Extract features
            features_df = self.extract_features(transaction)

            # Make prediction (probability of fraud class)
            prediction_proba = self.model.predict_proba(features_df)[0, 1]

            inference_time = (time.time() - start_time) * 1000  # Convert to ms

            # Ensure score is in valid range
            score = float(np.clip(prediction_proba, 0.0, 1.0))

            logger.debug(
                f"Model prediction complete: score={score:.3f}, "
                f"inference_time={inference_time:.2f}ms"
            )

            return {
                "score": round(score, 3),
                "inference_time_ms": round(inference_time, 2),
                "model_version": self.model_metadata.get("version", "unknown"),
                "features_used": len(self.feature_names),
            }

        except Exception as e:
            logger.error(f"Model prediction failed: {e}", exc_info=True)
            raise

    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the loaded model.

        Returns:
            Dictionary containing model metadata
        """
        if not self.is_loaded:
            return {
                "is_loaded": False,
                "error": "Model not loaded"
            }

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

    # ========================================================================
    # Helper methods for feature engineering
    # ========================================================================

    def _calculate_amount_ratio(self, transaction: TransactionRequest) -> float:
        """
        Calculate transaction amount vs user average ratio.

        In a full implementation, this would fetch the user's historical
        average from a feature store. For now, we use a placeholder.

        Args:
            transaction: Transaction data

        Returns:
            Ratio of transaction amount to user average
        """
        # Placeholder: Use a fixed average of $100
        # In Story 3.3, this will be replaced with real user history
        user_avg = 100.0
        ratio = float(transaction.amount) / user_avg if user_avg > 0 else 1.0
        return ratio

    def _is_high_risk_category(self, category: str) -> float:
        """
        Check if merchant category is high-risk.

        Args:
            category: Merchant category code

        Returns:
            1.0 if high-risk, 0.0 otherwise
        """
        high_risk_categories = [
            "online_gambling",
            "crypto",
            "foreign_exchange",
            "money_transfer",
            "prepaid_cards"
        ]
        return 1.0 if category.lower() in high_risk_categories else 0.0

    def _is_foreign_country(self, country: str) -> float:
        """
        Check if transaction is from a foreign country.

        Args:
            country: ISO country code

        Returns:
            1.0 if foreign country, 0.0 if domestic (US)
        """
        # Assume US is domestic, all others are foreign
        # In a real system, this would be based on the user's home country
        return 0.0 if country.upper() == "US" else 1.0


# Global model service instance (will be initialized at startup)
model_service: Optional[ModelService] = None


def get_model_service() -> ModelService:
    """
    Get the global model service instance.

    Returns:
        ModelService instance

    Raises:
        RuntimeError: If model service is not initialized
    """
    if model_service is None:
        raise RuntimeError(
            "Model service not initialized. "
            "This should be initialized at application startup."
        )
    return model_service


def initialize_model_service(model_path: Optional[str] = None) -> None:
    """
    Initialize the global model service and load the model.

    This should be called once at application startup.

    Args:
        model_path: Optional path to model file
    """
    global model_service

    if model_service is not None:
        logger.warning("Model service already initialized")
        return

    logger.info("Initializing model service...")
    model_service = ModelService(model_path)
    model_service.load_model()
    logger.info("✓ Model service initialized successfully")
