#!/bin/bash
# IDE Agent Wizard - Port Configuration
# =====================================
# Configure custom ports before running setup.sh
# Usage: ./port-setup.sh

set -e

echo "🔧 IDE Agent Wizard - Port Configuration"
echo "========================================"
echo ""

# Default ports
DEFAULT_KIMI_PORT=8081
DEFAULT_WEB_PORT=8082

# Ask for ports
echo "Enter the ports you want to use (press Enter for defaults):"
echo ""
read -p "Kimi Agent port [$DEFAULT_KIMI_PORT]: " KIMI_PORT
KIMI_PORT=${KIMI_PORT:-$DEFAULT_KIMI_PORT}

read -p "Web UI port [$DEFAULT_WEB_PORT]: " WEB_PORT
WEB_PORT=${WEB_PORT:-$DEFAULT_WEB_PORT}

echo ""
echo "Configuring ports:"
echo "  - Kimi Agent: $KIMI_PORT"
echo "  - Web UI: $WEB_PORT"
echo ""

# Confirm
read -p "Proceed? [Y/n]: " CONFIRM
CONFIRM=${CONFIRM:-Y}

if [[ ! $CONFIRM =~ ^[Yy]$ ]]; then
    echo "Cancelled."
    exit 0
fi

echo ""
echo "📝 Updating configuration files..."

# 1. Update docker-compose.yml
echo "  - docker/docker-compose.yml"
sed -i.bak "s/- \"$DEFAULT_KIMI_PORT:8080\"/\"$KIMI_PORT:8080\"/g" ../docker/docker-compose.yml
sed -i.bak "s/- \"$DEFAULT_WEB_PORT:$DEFAULT_WEB_PORT\"/\"$WEB_PORT:$DEFAULT_WEB_PORT\"/g" ../docker/docker-compose.yml
rm -f ../docker/docker-compose.yml.bak

# 2. Update web-ui Dockerfile
echo "  - docker/web-ui/Dockerfile"
sed -i.bak "s/EXPOSE $DEFAULT_WEB_PORT/EXPOSE $WEB_PORT/g" ../docker/web-ui/Dockerfile
sed -i.bak "s/WEB_UI_PORT=$DEFAULT_WEB_PORT/WEB_UI_PORT=$WEB_PORT/g" ../docker/web-ui/Dockerfile
rm -f ../docker/web-ui/Dockerfile.bak

# 3. Update app.py (WEB_UI_PORT default)
echo "  - docker/web-ui/app.py"
sed -i.bak "s/WEB_UI_PORT = int(os.getenv(\"WEB_UI_PORT\", \"$DEFAULT_WEB_PORT\"))/WEB_UI_PORT = int(os.getenv(\"WEB_UI_PORT\", \"$WEB_PORT\"))/g" ../docker/web-ui/app.py
rm -f ../docker/web-ui/app.py.bak

# 4. Update setup.sh messages
echo "  - scripts/setup.sh"
sed -i.bak "s/localhost:$DEFAULT_WEB_PORT/localhost:$WEB_PORT/g" setup.sh
rm -f setup.sh.bak

# 5. Update health_check.sh
echo "  - scripts/health_check.sh"
sed -i.bak "s/localhost:$DEFAULT_KIMI_PORT/localhost:$KIMI_PORT/g" scripts/health_check.sh
sed -i.bak "s/localhost:$DEFAULT_WEB_PORT/localhost:$WEB_PORT/g" scripts/health_check.sh
rm -f scripts/health_check.sh.bak

echo ""
echo "✅ Ports configured successfully!"
echo ""
echo "Next steps:"
echo "  1. Copy .env.example to .env and add your API keys"
echo "  2. Run: ./scripts/setup.sh"
echo ""
echo "Your services will be available at:"
echo "  - Web UI: http://localhost:$WEB_PORT"
echo "  - Kimi Agent: http://localhost:$KIMI_PORT"
echo ""
