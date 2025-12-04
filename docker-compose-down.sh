#!/bin/bash
# PaymentMate AI - Docker Compose Shutdown Script

set -e

echo "=========================================="
echo "PaymentMate AI - Stopping All Services"
echo "=========================================="
echo ""

# Check if user wants to remove volumes
if [ "$1" = "-v" ] || [ "$1" = "--volumes" ]; then
    echo "🗑️  Stopping services and removing volumes..."
    docker-compose down -v
    echo "✅ Services stopped and volumes removed"
else
    echo "🛑 Stopping services..."
    docker-compose down
    echo "✅ Services stopped (volumes preserved)"
    echo ""
    echo "To remove volumes as well, run:"
    echo "  ./docker-compose-down.sh -v"
fi

echo ""
