#!/bin/bash
# Klaus - Auto-Start Installation
# ==========================================
# Configures services to start automatically on macOS login
# Usage: ./install-auto-start.sh

set -e

PLIST_NAME="com.ide-agent-wizard.services.plist"
PLIST_PATH="$HOME/Library/LaunchAgents/$PLIST_NAME"
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

echo "🔧 Klaus - Auto-Start Configuration"
echo "=============================================="
echo ""

# Check if running on macOS
if [[ "$OSTYPE" != "darwin"* ]]; then
    echo "❌ This script is for macOS only."
    echo "   For Linux, use systemd: systemctl enable docker-compose@ide-agent"
    exit 1
fi

echo "📁 Project directory: $PROJECT_DIR"
echo "📝 Creating LaunchAgent plist..."

# Create LaunchAgent plist
cat > "$PLIST_PATH" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.ide-agent-wizard.services</string>
    
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>$PROJECT_DIR/scripts/start-services.sh</string>
        <string>all</string>
    </array>
    
    <key>RunAtLoad</key>
    <true/>
    
    <key>KeepAlive</key>
    <false/>
    
    <key>StandardOutPath</key>
    <string>$PROJECT_DIR/scripts/logs/services.out</string>
    
    <key>StandardErrorPath</key>
    <string>$PROJECT_DIR/scripts/logs/services.err</string>
    
    <key>WorkingDirectory</key>
    <string>$PROJECT_DIR</string>
    
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin:/opt/homebrew/bin</string>
    </dict>
</dict>
</plist>
EOF

# Create logs directory
mkdir -p "$PROJECT_DIR/logs"

echo "✅ LaunchAgent created at: $PLIST_PATH"
echo ""

# Load the LaunchAgent
echo "🚀 Loading LaunchAgent..."
launchctl load "$PLIST_PATH" 2>/dev/null || launchctl bootstrap gui/$(id -u) "$PLIST_PATH"

echo "✅ Auto-start configured!"
echo ""
echo "Services will start automatically when you login."
echo ""
echo "Commands:"
echo "  Start now:    ./scripts/start-services.sh"
echo "  Stop:         docker compose -f docker/docker-compose.yml --profile web down"
echo "  Disable:      launchctl unload ~/Library/LaunchAgents/$PLIST_NAME"
echo "  Re-enable:    launchctl load ~/Library/LaunchAgents/$PLIST_NAME"
echo ""
echo "Logs:"
echo "  Output:       logs/services.out"
echo "  Errors:       logs/services.err"
