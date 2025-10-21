"""
Pydantic models and schemas for PaymentMate AI.
Defines request/response models with validation rules.
"""

from datetime import datetime
from typing import Dict, List, Optional, Literal
from pydantic import BaseModel, Field, field_validator, ConfigDict
from decimal import Decimal


class TransactionRequest(BaseModel):
    """
    Request model for transaction scoring.
    Represents an incoming financial transaction to be scored for fraud.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user_id": 12345,
                "amount": 99.99,
                "merchant_id": "MERCHANT_001",
                "merchant_category": "retail",
                "timestamp": "2025-10-20T14:30:00Z",
                "currency": "USD",
                "country": "US",
                "payment_method": "credit_card",
                "device_id": "DEVICE_123",
                "ip_address": "192.168.1.1"
            }
        }
    )

    # Required fields
    user_id: int = Field(
        ...,
        description="Unique identifier for the user/customer",
        gt=0,
        examples=[12345]
    )

    amount: float = Field(
        ...,
        description="Transaction amount in the specified currency",
        gt=0.0,
        examples=[99.99]
    )

    merchant_id: str = Field(
        ...,
        description="Unique identifier for the merchant",
        min_length=1,
        max_length=100,
        examples=["MERCHANT_001"]
    )

    # Optional fields with defaults
    merchant_category: Optional[str] = Field(
        default=None,
        description="Category of the merchant (e.g., retail, food, travel)",
        max_length=50,
        examples=["retail"]
    )

    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Transaction timestamp (UTC)",
        examples=["2025-10-20T14:30:00Z"]
    )

    currency: str = Field(
        default="USD",
        description="Transaction currency code (ISO 4217)",
        min_length=3,
        max_length=3,
        examples=["USD"]
    )

    country: Optional[str] = Field(
        default=None,
        description="Country code where transaction occurred (ISO 3166-1 alpha-2)",
        min_length=2,
        max_length=2,
        examples=["US"]
    )

    payment_method: Optional[str] = Field(
        default="credit_card",
        description="Payment method used",
        examples=["credit_card", "debit_card", "bank_transfer"]
    )

    device_id: Optional[str] = Field(
        default=None,
        description="Device identifier",
        max_length=100,
        examples=["DEVICE_123"]
    )

    ip_address: Optional[str] = Field(
        default=None,
        description="IP address of the transaction",
        max_length=45,  # IPv6 max length
        examples=["192.168.1.1"]
    )

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: float) -> float:
        """Validate transaction amount is positive and reasonable."""
        if v <= 0:
            raise ValueError("Amount must be greater than 0")
        if v > 1_000_000:
            raise ValueError("Amount exceeds maximum allowed (1,000,000)")
        # Round to 2 decimal places for currency
        return round(v, 2)

    @field_validator("timestamp")
    @classmethod
    def validate_timestamp(cls, v: datetime) -> datetime:
        """Validate timestamp is not in the future."""
        now = datetime.utcnow()

        # Remove timezone info for comparison (convert to naive UTC)
        v_naive = v.replace(tzinfo=None) if v.tzinfo else v

        if v_naive > now:
            raise ValueError("Timestamp cannot be in the future")
        # Warn if transaction is very old (more than 24 hours)
        age_hours = (now - v_naive).total_seconds() / 3600
        if age_hours > 24:
            # In production, you might want to log this or handle differently
            pass
        return v

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v: str) -> str:
        """Validate currency code format."""
        v = v.upper()
        # Common currency codes (expand as needed)
        valid_currencies = {"USD", "EUR", "GBP", "CAD", "AUD", "JPY", "CNY"}
        if v not in valid_currencies:
            # In production, you might want to accept any 3-letter code
            # For MVP, we'll be lenient and just uppercase it
            pass
        return v

    @field_validator("country")
    @classmethod
    def validate_country(cls, v: Optional[str]) -> Optional[str]:
        """Validate country code format."""
        if v is None:
            return v
        return v.upper()


class SHAPExplanation(BaseModel):
    """SHAP explanation for a single feature."""

    feature_name: str = Field(..., description="Name of the feature")
    feature_value: float = Field(..., description="Value of the feature for this transaction")
    shap_value: float = Field(..., description="SHAP contribution value")
    contribution: Literal["fraud", "legitimate"] = Field(
        ...,
        description="Whether this feature contributes toward fraud or legitimate classification"
    )


class TransactionResponse(BaseModel):
    """
    Response model for transaction scoring.
    Contains the fraud score, decision, and explanation.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
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
                "timestamp": "2025-10-20T14:30:00Z",
                "processing_time_ms": 45.2
            }
        }
    )

    transaction_id: str = Field(
        ...,
        description="Unique identifier for this scoring event",
        examples=["txn_123456"]
    )

    score: float = Field(
        ...,
        description="Fraud probability score (0.0 to 1.0)",
        ge=0.0,
        le=1.0,
        examples=[0.85]
    )

    decision: Literal["ALLOW", "FLAG", "DECLINE"] = Field(
        ...,
        description="Decision based on the score and threshold",
        examples=["FLAG"]
    )

    explanation: Dict = Field(
        ...,
        description="SHAP explanation with top contributing features"
    )

    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Time when the scoring was completed"
    )

    processing_time_ms: Optional[float] = Field(
        default=None,
        description="Time taken to process the transaction (milliseconds)",
        ge=0.0,
        examples=[45.2]
    )


class TransactionHistoryItem(BaseModel):
    """Single transaction in the history list."""

    transaction_id: str = Field(..., description="Transaction ID")
    user_id: int = Field(..., description="User ID")
    amount: float = Field(..., description="Transaction amount")
    merchant_id: str = Field(..., description="Merchant ID")
    score: float = Field(..., ge=0.0, le=1.0, description="Fraud score")
    decision: Literal["ALLOW", "FLAG", "DECLINE"] = Field(..., description="Decision")
    timestamp: datetime = Field(..., description="Transaction timestamp")
    country: Optional[str] = Field(default=None, description="Country code")


class HistoryResponse(BaseModel):
    """
    Response model for transaction history.
    Returns a list of recent scored transactions.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "transactions": [
                    {
                        "transaction_id": "txn_123456",
                        "user_id": 12345,
                        "amount": 99.99,
                        "merchant_id": "MERCHANT_001",
                        "score": 0.85,
                        "decision": "FLAG",
                        "timestamp": "2025-10-20T14:30:00Z",
                        "country": "US"
                    }
                ],
                "total_count": 1,
                "returned_count": 1
            }
        }
    )

    transactions: List[TransactionHistoryItem] = Field(
        default_factory=list,
        description="List of recent transactions"
    )

    total_count: int = Field(
        ...,
        description="Total number of transactions in history",
        ge=0
    )

    returned_count: int = Field(
        ...,
        description="Number of transactions returned in this response",
        ge=0
    )


class MetricsResponse(BaseModel):
    """
    Response model for aggregate performance metrics.
    Contains model performance and business metrics.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "total_transactions": 1000,
                "flagged_count": 120,
                "allowed_count": 850,
                "declined_count": 30,
                "precision": 0.85,
                "recall": 0.78,
                "f1_score": 0.81,
                "average_score": 0.23,
                "losses_prevented": 45000.00,
                "false_positive_rate": 0.05,
                "timestamp": "2025-10-20T14:30:00Z"
            }
        }
    )

    # Transaction counts
    total_transactions: int = Field(
        default=0,
        description="Total number of transactions processed",
        ge=0
    )

    flagged_count: int = Field(
        default=0,
        description="Number of transactions flagged for review",
        ge=0
    )

    allowed_count: int = Field(
        default=0,
        description="Number of transactions allowed",
        ge=0
    )

    declined_count: int = Field(
        default=0,
        description="Number of transactions declined",
        ge=0
    )

    # Model performance metrics
    precision: float = Field(
        default=0.0,
        description="Model precision (true positives / (true positives + false positives))",
        ge=0.0,
        le=1.0
    )

    recall: float = Field(
        default=0.0,
        description="Model recall (true positives / (true positives + false negatives))",
        ge=0.0,
        le=1.0
    )

    f1_score: float = Field(
        default=0.0,
        description="F1 score (harmonic mean of precision and recall)",
        ge=0.0,
        le=1.0
    )

    average_score: float = Field(
        default=0.0,
        description="Average fraud score across all transactions",
        ge=0.0,
        le=1.0
    )

    # Business metrics
    losses_prevented: float = Field(
        default=0.0,
        description="Estimated monetary losses prevented (simulated)",
        ge=0.0
    )

    false_positive_rate: float = Field(
        default=0.0,
        description="Rate of false positives (legitimate transactions flagged as fraud)",
        ge=0.0,
        le=1.0
    )

    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Time when metrics were calculated"
    )
