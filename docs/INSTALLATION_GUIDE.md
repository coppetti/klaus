# Installation Guide

---

## Requirements

| Component | Requirement |
|-----------|-------------|
| **Python** | 3.11+ |
| **Docker** | 20.10+ with Docker Compose |
| **OS** | macOS 11+, Ubuntu 20.04+, Windows 10+ (WSL2) |
| **API Key** | At least one LLM provider |

---

## Install

```bash
git clone https://github.com/coppetti/klaus.git
cd klaus
./setup.sh
```

The setup wizard will:
1. Check dependencies (Python, Docker)
2. Ask for your LLM provider and API key
3. Create agent identity (`workspace/SOUL.md`)
4. Build and start containers

After setup, open `http://localhost:12049`.

---

## Ports

| Service | Port |
|---------|------|
| Agent (Klaus_Nexus_1) | 12019 |
| Web UI (Klaus_Spinner) | 12049 |

---

## Providers

You need at least one API key:

| Provider | Get your key |
|----------|-------------|
| Anthropic | [console.anthropic.com](https://console.anthropic.com) |
| OpenAI | [platform.openai.com](https://platform.openai.com) |
| Google | [aistudio.google.com](https://aistudio.google.com) |
| Kimi | [platform.moonshot.cn](https://platform.moonshot.cn) |
| OpenRouter | [openrouter.ai](https://openrouter.ai) |
| Ollama | Local — no key needed |

Switch providers anytime in Settings.

---

## Commands

```bash
./setup.sh                        # Install
./reset.sh                        # Factory reset (erases everything)
bash scripts/start-services.sh    # Start
bash scripts/stop-services.sh     # Stop
```

---

## Telegram (optional)

After setup:
1. Open `http://localhost:12049` → Settings → Telegram Bot
2. Enter bot token (from [@BotFather](https://t.me/botfather))
3. Enter chat ID
4. Save and start

---

## Verify

```bash
# Check containers
docker ps | grep Klaus

# Expected:
# Klaus_Nexus_1    ... 0.0.0.0:12019->8080/tcp
# Klaus_Spinner    ... 0.0.0.0:12049->8082/tcp
```

---

## Troubleshooting

**Port in use:**
```bash
lsof -i :12049    # macOS/Linux
# Kill the process or change ports
```

**Docker not running:**
```bash
open -a Docker    # macOS
sudo systemctl start docker    # Linux
```

**Permission denied:**
```bash
chmod +x setup.sh reset.sh scripts/*.sh
```

**API key error (401):**
Check Settings → Provider in the Web UI. Make sure your key is valid and the correct provider is selected.

**Factory reset:**
```bash
./reset.sh
```
This erases all data, memory, and configuration. Start fresh with `./setup.sh`.

---

## Uninstall

```bash
bash scripts/stop-services.sh
docker rmi klaus-kimi-agent klaus-web-ui klaus-telegram-bot 2>/dev/null
cd .. && rm -rf klaus
```

Back up `workspace/` first if you want to keep your data.
