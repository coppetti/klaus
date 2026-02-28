#!/bin/bash
# Klaus - Start Services
# =================================
# Starts Web UI and Telegram Bot services
# Usage: ./start-services.sh [web|telegram|all]

set -e

cd "$(dirname "$0")"
COMPOSE_FILE="../docker/docker-compose.yml"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Klaus - Starting Services${NC}"
echo "========================================"
echo ""

# Check Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  Docker is not running. Please start Docker Desktop first.${NC}"
    echo ""
    echo "Starting Docker Desktop..."
    open -a Docker
    
    # Wait for Docker to start
    echo "Waiting for Docker to be ready..."
    for i in {1..30}; do
        if docker info > /dev/null 2>&1; then
            echo -e "${GREEN}✅ Docker is ready!${NC}"
            break
        fi
        sleep 2
        echo -n "."
    done
    
    if ! docker info > /dev/null 2>&1; then
        echo -e "${YELLOW}❌ Docker failed to start. Please start it manually.${NC}"
        exit 1
    fi
    echo ""
fi

# Determine what to start
MODE="${1:-all}"

# Check if telegram is configured and enabled in init.yaml
is_telegram_configured() {
    INIT_YAML="../init.yaml"
    if [ ! -f "$INIT_YAML" ]; then return 1; fi
    grep -A5 "telegram:" "$INIT_YAML" | grep -q "enabled: true"
}

start_web() {
    echo -e "${BLUE}🌐 Starting Web UI...${NC}"
    docker compose -f "$COMPOSE_FILE" --profile web up -d
    echo -e "${GREEN}✅ Web UI started!${NC}"
    echo "   Access: http://localhost:12049"
    echo ""
}

start_telegram() {
    echo -e "${BLUE}📱 Starting Telegram Bot...${NC}"
    docker compose -f "$COMPOSE_FILE" --profile telegram up -d
    echo -e "${GREEN}✅ Telegram Bot started!${NC}"
    echo ""
}

case "$MODE" in
    web)
        start_web
        ;;
    telegram)
        start_telegram
        ;;
    all|*)
        if is_telegram_configured; then
            start_telegram
        else
            echo -e "${YELLOW}⚠️  Telegram not configured — skipping.${NC}"
            echo ""
        fi
        start_web
        ;;
esac

echo -e "${GREEN}✅ All services started!${NC}"
echo ""
echo "📊 Check status: docker ps"
echo "📜 View logs: docker compose -f $COMPOSE_FILE logs -f"
echo "🛑 Stop all: docker compose -f $COMPOSE_FILE --profile web down"
