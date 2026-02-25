#!/bin/bash
# IDE Agent Wizard - Factory Reset
# ================================
# Resets everything to factory defaults.
# WARNING: This deletes all configurations and memories!

set -e

echo "🔄 IDE Agent Wizard - Factory Reset"
echo "===================================="
echo ""
echo "⚠️  WARNING: This will delete:"
echo "   • init.yaml (configuration)"
echo "   • workspace/SOUL.md (agent identity)"
echo "   • workspace/USER.md (user profile)"
echo "   • workspace/memory/ (all memories)"
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

# Stop Docker containers if running
if command -v docker &> /dev/null; then
    if docker ps | grep -q "ide-agent"; then
        echo "   🐳 Stopping Docker containers..."
        docker compose -f docker/docker-compose.yml down 2>/dev/null || true
        echo "   ✓ Docker containers stopped"
    fi
fi

# Remove configuration
[ -f "init.yaml" ] && rm init.yaml && echo "   ✓ Removed init.yaml"

# Remove workspace files
[ -f "workspace/SOUL.md" ] && rm workspace/SOUL.md && echo "   ✓ Removed workspace/SOUL.md"
[ -f "workspace/USER.md" ] && rm workspace/USER.md && echo "   ✓ Removed workspace/USER.md"
[ -f "workspace/memory.db" ] && rm workspace/memory.db && echo "   ✓ Removed workspace/memory.db"

# Remove memory directory
[ -d "workspace/memory" ] && rm -rf workspace/memory && echo "   ✓ Removed workspace/memory/"

# Remove projects (optional - keep structure)
# [ -d "workspace/projects" ] && rm -rf workspace/projects/*

# Remove virtual environment
[ -d ".venv" ] && rm -rf .venv && echo "   ✓ Removed .venv/"

echo ""
echo "✅ Reset complete!"
echo ""
echo "🚀 To start fresh, run:"
echo "   ./setup.sh"
