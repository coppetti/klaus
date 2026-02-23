# 🧙 IDE Agent Wizard v2.0

> Universal AI agent setup with **Hybrid Memory** (SQLite + Graph), **Web UI**, and **Telegram**.

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## ✨ What's New in v2.0

### 🧠 Hybrid Memory (SQLite + Kuzu Graph)
- **Dual storage**: SQLite for speed, Graph for intelligence
- **Automatic relationships**: Memories linked by topics, entities, and context
- **Smart queries**: Quick (SQLite) vs Semantic (Graph) - automatic routing
- **Transparent fallback**: Works with SQLite-only if Graph unavailable

### 🌐 Web UI (Browser Interface)
- Modern chat interface at `http://localhost:8082`
- Compact Context: Extract and save important facts to memory
- Professional 2/3 + 1/3 layout
- Markdown rendering with syntax highlighting

---

## 🚀 Quick Start

```bash
./setup.sh
```

That's it! The smart wizard detects your setup and guides you through:
- **New setup**: Choose IDE only / IDE + Telegram / IDE + Web UI / All three
- **Existing setup**: Add/remove interfaces, edit settings
- Auto-starts Docker when Telegram/Web is enabled

### Configuration Management

| Scenario | Options |
|----------|---------|
| No `init.yaml` | Create IDE only / IDE + Telegram / IDE + Web UI / All |
| Has `init.yaml` + IDE only | Add Telegram / Add Web UI / Edit / Start fresh |
| Has `init.yaml` + Interfaces | Remove interfaces / Edit / Start fresh |

---

## 📁 Project Structure

```
ide-agent-wizard/
├── setup.sh          # Main setup (launcher)
├── reset.sh          # Factory reset (launcher)
├── docker/           # Docker configuration
│   ├── docker-compose.yml
│   ├── Dockerfile
│   ├── web-ui/       # 🌐 Web UI container
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
│   ├── hybrid_memory.py  # 🧠 Hybrid SQLite + Graph memory
│   ├── providers/
│   └── connectors/
├── templates/        # Agent templates
│   ├── architect/
│   ├── developer/
│   └── ...
├── tests/            # 🧪 Test suite
│   ├── run_tests.py
│   ├── run.sh
│   └── unit/
├── docs/             # Documentation
│   ├── README.md
│   ├── AGENTS.md     # Agent operation guide (auto-loaded)
│   └── RELEASE_NOTES.md
└── workspace/        # Your data (gitignored)
    ├── SOUL.md       # Agent identity
    ├── USER.md       # Your profile
    ├── memory/       # SQLite database + Graph
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

Access the browser interface at `http://localhost:8082` (when enabled).

Features:
- 💬 **Chat**: Markdown support with syntax highlighting
- 🗜️ **Compact Context**: Extract key facts and save to memory
- 🔄 **Reset Session**: Clear conversation while preserving context
- 📊 **Status Panel**: Real-time monitoring of all services

---

## 📱 Telegram Mode

After setup, your bot is ready! Just send `/start` in Telegram.

The bot uses **Hybrid Memory** for contextual conversations, with graph-based relationship tracking.

---

## 🧪 Testing

Run the test suite:

```bash
# Quick tests (no Docker)
python3 tests/run_tests.py

# Full tests with Docker
python3 tests/run_tests.py --docker

# Unit tests only
python3 -m pytest tests/unit/ -v
```

---

**Ready?** Run `./setup.sh` and start building! 🚀
