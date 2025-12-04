#!/bin/bash
# PaymentMate AI - Docker Compose Startup Script

set -e

echo "=========================================="
echo "PaymentMate AI - Starting All Services"
echo "=========================================="
echo ""

# Check if .env exists, create from .env.example if not
if [ ! -f .env ]; then
    echo "⚠️  No .env file found"
    if [ -f .env.example ]; then
        echo "📄 Creating .env from .env.example"
        cp .env.example .env
        echo "✅ Created .env file (you can customize it if needed)"
    else
        echo "Using default environment variables"
    fi
    echo ""
fi

# Build images
echo "🔨 Building Docker images..."
docker-compose build

echo ""
echo "🚀 Starting services..."
docker-compose up -d

echo ""
echo "⏳ Waiting for services to become healthy..."

# Wait for backend to be healthy
timeout=60
elapsed=0
while [ $elapsed -lt $timeout ]; do
    if docker-compose ps | grep -q "backend.*healthy"; then
        echo "✅ Backend is healthy"
        break
    fi
    sleep 2
    elapsed=$((elapsed + 2))
    echo "   Waiting for backend... (${elapsed}s)"
done

# Wait for frontend to be healthy
elapsed=0
while [ $elapsed -lt $timeout ]; do
    if docker-compose ps | grep -q "frontend.*healthy"; then
        echo "✅ Frontend is healthy"
        break
    fi
    sleep 2
    elapsed=$((elapsed + 2))
    echo "   Waiting for frontend... (${elapsed}s)"
done

echo ""
echo "=========================================="
echo "✅ PaymentMate AI is running!"
echo "=========================================="
echo ""
echo "🌐 Frontend Dashboard:  http://localhost"
echo "🔧 Backend API:          http://localhost:8000"
echo "📚 API Documentation:    http://localhost:8000/docs"
echo "❤️  Backend Health:      http://localhost:8000/health"
echo "📊 Redis:                localhost:6379"
echo ""
echo "To view logs:"
echo "  docker-compose logs -f"
echo ""
echo "To view service status:"
echo "  docker-compose ps"
echo ""
echo "To stop all services:"
echo "  docker-compose down"
echo ""
echo "To stop and remove volumes:"
echo "  docker-compose down -v"
echo ""
