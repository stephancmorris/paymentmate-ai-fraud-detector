#!/bin/bash
# PaymentMate AI - Frontend Docker Run Script

set -e

echo "Running PaymentMate AI Frontend Container..."

# Check if backend URL is provided
if [ -z "$VITE_API_BASE_URL" ]; then
    echo "Using default API URL: http://localhost:8000"
    VITE_API_BASE_URL="http://localhost:8000"
else
    echo "Using API URL: $VITE_API_BASE_URL"
fi

# Run container
docker run -d \
    --name paymentmate-frontend \
    -p 80:80 \
    -e VITE_API_BASE_URL="$VITE_API_BASE_URL" \
    -e VITE_API_VERSION="${VITE_API_VERSION:-v1}" \
    -e VITE_POLL_INTERVAL="${VITE_POLL_INTERVAL:-2000}" \
    -e VITE_DEBUG="${VITE_DEBUG:-false}" \
    paymentmate-ai-frontend:latest

echo "✅ Container started: paymentmate-frontend"
echo ""
echo "Frontend is running at: http://localhost"
echo "Health check: http://localhost/health"
echo ""
echo "To view logs:"
echo "  docker logs -f paymentmate-frontend"
echo ""
echo "To stop the container:"
echo "  docker stop paymentmate-frontend"
echo ""
echo "To remove the container:"
echo "  docker rm paymentmate-frontend"
