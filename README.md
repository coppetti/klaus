# 🧙 IDE Agent Wizard

> Universal AI agent setup that works with **any IDE** and **any LLM provider**.

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## 🚀 Quick Start

```bash
./setup.sh
```

That's it! The wizard will guide you through:
- Choosing your agent template
- Configuring your profile
- Setting up Telegram (optional)
- Starting Docker automatically

---

## 📁 Project Structure

```
ide-agent-wizard/
├── setup.sh          # Main setup (launcher)
├── reset.sh          # Factory reset (launcher)
├── docker/           # Docker configuration
│   ├── docker-compose.yml
│   ├── Dockerfile
│   └── kimi-agent-patch/  # Patched Kimi Agent with AGENTS.md support
├── scripts/          # Setup scripts
│   ├── setup.sh
│   ├── setup_wizard.py
│   ├── initialize.py
│   └── reset.sh
├── cli/              # CLI tools
│   └── agent-cli.py
├── bot/              # Telegram bot
│   └── telegram_bot.py
├── core/             # Core modules
│   ├── agent.py
│   ├── memory.py
│   ├── providers/
│   └── connectors/
├── templates/        # Agent templates
│   ├── architect/
│   ├── developer/
│   └── ...
├── docs/             # Documentation
│   ├── README.md
│   ├── AGENTS.md     # Agent operation guide (auto-loaded)
│   └── RELEASE_NOTES.md
└── workspace/        # Your data (gitignored)
    ├── SOUL.md       # Agent identity
    ├── USER.md       # Your profile
    ├── memory/       # SQLite database
    └── projects/     # Your projects (shared with containers)
```

---

## 📖 Documentation

- **[Full Guide](docs/README.md)** - Complete documentation
- **[For AI Agents](docs/AGENTS.md)** - Technical guide
- **[Release Notes](docs/RELEASE_NOTES.md)** - Version history

---

## 🔧 Commands

| Command | Description |
|---------|-------------|
| `./setup.sh` | Interactive setup wizard |
| `./reset.sh` | Factory reset |
| `docker compose -f docker/docker-compose.yml up -d` | Start Docker services |

---

## 📱 Telegram Mode

After setup, your bot is ready! Just send `/start` in Telegram.

---

**Ready?** Run `./setup.sh` and start building! 🚀
