#!/bin/bash
# Klaus - Factory Reset
# ================================
# Resets everything to factory defaults.
# WARNING: This deletes all configurations and memories!

echo "🔄 Klaus - Factory Reset"
echo "===================================="
echo ""
echo "⚠️  WARNING: This will delete:"
echo "   • init.yaml (configuration)"
echo "   • .env (API keys)"
echo "   • workspace/SOUL.md (agent identity)"
echo "   • workspace/USER.md (user profile)"
echo "   • workspace/memory/ (all memories)"
echo "   • workspace/sessions/, cognitive_memory/, semantic_memory/"
echo "   • .venv/ (virtual environment)"
echo ""

read -p "Are you sure? Type 'yes' to continue: " confirm

if [ "$confirm" != "yes" ]; then
    echo "❌ Reset cancelled."
    exit 0
fi

cd "$(dirname "$0")/.."

echo ""
echo "🗑️  Cleaning up..."

# Stop and remove Docker containers
if command -v docker &> /dev/null; then
    echo "   🐳 Stopping Docker containers..."
    docker compose -f docker/docker-compose.yml --profile web --profile telegram down 2>/dev/null || true
    echo "   ✓ Docker containers stopped"
fi

# Remove configuration
rm -f init.yaml   && echo "   ✓ Removed init.yaml"
rm -f .env        && echo "   ✓ Removed .env"

# Remove workspace files
rm -f workspace/SOUL.md     && echo "   ✓ Removed workspace/SOUL.md"
rm -f workspace/USER.md     && echo "   ✓ Removed workspace/USER.md"
rm -f workspace/memory.db   && echo "   ✓ Removed workspace/memory.db"

# Remove memory and session data
rm -rf workspace/memory           && echo "   ✓ Removed workspace/memory/"
rm -rf workspace/sessions         && echo "   ✓ Removed workspace/sessions/"
rm -rf workspace/cognitive_memory && echo "   ✓ Removed workspace/cognitive_memory/"
rm -rf workspace/semantic_memory  && echo "   ✓ Removed workspace/semantic_memory/"
rm -rf workspace/web_ui_data      && echo "   ✓ Removed workspace/web_ui_data/"

# Remove virtual environment
rm -rf .venv && echo "   ✓ Removed .venv/"

echo ""
echo "✅ Reset complete!"
echo ""
echo "🚀 To start fresh, run:"
echo "   ./setup.sh"
