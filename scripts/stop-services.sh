#!/bin/bash
# IDE Agent Wizard - Stop Services
# ================================
# Stops all Docker services

set -e

cd "$(dirname "$0")"
COMPOSE_FILE="../docker/docker-compose.yml"

echo "🛑 Stopping IDE Agent Wizard Services..."
echo "========================================"
echo ""

docker compose -f "$COMPOSE_FILE" --profile web down

echo ""
echo "✅ All services stopped!"
