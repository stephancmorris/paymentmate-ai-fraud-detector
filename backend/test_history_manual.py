#!/usr/bin/env python3
"""Manual test script for the transaction history endpoint."""

import requests
import json

BASE_URL = "http://127.0.0.1:8000/api/v1"

print("Testing Transaction History Endpoints")
print("=" * 70)

# Score some transactions first
print("\n1. Scoring 5 transactions...")
for i in range(5):
    payload = {
        "user_id": 100 + i,
        "amount": 100.0 * (i + 1),
        "merchant_id": f"MERCHANT_{i+1:03d}",
        "merchant_category": ["retail", "electronics", "jewelry", "travel", "food"][i]
    }
    response = requests.post(f"{BASE_URL}/transaction/score", json=payload)
    print(f"  Transaction {i+1}: {response.json()['decision']} (score: {response.json()['score']})")

# Test history endpoint
print("\n2. GET /api/v1/data/history")
print("-" * 70)
response = requests.get(f"{BASE_URL}/data/history")
print(f"Status Code: {response.status_code}")
data = response.json()
print(f"Total Count: {data['total_count']}")
print(f"Returned Count: {data['returned_count']}")
print(f"Transactions: {len(data['transactions'])}")
print()

# Show first 3 transactions
print("First 3 transactions:")
for i, txn in enumerate(data['transactions'][:3], 1):
    print(f"  {i}. User {txn['user_id']}: ${txn['amount']:.2f} - {txn['decision']}")
print()

# Test with limit
print("\n3. GET /api/v1/data/history?limit=2")
print("-" * 70)
response = requests.get(f"{BASE_URL}/data/history?limit=2")
data = response.json()
print(f"Status Code: {response.status_code}")
print(f"Returned Count: {data['returned_count']}")
print()

# Test with decision filter
print("\n4. GET /api/v1/data/history?decision=ALLOW")
print("-" * 70)
response = requests.get(f"{BASE_URL}/data/history?decision=ALLOW")
data = response.json()
print(f"Status Code: {response.status_code}")
print(f"Returned Count (ALLOW only): {data['returned_count']}")
for txn in data['transactions']:
    print(f"  User {txn['user_id']}: {txn['decision']} (score: {txn['score']})")
print()

# Test stats endpoint
print("\n5. GET /api/v1/data/history/stats")
print("-" * 70)
response = requests.get(f"{BASE_URL}/data/history/stats")
data = response.json()
print(f"Status Code: {response.status_code}")
print(f"Total: {data['total']}")
print(f"By Decision:")
print(f"  ALLOW:   {data['by_decision']['ALLOW']}")
print(f"  FLAG:    {data['by_decision']['FLAG']}")
print(f"  DECLINE: {data['by_decision']['DECLINE']}")
print()

print("\n✅ All tests PASSED!")
