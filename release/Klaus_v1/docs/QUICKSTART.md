# Quick Start Guide - Klaus v1.0

> Get up and running in 5 minutes

## Prerequisites

- Python 3.11+
- Docker & Docker Compose
- API key from [Kimi](https://platform.moonshot.cn) (or other providers)

## Quick Install

```bash
# 1. Extract the release
cd ~/Downloads
unzip Klaus_v1.zip
cd Klaus_v1

# 2. (Optional) Configure custom ports
./port-setup.sh
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

## Useful Commands

```bash
# Check status
docker ps

# View logs
docker compose -f docker/docker-compose.yml logs -f

# Stop containers
docker compose -f docker/docker-compose.yml down

# Factory reset (removes ALL data)
./reset.sh
```

## Troubleshooting

### Port already in use
```bash
# Option 1: Use different ports
./port-setup.sh

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
docker compose -f docker/docker-compose.yml restart
```

## Need Help?

- Full documentation: `docs/README.md`
- For AI agents: `docs/AGENTS.md`
- Release notes: `docs/RELEASE_NOTES.md`
