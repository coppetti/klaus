#!/bin/bash
# IDE Agent Wizard Setup with Virtual Environment
# ================================================
# Called from root via launcher script
# v2.1.0 - Supports IDE | WEB | IDE+WEB modes

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

# Detect mode from init.yaml
TELEGRAM_ENABLED=false
WEB_ENABLED=false

if [ -f "init.yaml" ]; then
    if grep -q "telegram:" init.yaml 2>/dev/null && grep -A5 "telegram:" init.yaml | grep -q "enabled: true"; then
        TELEGRAM_ENABLED=true
    fi
    if grep -q "web:" init.yaml 2>/dev/null && grep -A5 "web:" init.yaml | grep -q "enabled: true"; then
        WEB_ENABLED=true
    fi
fi

# Start Docker containers based on mode
if [ "$TELEGRAM_ENABLED" = true ] || [ "$WEB_ENABLED" = true ]; then
    echo "🐳 Docker services needed!"
    echo ""
    
    cd "$(dirname "$0")/.."
    
    if [ "$WEB_ENABLED" = true ]; then
        echo "Starting Docker with Web UI (port 8082)..."
        docker compose -f docker/docker-compose.yml --profile web up -d
        echo ""
        echo "✅ Web UI started!"
        echo "   Access: http://localhost:8082"
    else
        echo "Starting Docker containers..."
        docker compose -f docker/docker-compose.yml up -d
    fi
    
    if [ "$TELEGRAM_ENABLED" = true ]; then
        echo ""
        echo "✅ Telegram Bot started!"
        echo "   Send /start in Telegram to test."
    fi
    
    echo ""
    echo "📊 Check status: docker ps"
    echo "📜 View logs: docker compose -f docker/docker-compose.yml logs -f"
else
    echo "🎯 IDE Only mode selected."
    echo ""
    echo "Next steps:"
    echo "  1. Start chatting: python cli/agent-cli.py chat"
    echo "  2. Or just start asking me questions!"
fi

echo ""

# Deactivate
deactivate
