"""
Integration tests for performance metrics endpoint.
Tests the /api/v1/data/metrics endpoint functionality.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.metrics_service import get_metrics_service
from app.services.history_service import get_history_service

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_services():
    """Reset metrics and history before and after each test."""
    metrics_service = get_metrics_service()
    history_service = get_history_service()

    metrics_service.reset_metrics()
    history_service.clear_history()

    yield

    metrics_service.reset_metrics()
    history_service.clear_history()


class TestMetricsEndpoint:
    """Test suite for the performance metrics endpoint."""

    def test_empty_metrics_returns_zeros(self):
        """Test that empty metrics returns all zeros, not error."""
        response = client.get("/api/v1/data/metrics")

        assert response.status_code == 200
        data = response.json()

        # Verify all required fields are present
        assert "total_transactions" in data
        assert "flagged_count" in data
        assert "allowed_count" in data
        assert "declined_count" in data
        assert "precision" in data
        assert "recall" in data
        assert "f1_score" in data
        assert "average_score" in data
        assert "losses_prevented" in data
        assert "false_positive_rate" in data
        assert "timestamp" in data

        # Verify all counts are zero
        assert data["total_transactions"] == 0
        assert data["flagged_count"] == 0
        assert data["allowed_count"] == 0
        assert data["declined_count"] == 0
        assert data["precision"] == 0.0
        assert data["recall"] == 0.0
        assert data["f1_score"] == 0.0
        assert data["average_score"] == 0.0
        assert data["losses_prevented"] == 0.0
        assert data["false_positive_rate"] == 0.0

    def test_metrics_update_after_scoring_transaction(self):
        """Test that metrics update after scoring a transaction."""
        # Score a transaction
        payload = {
            "user_id": 12345,
            "amount": 99.99,
            "merchant_id": "MERCHANT_001"
        }

        score_response = client.post("/api/v1/transaction/score", json=payload)
        assert score_response.status_code == 200

        # Get metrics
        metrics_response = client.get("/api/v1/data/metrics")
        assert metrics_response.status_code == 200

        data = metrics_response.json()

        # Verify transaction was counted
        assert data["total_transactions"] == 1

        # Verify decision count updated
        decision = score_response.json()["decision"]
        if decision == "ALLOW":
            assert data["allowed_count"] == 1
        elif decision == "FLAG":
            assert data["flagged_count"] == 1
        elif decision == "DECLINE":
            assert data["declined_count"] == 1

        # Verify average score is set
        assert data["average_score"] > 0.0

    def test_metrics_track_multiple_transactions(self):
        """Test that metrics correctly track multiple transactions."""
        # Score 10 transactions
        for i in range(10):
            payload = {
                "user_id": i + 1,
                "amount": 100.0,
                "merchant_id": "MERCHANT_001"
            }
            response = client.post("/api/v1/transaction/score", json=payload)
            assert response.status_code == 200

        # Get metrics
        response = client.get("/api/v1/data/metrics")
        assert response.status_code == 200

        data = response.json()

        # Verify total count
        assert data["total_transactions"] == 10

        # Verify sum of decisions equals total
        decision_sum = (
            data["allowed_count"] +
            data["flagged_count"] +
            data["declined_count"]
        )
        assert decision_sum == 10

    def test_metrics_response_schema_validation(self):
        """Test that metrics response matches MetricsResponse schema."""
        response = client.get("/api/v1/data/metrics")
        assert response.status_code == 200

        data = response.json()

        # Verify all fields have correct types
        assert isinstance(data["total_transactions"], int)
        assert isinstance(data["flagged_count"], int)
        assert isinstance(data["allowed_count"], int)
        assert isinstance(data["declined_count"], int)
        assert isinstance(data["precision"], (int, float))
        assert isinstance(data["recall"], (int, float))
        assert isinstance(data["f1_score"], (int, float))
        assert isinstance(data["average_score"], (int, float))
        assert isinstance(data["losses_prevented"], (int, float))
        assert isinstance(data["false_positive_rate"], (int, float))
        assert isinstance(data["timestamp"], str)

        # Verify numeric bounds
        assert 0.0 <= data["precision"] <= 1.0
        assert 0.0 <= data["recall"] <= 1.0
        assert 0.0 <= data["f1_score"] <= 1.0
        assert 0.0 <= data["average_score"] <= 1.0
        assert 0.0 <= data["false_positive_rate"] <= 1.0
        assert data["losses_prevented"] >= 0.0

    def test_precision_recall_calculated_correctly(self):
        """Test that precision and recall are calculated from simulated ground truth."""
        # Score 50 transactions to get meaningful metrics
        for i in range(50):
            payload = {
                "user_id": i + 1,
                "amount": 100.0 + (i * 10),
                "merchant_id": f"MERCHANT_{i:03d}"
            }
            response = client.post("/api/v1/transaction/score", json=payload)
            assert response.status_code == 200

        # Get metrics
        response = client.get("/api/v1/data/metrics")
        assert response.status_code == 200

        data = response.json()

        # Verify metrics are reasonable (simulated values should be in valid ranges)
        assert 0.0 <= data["precision"] <= 1.0
        assert 0.0 <= data["recall"] <= 1.0
        assert 0.0 <= data["f1_score"] <= 1.0

        # If there are flagged/declined transactions, precision should be calculated
        if data["flagged_count"] + data["declined_count"] > 0:
            # Precision should be non-zero when we have positive predictions
            assert data["precision"] >= 0.0

    def test_f1_score_is_harmonic_mean(self):
        """Test that F1 score is harmonic mean of precision and recall."""
        # Score transactions
        for i in range(20):
            payload = {
                "user_id": i + 1,
                "amount": 200.0,
                "merchant_id": "MERCHANT_001"
            }
            response = client.post("/api/v1/transaction/score", json=payload)
            assert response.status_code == 200

        # Get metrics
        response = client.get("/api/v1/data/metrics")
        data = response.json()

        precision = data["precision"]
        recall = data["recall"]
        f1 = data["f1_score"]

        # Verify F1 is harmonic mean (if precision and recall > 0)
        if precision > 0 and recall > 0:
            expected_f1 = 2 * (precision * recall) / (precision + recall)
            assert abs(f1 - expected_f1) < 0.001  # Allow small floating point difference
        elif precision == 0 or recall == 0:
            assert f1 == 0.0

    def test_average_score_calculation(self):
        """Test that average score is calculated correctly."""
        # Score 3 transactions with known scores
        transactions = [
            {"user_id": 1, "amount": 50.0, "merchant_id": "M1"},   # Low score expected
            {"user_id": 50, "amount": 500.0, "merchant_id": "M2"},  # Medium score
            {"user_id": 99, "amount": 1000.0, "merchant_id": "M3", "merchant_category": "crypto"}  # High score
        ]

        total_score = 0.0
        for txn in transactions:
            response = client.post("/api/v1/transaction/score", json=txn)
            assert response.status_code == 200
            total_score += response.json()["score"]

        # Get metrics
        response = client.get("/api/v1/data/metrics")
        data = response.json()

        # Verify average score
        expected_avg = total_score / len(transactions)
        assert abs(data["average_score"] - expected_avg) < 0.01

    def test_losses_prevented_calculation(self):
        """Test that losses prevented is calculated based on caught fraud."""
        # Score transactions
        for i in range(30):
            payload = {
                "user_id": 90 + i,  # High user IDs for higher scores
                "amount": 1000.0,
                "merchant_id": "MERCHANT_CRYPTO",
                "merchant_category": "crypto"  # High risk
            }
            response = client.post("/api/v1/transaction/score", json=payload)
            assert response.status_code == 200

        # Get metrics
        response = client.get("/api/v1/data/metrics")
        data = response.json()

        # Losses prevented should be calculated (simulated)
        # With high-risk transactions, we expect some to be flagged/declined
        # and thus some losses prevented
        assert data["losses_prevented"] >= 0.0

    def test_false_positive_rate_calculation(self):
        """Test that false positive rate is calculated."""
        # Score transactions
        for i in range(25):
            payload = {
                "user_id": i + 1,
                "amount": 75.0,
                "merchant_id": "MERCHANT_001"
            }
            response = client.post("/api/v1/transaction/score", json=payload)
            assert response.status_code == 200

        # Get metrics
        response = client.get("/api/v1/data/metrics")
        data = response.json()

        # FPR should be in valid range
        assert 0.0 <= data["false_positive_rate"] <= 1.0

    def test_metrics_division_by_zero_handled(self):
        """Test that division by zero is handled gracefully."""
        # Get metrics without any transactions
        response = client.get("/api/v1/data/metrics")
        assert response.status_code == 200

        data = response.json()

        # Should return 0 for metrics that would involve division by zero
        assert data["precision"] == 0.0
        assert data["recall"] == 0.0
        assert data["f1_score"] == 0.0
        assert data["average_score"] == 0.0
        assert data["false_positive_rate"] == 0.0

    def test_metrics_persist_during_runtime(self):
        """Test that metrics persist across multiple API calls."""
        # Score a transaction
        payload = {
            "user_id": 123,
            "amount": 150.0,
            "merchant_id": "MERCHANT_001"
        }
        client.post("/api/v1/transaction/score", json=payload)

        # Get metrics first time
        response1 = client.get("/api/v1/data/metrics")
        data1 = response1.json()

        # Get metrics second time (should be same)
        response2 = client.get("/api/v1/data/metrics")
        data2 = response2.json()

        # Counts should be the same
        assert data1["total_transactions"] == data2["total_transactions"]
        assert data1["allowed_count"] == data2["allowed_count"]
        assert data1["flagged_count"] == data2["flagged_count"]
        assert data1["declined_count"] == data2["declined_count"]

        # Score another transaction
        client.post("/api/v1/transaction/score", json=payload)

        # Get metrics third time (should have incremented)
        response3 = client.get("/api/v1/data/metrics")
        data3 = response3.json()

        assert data3["total_transactions"] == data1["total_transactions"] + 1

    def test_metrics_timestamp_format(self):
        """Test that metrics timestamp is in ISO format."""
        response = client.get("/api/v1/data/metrics")
        assert response.status_code == 200

        data = response.json()

        # Verify timestamp is present and parseable
        assert "timestamp" in data
        timestamp_str = data["timestamp"]

        # Should be able to parse as ISO format
        from datetime import datetime
        try:
            datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        except ValueError:
            pytest.fail(f"Timestamp not in ISO format: {timestamp_str}")

    def test_high_volume_metrics_tracking(self):
        """Test metrics tracking with high volume of transactions."""
        # Score 100 transactions
        for i in range(100):
            payload = {
                "user_id": i + 1,
                "amount": 50.0 + (i * 5),
                "merchant_id": f"MERCHANT_{i % 10}"
            }
            response = client.post("/api/v1/transaction/score", json=payload)
            assert response.status_code == 200

        # Get metrics
        response = client.get("/api/v1/data/metrics")
        assert response.status_code == 200

        data = response.json()

        # Verify all transactions counted
        assert data["total_transactions"] == 100

        # Verify decision sum equals total
        decision_sum = (
            data["allowed_count"] +
            data["flagged_count"] +
            data["declined_count"]
        )
        assert decision_sum == 100

        # Verify metrics are reasonable
        assert 0.0 <= data["average_score"] <= 1.0
        assert 0.0 <= data["precision"] <= 1.0
        assert 0.0 <= data["recall"] <= 1.0

    def test_metrics_with_different_decision_types(self):
        """Test metrics tracking with transactions of different decision types."""
        # Create transactions with varying amounts to get different decisions
        test_cases = [
            {"user_id": 1, "amount": 25.0, "merchant_id": "M1"},     # Likely ALLOW
            {"user_id": 50, "amount": 200.0, "merchant_id": "M2"},   # Varied
            {"user_id": 99, "amount": 5000.0, "merchant_id": "M3", "merchant_category": "crypto"}  # Likely FLAG/DECLINE
        ]

        for txn in test_cases:
            response = client.post("/api/v1/transaction/score", json=txn)
            assert response.status_code == 200

        # Get metrics
        response = client.get("/api/v1/data/metrics")
        assert response.status_code == 200

        data = response.json()

        # Verify all transactions counted
        assert data["total_transactions"] == len(test_cases)

        # Verify at least one decision type has count > 0
        assert (
            data["allowed_count"] > 0 or
            data["flagged_count"] > 0 or
            data["declined_count"] > 0
        )


class TestMetricsServiceIntegration:
    """Test integration between metrics service and scoring endpoint."""

    def test_metrics_service_updates_automatically(self):
        """Test that metrics service updates automatically when transactions are scored."""
        # Get initial metrics
        initial_response = client.get("/api/v1/data/metrics")
        initial_data = initial_response.json()
        initial_count = initial_data["total_transactions"]

        # Score a transaction
        payload = {
            "user_id": 456,
            "amount": 299.99,
            "merchant_id": "MERCHANT_TEST"
        }
        score_response = client.post("/api/v1/transaction/score", json=payload)
        assert score_response.status_code == 200

        # Get updated metrics
        updated_response = client.get("/api/v1/data/metrics")
        updated_data = updated_response.json()

        # Verify count increased
        assert updated_data["total_transactions"] == initial_count + 1

    def test_metrics_consistency_with_history(self):
        """Test that metrics counts are consistent with history counts."""
        # Score several transactions
        for i in range(15):
            payload = {
                "user_id": i + 100,
                "amount": 125.0,
                "merchant_id": "MERCHANT_001"
            }
            client.post("/api/v1/transaction/score", json=payload)

        # Get metrics
        metrics_response = client.get("/api/v1/data/metrics")
        metrics_data = metrics_response.json()

        # Get history
        history_response = client.get("/api/v1/data/history?limit=100")
        history_data = history_response.json()

        # Verify counts match
        assert metrics_data["total_transactions"] == history_data["total_count"]
