# Quick Start Guide - IDE Agent Wizard v2.1

> Get up and running in 5 minutes

## Prerequisites

- Python 3.11+
- Docker & Docker Compose
- API key from [Kimi](https://platform.moonshot.cn) (or other providers)

## Quick Install

```bash
# 1. Extract the release
cd ~/Downloads
unzip ide-agent-wizard-v2.1.0.zip
cd 20260224-v2_1

# 2. (Optional) Configure custom ports
./scripts/port-setup.sh
#    Kimi Agent port [8081]: 8083
#    Web UI port [8082]: 8084

# 3. Configure API keys
cp .env.example .env
# Edit .env with your API keys:
#   KIMI_API_KEY=sk-your-key-here

# 4. Run setup
./setup.sh
```

## Setup Options

The wizard will ask you to choose:

| Mode | Description | Docker |
|------|-------------|--------|
| **IDE Only** | Agent runs in your IDE (VS Code, Cursor, etc.) | ❌ No |
| **WEB Only** | Browser interface at `http://localhost:8082` | ✅ Yes |
| **IDE + WEB** | Both interfaces with shared memory | ✅ Yes |

## After Setup

### Web UI
Open http://localhost:8082 (or your custom port)

### Telegram Bot (optional)
1. Open Web UI → Settings → Telegram Bot
2. Enter Bot Token (from [@BotFather](https://t.me/botfather))
3. Enter Chat ID
4. Click "Save Configuration" → "Launch Bot"

### IDE Mode
Just start chatting in your IDE!

## Auto-Start (Keep Services Running)

To ensure services start automatically when you login:

```bash
# Install auto-start (macOS)
./scripts/install-auto-start.sh

# Or manually start services
./scripts/start-services.sh          # Start all
./scripts/start-services.sh web      # Start Web UI only
./scripts/start-services.sh telegram # Start Telegram only

# Stop services
./scripts/stop-services.sh
```

### What This Does

- **Auto-start**: Services start automatically when you login
- **Auto-restart**: Containers restart if they crash (via Docker)
- **Logs**: Service logs saved to `logs/services.out` and `logs/services.err`

### Manage Auto-Start

```bash
# Disable auto-start
launchctl unload ~/Library/LaunchAgents/com.ide-agent-wizard.services.plist

# Re-enable auto-start
launchctl load ~/Library/LaunchAgents/com.ide-agent-wizard.services.plist

# Check if running
launchctl list | grep ide-agent-wizard
```

## Useful Commands

```bash
# Check status
docker ps

# View logs
docker compose -f docker/docker-compose.yml logs -f

# Restart services
./scripts/stop-services.sh && ./scripts/start-services.sh

# Factory reset (removes ALL data)
./reset.sh
```

## Troubleshooting

### Port already in use
```bash
# Option 1: Use different ports
./scripts/port-setup.sh

# Option 2: Stop existing containers
docker stop ide-agent-web ide-agent-kimi
```

### 401 API Key error
Edit `.env` file and add a valid API key:
```bash
KIMI_API_KEY=sk-your-real-key-here
```

Then restart:
```bash
./stop-services.sh && ./start-services.sh
```

### Services not starting on login (macOS)
```bash
# Check LaunchAgent status
launchctl list | grep ide-agent-wizard

# View logs
cat logs/services.err

# Reinstall auto-start
./scripts/install-auto-start.sh
```

## Need Help?

- Full documentation: `docs/README.md`
- For AI agents: `docs/AGENTS.md`
- Release notes: `docs/RELEASE_NOTES.md`
