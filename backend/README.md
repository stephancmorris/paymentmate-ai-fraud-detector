# PaymentMate AI - Backend Service

Real-time fraud detection system using FastAPI, XGBoost, and SHAP explainability.

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

### 5. Run Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_health.py -v
```

## API Documentation

Once the server is running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Available Endpoints

### Monitoring
- `GET /health` - Health check endpoint
- `GET /readiness` - Readiness check endpoint

### Root
- `GET /` - Service information

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

## Next Steps

- [ ] Implement transaction scoring endpoint (Story 1.3)
- [ ] Create Pydantic data models (Story 1.2)
- [ ] Integrate XGBoost model (Story 2.3)
- [ ] Implement feature engineering pipeline (Epic 3)
- [ ] Add SHAP explainability (Story 2.4)

## License

Copyright © 2025 PaymentMate AI
