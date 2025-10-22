"""
Data and analytics endpoints.
Provides access to transaction history and system metrics.
"""

import logging
from typing import Optional, Literal
from fastapi import APIRouter, status, Query

from app.models.schemas import HistoryResponse
from app.services.history_service import get_history_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/data/history",
    response_model=HistoryResponse,
    status_code=status.HTTP_200_OK,
    tags=["data"],
    summary="Get transaction history",
    description="Retrieve recent scored transactions with optional filtering by decision type"
)
async def get_transaction_history(
    limit: int = Query(
        default=20,
        ge=1,
        le=100,
        description="Maximum number of transactions to return (1-100)"
    ),
    decision: Optional[Literal["ALLOW", "FLAG", "DECLINE"]] = Query(
        default=None,
        description="Filter by decision type (ALLOW, FLAG, or DECLINE)"
    )
) -> HistoryResponse:
    """
    Retrieve transaction history.

    Returns a list of recently scored transactions, ordered by timestamp
    (most recent first). Can be filtered by decision type.

    Args:
        limit: Maximum number of transactions to return (default: 20, max: 100)
        decision: Optional filter by decision type

    Returns:
        HistoryResponse with list of transactions and counts

    Example:
        ```
        GET /api/v1/data/history?limit=10&decision=FLAG
        ```

        Returns the 10 most recent flagged transactions.
    """
    logger.info(
        "Retrieving transaction history",
        extra={
            "limit": limit,
            "decision_filter": decision
        }
    )

    # Get history service
    history_service = get_history_service()

    # Retrieve transactions
    transactions = history_service.get_recent_transactions(
        limit=limit,
        decision_filter=decision
    )

    # Get total count
    total_count = history_service.get_transaction_count()

    logger.info(
        "Transaction history retrieved",
        extra={
            "total_count": total_count,
            "returned_count": len(transactions),
            "decision_filter": decision
        }
    )

    return HistoryResponse(
        transactions=transactions,
        total_count=total_count,
        returned_count=len(transactions)
    )


@router.get(
    "/data/history/stats",
    status_code=status.HTTP_200_OK,
    tags=["data"],
    summary="Get transaction history statistics",
    description="Get counts of transactions by decision type"
)
async def get_history_stats() -> dict:
    """
    Get transaction history statistics.

    Returns counts of transactions by decision type (ALLOW/FLAG/DECLINE)
    and total count.

    Returns:
        Dictionary with transaction counts

    Example Response:
        ```json
        {
            "total": 150,
            "by_decision": {
                "ALLOW": 120,
                "FLAG": 25,
                "DECLINE": 5
            }
        }
        ```
    """
    logger.info("Retrieving transaction history statistics")

    # Get history service
    history_service = get_history_service()

    # Get counts
    decision_counts = history_service.get_decision_counts()
    total_count = history_service.get_transaction_count()

    return {
        "total": total_count,
        "by_decision": decision_counts
    }


@router.delete(
    "/data/history",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["data"],
    summary="Clear transaction history (testing only)",
    description="Clear all transactions from history. For testing purposes only."
)
async def clear_transaction_history() -> None:
    """
    Clear all transaction history.

    **Warning**: This deletes all stored transaction history.
    This endpoint should only be used for testing.

    Returns:
        204 No Content
    """
    logger.warning("Clearing transaction history (testing endpoint)")

    # Get history service
    history_service = get_history_service()

    # Clear history
    history_service.clear_history()

    logger.info("Transaction history cleared")
