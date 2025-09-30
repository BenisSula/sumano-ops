#!/bin/bash
# Sumano OMS Development Startup Script

echo "🚀 Starting Sumano OMS Development Environment"
echo "=============================================="

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker Desktop."
    exit 1
fi

# Check if .env file exists
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp env.example .env
    echo "✅ .env file created. Please review and update as needed."
fi

# Build and start services
echo "🔨 Building and starting services..."
docker-compose up --build -d

# Wait for services to start
echo "⏳ Waiting for services to start..."
sleep 10

# Check health
echo "🏥 Checking service health..."
if curl -f http://localhost:8000/health/ > /dev/null 2>&1; then
    echo "✅ Backend is healthy!"
    echo "🌐 Backend API: http://localhost:8000"
    echo "🏥 Health Check: http://localhost:8000/health/"
    echo "📄 PDF Test: http://localhost:8000/api/pdf/test/"
else
    echo "❌ Backend health check failed. Check logs with: docker-compose logs"
fi

echo ""
echo "📋 Useful commands:"
echo "  View logs: docker-compose logs -f"
echo "  Stop services: docker-compose down"
echo "  Restart: docker-compose restart"
echo "  Shell access: docker-compose exec ops_backend bash"
