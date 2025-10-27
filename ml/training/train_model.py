"""
XGBoost Fraud Detection Model Training Script

This script trains an XGBoost classifier on synthetic transaction data to detect fraud.
The model uses gradient boosting with class imbalance handling to achieve >70% precision and recall.

Usage:
    python train_model.py [--seed SEED] [--test-size RATIO] [--max-depth DEPTH]

Author: PaymentMate AI Team
Date: October 2025
"""

import argparse
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Tuple

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import xgboost as xgb
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_recall_curve,
    precision_recall_fscore_support,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)
from sklearn.model_selection import (
    StratifiedKFold,
    cross_validate,
    train_test_split,
)

# ============================================================================
# CONFIGURATION
# ============================================================================

# Paths
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
DATA_PATH = PROJECT_ROOT / "data" / "synthetic_transactions.csv"
MODEL_DIR = PROJECT_ROOT / "models"
MODEL_PATH = MODEL_DIR / "fraud_detector_v1.joblib"

# Training parameters
RANDOM_SEED = 42
TEST_SIZE = 0.2
CV_FOLDS = 5

# Feature columns (13 engineered features)
FEATURE_COLUMNS = [
    # Amount features
    "amount",
    "amount_vs_avg_ratio",
    "amount_sum_last10",
    "user_avg_amount",
    # Velocity features
    "txn_count_5min",
    "txn_count_1hour",
    # Temporal features
    "hour_of_day",
    "day_of_week",
    "is_weekend",
    "is_night",
    # Categorical features
    "is_high_risk_category",
    "is_foreign_country",
    "merchant_txn_count",
]

# Columns to exclude (non-predictive or data leakage)
EXCLUDE_COLUMNS = [
    "transaction_id",  # Identifier
    "user_id",  # Identifier
    "merchant_id",  # Identifier
    "timestamp",  # Already encoded as temporal features
    "merchant_category",  # Already encoded as is_high_risk_category
    "country",  # Already encoded as is_foreign_country
    "currency",  # Not predictive for fraud in this dataset
    "payment_method",  # Not used in engineered features
    "device_type",  # Not used in engineered features
    "fraud_type",  # Data leakage (only exists for fraud transactions)
]

# XGBoost hyperparameters
XGBOOST_PARAMS = {
    "max_depth": 6,
    "n_estimators": 100,
    "learning_rate": 0.1,
    "min_child_weight": 1,
    "gamma": 0,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "objective": "binary:logistic",
    "eval_metric": "auc",
    "n_jobs": -1,
    "random_state": RANDOM_SEED,
}

# Performance thresholds
MIN_PRECISION = 0.70
MIN_RECALL = 0.70
MIN_ROC_AUC = 0.80

# ============================================================================
# LOGGING SETUP
# ============================================================================


def setup_logging(verbose: bool = False) -> logging.Logger:
    """Configure logging for training script."""
    log_level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(SCRIPT_DIR / "training.log"),
        ],
    )
    return logging.getLogger(__name__)


# ============================================================================
# DATA LOADING
# ============================================================================


def load_data(data_path: Path) -> pd.DataFrame:
    """
    Load synthetic transaction data from CSV.

    Args:
        data_path: Path to synthetic_transactions.csv

    Returns:
        DataFrame with all transaction data
    """
    logger = logging.getLogger(__name__)
    logger.info(f"Loading data from {data_path}")

    if not data_path.exists():
        raise FileNotFoundError(f"Data file not found: {data_path}")

    df = pd.read_csv(data_path)
    logger.info(f"Loaded {len(df):,} transactions")
    logger.info(f"Fraud rate: {df['is_fraud'].mean():.2%}")
    logger.info(f"Columns: {list(df.columns)}")

    return df


def prepare_features(
    df: pd.DataFrame, feature_columns: list[str]
) -> Tuple[pd.DataFrame, pd.Series]:
    """
    Prepare feature matrix X and target vector y.

    Args:
        df: Raw transaction dataframe
        feature_columns: List of feature column names

    Returns:
        Tuple of (X, y) where X is feature matrix, y is target vector
    """
    logger = logging.getLogger(__name__)

    # Verify all feature columns exist
    missing_cols = set(feature_columns) - set(df.columns)
    if missing_cols:
        raise ValueError(f"Missing feature columns: {missing_cols}")

    # Extract features and target
    X = df[feature_columns].copy()
    y = df["is_fraud"].copy()

    logger.info(f"Feature matrix shape: {X.shape}")
    logger.info(f"Feature columns: {list(X.columns)}")
    logger.info(f"Target distribution: Fraud={y.sum():,} ({y.mean():.2%}), "
                f"Legitimate={(~y).sum():,} ({(~y).mean():.2%})")

    # Check for missing values
    missing_counts = X.isnull().sum()
    if missing_counts.sum() > 0:
        logger.warning(f"Missing values detected:\n{missing_counts[missing_counts > 0]}")

    return X, y


def split_data(
    X: pd.DataFrame, y: pd.Series, test_size: float = TEST_SIZE, random_state: int = RANDOM_SEED
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
    """
    Split data into stratified train/test sets.

    Args:
        X: Feature matrix
        y: Target vector
        test_size: Proportion of data for test set (default 0.2)
        random_state: Random seed for reproducibility

    Returns:
        Tuple of (X_train, X_test, y_train, y_test)
    """
    logger = logging.getLogger(__name__)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state, stratify=y
    )

    logger.info(f"Train set: {len(X_train):,} transactions ({len(X_train)/len(X):.1%})")
    logger.info(f"  Fraud rate: {y_train.mean():.2%}")
    logger.info(f"Test set: {len(X_test):,} transactions ({len(X_test)/len(X):.1%})")
    logger.info(f"  Fraud rate: {y_test.mean():.2%}")

    return X_train, X_test, y_train, y_test


# ============================================================================
# MODEL TRAINING
# ============================================================================


def calculate_scale_pos_weight(y_train: pd.Series) -> float:
    """
    Calculate scale_pos_weight for XGBoost to handle class imbalance.

    Args:
        y_train: Training target vector

    Returns:
        Ratio of negative to positive samples
    """
    fraud_count = y_train.sum()
    legitimate_count = len(y_train) - fraud_count
    scale_pos_weight = legitimate_count / fraud_count

    logger = logging.getLogger(__name__)
    logger.info(f"Class imbalance: {legitimate_count:,} legitimate / {fraud_count:,} fraud")
    logger.info(f"scale_pos_weight: {scale_pos_weight:.2f}")

    return scale_pos_weight


def create_model(scale_pos_weight: float, **kwargs) -> xgb.XGBClassifier:
    """
    Create XGBoost classifier with configured hyperparameters.

    Args:
        scale_pos_weight: Weight for positive class (fraud)
        **kwargs: Additional XGBoost parameters to override defaults

    Returns:
        Configured XGBoost classifier
    """
    params = XGBOOST_PARAMS.copy()
    params["scale_pos_weight"] = scale_pos_weight
    params.update(kwargs)

    model = xgb.XGBClassifier(**params)

    logger = logging.getLogger(__name__)
    logger.info("XGBoost configuration:")
    for key, value in params.items():
        logger.info(f"  {key}: {value}")

    return model


def cross_validate_model(
    model: xgb.XGBClassifier,
    X_train: pd.DataFrame,
    y_train: pd.Series,
    cv_folds: int = CV_FOLDS,
) -> Dict[str, np.ndarray]:
    """
    Perform stratified k-fold cross-validation.

    Args:
        model: XGBoost classifier
        X_train: Training features
        y_train: Training target
        cv_folds: Number of CV folds (default 5)

    Returns:
        Dictionary of CV results
    """
    logger = logging.getLogger(__name__)
    logger.info(f"Running {cv_folds}-fold cross-validation...")

    cv = StratifiedKFold(n_splits=cv_folds, shuffle=True, random_state=RANDOM_SEED)

    scoring = {
        "accuracy": "accuracy",
        "precision": "precision",
        "recall": "recall",
        "f1": "f1",
        "roc_auc": "roc_auc",
    }

    start_time = time.time()
    cv_results = cross_validate(
        model, X_train, y_train, cv=cv, scoring=scoring, n_jobs=-1, return_train_score=True
    )
    cv_time = time.time() - start_time

    logger.info(f"Cross-validation completed in {cv_time:.2f} seconds")
    logger.info(f"Cross-Validation Results ({cv_folds}-fold):")
    logger.info(f"  Accuracy:  {cv_results['test_accuracy'].mean():.3f} ± {cv_results['test_accuracy'].std():.3f}")
    logger.info(f"  Precision: {cv_results['test_precision'].mean():.3f} ± {cv_results['test_precision'].std():.3f}")
    logger.info(f"  Recall:    {cv_results['test_recall'].mean():.3f} ± {cv_results['test_recall'].std():.3f}")
    logger.info(f"  F1 Score:  {cv_results['test_f1'].mean():.3f} ± {cv_results['test_f1'].std():.3f}")
    logger.info(f"  ROC-AUC:   {cv_results['test_roc_auc'].mean():.3f} ± {cv_results['test_roc_auc'].std():.3f}")

    return cv_results


def train_model(
    model: xgb.XGBClassifier,
    X_train: pd.DataFrame,
    y_train: pd.Series,
    X_test: pd.DataFrame,
    y_test: pd.Series,
) -> xgb.XGBClassifier:
    """
    Train XGBoost model on full training set.

    Args:
        model: XGBoost classifier
        X_train: Training features
        y_train: Training target
        X_test: Test features (for early stopping monitoring)
        y_test: Test target (for early stopping monitoring)

    Returns:
        Trained XGBoost model
    """
    logger = logging.getLogger(__name__)
    logger.info("Training XGBoost model on full training set...")

    start_time = time.time()

    model.fit(
        X_train,
        y_train,
        eval_set=[(X_train, y_train), (X_test, y_test)],
        verbose=False,
    )

    training_time = time.time() - start_time
    logger.info(f"Training completed in {training_time:.2f} seconds")

    return model


# ============================================================================
# MODEL EVALUATION
# ============================================================================


def evaluate_model(
    model: xgb.XGBClassifier,
    X_test: pd.DataFrame,
    y_test: pd.Series,
) -> Dict[str, float]:
    """
    Evaluate trained model on test set.

    Args:
        model: Trained XGBoost classifier
        X_test: Test features
        y_test: Test target

    Returns:
        Dictionary of evaluation metrics
    """
    logger = logging.getLogger(__name__)
    logger.info("Evaluating model on test set...")

    # Make predictions
    y_pred = model.predict(X_test)
    y_pred_proba = model.predict_proba(X_test)[:, 1]

    # Calculate metrics
    accuracy = accuracy_score(y_test, y_pred)
    precision, recall, f1, _ = precision_recall_fscore_support(
        y_test, y_pred, average="binary", pos_label=1
    )
    roc_auc = roc_auc_score(y_test, y_pred_proba)

    metrics = {
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "roc_auc": roc_auc,
    }

    # Log results
    logger.info("Test Set Performance:")
    logger.info(f"  Accuracy:  {accuracy:.3f}")
    logger.info(f"  Precision: {precision:.3f} {'✓' if precision >= MIN_PRECISION else '✗ BELOW TARGET'}")
    logger.info(f"  Recall:    {recall:.3f} {'✓' if recall >= MIN_RECALL else '✗ BELOW TARGET'}")
    logger.info(f"  F1 Score:  {f1:.3f}")
    logger.info(f"  ROC-AUC:   {roc_auc:.3f} {'✓' if roc_auc >= MIN_ROC_AUC else '✗ BELOW TARGET'}")

    # Classification report
    logger.info("\nClassification Report:")
    report = classification_report(y_test, y_pred, target_names=["Legitimate", "Fraud"])
    logger.info(f"\n{report}")

    return metrics


def generate_confusion_matrix(
    y_test: pd.Series,
    y_pred: np.ndarray,
    output_path: Path,
) -> Tuple[int, int, int, int]:
    """
    Generate and visualize confusion matrix.

    Args:
        y_test: True labels
        y_pred: Predicted labels
        output_path: Path to save confusion matrix plot

    Returns:
        Tuple of (tn, fp, fn, tp)
    """
    logger = logging.getLogger(__name__)

    # Generate confusion matrix
    cm = confusion_matrix(y_test, y_pred)
    tn, fp, fn, tp = cm.ravel()

    # Calculate rates
    fpr = fp / (fp + tn) if (fp + tn) > 0 else 0
    fnr = fn / (fn + tp) if (fn + tp) > 0 else 0

    logger.info("\nConfusion Matrix:")
    logger.info(f"  True Negatives:  {tn:,}")
    logger.info(f"  False Positives: {fp:,} (FPR: {fpr:.2%})")
    logger.info(f"  False Negatives: {fn:,} (FNR: {fnr:.2%})")
    logger.info(f"  True Positives:  {tp:,}")

    # Visualize
    plt.figure(figsize=(8, 6))
    sns.heatmap(
        cm,
        annot=True,
        fmt="d",
        cmap="Blues",
        xticklabels=["Legitimate", "Fraud"],
        yticklabels=["Legitimate", "Fraud"],
        cbar=True,
    )
    plt.title("Confusion Matrix - Test Set", fontsize=14, fontweight="bold")
    plt.ylabel("Actual", fontsize=12)
    plt.xlabel("Predicted", fontsize=12)
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    logger.info(f"Confusion matrix saved to {output_path}")
    plt.close()

    return tn, fp, fn, tp


def optimize_threshold(
    y_test: pd.Series,
    y_pred_proba: np.ndarray,
    output_path: Path,
) -> float:
    """
    Optimize decision threshold using precision-recall curve.

    Args:
        y_test: True labels
        y_pred_proba: Predicted probabilities
        output_path: Path to save precision-recall curve

    Returns:
        Optimal threshold (F1-optimal)
    """
    logger = logging.getLogger(__name__)
    logger.info("\nOptimizing decision threshold...")

    # Calculate precision-recall curve
    precisions, recalls, thresholds = precision_recall_curve(y_test, y_pred_proba)

    # Test specific thresholds
    test_thresholds = [0.3, 0.4, 0.5, 0.6, 0.7]
    logger.info("Threshold Analysis:")
    for threshold in test_thresholds:
        y_pred_threshold = (y_pred_proba >= threshold).astype(int)
        precision = precision_score(y_test, y_pred_threshold)
        recall = recall_score(y_test, y_pred_threshold)
        f1 = f1_score(y_test, y_pred_threshold)
        logger.info(
            f"  Threshold {threshold:.1f}: "
            f"Precision={precision:.3f}, Recall={recall:.3f}, F1={f1:.3f}"
        )

    # Find F1-optimal threshold
    f1_scores = 2 * (precisions * recalls) / (precisions + recalls + 1e-10)
    optimal_idx = np.argmax(f1_scores)
    optimal_threshold = thresholds[optimal_idx] if optimal_idx < len(thresholds) else 0.5

    logger.info(f"\nRecommended threshold (F1-optimal): {optimal_threshold:.3f}")
    logger.info(f"  Precision: {precisions[optimal_idx]:.3f}")
    logger.info(f"  Recall: {recalls[optimal_idx]:.3f}")
    logger.info(f"  F1 Score: {f1_scores[optimal_idx]:.3f}")

    # Plot precision-recall curve
    plt.figure(figsize=(10, 6))
    plt.plot(recalls, precisions, linewidth=2, label="Precision-Recall Curve")
    plt.scatter(
        [recalls[optimal_idx]],
        [precisions[optimal_idx]],
        color="red",
        s=100,
        zorder=5,
        label=f"Optimal Threshold ({optimal_threshold:.3f})",
    )
    plt.xlabel("Recall", fontsize=12)
    plt.ylabel("Precision", fontsize=12)
    plt.title("Precision-Recall Curve", fontsize=14, fontweight="bold")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    logger.info(f"Precision-recall curve saved to {output_path}")
    plt.close()

    return optimal_threshold


def analyze_feature_importance(
    model: xgb.XGBClassifier,
    feature_columns: list[str],
    output_path: Path,
) -> pd.DataFrame:
    """
    Analyze and visualize feature importance.

    Args:
        model: Trained XGBoost model
        feature_columns: List of feature names
        output_path: Path to save feature importance plot

    Returns:
        DataFrame of feature importance sorted by importance
    """
    logger = logging.getLogger(__name__)
    logger.info("\nAnalyzing feature importance...")

    # Get feature importance
    importance = model.feature_importances_
    feature_importance = pd.DataFrame(
        {"feature": feature_columns, "importance": importance}
    ).sort_values("importance", ascending=False)

    logger.info("Top 10 Most Important Features:")
    for idx, row in feature_importance.head(10).iterrows():
        logger.info(f"  {row['feature']:30s}: {row['importance']:.4f}")

    # Visualize
    plt.figure(figsize=(10, 8))
    top_features = feature_importance.head(10)
    plt.barh(range(len(top_features)), top_features["importance"], color="steelblue")
    plt.yticks(range(len(top_features)), top_features["feature"])
    plt.xlabel("Feature Importance (Gain)", fontsize=12)
    plt.title("Top 10 Most Important Features for Fraud Detection", fontsize=14, fontweight="bold")
    plt.gca().invert_yaxis()
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    logger.info(f"Feature importance plot saved to {output_path}")
    plt.close()

    return feature_importance


# ============================================================================
# MODEL PERSISTENCE
# ============================================================================


def save_model(
    model: xgb.XGBClassifier,
    metrics: Dict[str, float],
    feature_columns: list[str],
    optimal_threshold: float,
    scale_pos_weight: float,
    output_path: Path,
) -> None:
    """
    Save trained model with metadata.

    Args:
        model: Trained XGBoost model
        metrics: Evaluation metrics dictionary
        feature_columns: List of feature names
        optimal_threshold: Optimal decision threshold
        scale_pos_weight: Class imbalance weight used
        output_path: Path to save model
    """
    logger = logging.getLogger(__name__)

    # Create model artifact with metadata
    model_artifact = {
        "model": model,
        "metadata": {
            "version": "1.0",
            "training_date": datetime.now().isoformat(),
            "features": feature_columns,
            "n_features": len(feature_columns),
            "test_accuracy": metrics["accuracy"],
            "test_precision": metrics["precision"],
            "test_recall": metrics["recall"],
            "test_f1": metrics["f1"],
            "test_roc_auc": metrics["roc_auc"],
            "optimal_threshold": optimal_threshold,
            "scale_pos_weight": scale_pos_weight,
            "xgboost_params": XGBOOST_PARAMS,
        },
    }

    # Save to disk
    output_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model_artifact, output_path)

    file_size_kb = output_path.stat().st_size / 1024
    logger.info(f"\n✓ Model saved to: {output_path}")
    logger.info(f"  File size: {file_size_kb:.1f} KB")


def load_and_test_model(model_path: Path, X_test: pd.DataFrame) -> None:
    """
    Test loading saved model and making predictions.

    Args:
        model_path: Path to saved model
        X_test: Test features for inference test
    """
    logger = logging.getLogger(__name__)
    logger.info("\nTesting model loading and inference...")

    # Load model
    loaded_artifact = joblib.load(model_path)
    loaded_model = loaded_artifact["model"]
    loaded_metadata = loaded_artifact["metadata"]

    logger.info("✓ Model loaded successfully")
    logger.info(f"  Version: {loaded_metadata['version']}")
    logger.info(f"  Training date: {loaded_metadata['training_date']}")
    logger.info(f"  Features: {loaded_metadata['n_features']}")

    # Test inference on small batch
    sample_size = min(5, len(X_test))
    X_sample = X_test.iloc[:sample_size]

    start_time = time.time()
    predictions = loaded_model.predict_proba(X_sample)[:, 1]
    inference_time = (time.time() - start_time) / sample_size * 1000  # ms per transaction

    logger.info(f"✓ Inference test passed")
    logger.info(f"  Sample predictions: {predictions}")
    logger.info(f"  Inference time: {inference_time:.3f}ms per transaction")

    # Validate predictions are in valid range
    assert all((predictions >= 0) & (predictions <= 1)), "Invalid prediction range"
    logger.info("✓ All predictions in valid range [0, 1]")


# ============================================================================
# MAIN SCRIPT
# ============================================================================


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Train XGBoost fraud detection model")
    parser.add_argument("--seed", type=int, default=RANDOM_SEED, help="Random seed")
    parser.add_argument("--test-size", type=float, default=TEST_SIZE, help="Test set ratio")
    parser.add_argument("--max-depth", type=int, default=6, help="XGBoost max depth")
    parser.add_argument("--cv-folds", type=int, default=CV_FOLDS, help="CV folds")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    return parser.parse_args()


def main():
    """Main training pipeline."""
    # Parse arguments
    args = parse_args()

    # Setup logging
    logger = setup_logging(verbose=args.verbose)
    logger.info("=" * 80)
    logger.info("XGBoost Fraud Detection Model Training")
    logger.info("=" * 80)

    try:
        # Step 1: Load and prepare data
        df = load_data(DATA_PATH)
        X, y = prepare_features(df, FEATURE_COLUMNS)
        X_train, X_test, y_train, y_test = split_data(X, y, test_size=args.test_size, random_state=args.seed)

        # Step 2: Configure model
        scale_pos_weight = calculate_scale_pos_weight(y_train)
        model = create_model(scale_pos_weight, max_depth=args.max_depth, random_state=args.seed)

        # Step 3: Cross-validation
        cv_results = cross_validate_model(model, X_train, y_train, cv_folds=args.cv_folds)

        # Step 4: Train on full training set
        model = train_model(model, X_train, y_train, X_test, y_test)

        # Step 5: Evaluate on test set
        metrics = evaluate_model(model, X_test, y_test)

        # Step 6: Generate confusion matrix
        y_pred = model.predict(X_test)
        y_pred_proba = model.predict_proba(X_test)[:, 1]
        generate_confusion_matrix(y_test, y_pred, MODEL_DIR / "confusion_matrix.png")

        # Step 7: Optimize threshold
        optimal_threshold = optimize_threshold(
            y_test, y_pred_proba, MODEL_DIR / "precision_recall_curve.png"
        )

        # Step 8: Feature importance
        feature_importance = analyze_feature_importance(
            model, FEATURE_COLUMNS, MODEL_DIR / "feature_importance.png"
        )

        # Step 9: Save model
        save_model(model, metrics, FEATURE_COLUMNS, optimal_threshold, scale_pos_weight, MODEL_PATH)

        # Step 10: Test loading
        load_and_test_model(MODEL_PATH, X_test)

        # Final summary
        logger.info("\n" + "=" * 80)
        logger.info("TRAINING COMPLETE ✓")
        logger.info("=" * 80)
        logger.info(f"Model: {MODEL_PATH}")
        logger.info(f"Precision: {metrics['precision']:.3f} ({'PASS' if metrics['precision'] >= MIN_PRECISION else 'FAIL'})")
        logger.info(f"Recall: {metrics['recall']:.3f} ({'PASS' if metrics['recall'] >= MIN_RECALL else 'FAIL'})")
        logger.info(f"ROC-AUC: {metrics['roc_auc']:.3f} ({'PASS' if metrics['roc_auc'] >= MIN_ROC_AUC else 'FAIL'})")
        logger.info("=" * 80)

        # Exit with appropriate code
        if (
            metrics["precision"] >= MIN_PRECISION
            and metrics["recall"] >= MIN_RECALL
            and metrics["roc_auc"] >= MIN_ROC_AUC
        ):
            sys.exit(0)
        else:
            logger.error("Model did not meet performance requirements")
            sys.exit(1)

    except Exception as e:
        logger.exception(f"Training failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
