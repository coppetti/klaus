# KLAUS

> **It remembers.**

[![Agent](https://img.shields.io/badge/Agent-12019-8B7355)]()
[![Web](https://img.shields.io/badge/Web-12049-FF6B35)]()
[![Baseline](https://img.shields.io/badge/Baseline-Stable-00D4AA)]()
[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
<a href='https://ko-fi.com/B0B41UXJ9K' target='_blank'><img height='36' style='border:0px;height:36px;' src='https://storage.ko-fi.com/cdn/kofi5.png?v=6' border='0' alt='Buy Me a Coffee at ko-fi.com' /></a>

---

## What is Klaus?

**KLAUS** is a local AI agent that actually remembers you.

It has a **SOUL.md** that defines who it is, **hybrid memory** that accumulates everything important across sessions, and the ability to connect to any LLM provider. It runs on your machine. Your data stays yours.

> *"Tell me about our last conversation."*

Klaus will.

---

## What's Different

### 🧠 Memory That Works

Klaus combines **SQLite** (fast retrieval) with **graph relationships** (semantic connections) and **local embeddings**:

- **Baseline identity**: SOUL.md defines the agent's foundation
- **Accumulated**: Every conversation builds its memory of you
- **Persistent**: Remembers across IDE, Web, and Telegram

```python
# Store a memory
memory.store("I prefer Python for backend development")

# Fast recall (SQLite)
results = memory.recall(MemoryQuery(query_type="quick", text="Python"))

# Semantic recall (Graph) - finds related concepts
results = memory.recall(MemoryQuery(query_type="context", text="backend preferences"))
```

### 🖥️ One Agent, Every Interface

The same Klaus, everywhere:
- **IDE** (Port 12019) — Deep in the code with you
- **Web UI / Spinner** (Port 12049) — Full interface with memory explorer
- **Telegram** — In your pocket

### 🔌 Off-World Protocols

Connect to any model:
- **Kimi** (Moonshot AI) — Default
- **Anthropic** (Claude) — claude-3-5-sonnet, claude-opus
- **OpenAI** (GPT-4) — gpt-4, gpt-4o
- **Google** (Gemini) — gemini-2.5-flash, gemini-2.0
- **OpenRouter** — Multi-model access
- **Custom** (Ollama) — Local, private, offline

---

## 🚀 Install

```bash
./setup.sh
```

The setup wizard will:
1. Choose your mode (IDE / WEB / IDE+WEB)
2. Configure API keys
3. Create your agent identity (SOUL.md)
4. Initialize memory

### Ports
```
Agent:  12019
Web UI: 12049
```

### Access
```bash
open http://localhost:12049
```

---

## 📁 Project Structure

```
klaus/
├── setup.sh              # Initialization wizard
├── reset.sh              # Memory wipe (factory reset)
├── docker/               # Container architecture
│   ├── docker-compose.yml
│   ├── Dockerfile
│   └── web-ui/           # Spinner interface (Port 12049)
│       ├── app.py        # Core API
│       └── static/
├── bot/                  # Telegram interface
│   └── telegram_bot.py
├── core/                 # Agent core
│   ├── agent.py
│   ├── memory.py
│   ├── hybrid_memory.py
│   ├── providers/        # Off-world protocols
│   └── connectors/       # IDE interfaces
├── templates/            # Agent templates
│   ├── architect/
│   ├── developer/
│   └── ...
├── tests/                # Baseline tests
│   ├── test_sanity.py
│   └── unit/
├── docs/                 # Documentation
│   ├── README.md
│   ├── AGENTS.md
│   └── RELEASE_NOTES.md
└── workspace/            # Your data (private, gitignored)
    ├── SOUL.md
    ├── USER.md
    └── memory/
```

---

## 🎨 Themes

| Theme | Vibe |
|-------|------|
| **Deckard** 🕵️ | Noir, dark, focused |
| **Rachael** 👠 | Elegant, warm, precise |
| **Gaff** 🦄 | Minimal, silent, watching |

Light and Dark variants for each. Switch in Settings → Appearance.

---

## 🧠 Memory Architecture

The graph automatically creates:
- **Topic links**: `Memory -[HAS_TOPIC]-> Topic`
- **Entity mentions**: `Memory -[MENTIONS]-> Entity`
- **Related memories**: `Memory -[RELATED_TO]-> Memory`
- **Temporal sequence**: `Memory -[FOLLOWS]-> Memory`

All interfaces share the same memory graph.

Visualize at `http://localhost:12049/memory-graph`

---

## 🤖 Telegram

Configure via Web UI Settings, then:

| Command | Description |
|---------|-------------|
| `/start` | Baseline test |
| `/new` | New session |
| `/memory` | View memory graph |
| `/help` | Help |

---

## 🔌 Provider Reference

| Provider | Key | Models |
|----------|-----|--------|
| Kimi | `KIMI_API_KEY` | kimi-k2-0711, kimi-k2 |
| Anthropic | `ANTHROPIC_API_KEY` | claude-sonnet-4-6, claude-opus-4-6, claude-haiku-4-5 |
| OpenAI | `OPENAI_API_KEY` | gpt-4o, gpt-4o-mini |
| Google | `GOOGLE_API_KEY` | gemini-2.5-flash, gemini-2.0-flash |
| OpenRouter | `OPENROUTER_API_KEY` | Various |
| Custom | — | Ollama-compatible |

Configure in Settings → Provider.

---

## 🧪 Testing

```bash
# Baseline test
python3 tests/test_sanity.py

# Full baseline protocol
python3 tests/run_tests.py --docker

# Unit tests
python3 -m pytest tests/unit/ -v
```

---

## 🔒 Security

- **API Keys**: Stored in `.env` (gitignored)
- **Data**: Never leaves your machine
- **Docker**: Isolated containers
- **Memory**: Yours alone

---

## 📖 Documentation

- **[Full Guide](docs/README.md)**
- **[For AI Agents](docs/AGENTS.md)**
- **[Release Notes](docs/RELEASE_NOTES.md)**

---

## 🔧 Commands

| Command | Description |
|---------|-------------|
| `./setup.sh` | Initialize |
| `./reset.sh` | Factory reset |
| `./scripts/start-services.sh` | Start all |
| `./scripts/start-services.sh web` | Web UI only |
| `./scripts/stop-services.sh` | Stop all |

---

> *Your assistant actually remembers you.*
