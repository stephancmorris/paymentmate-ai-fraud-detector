#!/bin/bash
# PaymentMate AI - Docker Build Script

set -e

echo "Building PaymentMate AI Backend Docker Image..."

# Build the image
docker build -t paymentmate-ai-backend:latest .

echo "✅ Image built successfully: paymentmate-ai-backend:latest"
echo ""
echo "To run the container:"
echo "  docker run -p 8000:8000 paymentmate-ai-backend:latest"
echo ""
echo "To run with environment variables:"
echo "  docker run -p 8000:8000 --env-file .env paymentmate-ai-backend:latest"
