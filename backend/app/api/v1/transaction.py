"""
Transaction scoring endpoints.
Provides fraud scoring for financial transactions.
"""

import logging
import time
import uuid
from datetime import datetime
from typing import Dict, Any
from fastapi import APIRouter, status, Request
from fastapi.responses import JSONResponse

from app.models.schemas import TransactionRequest, TransactionResponse
from app.services.scoring_service import ScoringService
from app.services.history_service import get_history_service

logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize scoring service
scoring_service = ScoringService()


@router.post(
    "/transaction/score",
    response_model=TransactionResponse,
    status_code=status.HTTP_200_OK,
    tags=["transactions"],
    summary="Score a transaction for fraud",
    description="Analyzes a financial transaction and returns a fraud probability score with explanation"
)
async def score_transaction(
    transaction: TransactionRequest,
    request: Request
) -> TransactionResponse:
    """
    Score a transaction for fraud risk.

    This endpoint accepts transaction data, performs fraud detection analysis,
    and returns a score (0.0-1.0), decision (ALLOW/FLAG/DECLINE), and
    explainability information.

    Args:
        transaction: The transaction data to score
        request: FastAPI request object (for request ID and logging)

    Returns:
        TransactionResponse: Score, decision, and explanation

    Example:
        ```json
        POST /api/v1/transaction/score
        {
            "user_id": 12345,
            "amount": 99.99,
            "merchant_id": "MERCHANT_001",
            "merchant_category": "retail",
            "timestamp": "2025-10-20T14:30:00Z",
            "currency": "USD",
            "country": "US",
            "payment_method": "credit_card"
        }
        ```
    """
    # Start timing
    start_time = time.time()

    # Get or generate request ID
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))

    # Log incoming request
    logger.info(
        "Scoring transaction",
        extra={
            "request_id": request_id,
            "user_id": transaction.user_id,
            "amount": transaction.amount,
            "merchant_id": transaction.merchant_id,
            "currency": transaction.currency,
            "country": transaction.country
        }
    )

    try:
        # Score the transaction using the scoring service
        response = await scoring_service.score_transaction(transaction, request_id)

        # Calculate processing time
        processing_time_ms = (time.time() - start_time) * 1000
        response.processing_time_ms = round(processing_time_ms, 2)

        # Add to transaction history
        history_service = get_history_service()
        history_service.add_transaction(transaction, response)

        # Log response
        logger.info(
            "Transaction scored",
            extra={
                "request_id": request_id,
                "transaction_id": response.transaction_id,
                "score": response.score,
                "decision": response.decision,
                "processing_time_ms": response.processing_time_ms
            }
        )

        return response

    except Exception as e:
        # Log error
        logger.error(
            "Error scoring transaction",
            extra={
                "request_id": request_id,
                "error": str(e),
                "user_id": transaction.user_id
            },
            exc_info=True
        )
        raise


@router.get(
    "/transaction/{transaction_id}",
    status_code=status.HTTP_501_NOT_IMPLEMENTED,
    tags=["transactions"],
    summary="Get transaction details (not yet implemented)",
    description="Retrieve details of a previously scored transaction"
)
async def get_transaction(transaction_id: str) -> Dict[str, Any]:
    """
    Retrieve a previously scored transaction.

    This endpoint is a placeholder for future functionality to retrieve
    historical transaction scores.

    Args:
        transaction_id: The unique transaction ID

    Returns:
        Transaction details
    """
    return {
        "message": "Transaction history retrieval not yet implemented",
        "transaction_id": transaction_id,
        "status": "not_implemented"
    }
