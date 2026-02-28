#!/bin/bash
# Klaus - Stop Services
# ================================
# Stops all Docker services

set -e

cd "$(dirname "$0")"
COMPOSE_FILE="../docker/docker-compose.yml"

echo "🛑 Stopping Klaus Services..."
echo "========================================"
echo ""

# Stop SDK-created orphan containers (not managed by docker compose)
docker stop Klaus_Telegaaf 2>/dev/null || true
docker rm Klaus_Telegaaf 2>/dev/null || true

docker compose -f "$COMPOSE_FILE" --profile web --profile telegram down

echo ""
echo "✅ All services stopped!"
