# 🧙 IDE Agent Wizard

> Universal AI agent setup that works with **any IDE** and **any LLM provider**.

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## ✨ Features

- 🔌 **Multi-Provider** - Works with Kimi, Anthropic, OpenAI, OpenRouter
- 💻 **IDE Agnostic** - Claude Code, Kimi Code, Gemini Code Assist, Cursor
- 📱 **Telegram Support** - Full Telegram bot with memory sync
- 🧠 **Persistent Memory** - SQLite-based with context retrieval
- ⚙️ **YAML Config** - Simple, readable configuration
- 🐳 **Docker Ready** - One-command deployment
- 🚀 **Universal CLI** - Works everywhere Python runs

---

## 🚀 Quick Start

### Option 1: Interactive Setup (Recommended)

```bash
./setup.sh
```

This will:
1. Create virtual environment
2. Install dependencies
3. Run interactive wizard (name, template, profile)
4. Initialize agent with full context
5. **Auto-start Docker** (if Telegram/Hybrid mode)

### Option 2: Manual Setup

```bash
# 1. Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run wizard
python setup_wizard.py

# 4. Initialize
python initialize.py

# 5. Start Docker (for Telegram mode)
docker compose up -d
```

---

## 📱 Telegram Mode

### Architecture

```
Telegram → Bot Container → Kimi Agent (port 8081) → API Kimi
                ↓                ↓
           Local SQLite ←── Shared Memory
```

### Requirements

1. **Telegram Bot Token** - Get from [@BotFather](https://t.me/BotFather)
2. **Kimi API Key** - Get from [platform.moonshot.cn](https://platform.moonshot.cn)

### Start

```bash
# After setup.sh, Docker starts automatically
# Or manually:
docker compose up -d

# Check status
docker compose ps

# View logs
docker compose logs -f
```

### Bot Commands

- `/start` - Welcome message
- `/help` - Show help
- `/memory` - Memory statistics
- `/health` - Check Kimi Agent status
- `/clear` - Clear conversation history

### File Access

Both IDE and Telegram modes can access:
- `workspace/projects/` - Your projects folder
- `workspace/SOUL.md` - Agent identity
- `workspace/USER.md` - Your profile
- `docs/AGENTS.md` - Agent operation guide (auto-loaded)

---

## 💻 IDE Mode

### Supported IDEs

- Claude Code
- Kimi Code
- Gemini Code Assist
- Cursor
- Continue.dev
- Any IDE with tool support

### Usage

The agent reads `init.yaml` and context files automatically:

```python
# Agent knows your identity from workspace/SOUL.md
# Agent knows your profile from workspace/USER.md
# Agent remembers conversations via SQLite memory
```

---

## 📋 Templates

| Template | Best For |
|----------|----------|
| `general` | Everyday tasks, Q&A |
| `architect` | System design, cloud, AI/ML |
| `developer` | Coding, debugging, review |
| `finance` | Financial analysis, investing |
| `legal` | Legal research, contracts |
| `marketing` | Marketing strategy, copywriting |
| `ui` | UI/UX design, prototyping |

---

## 🔧 Configuration

### Files

| File | Purpose | In Git? |
|------|---------|---------|
| `init.yaml` | Your configuration | ❌ No (.gitignore) |
| `.env` | API keys and secrets | ❌ No (.gitignore) |
| `workspace/SOUL.md` | Agent identity | ❌ No (.gitignore) |
| `workspace/USER.md` | Your profile | ❌ No (.gitignore) |
| `workspace/memory/` | SQLite database | ❌ No (.gitignore) |
| `workspace/projects/` | Your projects | ❌ No (.gitignore) |
| `docs/AGENTS.md` | Agent operation guide | ✅ Yes |

### Environment Variables

```bash
# Required for Telegram mode
KIMI_API_KEY=your_key_here
KIMI_AGENT_URL=http://localhost:8081

# Optional: Other providers
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
OPENROUTER_API_KEY=
```

---

## 🐳 Docker Services

### Containers

| Service | Port | Purpose |
|---------|------|---------|
| `kimi-agent` | 8081 | LLM processing, has API key, loads AGENTS.md |
| `telegram-bot` | - | Receives Telegram messages |

### File Paths in Containers

| File | Container Path | Description |
|------|----------------|-------------|
| SOUL.md | `/app/workspace/SOUL.md` | Agent identity |
| USER.md | `/app/workspace/USER.md` | Your profile |
| AGENTS.md | `/app/docs/AGENTS.md` | Agent operation guide (auto-loaded) |
| Projects | `/app/workspace/projects/` | Your projects folder |

### Memory Sync

Both containers share `./workspace/memory/`:
- SQLite database synchronized
- Works across IDE and Telegram modes
- Persistent across restarts

---

## 🛠️ Development

### Project Structure

```
ide-agent-wizard/
├── setup.sh              # Main setup script
├── setup_wizard.py       # Interactive wizard
├── initialize.py         # Post-setup initialization
├── reset.sh              # Factory reset
├── agent-cli.py          # CLI commands
├── telegram_bot.py       # Telegram bot
├── docker-compose.yml    # Docker orchestration
├── docker/
│   ├── Dockerfile              # Telegram bot image
│   └── kimi-agent-patch/       # Patched Kimi Agent
│       ├── Dockerfile
│       └── app.py              # Modified to load AGENTS.md
├── core/
│   ├── agent.py          # Main agent logic
│   ├── memory.py         # SQLite memory store
│   ├── providers/        # LLM providers
│   │   ├── kimi_provider.py
│   │   ├── openrouter_provider.py
│   │   └── ...
│   └── connectors/
│       └── ide_connector.py
├── templates/            # Agent templates
│   ├── architect/
│   ├── developer/
│   └── ...
├── workspace/            # Your workspace (gitignored)
│   ├── SOUL.md           # Agent identity
│   ├── USER.md           # Your profile
│   ├── memory/           # SQLite database
│   └── projects/         # Your projects
├── docs/
│   ├── README.md
│   ├── AGENTS.md         # Agent operation guide (auto-loaded)
│   └── RELEASE_NOTES.md
├── init.yaml.example     # Config template
└── .env.example          # Environment template
```

### Adding New Provider

1. Create provider in `core/providers/`
2. Inherit from `BaseProvider`
3. Implement `generate()` method
4. Add to `core/providers/__init__.py`

---

## 🔒 Security

### PII Protection

- ✅ `.gitignore` excludes all sensitive files
- ✅ `.env` for secrets (never commit)
- ✅ `init.yaml` for config (never commit)
- ✅ Example templates provided

### Best Practices

1. **Never commit** `.env` or `init.yaml`
2. Use **example files** as templates
3. Rotate API keys regularly
4. Restrict Telegram bot to specific user ID (optional)

---

## 📝 License

MIT License - See [LICENSE](LICENSE) for details.

---

## 🙏 Credits

Built with:
- [python-telegram-bot](https://python-telegram-bot.org/)
- [httpx](https://www.python-httpx.org/)
- [PyYAML](https://pyyaml.org/)

---

**Ready to create your universal AI agent?** 🚀

```bash
./setup.sh
```
