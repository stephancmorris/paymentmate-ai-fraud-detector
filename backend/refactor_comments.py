#!/usr/bin/env python3
"""
Script to refactor verbose AI-generated comments to concise, developer-friendly ones.
Preserves functionality while improving code readability.
"""

import re
from pathlib import Path

# Mapping of verbose docstrings to concise versions
REFACTORS = {
    # model_service.py
    (
        '    def predict(self, transaction: TransactionRequest) -> Dict[str, Any]:\n'
        '        """\n'
        '        Make a fraud prediction for a transaction.\n'
        '\n'
        '        This method:\n'
        '        1. Extracts features from the transaction\n'
        '        2. Runs model inference\n'
        '        3. Returns the fraud probability score\n'
        '\n'
        '        Args:\n'
        '            transaction: The transaction to score\n'
        '\n'
        '        Returns:\n'
        '            Dictionary containing:\n'
        '            - score: Fraud probability (0.0 to 1.0)\n'
        '            - inference_time_ms: Time taken for inference\n'
        '            - model_version: Version of the model used\n'
        '\n'
        '        Raises:\n'
        '            RuntimeError: If model is not loaded\n'
        '            Exception: If prediction fails\n'
        '        """'
    ): (
        '    def predict(self, transaction: TransactionRequest) -> Dict[str, Any]:\n'
        '        """Run fraud prediction and return score, inference time, and version."""'
    ),

    (
        '    def generate_shap_explanation(\n'
        '        self,\n'
        '        features_df: pd.DataFrame,\n'
        '        top_n: int = 5\n'
        '    ) -> List[Dict[str, Any]]:\n'
        '        """\n'
        '        Generate SHAP explanations for a transaction.\n'
        '\n'
        '        This method computes SHAP values for the given transaction and returns\n'
        '        the top N features that contributed most to the prediction.\n'
        '\n'
        '        Args:\n'
        '            features_df: DataFrame with extracted features (from extract_features)\n'
        '            top_n: Number of top features to return (default: 5)\n'
        '\n'
        '        Returns:\n'
        '            List of dictionaries containing feature explanations:\n'
        '            - feature_name: Name of the feature\n'
        '            - feature_value: Value of the feature for this transaction\n'
        '            - shap_value: SHAP contribution value\n'
        '            - contribution: "fraud" or "legitimate" based on sign of SHAP value\n'
        '\n'
        '        Raises:\n'
        '            RuntimeError: If SHAP explainer is not initialized\n'
        '            Exception: If SHAP calculation fails\n'
        '        """'
    ): (
        '    def generate_shap_explanation(\n'
        '        self,\n'
        '        features_df: pd.DataFrame,\n'
        '        top_n: int = 5\n'
        '    ) -> List[Dict[str, Any]]:\n'
        '        """Generate SHAP values for top N features (sorted by absolute contribution)."""'
    ),

    (
        '    def get_model_info(self) -> Dict[str, Any]:\n'
        '        """\n'
        '        Get information about the loaded model.\n'
        '\n'
        '        Returns:\n'
        '            Dictionary containing model metadata\n'
        '        """'
    ): (
        '    def get_model_info(self) -> Dict[str, Any]:\n'
        '        """Return model metadata (version, metrics, features)."""'
    ),

    (
        '    def _calculate_amount_ratio(self, transaction: TransactionRequest) -> float:\n'
        '        """\n'
        '        Calculate transaction amount vs user average ratio.\n'
        '\n'
        '        In a full implementation, this would fetch the user\'s historical\n'
        '        average from a feature store. For now, we use a placeholder.\n'
        '\n'
        '        Args:\n'
        '            transaction: Transaction data\n'
        '\n'
        '        Returns:\n'
        '            Ratio of transaction amount to user average\n'
        '        """'
    ): (
        '    def _calculate_amount_ratio(self, transaction: TransactionRequest) -> float:\n'
        '        """Calculate amount/avg_amount ratio (placeholder $100 avg until Story 3.x)."""'
    ),

    (
        '    def _is_high_risk_category(self, category: str) -> float:\n'
        '        """\n'
        '        Check if merchant category is high-risk.\n'
        '\n'
        '        Args:\n'
        '            category: Merchant category code\n'
        '\n'
        '        Returns:\n'
        '            1.0 if high-risk, 0.0 otherwise\n'
        '        """'
    ): (
        '    def _is_high_risk_category(self, category: str) -> float:\n'
        '        """Return 1.0 if category in high-risk list, else 0.0."""'
    ),

    (
        '    def _is_foreign_country(self, country: str) -> float:\n'
        '        """\n'
        '        Check if transaction is from a foreign country.\n'
        '\n'
        '        Args:\n'
        '            country: ISO country code\n'
        '\n'
        '        Returns:\n'
        '            1.0 if foreign country, 0.0 if domestic (US)\n'
        '        """'
    ): (
        '    def _is_foreign_country(self, country: str) -> float:\n'
        '        """Return 1.0 if not US, else 0.0."""'
    ),

    (
        'def get_model_service() -> ModelService:\n'
        '    """\n'
        '    Get the global model service instance.\n'
        '\n'
        '    Returns:\n'
        '        ModelService instance\n'
        '\n'
        '    Raises:\n'
        '        RuntimeError: If model service is not initialized\n'
        '    """'
    ): (
        'def get_model_service() -> ModelService:\n'
        '    """Get global ModelService instance (must be initialized first)."""'
    ),

    (
        'def initialize_model_service(model_path: Optional[str] = None) -> None:\n'
        '    """\n'
        '    Initialize the global model service and load the model.\n'
        '\n'
        '    This should be called once at application startup.\n'
        '\n'
        '    Args:\n'
        '        model_path: Optional path to model file\n'
        '    """'
    ): (
        'def initialize_model_service(model_path: Optional[str] = None) -> None:\n'
        '    """Initialize and load model (call once at startup)."""'
    ),

    # Inline comment changes
    ('# Placeholder: Use a fixed average of $100\n        # In Story 3.3, this will be replaced with real user history'):
        ('# TODO(Story 3.3): Replace with real user history from feature store'),

    ('# Assume US is domestic, all others are foreign\n        # In a real system, this would be based on the user\'s home country'):
        ('# Assumes US domestic; TODO: base on user\'s home country'),

    ('# Calculate SHAP values\n            # For binary classification, shap_values returns values for the positive class (fraud)'):
        ('# Calculate SHAP values for fraud class (positive class)'),

    ('# shap_values is a 2D array: [samples, features]\n            # We have 1 sample, so extract first row'):
        ('# Extract single sample from SHAP output'),

    ('# Determine contribution direction\n                # Positive SHAP value = pushes toward fraud (class 1)\n                # Negative SHAP value = pushes toward legitimate (class 0)'):
        ('# Positive SHAP → fraud, Negative SHAP → legitimate'),

    ('# Sort by absolute SHAP value (most impactful features first)'):
        ('# Sort by impact (largest absolute value first)'),

    ('# Remove abs_shap_value (only used for sorting)'):
        ('# Clean up sorting helper'),

    ('# Don\'t fail the entire prediction if SHAP fails\n            # Return empty explanation instead'):
        ('# Return empty on SHAP failure (don\'t crash prediction)'),
}


def refactor_file(file_path: Path):
    """Refactor a single Python file."""
    content = file_path.read_text()
    original = content

    # Apply refactors
    for old, new in REFACTORS.items():
        content = content.replace(old, new)

    # Only write if changes were made
    if content != original:
        file_path.write_text(content)
        print(f"✓ Refactored: {file_path.relative_to(Path.cwd())}")
        return True
    return False


def main():
    """Refactor all Python files in backend/app."""
    backend_app = Path(__file__).parent / "app"

    if not backend_app.exists():
        print(f"❌ Directory not found: {backend_app}")
        return

    print("Refactoring Python files to have concise, developer-friendly comments...\n")

    py_files = list(backend_app.rglob("*.py"))
    refactored_count = 0

    for py_file in py_files:
        if refactor_file(py_file):
            refactored_count += 1

    print(f"\n✅ Refactored {refactored_count} / {len(py_files)} files")
    print("Note: Only files with matching patterns were modified")


if __name__ == "__main__":
    main()
