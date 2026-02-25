# 🧙 IDE Agent Wizard v2.1

> Universal AI agent setup with **Hybrid Memory** (SQLite + Graph), **Web UI**, **Multi-Provider Support**, and **Telegram Bot**.

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## ✨ What's New in v2.1

### 💬 Enhanced Chat Experience
- **Multi-line Input**: Textarea with Shift+Enter for new lines, Enter to send
- **Model Selector**: Quick-switch between providers and models
- **Smart Message Loading**: Configurable number of messages (5-100)
- **Context Compaction**: Selective compaction with importance visualization

### 🔌 Multi-Provider Support
- **Kimi** (Moonshot AI) - Default provider with function calling
- **Anthropic** (Claude 3.5 Sonnet)
- **OpenAI** (GPT-4, GPT-4o, GPT-3.5)
- **Google** (Gemini)
- **OpenRouter** - Access to multiple models
- **Custom** (Ollama-compatible) - Local LLM support with configurable base URL

### 🤖 Telegram Bot v2
- **Web UI Configuration**: Configure bot token and chat ID via web interface
- **Status Monitoring**: Real-time status badges (Offline/Saved/Online/Error)
- **Unified System Prompt**: Loads SOUL.md + USER.md for personalized responses
- **Safe Restart**: Graceful shutdown and restart with new configuration

### 🧠 Improved Memory & Context
- **Context Compaction**: Visual selection with importance-based coloring
  - Green (>70%): High importance memories
  - Orange (40-70%): Medium importance
  - Gray (<40%): Low importance (pre-selected for compaction)
- **Batch Selection**: Low/All/None buttons for quick selection
- **Better Synchronization**: Fixed timing issues between UI and backend

### 🎯 Simplified Setup
Choose your setup mode:
- **IDE Only**: Agent runs in your IDE (VS Code, Cursor, etc.)
- **WEB Only**: Browser interface with all features
- **IDE + WEB**: Both interfaces with shared memory

Telegram bot is configured through the Web UI (no setup wizard questions).

---

## 🚀 Quick Start

```bash
./setup.sh
```

The setup wizard will guide you through:
1. Choose setup mode (IDE / WEB / IDE+WEB)
2. Configure API keys
3. Create your agent identity (SOUL.md)
4. Start the services

### For Web UI + Telegram:
```bash
# 1. Setup with Web support
./setup.sh

# 2. Open Web UI
open http://localhost:8082

# 3. Configure Telegram in Settings → Telegram Bot
#    - Enter Bot Token (from @BotFather)
#    - Enter Chat ID
#    - Click "Save Configuration"
#    - Click "Launch Bot"
```

---

## 📁 Project Structure

```
ide-agent-wizard/
├── setup.sh              # Main setup (launcher)
├── reset.sh              # Factory reset (launcher)
├── docker/               # Docker configuration
│   ├── docker-compose.yml
│   ├── Dockerfile
│   └── web-ui/           # 🌐 Web UI container
│       ├── app.py        # FastAPI backend
│       └── static/       # HTML, CSS, JS assets
├── scripts/              # Setup scripts
│   ├── setup_wizard.py   # Interactive configuration
│   └── initialize.py     # Post-setup initialization
├── cli/                  # CLI tools
│   └── agent-cli.py
├── bot/                  # Telegram bot
│   └── telegram_bot.py
├── core/                 # Core modules
│   ├── agent.py
│   ├── memory.py
│   ├── hybrid_memory.py  # 🧠 Hybrid SQLite + Graph memory
│   ├── providers/        # LLM provider implementations
│   └── connectors/       # IDE connectors
├── templates/            # Agent templates
│   ├── architect/
│   ├── developer/
│   └── ...
├── tests/                # 🧪 Test suite
│   ├── test_sanity.py
│   └── unit/
├── docs/                 # Documentation
│   ├── README.md
│   ├── AGENTS.md         # Agent operation guide
│   └── RELEASE_NOTES.md
└── workspace/            # Your data (gitignored)
    ├── SOUL.md           # Agent identity
    ├── USER.md           # Your profile
    ├── memory/           # SQLite database + Graph
    └── projects/         # Your projects
```

---

## 📖 Documentation

- **[Full Guide](docs/README.md)** - Complete documentation
- **[For AI Agents](docs/AGENTS.md)** - Technical guide for AI agents
- **[Release Notes](docs/RELEASE_NOTES.md)** - Version history

---

## 🔧 Commands

| Command | Description |
|---------|-------------|
| `./setup.sh` | Interactive setup wizard |
| `./reset.sh` | Factory reset (removes all data) |
| `./scripts/start-services.sh` | Start all services (Web + Telegram) |
| `./scripts/start-services.sh web` | Start Web UI only |
| `./scripts/stop-services.sh` | Stop all services |
| `./scripts/port-setup.sh` | Configure custom ports |
| `./scripts/install-auto-start.sh` | Auto-start on login (macOS) |

---

## 🧠 Hybrid Memory

The Hybrid Memory system combines **SQLite** (fast, reliable) with **Kuzu Graph** (intelligent relationships):

```python
# Example: Store a memory
memory.store("I prefer Python for backend development")

# Quick search (SQLite)
results = memory.recall(MemoryQuery(query_type="quick", text="Python"))

# Semantic search (Graph) - finds related concepts
results = memory.recall(MemoryQuery(query_type="context", text="backend preferences"))
```

### Memory Relationships

The Graph automatically creates:
- **Topic links**: `Memory -[HAS_TOPIC]-> Topic`
- **Entity mentions**: `Memory -[MENTIONS]-> Entity`
- **Related memories**: `Memory -[RELATED_TO]-> Memory`
- **Temporal sequence**: `Memory -[FOLLOWS]-> Memory`

All three interfaces (IDE, Web, Telegram) share the same intelligent memory.

---

## 🌐 Web UI

Access the browser interface at **http://localhost:8082** (when enabled).

### Features
- 💬 **Chat**: Multi-line textarea with model selector
- 📎 **File Upload**: Upload .txt, .md, .py, .json, .yaml, .csv, .pdf files (max 10MB)
- 💾 **Session Management**: Create, save, load, rename conversation sessions
- 🗜️ **Context Compaction**: Extract key facts with visual importance indicators
- 🔄 **Reset Session**: Clear conversation while preserving context
- 📊 **Status Panel**: Real-time monitoring of all services
- 🧠 **Memory Explorer**: Search and browse memories (Quick/Smart search)
- ⚙️ **Settings**: Configure providers, models, Telegram bot

### Memory Graph Explorer

Visualize your memory relationships at **http://localhost:8082/memory-graph**

- **Interactive Graph**: Drag, zoom, explore connections
- **Node Types**: 
  - 🟣 **Memories** - Your stored knowledge
  - 🟢 **Topics** - Automatically extracted themes
  - 🟠 **Entities** - People, places, things mentioned
  - 🔵 **Categories** - Memory categories
- **Relationships**: See how memories connect
- **Layouts**: Force-directed, Hierarchical, Circular
- **Filters**: Show only specific node types

---

## 🤖 Telegram Bot

After configuration via Web UI, your bot is ready! Just send `/start` in Telegram.

The bot uses **Hybrid Memory** for contextual conversations, with graph-based relationship tracking. Both Web UI and Telegram share the same memory and system prompt (SOUL.md + USER.md).

### Bot Commands
- `/start` - Start conversation
- `/new` - Start new conversation
- `/memory` - View recent memories
- `/help` - Show help

---

## 🔌 Providers

The Web UI supports multiple LLM providers:

| Provider | Key Required | Models |
|----------|-------------|--------|
| Kimi | `KIMI_API_KEY` | moonshot-v1-8k, moonshot-v1-32k, moonshot-v1-128k |
| Anthropic | `ANTHROPIC_API_KEY` | claude-3-5-sonnet, claude-3-opus, claude-3-haiku |
| OpenAI | `OPENAI_API_KEY` | gpt-4, gpt-4o, gpt-3.5-turbo |
| Google | `GOOGLE_API_KEY` | gemini-pro, gemini-flash |
| OpenRouter | `OPENROUTER_API_KEY` | Various models |
| Custom | None (local) | Any Ollama-compatible model |

Configure provider keys in Settings → Provider.

---

## 🧪 Testing

Run the test suite:

```bash
# Quick sanity tests (no Docker)
python3 tests/test_sanity.py

# Full tests with Docker
python3 tests/run_tests.py --docker

# Unit tests only
python3 -m pytest tests/unit/ -v
```

---

## 🔒 Security

- **API Keys**: Stored in `.env` file (gitignored)
- **Tokens**: Never hardcoded, always via environment
- **Docker**: Containers isolated, volumes for persistence
- **PII Protection**: All sensitive files in `.gitignore`

---

**Ready?** Run `./setup.sh` and start building! 🚀
