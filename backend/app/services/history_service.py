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
    """
    Service for storing and retrieving transaction history.

    Uses an in-memory deque for efficient FIFO storage with automatic
    size limiting. Thread-safe for concurrent access.
    """

    def __init__(self, max_size: int = 100):
        """
        Initialize the history service.

        Args:
            max_size: Maximum number of transactions to store (default: 100)
        """
        self._history: deque = deque(maxlen=max_size)
        self._lock = Lock()  # Thread safety for concurrent access
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
        Add a scored transaction to the history.

        Args:
            request: The original transaction request
            response: The scoring response
        """
        with self._lock:
            # Create history item from request and response
            history_item = TransactionHistoryItem(
                transaction_id=response.transaction_id,
                user_id=request.user_id,
                amount=request.amount,
                merchant_id=request.merchant_id,
                score=response.score,
                decision=response.decision,
                timestamp=request.timestamp,
                country=request.country
            )

            # Add to deque (automatically removes oldest if at max_size)
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
        Retrieve recent transactions from history.

        Args:
            limit: Maximum number of transactions to return (default: 20)
            decision_filter: Optional filter by decision type (ALLOW/FLAG/DECLINE)

        Returns:
            List of transaction history items, most recent first
        """
        with self._lock:
            # Convert deque to list (most recent last in deque)
            transactions = list(self._history)

            # Apply decision filter if specified
            if decision_filter:
                transactions = [
                    t for t in transactions
                    if t.decision == decision_filter
                ]

            # Sort by timestamp, most recent first
            transactions.sort(key=lambda x: x.timestamp, reverse=True)

            # Apply limit
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
        """
        Retrieve all transactions from history.

        Returns:
            List of all transaction history items, most recent first
        """
        with self._lock:
            transactions = list(self._history)
            transactions.sort(key=lambda x: x.timestamp, reverse=True)
            return transactions

    def get_transaction_count(self) -> int:
        """
        Get the total number of transactions in history.

        Returns:
            Count of transactions stored
        """
        with self._lock:
            return len(self._history)

    def clear_history(self) -> None:
        """
        Clear all transactions from history.

        Note: This is primarily for testing purposes.
        """
        with self._lock:
            self._history.clear()
            logger.info("Transaction history cleared")

    def get_decision_counts(self) -> dict:
        """
        Get counts of transactions by decision type.

        Returns:
            Dictionary with counts for ALLOW, FLAG, and DECLINE
        """
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
    """
    Get the global transaction history service instance.

    Returns:
        TransactionHistoryService singleton instance
    """
    global _history_service
    if _history_service is None:
        _history_service = TransactionHistoryService()
    return _history_service
