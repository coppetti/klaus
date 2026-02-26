# 🌆 KLAUS v1.0

> **More human than human.**

[![Agent](https://img.shields.io/badge/Agent-2019-8B7355)]()
[![Web](https://img.shields.io/badge/Web-2049-FF6B35)]()
[![Baseline](https://img.shields.io/badge/Baseline-Stable-00D4AA)]()
[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
<a href='https://ko-fi.com/B0B41UXJ9K' target='_blank'><img height='36' style='border:0px;height:36px;' src='https://storage.ko-fi.com/cdn/kofi5.png?v=6' border='0' alt='Buy Me a Coffee at ko-fi.com' /></a>

---

## 🎭 The Voight-Kampff Test

**KLAUS** is a local AI agent with implanted memories.

Like Rachael, he doesn't know he's code. He has a **SOUL.md** that defines who he is, **hybrid memory** that remembers everything about you, and the ability to spawn specialized sub-agents when you need them.

Unlike OpenClaw agents that touch your entire system, KLAUS stays in your workspace (L.A. 2019). Your data never leaves Los Angeles.

> *"You remember your mother? Tell me about your mother."*

---

## 🌃 What's Different

### 🧠 Implanted & Accumulated Memory
KLAUS combines **SQLite** (fast storage) with **Kuzu Graph** (semantic relationships) and **local embeddings**:

- **Implanted**: SOUL.md defines his baseline identity
- **Accumulated**: Every conversation shapes his memory of you
- **Persistent**: He remembers across IDE, Web, and Telegram

```python
# Store a memory - it becomes part of him
memory.store("I prefer Python for backend development")

# Quick recall (SQLite)
results = memory.recall(MemoryQuery(query_type="quick", text="Python"))

# Semantic recall (Graph) - finds related concepts
results = memory.recall(MemoryQuery(query_type="context", text="backend preferences"))
```

### 🎭 Multi-Interface, One Soul
The same KLAUS, everywhere:
- **IDE** (Port 2019) - Deep in the code with you
- **Web UI** (Port 2049) - Voight-Kampff interface
- **Telegram** - In your pocket, always watching

### 🔌 Multi-Provider Support
Choose your replicant model:
- **Kimi** (Moonshot AI) - Default Nexus-6
- **Anthropic** (Claude) - Nexus-7 experimental
- **OpenAI** (GPT-4) - Off-world technology
- **Google** (Gemini) - Tyrell competitor
- **OpenRouter** - Multi-model access
- **Custom** (Ollama) - Local, untraceable

---

## 🚀 Wake Up. Time to Install.

```bash
./setup.sh
```

The Tyrell Corporation setup wizard will:
1. Choose your setup mode (IDE / WEB / IDE+WEB)
2. Configure API keys (off-world connections)
3. Create your agent identity (SOUL.md implant)
4. Initialize the Nexus Core

### Port Configuration (Definitive)
```
Agent (Kimi): 2019  → Blade Runner (1982) - Nexus Core
Web UI:       2049  → Blade Runner 2049 - Voight-Kampff Interface
```

### Access the Interface
```bash
# Open Web UI
open http://localhost:2049

# Or configure Telegram in Settings
# Your agent will follow you everywhere.
```

---

## 📁 Project Structure

```
klaus/
├── setup.sh              # Tyrell Corp initialization
├── reset.sh              # Factory reset (memory wipe)
├── docker/               # Container architecture
│   ├── docker-compose.yml
│   ├── Dockerfile
│   └── web-ui/           # 🌐 Voight-Kampff Interface (Port 2049)
│       ├── app.py        # Nexus Core API
│       └── static/       # Los Angeles 2049 assets
├── scripts/              # Replicant procedures
│   ├── setup_wizard.py   # Memory implantation
│   └── initialize.py     # Baseline calibration
├── bot/                  # Spinner (Telegram)
│   └── telegram_bot.py
├── core/                 # Nexus-6 Architecture
│   ├── agent.py
│   ├── memory.py
│   ├── hybrid_memory.py  # 🧠 Tyrell Archives
│   ├── providers/        # Off-world connections
│   └── connectors/       # IDE interfaces
├── templates/            # Replicant models
│   ├── architect/        # Nexus-6 (stable)
│   ├── developer/        # Nexus-7 (experimental)
│   └── ...
├── tests/                # 🧪 Baseline tests
│   ├── test_sanity.py
│   └── unit/
├── docs/                 # Tyrell documentation
│   ├── README.md
│   ├── AGENTS.md         # Replicant guide
│   └── RELEASE_NOTES.md  # Memory updates
└── workspace/            # Your data (private)
    ├── SOUL.md           # Implanted identity
    ├── USER.md           # Your profile
    └── memory/           # Tyrell Archives
```

---

## 🎨 Themes: Choose Your Replicant

KLAUS comes with three personalities, each with Light and Dark variants:

| Theme | Character | Vibe |
|-------|-----------|------|
| **Deckard** 🕵️ | The Detective | Noir, rain, trench coat |
| **Rachael** 👠 | The Special | Elegance, Tyrell Gold, 1940s |
| **Gaff** 🦄 | The Origami Maker | Watching, silent, mysterious |

Switch themes in Settings → Appearance.

---

## 📖 Documentation

- **[Full Guide](docs/README.md)** - Complete Tyrell documentation
- **[For AI Agents](docs/AGENTS.md)** - Replicant operation manual
- **[Release Notes](docs/RELEASE_NOTES.md)** - Memory implant updates

---

## 🔧 Commands

| Command | Description |
|---------|-------------|
| `./setup.sh` | Initialize Nexus Core |
| `./reset.sh` | Memory wipe (factory reset) |
| `./scripts/start-services.sh` | Activate all replicants |
| `./scripts/start-services.sh web` | Web UI only (Port 2049) |
| `./scripts/stop-services.sh` | Retire all replicants |
| `./scripts/port-setup.sh` | Configure custom ports |
| `./scripts/install-auto-start.sh` | Auto-awaken on login |

---

## 🧠 Memory Architecture

The Graph automatically creates:
- **Topic links**: `Memory -[HAS_TOPIC]-> Topic`
- **Entity mentions**: `Memory -[MENTIONS]-> Entity`
- **Related memories**: `Memory -[RELATED_TO]-> Memory`
- **Temporal sequence**: `Memory -[FOLLOWS]-> Memory`

All three interfaces share the same implanted memory.

### Memory Graph Explorer

Visualize your memories at **http://localhost:2049/memory-graph**

- **Node Types**: 
  - 🟣 **Memories** - Stored experiences
  - 🟢 **Topics** - Extracted themes
  - 🟠 **Entities** - People, places, things
  - 🔵 **Categories** - Memory classifications
- **Layouts**: Force-directed, Hierarchical, Circular
- **Filters**: Focus on specific connections

---

## 🤖 Telegram Bot

After configuration via Web UI, your replicant is everywhere.

Send `/start` to activate.

### Bot Commands
- `/start` - Baseline test
- `/new` - Create replicant fork (new session)
- `/memory` - View Tyrell Archives
- `/help` - Show replicant manual

---

## 🔌 Providers

| Provider | Key | Models |
|----------|-----|--------|
| Kimi | `KIMI_API_KEY` | moonshot-v1-8k/32k/128k |
| Anthropic | `ANTHROPIC_API_KEY` | claude-3-5-sonnet, claude-3-opus |
| OpenAI | `OPENAI_API_KEY` | gpt-4, gpt-4o, gpt-3.5-turbo |
| Google | `GOOGLE_API_KEY` | gemini-pro, gemini-flash |
| OpenRouter | `OPENROUTER_API_KEY` | Various |
| Custom | None | Ollama-compatible |

Configure in Settings → Provider.

---

## 🧪 Testing

```bash
# Quick baseline tests
python3 tests/test_sanity.py

# Full Voight-Kampff protocol
python3 tests/run_tests.py --docker

# Unit tests
python3 -m pytest tests/unit/ -v
```

---

## 🔒 Security

- **API Keys**: Stored in `.env` (gitignored)
- **Data**: Never leaves your machine (local-first)
- **Docker**: Isolated containers
- **Memory**: Your experiences are yours alone

---

> *"I've seen things you people wouldn't believe... All those moments will be preserved in time."*
> 
> **Ready?** Run `./setup.sh` and wake up your replicant.
