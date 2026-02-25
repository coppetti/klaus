#!/bin/bash
# IDE Agent Wizard - Start Services
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

echo -e "${BLUE}🚀 IDE Agent Wizard - Starting Services${NC}"
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

start_web() {
    echo -e "${BLUE}🌐 Starting Web UI...${NC}"
    docker compose -f "$COMPOSE_FILE" --profile web up -d
    echo -e "${GREEN}✅ Web UI started!${NC}"
    echo "   Access: http://localhost:8082"
    echo ""
}

start_telegram() {
    echo -e "${BLUE}📱 Starting Telegram Bot...${NC}"
    docker compose -f "$COMPOSE_FILE" up -d
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
        start_telegram
        start_web
        ;;
esac

echo -e "${GREEN}✅ All services started!${NC}"
echo ""
echo "📊 Check status: docker ps"
echo "📜 View logs: docker compose -f $COMPOSE_FILE logs -f"
echo "🛑 Stop all: docker compose -f $COMPOSE_FILE --profile web down"
