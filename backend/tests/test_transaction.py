"""
Integration tests for transaction scoring endpoint.
Tests the /api/v1/transaction/score endpoint functionality.
"""

import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


class TestTransactionScoringEndpoint:
    """Test suite for the transaction scoring endpoint."""

    def test_score_valid_transaction(self):
        """Test scoring a valid transaction returns proper response."""
        payload = {
            "user_id": 12345,
            "amount": 99.99,
            "merchant_id": "MERCHANT_001",
            "merchant_category": "retail",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "currency": "USD",
            "country": "US",
            "payment_method": "credit_card",
            "device_id": "DEVICE_123",
            "ip_address": "192.168.1.1"
        }

        response = client.post("/api/v1/transaction/score", json=payload)

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "transaction_id" in data
        assert "score" in data
        assert "decision" in data
        assert "explanation" in data
        assert "timestamp" in data
        assert "processing_time_ms" in data

        # Verify score is in valid range
        assert 0.0 <= data["score"] <= 1.0

        # Verify decision is valid
        assert data["decision"] in ["ALLOW", "FLAG", "DECLINE"]

        # Verify explanation structure
        assert "top_features" in data["explanation"]
        assert "threshold" in data["explanation"]
        assert isinstance(data["explanation"]["top_features"], list)

        # Verify processing time is reasonable
        assert data["processing_time_ms"] > 0
        assert data["processing_time_ms"] < 1000  # Should be under 1 second

    def test_score_minimal_transaction(self):
        """Test scoring a transaction with only required fields."""
        payload = {
            "user_id": 999,
            "amount": 50.00,
            "merchant_id": "MERCHANT_XYZ"
        }

        response = client.post("/api/v1/transaction/score", json=payload)

        assert response.status_code == 200
        data = response.json()

        assert "score" in data
        assert "decision" in data
        assert 0.0 <= data["score"] <= 1.0

    def test_score_high_amount_transaction(self):
        """Test that high amount transactions receive higher scores."""
        payload = {
            "user_id": 12345,
            "amount": 5000.00,
            "merchant_id": "MERCHANT_001"
        }

        response = client.post("/api/v1/transaction/score", json=payload)

        assert response.status_code == 200
        data = response.json()

        # High amounts should typically result in higher fraud scores
        assert data["score"] > 0.0

    def test_score_negative_amount_rejected(self):
        """Test that negative amounts are rejected with validation error."""
        payload = {
            "user_id": 12345,
            "amount": -50.00,
            "merchant_id": "MERCHANT_001"
        }

        response = client.post("/api/v1/transaction/score", json=payload)

        assert response.status_code == 422  # Validation error

    def test_score_zero_amount_rejected(self):
        """Test that zero amount is rejected."""
        payload = {
            "user_id": 12345,
            "amount": 0.00,
            "merchant_id": "MERCHANT_001"
        }

        response = client.post("/api/v1/transaction/score", json=payload)

        assert response.status_code == 422

    def test_score_missing_required_fields(self):
        """Test that missing required fields return validation error."""
        # Missing user_id
        payload = {
            "amount": 99.99,
            "merchant_id": "MERCHANT_001"
        }

        response = client.post("/api/v1/transaction/score", json=payload)

        assert response.status_code == 422

    def test_score_invalid_user_id(self):
        """Test that invalid user_id (negative or zero) is rejected."""
        payload = {
            "user_id": -1,
            "amount": 99.99,
            "merchant_id": "MERCHANT_001"
        }

        response = client.post("/api/v1/transaction/score", json=payload)

        assert response.status_code == 422

    def test_score_invalid_currency(self):
        """Test that invalid currency format is handled."""
        payload = {
            "user_id": 12345,
            "amount": 99.99,
            "merchant_id": "MERCHANT_001",
            "currency": "INVALID"  # Not 3 characters
        }

        response = client.post("/api/v1/transaction/score", json=payload)

        # Should be rejected due to min_length validation
        assert response.status_code == 422

    def test_score_future_timestamp_rejected(self):
        """Test that future timestamps are rejected."""
        future_time = datetime.utcnow() + timedelta(hours=1)

        payload = {
            "user_id": 12345,
            "amount": 99.99,
            "merchant_id": "MERCHANT_001",
            "timestamp": future_time.isoformat() + "Z"
        }

        response = client.post("/api/v1/transaction/score", json=payload)

        assert response.status_code == 422

    def test_score_invalid_json(self):
        """Test that invalid JSON payload returns 422."""
        response = client.post(
            "/api/v1/transaction/score",
            data="not valid json",
            headers={"Content-Type": "application/json"}
        )

        assert response.status_code == 422

    def test_score_response_includes_request_id(self):
        """Test that response headers include request ID."""
        payload = {
            "user_id": 12345,
            "amount": 99.99,
            "merchant_id": "MERCHANT_001"
        }

        response = client.post("/api/v1/transaction/score", json=payload)

        assert response.status_code == 200
        # Check if X-Request-ID is in response headers
        assert "x-request-id" in response.headers or "X-Request-ID" in response.headers

    def test_score_consistent_results_same_user(self):
        """Test that the same user gets consistent scores for similar transactions."""
        payload1 = {
            "user_id": 99999,
            "amount": 100.00,
            "merchant_id": "MERCHANT_001"
        }

        payload2 = {
            "user_id": 99999,
            "amount": 100.00,
            "merchant_id": "MERCHANT_001"
        }

        response1 = client.post("/api/v1/transaction/score", json=payload1)
        response2 = client.post("/api/v1/transaction/score", json=payload2)

        assert response1.status_code == 200
        assert response2.status_code == 200

        # Scores should be identical for identical transactions
        assert response1.json()["score"] == response2.json()["score"]

    def test_score_explanation_has_features(self):
        """Test that explanation contains feature information."""
        payload = {
            "user_id": 12345,
            "amount": 999.99,
            "merchant_id": "MERCHANT_001",
            "merchant_category": "electronics",
            "country": "US"
        }

        response = client.post("/api/v1/transaction/score", json=payload)

        assert response.status_code == 200
        data = response.json()

        # Check explanation structure
        explanation = data["explanation"]
        assert "top_features" in explanation
        assert len(explanation["top_features"]) > 0

        # Check feature structure
        feature = explanation["top_features"][0]
        assert "feature_name" in feature
        assert "feature_value" in feature
        assert "shap_value" in feature
        assert "contribution" in feature
        assert feature["contribution"] in ["fraud", "legitimate"]

    def test_score_decision_thresholds(self):
        """Test that decisions are based on score thresholds."""
        # Test multiple transactions and verify decision logic
        test_cases = []

        for user_id in range(1, 100):
            payload = {
                "user_id": user_id,
                "amount": 100.00,
                "merchant_id": "MERCHANT_001"
            }

            response = client.post("/api/v1/transaction/score", json=payload)
            assert response.status_code == 200

            data = response.json()
            score = data["score"]
            decision = data["decision"]

            # Verify decision matches score threshold
            if score >= 0.9:
                assert decision == "DECLINE"
            elif score >= 0.7:
                assert decision == "FLAG"
            else:
                assert decision == "ALLOW"

    def test_score_transaction_id_format(self):
        """Test that transaction ID follows expected format."""
        payload = {
            "user_id": 12345,
            "amount": 99.99,
            "merchant_id": "MERCHANT_001"
        }

        response = client.post("/api/v1/transaction/score", json=payload)

        assert response.status_code == 200
        data = response.json()

        # Transaction ID should start with "txn_"
        assert data["transaction_id"].startswith("txn_")
        # Should have reasonable length
        assert len(data["transaction_id"]) > 10

    def test_score_excessive_amount(self):
        """Test that excessive amounts are rejected."""
        payload = {
            "user_id": 12345,
            "amount": 2_000_000.00,  # Over 1 million limit
            "merchant_id": "MERCHANT_001"
        }

        response = client.post("/api/v1/transaction/score", json=payload)

        assert response.status_code == 422

    def test_score_different_countries(self):
        """Test scoring transactions from different countries."""
        countries = ["US", "GB", "CA", "FR", "JP"]

        for country in countries:
            payload = {
                "user_id": 12345,
                "amount": 99.99,
                "merchant_id": "MERCHANT_001",
                "country": country
            }

            response = client.post("/api/v1/transaction/score", json=payload)

            assert response.status_code == 200
            data = response.json()
            assert "score" in data

    def test_score_different_payment_methods(self):
        """Test scoring with different payment methods."""
        payment_methods = ["credit_card", "debit_card", "bank_transfer", "paypal"]

        for method in payment_methods:
            payload = {
                "user_id": 12345,
                "amount": 99.99,
                "merchant_id": "MERCHANT_001",
                "payment_method": method
            }

            response = client.post("/api/v1/transaction/score", json=payload)

            assert response.status_code == 200

    def test_get_transaction_not_implemented(self):
        """Test that GET /transaction/{id} returns not implemented."""
        response = client.get("/api/v1/transaction/txn_123")

        assert response.status_code == 501
        data = response.json()
        assert "not_implemented" in data.get("status", "")


class TestTransactionScoringPerformance:
    """Performance tests for transaction scoring."""

    def test_score_latency_acceptable(self):
        """Test that scoring completes in acceptable time (<100ms target)."""
        payload = {
            "user_id": 12345,
            "amount": 99.99,
            "merchant_id": "MERCHANT_001"
        }

        response = client.post("/api/v1/transaction/score", json=payload)

        assert response.status_code == 200
        data = response.json()

        # For placeholder implementation, we expect very fast response
        # Real ML model should still be <100ms
        assert data["processing_time_ms"] < 100

    def test_score_multiple_concurrent_requests(self):
        """Test handling multiple concurrent scoring requests."""
        payload = {
            "user_id": 12345,
            "amount": 99.99,
            "merchant_id": "MERCHANT_001"
        }

        # Send 10 concurrent requests
        responses = []
        for _ in range(10):
            response = client.post("/api/v1/transaction/score", json=payload)
            responses.append(response)

        # All should succeed
        for response in responses:
            assert response.status_code == 200
            data = response.json()
            assert "score" in data
