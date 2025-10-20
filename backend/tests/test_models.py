"""
Tests for Pydantic data models and validation rules.
"""

import pytest
from datetime import datetime, timedelta
from pydantic import ValidationError

from app.models.schemas import (
    TransactionRequest,
    TransactionResponse,
    HistoryResponse,
    MetricsResponse,
    TransactionHistoryItem,
    SHAPExplanation
)


class TestTransactionRequest:
    """Test TransactionRequest model and validation."""

    def test_valid_transaction_request(self):
        """Test that a valid transaction request is accepted."""
        data = {
            "user_id": 12345,
            "amount": 99.99,
            "merchant_id": "MERCHANT_001",
            "merchant_category": "retail",
            "currency": "USD",
            "country": "US"
        }

        transaction = TransactionRequest(**data)

        assert transaction.user_id == 12345
        assert transaction.amount == 99.99
        assert transaction.merchant_id == "MERCHANT_001"
        assert transaction.currency == "USD"
        assert transaction.country == "US"
        assert isinstance(transaction.timestamp, datetime)

    def test_negative_amount_rejected(self):
        """Test that negative transaction amounts are rejected with 422 status."""
        data = {
            "user_id": 12345,
            "amount": -50.00,
            "merchant_id": "MERCHANT_001"
        }

        with pytest.raises(ValidationError) as exc_info:
            TransactionRequest(**data)

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("amount",) for error in errors)

    def test_zero_amount_rejected(self):
        """Test that zero amount is rejected."""
        data = {
            "user_id": 12345,
            "amount": 0.0,
            "merchant_id": "MERCHANT_001"
        }

        with pytest.raises(ValidationError) as exc_info:
            TransactionRequest(**data)

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("amount",) for error in errors)

    def test_excessive_amount_rejected(self):
        """Test that amounts over 1 million are rejected."""
        data = {
            "user_id": 12345,
            "amount": 1_500_000.00,
            "merchant_id": "MERCHANT_001"
        }

        with pytest.raises(ValidationError) as exc_info:
            TransactionRequest(**data)

        errors = exc_info.value.errors()
        assert any("amount" in str(error) for error in errors)

    def test_missing_required_fields_return_validation_errors(self):
        """Test that missing required fields return validation errors."""
        # Missing user_id
        with pytest.raises(ValidationError) as exc_info:
            TransactionRequest(amount=99.99, merchant_id="MERCHANT_001")

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("user_id",) for error in errors)

        # Missing amount
        with pytest.raises(ValidationError) as exc_info:
            TransactionRequest(user_id=12345, merchant_id="MERCHANT_001")

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("amount",) for error in errors)

        # Missing merchant_id
        with pytest.raises(ValidationError) as exc_info:
            TransactionRequest(user_id=12345, amount=99.99)

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("merchant_id",) for error in errors)

    def test_invalid_data_types_are_rejected(self):
        """Test that invalid data types are rejected."""
        # String for user_id
        with pytest.raises(ValidationError):
            TransactionRequest(
                user_id="not_a_number",
                amount=99.99,
                merchant_id="MERCHANT_001"
            )

        # String for amount
        with pytest.raises(ValidationError):
            TransactionRequest(
                user_id=12345,
                amount="not_a_number",
                merchant_id="MERCHANT_001"
            )

    def test_future_timestamps_are_rejected(self):
        """Test that future timestamps are flagged/rejected."""
        future_time = datetime.utcnow() + timedelta(hours=1)

        data = {
            "user_id": 12345,
            "amount": 99.99,
            "merchant_id": "MERCHANT_001",
            "timestamp": future_time
        }

        with pytest.raises(ValidationError) as exc_info:
            TransactionRequest(**data)

        errors = exc_info.value.errors()
        assert any("timestamp" in str(error) for error in errors)

    def test_currency_code_normalization(self):
        """Test that currency codes are normalized to uppercase."""
        data = {
            "user_id": 12345,
            "amount": 99.99,
            "merchant_id": "MERCHANT_001",
            "currency": "usd"
        }

        transaction = TransactionRequest(**data)
        assert transaction.currency == "USD"

    def test_country_code_normalization(self):
        """Test that country codes are normalized to uppercase."""
        data = {
            "user_id": 12345,
            "amount": 99.99,
            "merchant_id": "MERCHANT_001",
            "country": "us"
        }

        transaction = TransactionRequest(**data)
        assert transaction.country == "US"

    def test_amount_rounding(self):
        """Test that amounts are rounded to 2 decimal places."""
        data = {
            "user_id": 12345,
            "amount": 99.999,
            "merchant_id": "MERCHANT_001"
        }

        transaction = TransactionRequest(**data)
        assert transaction.amount == 100.00

    def test_negative_user_id_rejected(self):
        """Test that negative user IDs are rejected."""
        data = {
            "user_id": -1,
            "amount": 99.99,
            "merchant_id": "MERCHANT_001"
        }

        with pytest.raises(ValidationError) as exc_info:
            TransactionRequest(**data)

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("user_id",) for error in errors)


class TestTransactionResponse:
    """Test TransactionResponse model."""

    def test_valid_transaction_response(self):
        """Test that response models serialize correctly to JSON."""
        data = {
            "transaction_id": "txn_123456",
            "score": 0.85,
            "decision": "FLAG",
            "explanation": {
                "top_features": [
                    {
                        "feature_name": "velocity_5min",
                        "feature_value": 6.0,
                        "shap_value": 0.45,
                        "contribution": "fraud"
                    }
                ],
                "threshold": 0.7
            },
            "processing_time_ms": 45.2
        }

        response = TransactionResponse(**data)

        assert response.transaction_id == "txn_123456"
        assert response.score == 0.85
        assert response.decision == "FLAG"
        assert response.processing_time_ms == 45.2

        # Test JSON serialization
        json_data = response.model_dump()
        assert "transaction_id" in json_data
        assert "score" in json_data
        assert "decision" in json_data

    def test_score_bounds_validation(self):
        """Test that score is validated to be between 0 and 1."""
        # Score > 1
        with pytest.raises(ValidationError):
            TransactionResponse(
                transaction_id="txn_123",
                score=1.5,
                decision="FLAG",
                explanation={}
            )

        # Score < 0
        with pytest.raises(ValidationError):
            TransactionResponse(
                transaction_id="txn_123",
                score=-0.1,
                decision="FLAG",
                explanation={}
            )

    def test_decision_enum_validation(self):
        """Test that decision field only accepts valid values."""
        valid_decisions = ["ALLOW", "FLAG", "DECLINE"]

        for decision in valid_decisions:
            response = TransactionResponse(
                transaction_id="txn_123",
                score=0.5,
                decision=decision,
                explanation={}
            )
            assert response.decision == decision

        # Invalid decision
        with pytest.raises(ValidationError):
            TransactionResponse(
                transaction_id="txn_123",
                score=0.5,
                decision="INVALID",
                explanation={}
            )


class TestHistoryResponse:
    """Test HistoryResponse model."""

    def test_empty_history_response(self):
        """Test that empty history returns empty array (not error)."""
        response = HistoryResponse(
            transactions=[],
            total_count=0,
            returned_count=0
        )

        assert response.transactions == []
        assert response.total_count == 0
        assert response.returned_count == 0

    def test_history_with_transactions(self):
        """Test history response with transaction items."""
        transactions = [
            TransactionHistoryItem(
                transaction_id="txn_1",
                user_id=12345,
                amount=99.99,
                merchant_id="MERCHANT_001",
                score=0.85,
                decision="FLAG",
                timestamp=datetime.utcnow(),
                country="US"
            )
        ]

        response = HistoryResponse(
            transactions=transactions,
            total_count=1,
            returned_count=1
        )

        assert len(response.transactions) == 1
        assert response.transactions[0].transaction_id == "txn_1"
        assert response.total_count == 1


class TestMetricsResponse:
    """Test MetricsResponse model."""

    def test_valid_metrics_response(self):
        """Test that all required metric fields are present."""
        response = MetricsResponse(
            total_transactions=1000,
            flagged_count=120,
            allowed_count=850,
            declined_count=30,
            precision=0.85,
            recall=0.78,
            f1_score=0.81,
            average_score=0.23,
            losses_prevented=45000.00,
            false_positive_rate=0.05
        )

        assert response.total_transactions == 1000
        assert response.precision == 0.85
        assert response.recall == 0.78
        assert response.losses_prevented == 45000.00

    def test_metrics_bounds_validation(self):
        """Test that metric values are within valid ranges."""
        # Precision > 1
        with pytest.raises(ValidationError):
            MetricsResponse(precision=1.5)

        # Recall < 0
        with pytest.raises(ValidationError):
            MetricsResponse(recall=-0.1)

        # Negative counts
        with pytest.raises(ValidationError):
            MetricsResponse(total_transactions=-1)

    def test_default_metrics_values(self):
        """Test that metrics have sensible defaults."""
        response = MetricsResponse()

        assert response.total_transactions == 0
        assert response.precision == 0.0
        assert response.recall == 0.0
        assert response.losses_prevented == 0.0


class TestSHAPExplanation:
    """Test SHAPExplanation model."""

    def test_valid_shap_explanation(self):
        """Test SHAP explanation model."""
        shap = SHAPExplanation(
            feature_name="velocity_5min",
            feature_value=6.0,
            shap_value=0.45,
            contribution="fraud"
        )

        assert shap.feature_name == "velocity_5min"
        assert shap.feature_value == 6.0
        assert shap.shap_value == 0.45
        assert shap.contribution == "fraud"

    def test_contribution_enum_validation(self):
        """Test that contribution field only accepts valid values."""
        # Valid values
        for contribution in ["fraud", "legitimate"]:
            shap = SHAPExplanation(
                feature_name="test",
                feature_value=1.0,
                shap_value=0.1,
                contribution=contribution
            )
            assert shap.contribution == contribution

        # Invalid value
        with pytest.raises(ValidationError):
            SHAPExplanation(
                feature_name="test",
                feature_value=1.0,
                shap_value=0.1,
                contribution="invalid"
            )
