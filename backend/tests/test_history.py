"""
Integration tests for transaction history endpoints.
Tests the /api/v1/data/history and related endpoints.
"""

import pytest
from datetime import datetime
from fastapi.testclient import TestClient

from app.main import app
from app.services.history_service import get_history_service

client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_history():
    """Clear history before and after each test."""
    history_service = get_history_service()
    history_service.clear_history()
    yield
    history_service.clear_history()


class TestHistoryEndpoint:
    """Test suite for the transaction history endpoint."""

    def test_empty_history_returns_empty_array(self):
        """Test that empty history returns empty array, not error."""
        response = client.get("/api/v1/data/history")

        assert response.status_code == 200
        data = response.json()

        assert "transactions" in data
        assert "total_count" in data
        assert "returned_count" in data

        assert data["transactions"] == []
        assert data["total_count"] == 0
        assert data["returned_count"] == 0

    def test_history_after_scoring_transaction(self):
        """Test that scoring a transaction adds it to history."""
        # Score a transaction
        transaction_payload = {
            "user_id": 12345,
            "amount": 99.99,
            "merchant_id": "MERCHANT_001"
        }

        score_response = client.post("/api/v1/transaction/score", json=transaction_payload)
        assert score_response.status_code == 200

        # Get history
        history_response = client.get("/api/v1/data/history")
        assert history_response.status_code == 200

        data = history_response.json()
        assert data["total_count"] == 1
        assert data["returned_count"] == 1
        assert len(data["transactions"]) == 1

        # Verify transaction data
        transaction = data["transactions"][0]
        assert transaction["user_id"] == 12345
        assert transaction["amount"] == 99.99
        assert transaction["merchant_id"] == "MERCHANT_001"
        assert "score" in transaction
        assert "decision" in transaction
        assert "transaction_id" in transaction
        assert "timestamp" in transaction

    def test_history_returns_most_recent_first(self):
        """Test that transactions are ordered by timestamp, most recent first."""
        # Score multiple transactions
        for i in range(5):
            payload = {
                "user_id": i + 1,
                "amount": (i + 1) * 10.0,
                "merchant_id": f"MERCHANT_{i+1:03d}"
            }
            response = client.post("/api/v1/transaction/score", json=payload)
            assert response.status_code == 200

        # Get history
        response = client.get("/api/v1/data/history")
        assert response.status_code == 200

        data = response.json()
        assert data["total_count"] == 5
        assert len(data["transactions"]) == 5

        # Verify order (most recent first = highest user_id first due to sequential creation)
        transactions = data["transactions"]
        assert transactions[0]["user_id"] == 5
        assert transactions[1]["user_id"] == 4
        assert transactions[2]["user_id"] == 3
        assert transactions[3]["user_id"] == 2
        assert transactions[4]["user_id"] == 1

    def test_history_limit_parameter(self):
        """Test that limit parameter restricts number of results."""
        # Score 15 transactions
        for i in range(15):
            payload = {
                "user_id": i + 1,
                "amount": 100.0,
                "merchant_id": "MERCHANT_001"
            }
            response = client.post("/api/v1/transaction/score", json=payload)
            assert response.status_code == 200

        # Get history with limit=5
        response = client.get("/api/v1/data/history?limit=5")
        assert response.status_code == 200

        data = response.json()
        assert data["total_count"] == 15
        assert data["returned_count"] == 5
        assert len(data["transactions"]) == 5

    def test_history_default_limit_is_20(self):
        """Test that default limit is 20 transactions."""
        # Score 25 transactions
        for i in range(25):
            payload = {
                "user_id": i + 1,
                "amount": 100.0,
                "merchant_id": "MERCHANT_001"
            }
            response = client.post("/api/v1/transaction/score", json=payload)
            assert response.status_code == 200

        # Get history without limit parameter
        response = client.get("/api/v1/data/history")
        assert response.status_code == 200

        data = response.json()
        assert data["total_count"] == 25
        assert data["returned_count"] == 20  # Default limit
        assert len(data["transactions"]) == 20

    def test_history_decision_filter_allow(self):
        """Test filtering by decision=ALLOW."""
        # Score transactions with different amounts to get different decisions
        # Low amounts should be ALLOW
        for i in range(5):
            payload = {
                "user_id": i + 1,
                "amount": 50.0,  # Low amount = ALLOW
                "merchant_id": "MERCHANT_001"
            }
            response = client.post("/api/v1/transaction/score", json=payload)
            assert response.status_code == 200

        # Get history with decision filter
        response = client.get("/api/v1/data/history?decision=ALLOW")
        assert response.status_code == 200

        data = response.json()
        assert data["returned_count"] > 0

        # Verify all returned transactions have decision=ALLOW
        for transaction in data["transactions"]:
            assert transaction["decision"] == "ALLOW"

    def test_history_decision_filter_flag(self):
        """Test filtering by decision=FLAG."""
        # Create transactions that will be flagged
        # We need to create transactions with scores between 0.7 and 0.9
        # Based on the scoring logic, certain merchant categories + amounts can trigger this
        for i in range(3):
            payload = {
                "user_id": 900 + i,  # High user_id for deterministic scoring
                "amount": 1500.0,  # High amount
                "merchant_id": "MERCHANT_JEWELRY",
                "merchant_category": "jewelry"  # Medium risk category
            }
            response = client.post("/api/v1/transaction/score", json=payload)
            assert response.status_code == 200

        # Get all history first to see what we have
        all_history = client.get("/api/v1/data/history")
        all_data = all_history.json()

        # Count FLAG decisions
        flag_count = sum(1 for t in all_data["transactions"] if t["decision"] == "FLAG")

        # Get history with decision filter
        response = client.get("/api/v1/data/history?decision=FLAG")
        assert response.status_code == 200

        data = response.json()
        assert data["returned_count"] == flag_count

        # Verify all returned transactions have decision=FLAG
        for transaction in data["transactions"]:
            assert transaction["decision"] == "FLAG"

    def test_history_decision_filter_decline(self):
        """Test filtering by decision=DECLINE."""
        # Create a transaction that will be declined (score >= 0.9)
        # Need very high risk factors
        for i in range(2):
            payload = {
                "user_id": 999,  # Max deterministic variance
                "amount": 5000.0,  # Very high amount
                "merchant_id": "MERCHANT_CRYPTO",
                "merchant_category": "crypto"  # High risk
            }
            response = client.post("/api/v1/transaction/score", json=payload)
            assert response.status_code == 200

        # Get history with decision filter
        response = client.get("/api/v1/data/history?decision=DECLINE")
        assert response.status_code == 200

        data = response.json()

        # Verify all returned transactions have decision=DECLINE
        for transaction in data["transactions"]:
            assert transaction["decision"] == "DECLINE"

    def test_history_limit_validation(self):
        """Test that limit parameter validates correctly."""
        # Test limit < 1
        response = client.get("/api/v1/data/history?limit=0")
        assert response.status_code == 422

        # Test limit > 100
        response = client.get("/api/v1/data/history?limit=101")
        assert response.status_code == 422

        # Test valid limits
        response = client.get("/api/v1/data/history?limit=1")
        assert response.status_code == 200

        response = client.get("/api/v1/data/history?limit=100")
        assert response.status_code == 200

    def test_history_invalid_decision_filter(self):
        """Test that invalid decision filter is rejected."""
        response = client.get("/api/v1/data/history?decision=INVALID")
        assert response.status_code == 422

    def test_history_preserves_transaction_metadata(self):
        """Test that all transaction metadata is preserved in history."""
        # Score a transaction with all fields
        payload = {
            "user_id": 12345,
            "amount": 99.99,
            "merchant_id": "MERCHANT_001",
            "merchant_category": "retail",
            "currency": "USD",
            "country": "US",
            "payment_method": "credit_card",
            "device_id": "DEVICE_123",
            "ip_address": "192.168.1.1"
        }

        score_response = client.post("/api/v1/transaction/score", json=payload)
        assert score_response.status_code == 200
        score_data = score_response.json()

        # Get history
        history_response = client.get("/api/v1/data/history")
        assert history_response.status_code == 200

        data = history_response.json()
        transaction = data["transactions"][0]

        # Verify all key fields are present
        assert transaction["transaction_id"] == score_data["transaction_id"]
        assert transaction["user_id"] == payload["user_id"]
        assert transaction["amount"] == payload["amount"]
        assert transaction["merchant_id"] == payload["merchant_id"]
        assert transaction["score"] == score_data["score"]
        assert transaction["decision"] == score_data["decision"]
        assert transaction["country"] == payload["country"]

    def test_history_timestamps_are_iso_format(self):
        """Test that timestamps are in ISO 8601 format."""
        # Score a transaction
        payload = {
            "user_id": 12345,
            "amount": 99.99,
            "merchant_id": "MERCHANT_001"
        }

        score_response = client.post("/api/v1/transaction/score", json=payload)
        assert score_response.status_code == 200

        # Get history
        history_response = client.get("/api/v1/data/history")
        assert history_response.status_code == 200

        data = history_response.json()
        transaction = data["transactions"][0]

        # Verify timestamp is present and can be parsed
        assert "timestamp" in transaction
        timestamp_str = transaction["timestamp"]

        # Should be able to parse as ISO format
        try:
            datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        except ValueError:
            pytest.fail(f"Timestamp not in ISO format: {timestamp_str}")

    def test_history_max_storage_100_transactions(self):
        """Test that history stores maximum 100 transactions."""
        # Score 150 transactions
        for i in range(150):
            payload = {
                "user_id": i + 1,
                "amount": 100.0,
                "merchant_id": "MERCHANT_001"
            }
            response = client.post("/api/v1/transaction/score", json=payload)
            assert response.status_code == 200

        # Get all history
        response = client.get("/api/v1/data/history?limit=100")
        assert response.status_code == 200

        data = response.json()
        # Should only store 100 (max deque size)
        assert data["total_count"] == 100

        # The oldest 50 should have been removed, so we should have users 51-150
        user_ids = [t["user_id"] for t in data["transactions"]]
        assert 1 not in user_ids  # Oldest transaction removed
        assert 50 not in user_ids
        assert 51 in user_ids  # Should still be there
        assert 150 in user_ids  # Most recent


class TestHistoryStatsEndpoint:
    """Test suite for the history statistics endpoint."""

    def test_stats_empty_history(self):
        """Test stats endpoint with empty history."""
        response = client.get("/api/v1/data/history/stats")

        assert response.status_code == 200
        data = response.json()

        assert "total" in data
        assert "by_decision" in data

        assert data["total"] == 0
        assert data["by_decision"]["ALLOW"] == 0
        assert data["by_decision"]["FLAG"] == 0
        assert data["by_decision"]["DECLINE"] == 0

    def test_stats_with_transactions(self):
        """Test stats endpoint with transactions."""
        # Score some transactions
        for i in range(10):
            payload = {
                "user_id": i + 1,
                "amount": 100.0,
                "merchant_id": "MERCHANT_001"
            }
            response = client.post("/api/v1/transaction/score", json=payload)
            assert response.status_code == 200

        # Get stats
        response = client.get("/api/v1/data/history/stats")
        assert response.status_code == 200

        data = response.json()
        assert data["total"] == 10

        # Sum of decisions should equal total
        decision_sum = (
            data["by_decision"]["ALLOW"] +
            data["by_decision"]["FLAG"] +
            data["by_decision"]["DECLINE"]
        )
        assert decision_sum == 10


class TestClearHistoryEndpoint:
    """Test suite for the clear history endpoint (testing only)."""

    def test_clear_history(self):
        """Test clearing transaction history."""
        # Add some transactions
        for i in range(5):
            payload = {
                "user_id": i + 1,
                "amount": 100.0,
                "merchant_id": "MERCHANT_001"
            }
            response = client.post("/api/v1/transaction/score", json=payload)
            assert response.status_code == 200

        # Verify history has transactions
        history_response = client.get("/api/v1/data/history")
        assert history_response.json()["total_count"] == 5

        # Clear history
        clear_response = client.delete("/api/v1/data/history")
        assert clear_response.status_code == 204

        # Verify history is empty
        history_response = client.get("/api/v1/data/history")
        assert history_response.json()["total_count"] == 0
