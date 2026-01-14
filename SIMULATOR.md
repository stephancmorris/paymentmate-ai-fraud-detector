# Transaction Simulator Guide

Quick guide when testing the application fraud detection system.

---

## Using the Simulator Script

The `simulator.py` script generates realistic transaction patterns automatically.

### Example Usage

```bash
# Will generate 50 transactions with 20% fraud rate
python3 simulator.py --count 50 --rate 5 --fraud 20
```

### Commands With Different Fraud Scenarios

```bash
# Velocity attack (rapid-fire transactions)
python3 simulator.py --scenario velocity --count 50 --rate 20 --fraud 80

# Large amount fraud (unusually high transactions)
python3 simulator.py --scenario large_amount --count 30 --fraud 70

# Geographic anomaly (foreign country transactions)
python3 simulator.py --scenario geographic --count 40 --fraud 60

# Card testing (many small transactions)
python3 simulator.py --scenario card_testing --count 100 --fraud 90
```

### Parameters

- `--count`: Number of transactions to generate
- `--rate`: Transactions per second (TPS)
- `--fraud`: Percentage of fraudulent transactions (0-100)
- `--scenario`: Fraud type (`mixed`, `velocity`, `large_amount`, `geographic`, `card_testing`)

---

## Sending Custom Transactions

### Using cURL

```bash
curl -X POST http://localhost:8000/api/v1/transaction/score \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 1234,
    "amount": 125.50,
    "merchant_id": "amazon_store_001",
    "merchant_category": "online",
    "timestamp": "2026-01-14T15:30:00Z",
    "country": "US",
    "payment_method": "credit_card"
  }'
```

### Example Response

```json
{
  "transaction_id": "txn_abc123",
  "score": 0.23,
  "decision": "ALLOW",
  "explanation": {
    "top_features": [
      {
        "feature_name": "amount_vs_avg_ratio",
        "feature_value": 1.2,
        "shap_value": 0.05,
        "contribution": "legitimate"
      },
      {
        "feature_name": "txn_count_5m",
        "feature_value": 2,
        "shap_value": -0.03,
        "contribution": "legitimate"
      }
    ]
  },
  "processing_time_ms": 15.2
}
```

### Request Fields

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `user_id` | integer | User identifier | `1234` |
| `amount` | float | Transaction amount (USD) | `125.50` |
| `merchant_id` | string | Merchant identifier | `"amazon_store_001"` |
| `merchant_category` | string | Merchant category | `"online"`, `"grocery"`, `"restaurant"` |
| `timestamp` | string | ISO 8601 timestamp | `"2026-01-14T15:30:00Z"` |
| `country` | string | Two-letter country code | `"US"`, `"CA"`, `"GB"` |
| `payment_method` | string | Payment method | `"credit_card"`, `"debit_card"`, `"digital_wallet"` |

### Decision Thresholds

- **ALLOW**: score < 0.5 (legitimate transaction)
- **FLAG**: 0.5 ≤ score < 0.9 (review recommended)
- **DECLINE**: score ≥ 0.9 (high confidence fraud)

---

## Additional Endpoints

### Get Transaction History

```bash
curl http://localhost:8000/api/v1/data/history?limit=20
```

### Get Performance Metrics

```bash
curl http://localhost:8000/api/v1/data/metrics
```

### Health Check

```bash
curl http://localhost:8000/api/v1/health
```

---

## Interactive API Testing

Visit **http://localhost:8000/docs** for Swagger UI with interactive API documentation and testing.
