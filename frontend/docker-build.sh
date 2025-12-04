#!/bin/bash
# PaymentMate AI - Frontend Docker Build Script

set -e

echo "Building PaymentMate AI Frontend Docker Image..."

# Build the image
docker build -t paymentmate-ai-frontend:latest .

echo "✅ Image built successfully: paymentmate-ai-frontend:latest"
echo ""
echo "To run the container:"
echo "  docker run -p 80:80 paymentmate-ai-frontend:latest"
echo ""
echo "To run with environment variables:"
echo "  docker run -p 80:80 -e VITE_API_BASE_URL=http://localhost:8000 paymentmate-ai-frontend:latest"
