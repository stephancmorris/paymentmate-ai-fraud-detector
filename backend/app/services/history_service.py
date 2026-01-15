"""
Transaction history storage and retrieval service.
Manages in-memory storage of scored transactions.
"""

import logging
from collections import deque
from datetime import datetime
from typing import List, Optional, Literal
from threading import Lock

from app.models.schemas import TransactionHistoryItem, TransactionRequest, TransactionResponse

logger = logging.getLogger(__name__)


class TransactionHistoryService:
    """Store and retrieve transaction history using in-memory deque."""

    def __init__(self, max_size: int = 100):
        """
        Initialize history service.

        Args:
            max_size: Maximum transactions to store (default: 100)
        """
        self._history: deque = deque(maxlen=max_size)
        self._lock = Lock()
        self._max_size = max_size

        logger.info(
            "TransactionHistoryService initialized",
            extra={"max_size": max_size}
        )

    def add_transaction(
        self,
        request: TransactionRequest,
        response: TransactionResponse
    ) -> None:
        """
        Add scored transaction to history.

        Args:
            request: Original transaction request
            response: Scoring response
        """
        with self._lock:
            history_item = TransactionHistoryItem(
                transaction_id=response.transaction_id,
                user_id=request.user_id,
                amount=request.amount,
                merchant_id=request.merchant_id,
                merchant_category=request.merchant_category,
                payment_method=request.payment_method,
                score=response.score,
                decision=response.decision,
                timestamp=request.timestamp,
                country=request.country,
                explanation=response.explanation
            )

            self._history.append(history_item)

            logger.debug(
                "Transaction added to history",
                extra={
                    "transaction_id": response.transaction_id,
                    "decision": response.decision,
                    "history_size": len(self._history)
                }
            )

    def get_recent_transactions(
        self,
        limit: int = 20,
        decision_filter: Optional[Literal["ALLOW", "FLAG", "DECLINE"]] = None
    ) -> List[TransactionHistoryItem]:
        """
        Retrieve recent transactions.

        Args:
            limit: Max transactions to return (default: 20)
            decision_filter: Optional filter by decision (ALLOW/FLAG/DECLINE)

        Returns:
            List of transactions, most recent first
        """
        with self._lock:
            transactions = list(self._history)

            if decision_filter:
                transactions = [
                    t for t in transactions
                    if t.decision == decision_filter
                ]

            transactions.sort(key=lambda x: x.timestamp, reverse=True)

            transactions = transactions[:limit]

            logger.debug(
                "Retrieved transactions from history",
                extra={
                    "total_in_history": len(self._history),
                    "returned_count": len(transactions),
                    "decision_filter": decision_filter,
                    "limit": limit
                }
            )

            return transactions

    def get_all_transactions(self) -> List[TransactionHistoryItem]:
        """Retrieve all transactions, most recent first."""
        with self._lock:
            transactions = list(self._history)
            transactions.sort(key=lambda x: x.timestamp, reverse=True)
            return transactions

    def get_transaction_count(self) -> int:
        """Get total number of transactions in history."""
        with self._lock:
            return len(self._history)

    def clear_history(self) -> None:
        """Clear all transactions from history."""
        with self._lock:
            self._history.clear()
            logger.info("Transaction history cleared")

    def get_decision_counts(self) -> dict:
        """Get transaction counts by decision type."""
        with self._lock:
            transactions = list(self._history)

            counts = {
                "ALLOW": 0,
                "FLAG": 0,
                "DECLINE": 0
            }

            for transaction in transactions:
                counts[transaction.decision] += 1

            return counts


# Global singleton instance
_history_service: Optional[TransactionHistoryService] = None


def get_history_service() -> TransactionHistoryService:
    """Get global transaction history service instance."""
    global _history_service
    if _history_service is None:
        _history_service = TransactionHistoryService()
    return _history_service
