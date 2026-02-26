# 🧙 Klaus v1.0

> Universal AI agent setup with **Hybrid Memory** (SQLite + Graph), **Web UI**, and **Telegram**.

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
<a href='https://ko-fi.com/B0B41UXJ9K' target='_blank'><img height='36' style='border:0px;height:36px;' src='https://storage.ko-fi.com/cdn/kofi5.png?v=6' border='0' alt='Buy Me a Coffee at ko-fi.com' /></a>

---

## ✨ What's New in v1.0

### 🧠 Cognitive Hardened Hybrid Memory (SQLite + Kuzu Graph)
- **Dual storage**: SQLite for fast fact retrieval, Graph for semantic intelligence
- **Relevance Gate**: Auto-rejects low-value inputs (e.g. "ok") before they pollute memory
- **Offline Embeddings**: Uses local `sentence-transformers` for dense Semantic Search
- **Denoised Relationships**: Strict connection caps (max 3 edges) and `FLOWS_INTO` temporal sequences eliminate graph "hairballs" and orphaned nodes.
- **Memory Graph Explorer**: Visual graph visualization at `/memory-graph`

### 🌐 Web UI (Port 8082)
- Modern chat interface with Shadcn-inspired design
- **File Upload**: Support for .txt, .md, .py, .json, .yaml, .csv, .pdf
- **Session Management**: Create, save, load, rename sessions
- **Memory Explorer**: Search and browse memories (Quick/Smart)
- **Multi-Provider**: Kimi, Anthropic, OpenAI, OpenRouter
- **Settings Panel**: Temperature, tokens, mode presets

### ✨ Features

- 🔌 **Multi-Provider** - Kimi, Anthropic, OpenAI, OpenRouter
- 💻 **IDE Agnostic** - Claude Code, Kimi Code, Gemini Code Assist, Cursor
- 🌐 **Web UI** - Browser interface at http://localhost:8082
- 📱 **Telegram Support** - Full Telegram bot with memory sync
- 🧠 **Cognitive Memory** - SQLite + Kuzu Graph + Offline Embeddings (`all-MiniLM-L6-v2`)
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
3. Run interactive wizard with **smart configuration management**:
   - **New setup**: IDE only / IDE + Telegram / IDE + Web UI / All
   - **Existing config**: Add/remove Telegram, edit settings
4. Initialize agent with full context
5. **Auto-start Docker** (if Telegram mode enabled)

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

## 🌐 Web UI Mode

### Access

Open your browser at **http://localhost:8082**

### Features

| Feature | Description |
|---------|-------------|
| 💬 **Chat** | Markdown support with syntax highlighting |
| 📎 **File Upload** | .txt, .md, .py, .js, .json, .yaml, .csv, .pdf (max 10MB) |
| 🧠 **Memory Explorer** | Search memories (Quick/Semantic), browse history |
| 📊 **Memory Graph** | Visual graph at `/memory-graph` - see relationships |
| 💾 **Sessions** | Create, save, load, rename conversation sessions |
| ⚙️ **Settings** | Provider, model, temperature, mode presets |
| 🗜️ **Compact Context** | Extract key facts and save to memory |

### Memory Graph Explorer

Visualize your memories as an interactive graph:
- **Nodes**: Memories (purple), Topics (green), Entities (orange), Categories (blue)
- **Edges**: Relationships between memories
- **Layouts**: Force-directed, Hierarchical, Circular
- **Filters**: Show only specific node types

Access at: http://localhost:8082/memory-graph

---

## 📱 Telegram Mode

### Architecture

```
Telegram → Bot Container → Kimi Agent (port 8081) → API Kimi
                ↓                ↓
           Hybrid Memory ←── Shared (SQLite + Graph)
```

### Requirements

1. **Telegram Bot Token** - Get from [@BotFather](https://t.me/BotFather)
2. **Kimi API Key** - Get from [platform.moonshot.cn](https://platform.moonshot.cn)

### Setup Telegram

You can add Telegram to an existing IDE-only setup anytime:

```bash
./setup.sh
# Select: "Add Telegram to existing setup"
```

Or remove it later:

```bash
./setup.sh
# Select: "Remove Telegram"
```

### Start

```bash
# After setup.sh, Docker starts automatically (if Telegram enabled)
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

## 🔄 Configuration Management

The setup wizard automatically detects existing configurations and offers context-appropriate options:

### New Setup (no init.yaml found)

```
🎯 New Configuration

[1] 💻 IDE only
    Works with Kimi Code, Claude Code, Cursor, etc.

[2] ⭐ IDE + Telegram
    [3] 🌐 IDE + Web UI
    [4] 🚀 IDE + Telegram + Web UI
    Both IDE and Telegram bot with shared memory
```

### Existing Setup (init.yaml detected)

```
🎯 Configuration Management
Existing init.yaml detected!

Current setup: IDE only  (or: IDE + Interfaces)

[1] 📱 Add Telegram              (shown if no Telegram)
[1] 💻 Remove Telegram           (shown if has Telegram)
    Add/remove Telegram bot

[2] ⚙️  Edit Settings
    Change agent identity, user profile, or template

[3] 🔄 Start Fresh
    Delete existing and create new configuration
```

### Examples

**Start with IDE only, add Telegram later:**
```bash
# First run - setup IDE only
./setup.sh
# Select: IDE only

# Later - add Telegram
./setup.sh
# Select: Add Telegram
```

**Remove Telegram temporarily:**
```bash
./setup.sh
# Select: Remove Telegram
# (Keeps IDE working, disables Telegram bot)
```

**Update your profile:**
```bash
./setup.sh
# Select: Edit Settings → User Profile
# Change name, role, or communication style
```

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
| `web-ui` | 8082 | Browser interface with chat, memory graph, file upload |
| `telegram-bot` | - | Receives Telegram messages |

### Web UI Profile

To start with Web UI:

```bash
# Start all services including Web UI
docker compose -f docker/docker-compose.yml --profile web up -d

# Or start only base services (no Web UI)
docker compose -f docker/docker-compose.yml up -d
```

### File Paths in Containers

| File | Container Path | Description |
|------|----------------|-------------|
| SOUL.md | `/app/workspace/SOUL.md` | Agent identity |
| USER.md | `/app/workspace/USER.md` | Your profile |
| AGENTS.md | `/app/docs/AGENTS.md` | Agent operation guide (auto-loaded) |
| Projects | `/app/workspace/projects/` | Your projects folder |

### Memory Sync

All containers share `./workspace/memory/`:
- **SQLite**: Fast queries, raw memory storage
- **Kuzu Graph**: Relationship mapping, semantic search
- **Sync**: Works across IDE, Web UI, and Telegram modes
- **Persistent**: Survives restarts

### Hybrid Memory System

```
┌─────────────┐     ┌─────────────┐
│   SQLite    │◄───►│ Kuzu Graph  │
│  (Fast)     │     │ (Semantic)  │
└──────┬──────┘     └──────┬──────┘
       │                   │
       └─────────┬─────────┘
                 ▼
          ┌─────────────┐
          │  Memories   │
          │  + Relations│
          └─────────────┘
```

**Query Types:**
- `quick`: Fast SQLite search (keywords)
- `semantic`: Graph-based semantic search
- `context`: Relationship-aware context retrieval

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
