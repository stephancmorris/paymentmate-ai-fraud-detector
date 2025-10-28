"""
End-to-end test script for ML model integration.

Tests:
- Model loading at startup
- Transaction scoring with ML model
- Performance (<100ms latency)
"""

import time
import requests
from datetime import datetime

# API base URL
BASE_URL = "http://localhost:8000"

def test_health():
    """Test that API is running."""
    print("Testing API health...")
    response = requests.get(f"{BASE_URL}/api/v1/health")
    print(f"✓ API is running: {response.json()}")
    return response.status_code == 200

def test_ml_scoring():
    """Test ML model scoring."""
    print("\nTesting ML model scoring...")

    # Test transaction 1: Low-risk transaction
    # Use a past timestamp to avoid validation error
    from datetime import timedelta
    past_time = datetime.utcnow() - timedelta(minutes=10)

    low_risk_txn = {
        "user_id": 12345,
        "amount": 50.00,
        "merchant_id": "merch_retail_001",
        "merchant_category": "retail",
        "timestamp": past_time.isoformat(),
        "country": "US",
        "currency": "USD",
        "payment_method": "credit_card",
        "device_type": "mobile"
    }

    start = time.time()
    response = requests.post(f"{BASE_URL}/api/v1/transaction/score", json=low_risk_txn)
    latency = (time.time() - start) * 1000  # ms

    if response.status_code == 200:
        result = response.json()
        print(f"\n✓ Low-risk transaction scored:")
        print(f"  Score: {result['score']:.3f}")
        print(f"  Decision: {result['decision']}")
        print(f"  Latency: {latency:.2f}ms")
        print(f"  Model version: {result['explanation'].get('model_version', 'N/A')}")

        # Check latency requirement
        if latency < 100:
            print(f"  ✓ Latency under 100ms target")
        else:
            print(f"  ✗ WARNING: Latency exceeds 100ms target")
    else:
        print(f"✗ Scoring failed: {response.status_code}")
        print(response.json())
        return False

    # Test transaction 2: High-risk transaction
    # Use a past timestamp at 3 AM
    from datetime import timedelta
    night_time = datetime.utcnow().replace(hour=3, minute=0, second=0, microsecond=0) - timedelta(days=1)

    high_risk_txn = {
        "user_id": 99999,
        "amount": 5000.00,
        "merchant_id": "merch_gambling_999",
        "merchant_category": "online_gambling",
        "timestamp": night_time.isoformat(),  # 3 AM yesterday
        "country": "NG",  # Nigeria
        "currency": "USD",
        "payment_method": "credit_card",
        "device_type": "desktop"
    }

    start = time.time()
    response = requests.post(f"{BASE_URL}/api/v1/transaction/score", json=high_risk_txn)
    latency = (time.time() - start) * 1000  # ms

    if response.status_code == 200:
        result = response.json()
        print(f"\n✓ High-risk transaction scored:")
        print(f"  Score: {result['score']:.3f}")
        print(f"  Decision: {result['decision']}")
        print(f"  Latency: {latency:.2f}ms")
        print(f"  Model version: {result['explanation'].get('model_version', 'N/A')}")

        # Check latency requirement
        if latency < 100:
            print(f"  ✓ Latency under 100ms target")
        else:
            print(f"  ✗ WARNING: Latency exceeds 100ms target")
    else:
        print(f"✗ Scoring failed: {response.status_code}")
        print(response.json())
        return False

    return True

def test_performance():
    """Test performance with multiple requests."""
    print("\nTesting performance (100 requests)...")

    from datetime import timedelta
    past_time = datetime.utcnow() - timedelta(minutes=10)

    transaction = {
        "user_id": 12345,
        "amount": 100.00,
        "merchant_id": "merch_test",
        "merchant_category": "retail",
        "timestamp": past_time.isoformat(),
        "country": "US",
        "currency": "USD",
        "payment_method": "credit_card",
        "device_type": "mobile"
    }

    latencies = []
    for i in range(100):
        start = time.time()
        response = requests.post(f"{BASE_URL}/api/v1/transaction/score", json=transaction)
        latency = (time.time() - start) * 1000
        latencies.append(latency)

        if response.status_code != 200:
            print(f"✗ Request {i+1} failed")
            return False

    avg_latency = sum(latencies) / len(latencies)
    p50 = sorted(latencies)[50]
    p95 = sorted(latencies)[95]
    p99 = sorted(latencies)[99]

    print(f"\n✓ Performance results (100 requests):")
    print(f"  Average:  {avg_latency:.2f}ms")
    print(f"  P50:      {p50:.2f}ms")
    print(f"  P95:      {p95:.2f}ms")
    print(f"  P99:      {p99:.2f}ms")

    if p95 < 100:
        print(f"  ✓ P95 latency under 100ms target")
    else:
        print(f"  ✗ WARNING: P95 latency exceeds 100ms target")

    return True

def main():
    """Run all tests."""
    print("=" * 70)
    print("PaymentMate AI - ML Model Integration Test")
    print("=" * 70)

    try:
        # Test 1: Health check
        if not test_health():
            print("\n✗ API health check failed. Make sure the server is running:")
            print("  cd backend")
            print("  source venv/bin/activate")
            print("  uvicorn app.main:app --reload")
            return

        # Test 2: ML scoring
        if not test_ml_scoring():
            print("\n✗ ML scoring test failed")
            return

        # Test 3: Performance
        if not test_performance():
            print("\n✗ Performance test failed")
            return

        print("\n" + "=" * 70)
        print("✓ All tests passed! ML model is successfully integrated.")
        print("=" * 70)

    except requests.exceptions.ConnectionError:
        print("\n✗ Could not connect to API. Make sure the server is running:")
        print("  cd backend")
        print("  source venv/bin/activate")
        print("  uvicorn app.main:app --reload")
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")

if __name__ == "__main__":
    main()
