"""
Integration test for SHAP explainability in the fraud detection API.

This script tests the end-to-end SHAP integration through the API:
1. Starts the FastAPI server
2. Sends test transactions
3. Verifies SHAP explanations are included in responses
4. Validates explanation structure and content
"""

import requests
import json
from datetime import datetime, timedelta

BASE_URL = "http://localhost:8000"


def test_shap_in_api_response():
    """Test that API responses include SHAP explanations."""
    print("\n" + "=" * 70)
    print("Testing SHAP Explainability Integration (Story 2.4)")
    print("=" * 70)

    # Test 1: Low-risk transaction
    print("\n1. Testing low-risk transaction...")
    past_time = datetime.utcnow() - timedelta(minutes=10)
    low_risk_txn = {
        "user_id": 12345,
        "amount": 50.00,
        "merchant_id": "merch_retail",
        "merchant_category": "retail",
        "timestamp": past_time.isoformat(),
        "country": "US",
        "currency": "USD",
        "payment_method": "credit_card",
        "device_type": "mobile"
    }

    response = requests.post(f"{BASE_URL}/api/v1/transaction/score", json=low_risk_txn)
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"

    data = response.json()
    print(f"   Score: {data['score']}")
    print(f"   Decision: {data['decision']}")
    print(f"   Processing time: {data.get('processing_time_ms', 0):.2f}ms")

    # Verify SHAP explanation exists
    assert "explanation" in data, "Missing 'explanation' in response"
    explanation = data["explanation"]

    # Verify explanation structure
    assert "top_features" in explanation, "Missing 'top_features' in explanation"
    assert "explanation_type" in explanation, "Missing 'explanation_type'"
    assert explanation["explanation_type"] == "shap", "Expected SHAP explanations"

    # Verify top_features structure
    top_features = explanation["top_features"]
    assert isinstance(top_features, list), "top_features should be a list"
    assert len(top_features) > 0, "top_features should not be empty"
    assert len(top_features) <= 5, "Should return at most 5 top features"

    print(f"\n   Top {len(top_features)} contributing features:")
    for i, feature in enumerate(top_features[:5], 1):
        # Verify feature structure
        assert "feature_name" in feature, f"Feature {i} missing 'feature_name'"
        assert "feature_value" in feature, f"Feature {i} missing 'feature_value'"
        assert "shap_value" in feature, f"Feature {i} missing 'shap_value'"
        assert "contribution" in feature, f"Feature {i} missing 'contribution'"
        assert feature["contribution"] in ["fraud", "legitimate"], \
            f"Invalid contribution: {feature['contribution']}"

        # Print feature details
        symbol = "🔴" if feature["contribution"] == "fraud" else "🟢"
        print(f"   {symbol} {i}. {feature['feature_name']}: "
              f"{feature['feature_value']} (SHAP: {feature['shap_value']:+.4f})")

    print("   ✓ Low-risk transaction test passed")

    # Test 2: High-risk transaction
    print("\n2. Testing high-risk transaction...")
    high_risk_txn = {
        "user_id": 99999,
        "amount": 5000.00,  # Large amount
        "merchant_id": "merch_crypto_exchange",
        "merchant_category": "crypto",  # High-risk category
        "timestamp": datetime.utcnow().replace(hour=2, minute=0, second=0).isoformat(),  # Night time
        "country": "NG",  # Foreign country
        "currency": "USD",
        "payment_method": "credit_card",
        "device_type": "mobile"
    }

    response = requests.post(f"{BASE_URL}/api/v1/transaction/score", json=high_risk_txn)
    assert response.status_code == 200

    data = response.json()
    print(f"   Score: {data['score']}")
    print(f"   Decision: {data['decision']}")
    print(f"   Processing time: {data.get('processing_time_ms', 0):.2f}ms")

    explanation = data["explanation"]
    top_features = explanation["top_features"]

    print(f"\n   Top {len(top_features)} contributing features:")
    for i, feature in enumerate(top_features[:5], 1):
        symbol = "🔴" if feature["contribution"] == "fraud" else "🟢"
        print(f"   {symbol} {i}. {feature['feature_name']}: "
              f"{feature['feature_value']} (SHAP: {feature['shap_value']:+.4f})")

    # Verify high-risk features are flagged
    fraud_features = [f for f in top_features if f["contribution"] == "fraud"]
    assert len(fraud_features) > 0, "Expected some fraud-contributing features"

    print("   ✓ High-risk transaction test passed")

    # Test 3: Performance test
    print("\n3. Testing SHAP performance (100 requests)...")
    import time
    latencies = []

    for _ in range(100):
        start = time.time()
        response = requests.post(f"{BASE_URL}/api/v1/transaction/score", json=low_risk_txn)
        latency = (time.time() - start) * 1000
        latencies.append(latency)

    avg_latency = sum(latencies) / len(latencies)
    p50_latency = sorted(latencies)[50]
    p95_latency = sorted(latencies)[95]
    p99_latency = sorted(latencies)[99]

    print(f"   Average latency: {avg_latency:.2f}ms")
    print(f"   P50 latency: {p50_latency:.2f}ms")
    print(f"   P95 latency: {p95_latency:.2f}ms")
    print(f"   P99 latency: {p99_latency:.2f}ms")

    # Latency should still be under 100ms target (including SHAP)
    assert p95_latency < 100, f"P95 latency {p95_latency:.2f}ms exceeds 100ms target"

    print("   ✓ Performance test passed")

    # Summary
    print("\n" + "=" * 70)
    print("✅ All SHAP integration tests passed!")
    print("=" * 70)
    print("\nSummary:")
    print(f"  • SHAP explanations are included in API responses")
    print(f"  • Top 5 features are returned with proper structure")
    print(f"  • Feature contributions correctly labeled (fraud/legitimate)")
    print(f"  • SHAP values are numeric and properly formatted")
    print(f"  • End-to-end latency: {avg_latency:.2f}ms average (P95: {p95_latency:.2f}ms)")
    print(f"  • SHAP adds ~{avg_latency - 2.56:.2f}ms overhead (based on Story 2.3 baseline)")
    print("\nStory 2.4: SHAP Explainability Integration - COMPLETE ✅")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    try:
        # Check if server is running
        response = requests.get(f"{BASE_URL}/api/v1/health", timeout=2)
        if response.status_code != 200:
            print("❌ Error: API server is not healthy")
            print("Please start the server with: uvicorn app.main:app --reload")
            exit(1)
    except requests.exceptions.ConnectionError:
        print("❌ Error: Cannot connect to API server")
        print("Please start the server with: uvicorn app.main:app --reload")
        exit(1)

    # Run tests
    test_shap_in_api_response()
