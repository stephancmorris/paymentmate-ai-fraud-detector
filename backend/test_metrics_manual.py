#!/usr/bin/env python3
"""Manual test script for the performance metrics endpoint."""

import requests
import json

BASE_URL = "http://127.0.0.1:8000/api/v1"

print("Testing Performance Metrics Endpoint")
print("=" * 70)

# First, score some transactions to generate metrics
print("\n1. Scoring 20 transactions to generate metrics...")
for i in range(20):
    payload = {
        "user_id": 100 + i,
        "amount": 50.0 + (i * 50),
        "merchant_id": f"MERCHANT_{i+1:03d}",
        "merchant_category": ["retail", "electronics", "jewelry", "travel", "food", "crypto"][i % 6]
    }
    response = requests.post(f"{BASE_URL}/transaction/score", json=payload)
    decision = response.json()['decision']
    score = response.json()['score']
    print(f"  Transaction {i+1}: {decision} (score: {score:.2f})")

# Test metrics endpoint
print("\n2. GET /api/v1/data/metrics")
print("-" * 70)
response = requests.get(f"{BASE_URL}/data/metrics")
print(f"Status Code: {response.status_code}")
data = response.json()

print("\nTransaction Counts:")
print(f"  Total Transactions: {data['total_transactions']}")
print(f"  Allowed:            {data['allowed_count']}")
print(f"  Flagged:            {data['flagged_count']}")
print(f"  Declined:           {data['declined_count']}")

print("\nModel Performance Metrics:")
print(f"  Precision:          {data['precision']:.4f}")
print(f"  Recall:             {data['recall']:.4f}")
print(f"  F1 Score:           {data['f1_score']:.4f}")

print("\nBusiness Metrics:")
print(f"  Average Score:      {data['average_score']:.4f}")
print(f"  Losses Prevented:   ${data['losses_prevented']:,.2f}")
print(f"  False Positive Rate:{data['false_positive_rate']:.4f}")

print(f"\nTimestamp: {data['timestamp']}")

# Verify sum of decisions equals total
decision_sum = data['allowed_count'] + data['flagged_count'] + data['declined_count']
assert decision_sum == data['total_transactions'], "Decision counts don't sum to total!"

# Verify metrics are in valid ranges
assert 0.0 <= data['precision'] <= 1.0, "Precision out of range!"
assert 0.0 <= data['recall'] <= 1.0, "Recall out of range!"
assert 0.0 <= data['f1_score'] <= 1.0, "F1 score out of range!"
assert 0.0 <= data['average_score'] <= 1.0, "Average score out of range!"
assert data['losses_prevented'] >= 0.0, "Losses prevented is negative!"
assert 0.0 <= data['false_positive_rate'] <= 1.0, "FPR out of range!"

print("\n✅ All validation checks PASSED!")
print("\n" + "=" * 70)
print("Summary:")
print(f"  {data['total_transactions']} transactions processed")
print(f"  {data['flagged_count'] + data['declined_count']} potentially fraudulent")
print(f"  Model Precision: {data['precision']:.1%}")
print(f"  Model Recall: {data['recall']:.1%}")
print(f"  Estimated savings: ${data['losses_prevented']:,.2f}")
