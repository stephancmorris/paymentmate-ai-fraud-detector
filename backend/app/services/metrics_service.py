"""
Metrics tracking service for fraud detection performance.
Tracks aggregate statistics and model performance metrics.
"""

import logging
from datetime import datetime
from threading import Lock
from typing import Dict, Optional

from app.models.schemas import TransactionRequest, TransactionResponse

logger = logging.getLogger(__name__)


class MetricsService:
    """
    Service for tracking and calculating system performance metrics.

    Maintains in-memory counters for transaction statistics and
    calculates simulated performance metrics for MVP.
    """

    def __init__(self):
        """Initialize the metrics service."""
        self._lock = Lock()

        # Transaction counters
        self._total_transactions = 0
        self._allowed_count = 0
        self._flagged_count = 0
        self._declined_count = 0

        # Score aggregation
        self._total_score_sum = 0.0

        # Simulated ground truth counters (for MVP)
        # In production, these would come from actual fraud investigations
        self._true_positives = 0  # Correctly identified fraud
        self._false_positives = 0  # Legitimate flagged as fraud
        self._true_negatives = 0  # Correctly identified legitimate
        self._false_negatives = 0  # Fraud that was missed

        logger.info("MetricsService initialized")

    def record_transaction(
        self,
        request: TransactionRequest,
        response: TransactionResponse
    ) -> None:
        """
        Record a transaction and update metrics.

        For MVP, this simulates ground truth by assuming:
        - Very high scores (>0.85) are likely actual fraud
        - Medium-high scores (0.65-0.85) are mixed (some fraud, some legitimate)
        - Lower scores (<0.65) are likely legitimate

        Args:
            request: The original transaction request
            response: The scoring response
        """
        with self._lock:
            # Update transaction counters
            self._total_transactions += 1
            self._total_score_sum += response.score

            if response.decision == "ALLOW":
                self._allowed_count += 1
            elif response.decision == "FLAG":
                self._flagged_count += 1
            elif response.decision == "DECLINE":
                self._declined_count += 1

            # Simulate ground truth for MVP
            # In production, this would come from actual fraud investigations
            self._simulate_ground_truth(response.score, response.decision)

            logger.debug(
                "Transaction metrics recorded",
                extra={
                    "transaction_id": response.transaction_id,
                    "decision": response.decision,
                    "score": response.score,
                    "total_transactions": self._total_transactions
                }
            )

    def _simulate_ground_truth(self, score: float, decision: str) -> None:
        """
        Simulate ground truth labels for MVP metrics calculation.

        This is a placeholder that simulates realistic fraud detection
        performance. In production, these values would come from actual
        fraud investigation results.

        Simulation logic:
        - Score >0.85: Assume 90% are actual fraud
        - Score 0.65-0.85: Assume 60% are actual fraud
        - Score <0.65: Assume 5% are actual fraud

        Args:
            score: Fraud probability score
            decision: Decision made (ALLOW/FLAG/DECLINE)
        """
        # Simulate whether this is actual fraud based on score
        # Using deterministic simulation based on score
        is_actual_fraud = self._simulate_is_fraud(score)

        if decision in ["FLAG", "DECLINE"]:
            # We flagged/declined this transaction
            if is_actual_fraud:
                self._true_positives += 1  # Correctly caught fraud
            else:
                self._false_positives += 1  # Incorrectly flagged legitimate
        else:
            # We allowed this transaction
            if is_actual_fraud:
                self._false_negatives += 1  # Missed fraud
            else:
                self._true_negatives += 1  # Correctly allowed legitimate

    def _simulate_is_fraud(self, score: float) -> bool:
        """
        Simulate whether a transaction is actually fraudulent.

        Uses score-based probability to simulate realistic ground truth.

        Args:
            score: Fraud probability score

        Returns:
            True if simulated as actual fraud, False otherwise
        """
        # High scores are more likely to be actual fraud
        if score >= 0.85:
            # 90% of high-score transactions are simulated as actual fraud
            fraud_probability = 0.90
        elif score >= 0.65:
            # 60% of medium-high scores are simulated as actual fraud
            fraud_probability = 0.60
        elif score >= 0.40:
            # 30% of medium scores are simulated as actual fraud
            fraud_probability = 0.30
        else:
            # 5% of low scores are simulated as actual fraud
            fraud_probability = 0.05

        # Deterministic simulation based on score value
        # This ensures consistent results for same score
        return (score * 100) % 100 < (fraud_probability * 100)

    def get_metrics(self) -> Dict:
        """
        Calculate and return current performance metrics.

        Returns:
            Dictionary containing all performance metrics
        """
        with self._lock:
            # Calculate precision, recall, F1
            precision = self._calculate_precision()
            recall = self._calculate_recall()
            f1_score = self._calculate_f1(precision, recall)

            # Calculate average score
            average_score = (
                self._total_score_sum / self._total_transactions
                if self._total_transactions > 0
                else 0.0
            )

            # Calculate losses prevented (simulated)
            losses_prevented = self._calculate_losses_prevented()

            # Calculate false positive rate
            false_positive_rate = self._calculate_false_positive_rate()

            return {
                "total_transactions": self._total_transactions,
                "flagged_count": self._flagged_count,
                "allowed_count": self._allowed_count,
                "declined_count": self._declined_count,
                "precision": round(precision, 4),
                "recall": round(recall, 4),
                "f1_score": round(f1_score, 4),
                "average_score": round(average_score, 4),
                "losses_prevented": round(losses_prevented, 2),
                "false_positive_rate": round(false_positive_rate, 4),
                "timestamp": datetime.utcnow()
            }

    def _calculate_precision(self) -> float:
        """
        Calculate precision: TP / (TP + FP)

        Precision measures the accuracy of positive predictions.

        Returns:
            Precision value between 0 and 1
        """
        denominator = self._true_positives + self._false_positives
        if denominator == 0:
            return 0.0
        return self._true_positives / denominator

    def _calculate_recall(self) -> float:
        """
        Calculate recall: TP / (TP + FN)

        Recall measures the ability to find all positive instances.

        Returns:
            Recall value between 0 and 1
        """
        denominator = self._true_positives + self._false_negatives
        if denominator == 0:
            return 0.0
        return self._true_positives / denominator

    def _calculate_f1(self, precision: float, recall: float) -> float:
        """
        Calculate F1 score: 2 * (precision * recall) / (precision + recall)

        F1 score is the harmonic mean of precision and recall.

        Args:
            precision: Precision value
            recall: Recall value

        Returns:
            F1 score between 0 and 1
        """
        if precision + recall == 0:
            return 0.0
        return 2 * (precision * recall) / (precision + recall)

    def _calculate_losses_prevented(self) -> float:
        """
        Calculate estimated monetary losses prevented.

        For MVP, this simulates the value by:
        - Assuming each caught fraud (TP) prevented $500 average loss
        - Assuming each missed fraud (FN) resulted in $500 average loss

        Returns:
            Estimated losses prevented in dollars
        """
        # Average fraud transaction amount (simulated)
        avg_fraud_amount = 500.0

        # Losses prevented = frauds we caught * average amount
        prevented = self._true_positives * avg_fraud_amount

        return prevented

    def _calculate_false_positive_rate(self) -> float:
        """
        Calculate false positive rate: FP / (FP + TN)

        This measures how often we incorrectly flag legitimate transactions.

        Returns:
            False positive rate between 0 and 1
        """
        denominator = self._false_positives + self._true_negatives
        if denominator == 0:
            return 0.0
        return self._false_positives / denominator

    def reset_metrics(self) -> None:
        """
        Reset all metrics to zero.

        Note: This is primarily for testing purposes.
        """
        with self._lock:
            self._total_transactions = 0
            self._allowed_count = 0
            self._flagged_count = 0
            self._declined_count = 0
            self._total_score_sum = 0.0
            self._true_positives = 0
            self._false_positives = 0
            self._true_negatives = 0
            self._false_negatives = 0

            logger.info("Metrics reset to zero")


# Global singleton instance
_metrics_service: Optional[MetricsService] = None


def get_metrics_service() -> MetricsService:
    """
    Get the global metrics service instance.

    Returns:
        MetricsService singleton instance
    """
    global _metrics_service
    if _metrics_service is None:
        _metrics_service = MetricsService()
    return _metrics_service
