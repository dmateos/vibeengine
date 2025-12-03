#!/bin/bash
# Quick start script for VibeEngine Docker setup

echo "🚀 Starting VibeEngine with Docker..."
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker and try again."
    exit 1
fi

# Build and start services
echo "📦 Building Docker images..."
docker-compose build

echo ""
echo "🎯 Starting services..."
docker-compose up -d

echo ""
echo "⏳ Waiting for services to be ready..."
sleep 10

# Check service status
echo ""
echo "📊 Service Status:"
docker-compose ps

echo ""
echo "✅ VibeEngine is starting up!"
echo ""
echo "📍 Access Points:"
echo "   Frontend:  http://localhost"
echo "   API:       http://localhost/api/"
echo "   Admin:     http://localhost/admin/"
echo ""
echo "📝 View logs:"
echo "   docker-compose logs -f"
echo ""
echo "🛑 Stop services:"
echo "   docker-compose down"
echo ""
