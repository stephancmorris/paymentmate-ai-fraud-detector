#!/usr/bin/env python3
"""
PaymentMate AI - Transaction Simulator

Generates realistic transaction patterns for testing the fraud detection system.
Supports both legitimate and fraudulent transaction scenarios.
"""

import argparse
import json
import logging
import random
import sys
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import requests

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('simulator.log')
    ]
)
logger = logging.getLogger(__name__)


class TransactionGenerator:
    """Generates realistic transaction data."""

    # Merchant categories
    CATEGORIES = [
        'retail', 'grocery', 'restaurant', 'gas_station', 'online',
        'entertainment', 'travel', 'utilities', 'healthcare', 'other'
    ]

    # Countries
    COUNTRIES = ['US', 'CA', 'GB', 'DE', 'FR', 'JP', 'AU', 'BR', 'IN', 'MX']

    # Payment methods
    PAYMENT_METHODS = ['credit_card', 'debit_card', 'digital_wallet']

    def __init__(self, num_users: int = 100):
        """Initialize generator with user pool."""
        self.num_users = num_users
        self.user_profiles = self._create_user_profiles()
        self.merchant_pool = self._create_merchant_pool()

    def _create_user_profiles(self) -> Dict[int, Dict]:
        """Create synthetic user profiles with spending habits."""
        profiles = {}
        for user_id in range(1000, 1000 + self.num_users):
            profiles[user_id] = {
                'avg_amount': random.uniform(20, 500),
                'std_amount': random.uniform(10, 100),
                'typical_category': random.choice(self.CATEGORIES),
                'home_country': random.choice(self.COUNTRIES[:3]),  # Mostly US, CA, GB
                'txn_per_day': random.randint(1, 5),
            }
        return profiles

    def _create_merchant_pool(self) -> List[str]:
        """Create pool of merchant IDs."""
        merchants = []
        for category in self.CATEGORIES:
            for i in range(10):
                merchants.append(f"{category}_merchant_{i:03d}")
        return merchants

    def generate_legitimate(self) -> Dict:
        """Generate a legitimate transaction."""
        user_id = random.choice(list(self.user_profiles.keys()))
        profile = self.user_profiles[user_id]

        # Amount follows user's typical spending pattern
        amount = max(1.0, random.gauss(profile['avg_amount'], profile['std_amount']))

        # Merchant category tends toward user's typical
        if random.random() < 0.7:
            category = profile['typical_category']
        else:
            category = random.choice(self.CATEGORIES)

        # Select merchant from category
        category_merchants = [m for m in self.merchant_pool if m.startswith(category)]
        merchant_id = random.choice(category_merchants) if category_merchants else random.choice(self.merchant_pool)

        return {
            'user_id': user_id,
            'amount': round(amount, 2),
            'merchant_id': merchant_id,
            'merchant_category': category,
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'country': profile['home_country'],
            'payment_method': random.choice(self.PAYMENT_METHODS),
        }

    def generate_fraud_velocity(self) -> Dict:
        """Generate a velocity attack transaction (rapid-fire)."""
        user_id = random.choice(list(self.user_profiles.keys()))

        return {
            'user_id': user_id,
            'amount': round(random.uniform(50, 300), 2),
            'merchant_id': random.choice(self.merchant_pool),
            'merchant_category': random.choice(self.CATEGORIES),
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'country': random.choice(self.COUNTRIES),
            'payment_method': random.choice(self.PAYMENT_METHODS),
        }

    def generate_fraud_large_amount(self) -> Dict:
        """Generate an unusually large transaction."""
        user_id = random.choice(list(self.user_profiles.keys()))
        profile = self.user_profiles[user_id]

        # 10-50x the user's average
        amount = profile['avg_amount'] * random.uniform(10, 50)

        return {
            'user_id': user_id,
            'amount': round(amount, 2),
            'merchant_id': random.choice(self.merchant_pool),
            'merchant_category': random.choice(self.CATEGORIES),
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'country': profile['home_country'],
            'payment_method': random.choice(self.PAYMENT_METHODS),
        }

    def generate_fraud_geographic(self) -> Dict:
        """Generate a geographic anomaly (foreign country)."""
        user_id = random.choice(list(self.user_profiles.keys()))
        profile = self.user_profiles[user_id]

        # Use foreign country
        foreign_countries = [c for c in self.COUNTRIES if c != profile['home_country']]

        return {
            'user_id': user_id,
            'amount': round(random.uniform(100, 1000), 2),
            'merchant_id': random.choice(self.merchant_pool),
            'merchant_category': random.choice(self.CATEGORIES),
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'country': random.choice(foreign_countries),
            'payment_method': random.choice(self.PAYMENT_METHODS),
        }

    def generate_fraud_card_testing(self) -> Dict:
        """Generate a card testing transaction (small amount)."""
        user_id = random.choice(list(self.user_profiles.keys()))

        return {
            'user_id': user_id,
            'amount': round(random.uniform(0.50, 5.0), 2),  # Very small
            'merchant_id': random.choice(self.merchant_pool),
            'merchant_category': 'online',
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'country': random.choice(self.COUNTRIES),
            'payment_method': random.choice(self.PAYMENT_METHODS),
        }


class TransactionSimulator:
    """Simulates transaction flow to the fraud detection API."""

    def __init__(self, api_url: str, rate: float, fraud_percentage: float):
        """
        Initialize simulator.

        Args:
            api_url: Base URL of the API (e.g., http://localhost:8000)
            rate: Transactions per second
            fraud_percentage: Percentage of transactions that are fraudulent (0-100)
        """
        self.api_url = api_url
        self.rate = rate
        self.fraud_percentage = fraud_percentage / 100.0
        self.generator = TransactionGenerator()

        self.stats = {
            'total': 0,
            'legitimate': 0,
            'fraud': 0,
            'allowed': 0,
            'flagged': 0,
            'declined': 0,
            'errors': 0,
            'total_latency': 0.0,
        }

    def _generate_transaction(self) -> Dict:
        """Generate a transaction (legitimate or fraud)."""
        is_fraud = random.random() < self.fraud_percentage

        if not is_fraud:
            self.stats['legitimate'] += 1
            return self.generator.generate_legitimate()
        else:
            self.stats['fraud'] += 1
            # Random fraud type
            fraud_type = random.choice([
                'velocity',
                'large_amount',
                'geographic',
                'card_testing',
            ])

            if fraud_type == 'velocity':
                return self.generator.generate_fraud_velocity()
            elif fraud_type == 'large_amount':
                return self.generator.generate_fraud_large_amount()
            elif fraud_type == 'geographic':
                return self.generator.generate_fraud_geographic()
            else:
                return self.generator.generate_fraud_card_testing()

    def _send_transaction(self, transaction: Dict) -> Optional[Dict]:
        """Send transaction to API and return response."""
        url = f"{self.api_url}/api/v1/transaction/score"

        try:
            start_time = time.time()
            response = requests.post(url, json=transaction, timeout=10)
            latency = (time.time() - start_time) * 1000  # Convert to ms

            self.stats['total_latency'] += latency

            if response.status_code == 200:
                result = response.json()
                decision = result.get('decision', 'UNKNOWN')

                if decision == 'ALLOW':
                    self.stats['allowed'] += 1
                elif decision == 'FLAG':
                    self.stats['flagged'] += 1
                elif decision == 'DECLINE':
                    self.stats['declined'] += 1

                logger.info(
                    f"Transaction {self.stats['total']}: user={transaction['user_id']}, "
                    f"amount=${transaction['amount']:.2f}, decision={decision}, "
                    f"score={result.get('score', 0):.3f}, latency={latency:.1f}ms"
                )

                return result
            else:
                logger.error(f"API error: {response.status_code} - {response.text}")
                self.stats['errors'] += 1
                return None

        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            self.stats['errors'] += 1
            return None

    def run(self, duration_seconds: Optional[int] = None, count: Optional[int] = None):
        """
        Run the simulator.

        Args:
            duration_seconds: Run for this many seconds (None = indefinite)
            count: Generate this many transactions (None = indefinite)
        """
        logger.info(f"Starting simulator: rate={self.rate} TPS, fraud={self.fraud_percentage*100:.1f}%")
        logger.info(f"API URL: {self.api_url}")

        if duration_seconds:
            logger.info(f"Running for {duration_seconds} seconds")
        if count:
            logger.info(f"Generating {count} transactions")

        start_time = time.time()
        interval = 1.0 / self.rate if self.rate > 0 else 1.0

        try:
            while True:
                # Check termination conditions
                if count and self.stats['total'] >= count:
                    break
                if duration_seconds and (time.time() - start_time) >= duration_seconds:
                    break

                # Generate and send transaction
                transaction = self._generate_transaction()
                self.stats['total'] += 1
                self._send_transaction(transaction)

                # Sleep to maintain rate
                time.sleep(interval)

        except KeyboardInterrupt:
            logger.info("\nSimulator stopped by user")

        # Print final statistics
        self._print_stats()

    def _print_stats(self):
        """Print simulation statistics."""
        elapsed = self.stats['total'] / self.rate if self.rate > 0 else 0
        avg_latency = self.stats['total_latency'] / self.stats['total'] if self.stats['total'] > 0 else 0

        logger.info("\n" + "="*60)
        logger.info("SIMULATION STATISTICS")
        logger.info("="*60)
        logger.info(f"Total transactions:     {self.stats['total']}")
        logger.info(f"Legitimate:             {self.stats['legitimate']} ({self.stats['legitimate']/self.stats['total']*100:.1f}%)")
        logger.info(f"Fraudulent:             {self.stats['fraud']} ({self.stats['fraud']/self.stats['total']*100:.1f}%)")
        logger.info(f"")
        logger.info(f"ALLOW decisions:        {self.stats['allowed']} ({self.stats['allowed']/self.stats['total']*100:.1f}%)")
        logger.info(f"FLAG decisions:         {self.stats['flagged']} ({self.stats['flagged']/self.stats['total']*100:.1f}%)")
        logger.info(f"DECLINE decisions:      {self.stats['declined']} ({self.stats['declined']/self.stats['total']*100:.1f}%)")
        logger.info(f"")
        logger.info(f"Errors:                 {self.stats['errors']}")
        logger.info(f"Average latency:        {avg_latency:.1f}ms")
        logger.info(f"Actual rate:            {self.stats['total']/elapsed:.2f} TPS" if elapsed > 0 else "N/A")
        logger.info("="*60)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='PaymentMate AI Transaction Simulator',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate 100 transactions at 10 TPS with 15% fraud
  python simulator.py --count 100 --rate 10 --fraud 15

  # Run for 60 seconds at 5 TPS with 20% fraud
  python simulator.py --duration 60 --rate 5 --fraud 20

  # Run indefinitely at 1 TPS with 10% fraud
  python simulator.py --rate 1 --fraud 10
        """
    )

    parser.add_argument(
        '--api-url',
        default='http://localhost:8000',
        help='Base URL of the API (default: http://localhost:8000)'
    )
    parser.add_argument(
        '--rate',
        type=float,
        default=1.0,
        help='Transactions per second (default: 1.0)'
    )
    parser.add_argument(
        '--fraud',
        type=float,
        default=15.0,
        help='Percentage of fraudulent transactions (default: 15.0)'
    )
    parser.add_argument(
        '--duration',
        type=int,
        help='Run for this many seconds (default: indefinite)'
    )
    parser.add_argument(
        '--count',
        type=int,
        help='Generate this many transactions (default: indefinite)'
    )
    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='Logging level (default: INFO)'
    )

    args = parser.parse_args()

    # Set log level
    logger.setLevel(getattr(logging, args.log_level))

    # Validate arguments
    if args.rate <= 0:
        parser.error("Rate must be greater than 0")
    if not (0 <= args.fraud <= 100):
        parser.error("Fraud percentage must be between 0 and 100")
    if args.duration and args.duration <= 0:
        parser.error("Duration must be greater than 0")
    if args.count and args.count <= 0:
        parser.error("Count must be greater than 0")

    # Create and run simulator
    simulator = TransactionSimulator(
        api_url=args.api_url,
        rate=args.rate,
        fraud_percentage=args.fraud
    )

    simulator.run(duration_seconds=args.duration, count=args.count)


if __name__ == '__main__':
    main()
