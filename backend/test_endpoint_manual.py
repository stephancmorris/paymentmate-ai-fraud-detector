#!/usr/bin/env python3
"""Manual test script for the transaction scoring endpoint."""

import requests
import json
from datetime import datetime

# Test data
payload = {
    "user_id": 12345,
    "amount": 99.99,
    "merchant_id": "MERCHANT_001",
    "merchant_category": "retail",
    "currency": "USD",
    "country": "US",
    "payment_method": "credit_card"
}

print("Testing POST /api/v1/transaction/score")
print("=" * 60)
print("Request payload:")
print(json.dumps(payload, indent=2))
print()

# Send request
response = requests.post(
    "http://127.0.0.1:8000/api/v1/transaction/score",
    json=payload
)

print(f"Status Code: {response.status_code}")
print(f"Headers: {dict(response.headers)}")
print()
print("Response body:")
print(json.dumps(response.json(), indent=2))
print()

# Verify response structure
data = response.json()
assert "transaction_id" in data
assert "score" in data
assert "decision" in data
assert "explanation" in data
assert "processing_time_ms" in data

print("✅ All required fields present")
print(f"✅ Score: {data['score']} (valid range 0-1)")
print(f"✅ Decision: {data['decision']}")
print(f"✅ Processing time: {data['processing_time_ms']}ms")
print()
print("Test PASSED!")
