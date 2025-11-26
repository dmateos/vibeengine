#!/bin/bash

# VibeEngine Setup Script
# This script helps you set up VibeEngine on a new machine

echo "🚀 VibeEngine Setup"
echo "===================="
echo ""

# Check Python version
echo "Checking Python version..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "✓ Python $python_version found"
echo ""

# Check Node.js version
echo "Checking Node.js version..."
node_version=$(node --version 2>&1)
echo "✓ Node.js $node_version found"
echo ""

# Create virtual environment
echo "Creating Python virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✓ Virtual environment created"
else
    echo "✓ Virtual environment already exists"
fi
echo ""

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate
echo "✓ Virtual environment activated"
echo ""

# Install Python dependencies
echo "Installing Python dependencies..."
pip install -r requirements.txt
echo "✓ Python dependencies installed"
echo ""

# Copy .env.example if .env doesn't exist
if [ ! -f ".env" ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
    echo "✓ .env file created"
    echo "⚠️  Please edit .env and add your API keys!"
    echo ""
else
    echo "✓ .env file already exists"
    echo ""
fi

# Run migrations
echo "Running database migrations..."
python manage.py migrate
echo "✓ Migrations completed"
echo ""

# Check if superuser exists
echo "Checking for Django superuser..."
python manage.py shell -c "from django.contrib.auth.models import User; exit(0 if User.objects.filter(is_superuser=True).exists() else 1)" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "Creating Django superuser..."
    echo "Please follow the prompts:"
    python manage.py createsuperuser
    echo ""
else
    echo "✓ Superuser already exists"
    echo ""
fi

# Install frontend dependencies
echo "Installing frontend dependencies..."
cd frontend
npm install
echo "✓ Frontend dependencies installed"
cd ..
echo ""

# Done
echo "✅ Setup Complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env and add your API keys (OPENAI_API_KEY, ANTHROPIC_API_KEY)"
echo "2. Start the backend:  python manage.py runserver"
echo "3. Start the frontend: cd frontend && npm run dev"
echo "4. Open http://localhost:5173 in your browser"
echo ""
echo "Happy building! 🎉"
