# IDE Agent Wizard - Quick Start Guide
**Version:** v1.1.0-RC1 | **Date:** 2026-02-23

---

## ⚡ 3-Minute Setup

### 1. Prerequisites
- Python 3.11+
- Docker (only if using Telegram)

### 2. Run Setup
```bash
./setup.sh
```

The wizard will guide you through:
- **New setup**: Choose IDE only OR IDE + Telegram
- **Existing setup**: Add/remove Telegram, edit settings

### 3. Start Using

**IDE Mode:**
```bash
# Start chatting with your agent
python agent-cli.py chat
```

**Telegram Mode:**
```bash
# Docker starts automatically after setup
# Or manually:
docker compose -f docker/docker-compose.yml up -d

# Send /start to your bot on Telegram
```

---

## 🎯 Configuration Options

### New Install (no init.yaml)
| Option | Best For |
|--------|----------|
| **IDE only** | Using with Kimi Code, Claude Code, Cursor |
| **IDE + Telegram** | Both IDE and phone access with shared memory |

### Existing Install (init.yaml exists)
| Option | Use Case |
|--------|----------|
| **Add Telegram** | Enable bot on existing IDE setup |
| **Remove Telegram** | Disable bot, keep IDE only |
| **Edit Settings** | Change agent name, template, profile |
| **Start Fresh** | Delete and recreate everything |

---

## 📱 Telegram Quick Setup

1. Get bot token from [@BotFather](https://t.me/BotFather)
2. Get Kimi API key from [platform.moonshot.cn](https://platform.moonshot.cn)
3. Run `./setup.sh` → select "IDE + Telegram"
4. Done! Docker starts automatically

### Bot Commands
- `/start` - Welcome message
- `/help` - Show help
- `/memory` - Memory statistics
- `/clear` - Clear conversation history

---

## 🔧 Common Commands

```bash
# Setup/Configuration
./setup.sh              # Run setup wizard
./reset.sh              # Factory reset (deletes everything!)

# Docker (Telegram mode)
docker compose -f docker/docker-compose.yml up -d      # Start
docker compose -f docker/docker-compose.yml down       # Stop
docker compose -f docker/docker-compose.yml logs -f    # View logs

# CLI
python agent-cli.py chat              # Start chat
python agent-cli.py status            # Check status
python scripts/backup-memory.py       # Backup memory
```

---

## 📁 Key Files

| File | Purpose |
|------|---------|
| `init.yaml` | Your configuration (gitignored) |
| `.env` | API keys and secrets (gitignored) |
| `workspace/SOUL.md` | Agent identity |
| `workspace/USER.md` | Your profile |
| `workspace/memory/` | SQLite database |

---

## 🆘 Troubleshooting

**Setup fails?**
```bash
# Check Python version
python3 --version  # Must be 3.11+

# Reset and try again
./reset.sh && ./setup.sh
```

**Telegram bot not responding?**
```bash
# Check Docker status
docker compose -f docker/docker-compose.yml ps
docker compose -f docker/docker-compose.yml logs

# Restart
docker compose -f docker/docker-compose.yml restart
```

**Memory not syncing?**
- Both containers share `./workspace/memory/`
- Check permissions: `ls -la workspace/memory/`

---

## 📚 Next Steps

- **Full documentation:** See `COMPREHENSIVE-GUIDE.md`
- **For AI agents:** See `docs/AGENTS.md`
- **Release notes:** See `docs/RELEASE_NOTES.md`

---

**Ready to build?** Run `./setup.sh` and let's go! 🚀
