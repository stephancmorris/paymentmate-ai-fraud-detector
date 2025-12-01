#!/bin/bash
# PaymentMate AI - Docker Run Script

set -e

echo "Running PaymentMate AI Backend Container..."

# Check if .env exists
if [ -f .env ]; then
    echo "Using .env file for environment variables"
    docker run -d \
        --name paymentmate-backend \
        -p 8000:8000 \
        --env-file .env \
        paymentmate-ai-backend:latest
else
    echo "No .env file found, using defaults"
    docker run -d \
        --name paymentmate-backend \
        -p 8000:8000 \
        paymentmate-ai-backend:latest
fi

echo "✅ Container started: paymentmate-backend"
echo ""
echo "Container is running at: http://localhost:8000"
echo "Health check: http://localhost:8000/health"
echo "API docs: http://localhost:8000/docs"
echo ""
echo "To view logs:"
echo "  docker logs -f paymentmate-backend"
echo ""
echo "To stop the container:"
echo "  docker stop paymentmate-backend"
echo ""
echo "To remove the container:"
echo "  docker rm paymentmate-backend"
