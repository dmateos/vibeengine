#!/bin/bash
# Development start script with hot reloading

echo "🚀 Starting VibeEngine in DEVELOPMENT mode..."
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker and try again."
    exit 1
fi

# Ask user which mode
echo "Choose development mode:"
echo "  1) With nginx proxy (access via http://localhost)"
echo "  2) Direct access (Frontend: :5173, API: :8000)"
read -p "Enter choice [1-2, default: 2]: " choice
choice=${choice:-2}

if [ "$choice" = "1" ]; then
    echo ""
    echo "📦 Starting with nginx proxy..."
    docker-compose -f docker-compose.dev.yml --profile with-nginx up -d --build
    echo ""
    echo "✅ Services started with nginx!"
    echo ""
    echo "📍 Access Points:"
    echo "   Full App:  http://localhost"
    echo "   Frontend:  http://localhost:5173 (direct, with HMR)"
    echo "   API:       http://localhost:8000 (direct)"
    echo "   API (via nginx): http://localhost/api/"
else
    echo ""
    echo "📦 Starting without nginx..."
    docker-compose -f docker-compose.dev.yml up -d --build
    echo ""
    echo "✅ Services started!"
    echo ""
    echo "📍 Access Points:"
    echo "   Frontend:  http://localhost:5173 (with hot reload)"
    echo "   API:       http://localhost:8000"
    echo "   Admin:     http://localhost:8000/admin/"
fi

echo ""
echo "⏳ Waiting for services..."
sleep 5

# Check service status
echo ""
echo "📊 Service Status:"
docker-compose -f docker-compose.dev.yml ps

echo ""
echo "📝 Useful commands:"
echo "   View logs:        docker-compose -f docker-compose.dev.yml logs -f"
echo "   Frontend logs:    docker-compose -f docker-compose.dev.yml logs -f frontend"
echo "   Backend logs:     docker-compose -f docker-compose.dev.yml logs -f web"
echo "   Stop services:    docker-compose -f docker-compose.dev.yml down"
echo "   Django shell:     docker-compose -f docker-compose.dev.yml exec web python manage.py shell"
echo ""
echo "💡 The frontend has HOT RELOAD enabled - changes will reflect immediately!"
echo ""
