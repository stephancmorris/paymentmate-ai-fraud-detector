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

    CATEGORIES = [
        'retail', 'grocery', 'restaurant', 'gas_station', 'online',
        'entertainment', 'travel', 'utilities', 'healthcare', 'other'
    ]

    COUNTRIES = ['US', 'CA', 'GB', 'DE', 'FR', 'JP', 'AU', 'BR', 'IN', 'MX']

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
                'home_country': random.choice(self.COUNTRIES[:3]),
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

        amount = max(1.0, random.gauss(profile['avg_amount'], profile['std_amount']))

        if random.random() < 0.7:
            category = profile['typical_category']
        else:
            category = random.choice(self.CATEGORIES)

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
        """Generate velocity attack transaction."""
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
        """Generate unusually large transaction."""
        user_id = random.choice(list(self.user_profiles.keys()))
        profile = self.user_profiles[user_id]

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
        """Generate geographic anomaly transaction."""
        user_id = random.choice(list(self.user_profiles.keys()))
        profile = self.user_profiles[user_id]

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
        """Generate card testing transaction."""
        user_id = random.choice(list(self.user_profiles.keys()))

        return {
            'user_id': user_id,
            'amount': round(random.uniform(0.50, 5.0), 2),
            'merchant_id': random.choice(self.merchant_pool),
            'merchant_category': 'online',
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'country': random.choice(self.COUNTRIES),
            'payment_method': random.choice(self.PAYMENT_METHODS),
        }


class TransactionSimulator:
    """Simulates transaction flow to the fraud detection API."""

    def __init__(self, api_url: str, rate: float, fraud_percentage: float, scenario: str = 'mixed'):
        """
        Initialize simulator.

        Args:
            api_url: Base URL of the API (e.g., http://localhost:8000)
            rate: Transactions per second
            fraud_percentage: Percentage of transactions that are fraudulent (0-100)
            scenario: Fraud scenario type ('mixed', 'velocity', 'large_amount', 'geographic', 'card_testing')
        """
        self.api_url = api_url
        self.rate = rate
        self.fraud_percentage = fraud_percentage / 100.0
        self.scenario = scenario
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
            'velocity_count': 0,
            'large_amount_count': 0,
            'geographic_count': 0,
            'card_testing_count': 0,
        }

    def _generate_transaction(self) -> Dict:
        """Generate transaction based on fraud percentage."""
        is_fraud = random.random() < self.fraud_percentage

        if not is_fraud:
            self.stats['legitimate'] += 1
            return self.generator.generate_legitimate()
        else:
            self.stats['fraud'] += 1
            if self.scenario == 'velocity':
                fraud_type = 'velocity'
            elif self.scenario == 'large_amount':
                fraud_type = 'large_amount'
            elif self.scenario == 'geographic':
                fraud_type = 'geographic'
            elif self.scenario == 'card_testing':
                fraud_type = 'card_testing'
            else:
                fraud_type = random.choice([
                    'velocity',
                    'large_amount',
                    'geographic',
                    'card_testing',
                ])
            if fraud_type == 'velocity':
                self.stats['velocity_count'] += 1
                return self.generator.generate_fraud_velocity()
            elif fraud_type == 'large_amount':
                self.stats['large_amount_count'] += 1
                return self.generator.generate_fraud_large_amount()
            elif fraud_type == 'geographic':
                self.stats['geographic_count'] += 1
                return self.generator.generate_fraud_geographic()
            else:
                self.stats['card_testing_count'] += 1
                return self.generator.generate_fraud_card_testing()

    def _send_transaction(self, transaction: Dict) -> Optional[Dict]:
        """Send transaction to API and return response."""
        url = f"{self.api_url}/api/v1/transaction/score"

        try:
            start_time = time.time()
            response = requests.post(url, json=transaction, timeout=10)
            latency = (time.time() - start_time) * 1000

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
        logger.info(f"Starting simulator: rate={self.rate} TPS, fraud={self.fraud_percentage*100:.1f}%, scenario={self.scenario}")
        logger.info(f"API URL: {self.api_url}")

        if duration_seconds:
            logger.info(f"Running for {duration_seconds} seconds")
        if count:
            logger.info(f"Generating {count} transactions")

        start_time = time.time()
        interval = 1.0 / self.rate if self.rate > 0 else 1.0

        try:
            while True:
                if count and self.stats['total'] >= count:
                    break
                if duration_seconds and (time.time() - start_time) >= duration_seconds:
                    break

                transaction = self._generate_transaction()
                self.stats['total'] += 1
                self._send_transaction(transaction)

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
        logger.info(f"Scenario:               {self.scenario}")
        logger.info(f"Total transactions:     {self.stats['total']}")
        logger.info(f"Legitimate:             {self.stats['legitimate']} ({self.stats['legitimate']/self.stats['total']*100:.1f}%)")
        logger.info(f"Fraudulent:             {self.stats['fraud']} ({self.stats['fraud']/self.stats['total']*100:.1f}%)")
        logger.info(f"")

        if self.stats['fraud'] > 0:
            logger.info("FRAUD TYPE BREAKDOWN:")
            if self.stats['velocity_count'] > 0:
                logger.info(f"  Velocity attacks:     {self.stats['velocity_count']} ({self.stats['velocity_count']/self.stats['fraud']*100:.1f}% of fraud)")
            if self.stats['large_amount_count'] > 0:
                logger.info(f"  Large amounts:        {self.stats['large_amount_count']} ({self.stats['large_amount_count']/self.stats['fraud']*100:.1f}% of fraud)")
            if self.stats['geographic_count'] > 0:
                logger.info(f"  Geographic anomalies: {self.stats['geographic_count']} ({self.stats['geographic_count']/self.stats['fraud']*100:.1f}% of fraud)")
            if self.stats['card_testing_count'] > 0:
                logger.info(f"  Card testing:         {self.stats['card_testing_count']} ({self.stats['card_testing_count']/self.stats['fraud']*100:.1f}% of fraud)")
            logger.info(f"")

        logger.info("DECISIONS:")
        logger.info(f"  ALLOW:                {self.stats['allowed']} ({self.stats['allowed']/self.stats['total']*100:.1f}%)")
        logger.info(f"  FLAG:                 {self.stats['flagged']} ({self.stats['flagged']/self.stats['total']*100:.1f}%)")
        logger.info(f"  DECLINE:              {self.stats['declined']} ({self.stats['declined']/self.stats['total']*100:.1f}%)")
        logger.info(f"")
        logger.info(f"Errors:                 {self.stats['errors']}")
        logger.info(f"Average latency:        {avg_latency:.1f}ms")
        logger.info(f"Actual rate:            {self.stats['total']/elapsed:.2f} TPS" if elapsed > 0 else "N/A")
        logger.info("="*60)


def main():
    parser = argparse.ArgumentParser(
        description='PaymentMate AI Transaction Simulator',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate 100 transactions at 10 TPS with 15% fraud (mixed scenarios)
  python3 simulator.py --count 100 --rate 10 --fraud 15

  # Run velocity attack scenario: 50 rapid transactions at 20 TPS
  python3 simulator.py --scenario velocity --count 50 --rate 20 --fraud 80

  # Run large amount scenario: test unusually high transaction amounts
  python3 simulator.py --scenario large_amount --count 30 --rate 5 --fraud 70

  # Run geographic anomaly scenario: foreign country transactions
  python3 simulator.py --scenario geographic --count 40 --rate 5 --fraud 60

  # Run card testing scenario: many small transactions
  python3 simulator.py --scenario card_testing --count 100 --rate 10 --fraud 90

  # Mixed scenario with indefinite run (Ctrl+C to stop)
  python3 simulator.py --scenario mixed --rate 10 --fraud 15
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
    parser.add_argument(
        '--scenario',
        choices=['mixed', 'velocity', 'large_amount', 'geographic', 'card_testing'],
        default='mixed',
        help='Fraud scenario to run (default: mixed)'
    )

    args = parser.parse_args()

    logger.setLevel(getattr(logging, args.log_level))
    if args.rate <= 0:
        parser.error("Rate must be greater than 0")
    if not (0 <= args.fraud <= 100):
        parser.error("Fraud percentage must be between 0 and 100")
    if args.duration and args.duration <= 0:
        parser.error("Duration must be greater than 0")
    if args.count and args.count <= 0:
        parser.error("Count must be greater than 0")

    simulator = TransactionSimulator(
        api_url=args.api_url,
        rate=args.rate,
        fraud_percentage=args.fraud,
        scenario=args.scenario
    )

    simulator.run(duration_seconds=args.duration, count=args.count)


if __name__ == '__main__':
    main()
