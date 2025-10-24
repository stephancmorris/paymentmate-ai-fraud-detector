# PaymentMate AI - Backend Service

Real-time fraud detection system using FastAPI, XGBoost, and SHAP explainability.

**Status**: ✅ Backend API MVP Complete (Stories 1.1-1.5)
**Test Coverage**: 94% | **Tests Passing**: 82/82

## Project Structure

```
backend/
├── app/
│   ├── api/
│   │   └── v1/           # API version 1 endpoints
│   │       └── health.py # Health check endpoints
│   ├── core/             # Core functionality
│   │   ├── config.py     # Configuration management
│   │   ├── exceptions.py # Exception handlers
│   │   ├── logging.py    # Structured logging
│   │   └── middleware.py # Custom middleware
│   ├── models/           # Pydantic models and schemas
│   ├── services/         # Business logic
│   └── utils/            # Utility functions
├── tests/                # Test suite
├── requirements.txt      # Python dependencies
└── .env.example         # Example environment variables
```

## Setup Instructions

### 1. Create Virtual Environment

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment

Copy the example environment file and configure as needed:

```bash
cp .env.example .env
```

Edit `.env` to customize settings:
- `DEBUG`: Enable/disable debug mode
- `LOG_LEVEL`: Set logging level (DEBUG, INFO, WARNING, ERROR)
- `CORS_ORIGINS`: Configure allowed frontend origins

### 4. Run the Application

```bash
# Development mode (with auto-reload)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Or using Python directly
python -m app.main
```

### 5. Access API Documentation

Once the server is running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## Testing the Backend API MVP

The backend API MVP is fully functional and ready for testing. Here are several ways to test it:

### Option 1: Interactive API Documentation (Recommended)

Visit the interactive Swagger UI at **http://localhost:8000/docs**

1. Click on any endpoint to expand it
2. Click "Try it out"
3. Fill in the request parameters
4. Click "Execute" to see the response

**Try this first**: POST `/api/v1/transaction/score`
```json
{
  "user_id": 12345,
  "amount": 99.99,
  "merchant_id": "MERCHANT_001",
  "merchant_category": "retail",
  "currency": "USD",
  "country": "US",
  "payment_method": "credit_card"
}
```

### Option 2: Using cURL (Command Line)

#### 1. Score a Transaction
```bash
curl -X POST http://localhost:8000/api/v1/transaction/score \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 12345,
    "amount": 299.99,
    "merchant_id": "MERCHANT_001",
    "merchant_category": "electronics",
    "currency": "USD",
    "country": "US",
    "payment_method": "credit_card"
  }'
```

**Expected Response**:
```json
{
  "transaction_id": "txn_abc123...",
  "score": 0.23,
  "decision": "ALLOW",
  "explanation": {
    "top_features": [
      {
        "feature_name": "transaction_amount",
        "feature_value": 299.99,
        "shap_value": 0.15,
        "contribution": "fraud"
      }
    ],
    "threshold": 0.7
  },
  "timestamp": "2025-10-23T...",
  "processing_time_ms": 0.06
}
```

#### 2. View Transaction History
```bash
# Get last 20 transactions
curl http://localhost:8000/api/v1/data/history

# Get last 10 flagged transactions
curl "http://localhost:8000/api/v1/data/history?decision=FLAG&limit=10"

# Get last 5 transactions
curl "http://localhost:8000/api/v1/data/history?limit=5"
```

#### 3. View Performance Metrics
```bash
curl http://localhost:8000/api/v1/data/metrics
```

**Expected Response**:
```json
{
  "total_transactions": 150,
  "flagged_count": 25,
  "allowed_count": 120,
  "declined_count": 5,
  "precision": 0.85,
  "recall": 0.78,
  "f1_score": 0.81,
  "average_score": 0.23,
  "losses_prevented": 12500.00,
  "false_positive_rate": 0.05,
  "timestamp": "2025-10-23T..."
}
```

#### 4. View History Statistics
```bash
curl http://localhost:8000/api/v1/data/history/stats
```

#### 5. Health Checks
```bash
# Health check
curl http://localhost:8000/api/v1/health

# Readiness check
curl http://localhost:8000/api/v1/readiness
```

### Option 3: Using Python Requests

Create a test script:

```python
import requests
import json

BASE_URL = "http://localhost:8000/api/v1"

# 1. Score multiple transactions
print("Scoring transactions...")
for i in range(10):
    response = requests.post(f"{BASE_URL}/transaction/score", json={
        "user_id": 100 + i,
        "amount": 50.0 + (i * 100),
        "merchant_id": f"MERCHANT_{i:03d}",
        "merchant_category": "retail"
    })
    data = response.json()
    print(f"Transaction {i+1}: {data['decision']} (score: {data['score']:.2f})")

# 2. View transaction history
print("\nTransaction History:")
response = requests.get(f"{BASE_URL}/data/history")
history = response.json()
print(f"Total transactions: {history['total_count']}")
print(f"Returned: {history['returned_count']}")

# 3. View performance metrics
print("\nPerformance Metrics:")
response = requests.get(f"{BASE_URL}/data/metrics")
metrics = response.json()
print(f"Total: {metrics['total_transactions']}")
print(f"Precision: {metrics['precision']:.2%}")
print(f"Recall: {metrics['recall']:.2%}")
print(f"F1 Score: {metrics['f1_score']:.2%}")
print(f"Losses Prevented: ${metrics['losses_prevented']:,.2f}")
```

Save as `test_api.py` and run:
```bash
python test_api.py
```

### Option 4: Run Automated Tests

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run with coverage report
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_transaction.py -v
pytest tests/test_history.py -v
pytest tests/test_metrics.py -v

# View coverage report
open htmlcov/index.html  # macOS
# or
xdg-open htmlcov/index.html  # Linux
```

**Expected Output**:
```
======================== 82 passed in 2.76s ========================
Coverage: 94%
```

### Option 5: End-to-End Testing Workflow

Test the complete fraud detection workflow:

```bash
# 1. Start the server
uvicorn app.main:app --reload

# 2. In another terminal, run this workflow:

# Score a low-risk transaction (should be ALLOWED)
curl -X POST http://localhost:8000/api/v1/transaction/score \
  -H "Content-Type: application/json" \
  -d '{"user_id": 1, "amount": 25.00, "merchant_id": "M001"}'

# Score a high-risk transaction (should be FLAGGED/DECLINED)
curl -X POST http://localhost:8000/api/v1/transaction/score \
  -H "Content-Type: application/json" \
  -d '{"user_id": 999, "amount": 5000.00, "merchant_id": "M002", "merchant_category": "crypto"}'

# View the history to see both transactions
curl http://localhost:8000/api/v1/data/history

# Check metrics to see performance stats
curl http://localhost:8000/api/v1/data/metrics
```

### Testing Different Scenarios

#### Low Risk Transaction (Expected: ALLOW)
```bash
curl -X POST http://localhost:8000/api/v1/transaction/score \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 100,
    "amount": 49.99,
    "merchant_id": "MERCHANT_RETAIL",
    "merchant_category": "retail"
  }'
```

#### Medium Risk Transaction (Expected: ALLOW or FLAG)
```bash
curl -X POST http://localhost:8000/api/v1/transaction/score \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 500,
    "amount": 599.99,
    "merchant_id": "MERCHANT_ELECTRONICS",
    "merchant_category": "electronics"
  }'
```

#### High Risk Transaction (Expected: FLAG or DECLINE)
```bash
curl -X POST http://localhost:8000/api/v1/transaction/score \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 999,
    "amount": 4999.99,
    "merchant_id": "MERCHANT_CRYPTO",
    "merchant_category": "crypto"
  }'
```

### Validation Testing

Test input validation:

```bash
# Negative amount (should fail with 422)
curl -X POST http://localhost:8000/api/v1/transaction/score \
  -H "Content-Type: application/json" \
  -d '{"user_id": 1, "amount": -50.00, "merchant_id": "M001"}'

# Missing required field (should fail with 422)
curl -X POST http://localhost:8000/api/v1/transaction/score \
  -H "Content-Type: application/json" \
  -d '{"user_id": 1, "merchant_id": "M001"}'

# Future timestamp (should fail with 422)
curl -X POST http://localhost:8000/api/v1/transaction/score \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 1,
    "amount": 100.00,
    "merchant_id": "M001",
    "timestamp": "2030-01-01T00:00:00Z"
  }'
```

### Performance Testing

Test the <100ms latency requirement:

```bash
# Run multiple requests and check processing_time_ms in responses
for i in {1..10}; do
  curl -X POST http://localhost:8000/api/v1/transaction/score \
    -H "Content-Type: application/json" \
    -d "{\"user_id\": $i, \"amount\": 100.00, \"merchant_id\": \"M001\"}" \
    | jq '.processing_time_ms'
done
```

All response times should be well under 100ms (typically <1ms for placeholder scoring).

---

## Test Results

Current test suite status:

```
Total Tests: 82
Passing: 82 (100%)
Code Coverage: 94%

Test Breakdown:
- Health & Monitoring: 9 tests
- Data Models: 30 tests
- Transaction Scoring: 21 tests
- Transaction History: 16 tests
- Performance Metrics: 16 tests
```

## Available Endpoints

### Monitoring
- `GET /` - Service information
- `GET /api/v1/health` - Health check endpoint
- `GET /api/v1/readiness` - Readiness check endpoint

### Transaction Scoring
- `POST /api/v1/transaction/score` - Score a transaction for fraud risk
  - Returns: fraud score (0-1), decision (ALLOW/FLAG/DECLINE), SHAP explanation

### Data & Analytics
- `GET /api/v1/data/history` - Get transaction history (supports filtering & pagination)
- `GET /api/v1/data/history/stats` - Get transaction statistics by decision type
- `GET /api/v1/data/metrics` - Get system performance metrics (precision, recall, F1)
- `DELETE /api/v1/data/history` - Clear transaction history (testing only)

## Development

### Code Quality

```bash
# Format code
black app/ tests/

# Lint code
flake8 app/ tests/

# Type checking
mypy app/
```

### Adding New Endpoints

1. Create a new router file in `app/api/v1/`
2. Define your endpoints using FastAPI decorators
3. Create Pydantic models in `app/models/`
4. Register the router in `app/main.py`

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `APP_NAME` | Application name | PaymentMate AI |
| `DEBUG` | Debug mode | False |
| `ENVIRONMENT` | Environment (development/staging/production) | development |
| `LOG_LEVEL` | Logging level | INFO |
| `LOG_FORMAT` | Log format (json/text) | json |
| `CORS_ORIGINS` | Allowed CORS origins | ["http://localhost:3000"] |
| `MODEL_PATH` | Path to ML model file | models/fraud_detector.pkl |
| `MODEL_THRESHOLD` | Fraud detection threshold | 0.7 |

## Performance Targets

- **Latency**: Transaction scoring must complete in <100ms
- **Throughput**: Handle concurrent requests efficiently
- **Availability**: 99.9% uptime target

## Completed Features ✅

- ✅ FastAPI project setup with best practices (Story 1.1)
- ✅ Pydantic data models with validation (Story 1.2)
- ✅ Transaction scoring endpoint with placeholder logic (Story 1.3)
- ✅ Transaction history with filtering & pagination (Story 1.4)
- ✅ Performance metrics tracking (Story 1.5)
- ✅ Health check & monitoring endpoints
- ✅ Structured JSON logging
- ✅ Request ID tracking
- ✅ CORS middleware
- ✅ Exception handling
- ✅ 94% test coverage

## Next Steps

- [ ] Integrate XGBoost model for real scoring (Story 2.3)
- [ ] Generate synthetic training data (Story 2.1)
- [ ] Implement feature engineering pipeline (Epic 3)
- [ ] Add real SHAP explainability (Story 2.4)
- [ ] Build React frontend dashboard (Epic 4)

## License

Copyright © 2025 PaymentMate AI
