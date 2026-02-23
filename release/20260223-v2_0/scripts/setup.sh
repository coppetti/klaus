#!/bin/bash
# IDE Agent Wizard Setup with Virtual Environment
# ================================================
# Called from root via launcher script

set -e

cd "$(dirname "$0")/.."

echo "🧙 IDE Agent Wizard Setup"
echo ""

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv .venv
fi

# Activate virtual environment
echo "🚀 Activating virtual environment..."
source .venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install -q -r requirements.txt

echo "✅ Dependencies installed!"
echo ""

# Run setup wizard
echo "🎯 Starting setup wizard..."
echo ""
python scripts/setup_wizard.py

# Post-setup initialization
echo ""
echo "🔧 Running post-setup initialization..."
python scripts/initialize.py

echo ""
echo "✅ Setup and initialization complete!"
echo ""

# Check if Telegram/Hybrid mode and start Docker
if grep -q "primary: telegram\|primary: hybrid" init.yaml 2>/dev/null; then
    echo "🐳 Telegram/Hybrid mode detected!"
    echo ""
    echo "Starting Docker containers..."
    # Must run from project root where .env is located
    cd "$(dirname "$0")/.."
    docker compose -f docker/docker-compose.yml up -d
    echo ""
    echo "✅ Docker containers started!"
    echo "   Check status: docker ps"
    echo "   View logs: docker compose -f docker/docker-compose.yml logs -f"
    echo ""
    echo "Your Telegram bot is now running!"
    echo "Test it by sending /start in Telegram."
else
    echo "Next steps:"
    echo "  1. Start chatting: python cli/agent-cli.py chat"
    echo "  2. Or just start asking me questions!"
fi

# Deactivate
deactivate
