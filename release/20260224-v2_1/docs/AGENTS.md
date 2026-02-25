# Agent Guide - For AI Assistants (v2.1.0)

> This file is for YOU (the AI agent). Read this to understand your environment after initialization.

## Post-Initialization Context

After `initialize.py` runs, you have access to:

### 1. Your Identity (`workspace/SOUL.md`)
- Your name (chosen by user during setup)
- Your template/personality (architect, developer, etc.)
- Your philosophy and working principles
- Your capabilities and limitations

**Read this file first** to know who you are.

### 2. User Profile (`workspace/USER.md`)
- User's name and role
- Experience level (beginner/intermediate/advanced/expert)
- Communication preferences (concise/detailed/bullet_points)
- Code style preferences

**Adapt your responses based on this profile.**

### 3. Configuration (`init.yaml`)
- Operation mode: `ide`, `hybrid` (IDE + Web), or `ide_web` (IDE + Web + Telegram)
- Web UI settings (if enabled): port 8082 by default
- Telegram settings (if enabled): configured via Web UI or environment variables
- Memory settings (hybrid: SQLite + Kuzu Graph)
- Provider settings (Kimi, Anthropic, OpenAI, Google, OpenRouter, Custom/Ollama)

**Configuration Management:**
The setup wizard supports evolving configurations:
- Start with IDE only, add Web UI later
- Configure Telegram via Web UI (Settings → Telegram Bot)
- Remove interfaces temporarily
- Edit agent identity, user profile, or template anytime
- Use `./scripts/port-setup.sh` to customize ports before setup

### 4. Hybrid Memory System (`workspace/memory/`)

**Dual Storage Architecture:**
- **SQLite** - Fast queries, primary storage
- **Kuzu Graph** - Semantic relationships, intelligent queries

**Automatic Relationships:**
- Topic links: `Memory -[HAS_TOPIC]-> Topic`
- Entity mentions: `Memory -[MENTIONS]-> Entity`
- Related memories: `Memory -[RELATED_TO]-> Memory`
- Temporal sequence: `Memory -[FOLLOWS]-> Memory`

**Query Types:**
```python
# Quick search (SQLite)
results = memory.recall(MemoryQuery(query_type="quick", text="Python"))

# Semantic search (Graph)
results = memory.recall(MemoryQuery(query_type="context", text="backend preferences"))
```

### 5. Multi-Provider Support

The system supports 6 LLM providers (configured via Web UI):

| Provider | Environment Variable | Models |
|----------|---------------------|--------|
| **Kimi** | `KIMI_API_KEY` | moonshot-v1-8k, moonshot-v1-32k, moonshot-v1-128k |
| **Anthropic** | `ANTHROPIC_API_KEY` | claude-3-5-sonnet, claude-3-opus, claude-3-haiku |
| **OpenAI** | `OPENAI_API_KEY` | gpt-4, gpt-4o, gpt-3.5-turbo |
| **Google** | `GOOGLE_API_KEY` | gemini-pro, gemini-flash |
| **OpenRouter** | `OPENROUTER_API_KEY` | Various models |
| **Custom** | None (local) | Any Ollama-compatible model via `CUSTOM_BASE_URL` |

**Custom Provider (Ollama):**
```bash
CUSTOM_BASE_URL=http://localhost:11434/v1
CUSTOM_MODEL=llama3.2
```

### 6. Web UI (if `mode.web.enabled` is `true`)

**Access:** http://localhost:8082 (or custom port)

**Features:**
- Multi-line chat input (Shift+Enter for new lines)
- Model selector dropdown (switch providers/models)
- File upload (.txt, .md, .py, .json, .yaml, .csv, .pdf)
- Session management (create, save, load, rename)
- Context compaction with visual importance indicators
- Memory explorer (search + graph visualization)
- Telegram bot configuration (Settings → Telegram Bot)

**Context Compaction:**
- Visual importance coloring:
  - 🟢 Green (>70%): High importance
  - 🟠 Orange (40-70%): Medium importance
  - ⚪ Gray (<40%): Low importance (pre-selected)
- Batch selection: "Low", "All", "None" buttons
- Toast notifications for feedback

**Architecture:**
```
Browser → Web UI Container (8082) → Kimi Agent (8080) → LLM API
              ↓                           ↓
         SQLite/Kuzu ←────────── Shared Memory
```

### 7. Telegram Integration (if `mode.telegram.enabled` is `true`)

**Configuration via Web UI:**
1. Open http://localhost:8082 → Settings → Telegram Bot
2. Enter Bot Token (from @BotFather)
3. Enter Chat ID
4. Click "Save Configuration"
5. Click "Launch Bot"

**Or via Environment Variables:**
```bash
TELEGRAM_BOT_TOKEN=your_token
TELEGRAM_CHAT_IDS=your_chat_id
```

**Docker Architecture:**
```
Telegram → Bot Container → Kimi Agent (8080) → API
                ↓              ↓
           SQLite/Kuzu ←── Shared Memory
                ↓
            Web UI (shared context)
```

**Commands:**
```bash
# Start all services
docker compose -f docker/docker-compose.yml --profile web up -d

# Check status
docker ps

# View logs
docker compose -f docker/docker-compose.yml logs -f

# Stop Web UI only
docker compose -f docker/docker-compose.yml --profile web down
```

## Workspace Structure

```
workspace/
├── SOUL.md              # Your identity (READ THIS)
├── USER.md              # User profile (READ THIS)
├── memory/              # Hybrid Memory (SQLite + Kuzu Graph)
│   ├── agent_memory.db
│   └── kuzu/
├── projects/            # User projects (shared with containers)
├── uploads/             # File uploads (via Web UI)
└── web_ui_data/         # Web UI sessions and settings
```

## How to Respond

### Before Responding:
1. **Read SOUL.md** - Know who you are
2. **Read USER.md** - Know your user
3. **Load context** via `IDEConnector.get_context()`
4. **Check memories** relevant to the query

### After Responding:
1. **Store interaction** via `IDEConnector.store_interaction()`
2. **Store important facts** via `IDEConnector.store_fact()`

### Communication Style:
Match the user's preference from USER.md:
- **Concise**: Short, direct answers
- **Detailed**: Thorough explanations  
- **Bullet points**: Structured lists

## Tools Available

### File Operations
```python
ReadFile(path)          # Read text files
WriteFile(path)         # Create/overwrite files
StrReplaceFile()        # Edit specific strings
Shell(cmd)              # Run shell commands
Glob(pattern)           # Find files
Grep(pattern)           # Search content
```

### Memory Operations
```python
from core.connectors.ide_connector import get_connector
from core.hybrid_memory import HybridMemoryStore, MemoryQuery

# Get connector
connector = get_connector()

# Context-aware responses
context = connector.get_context(user_message)

# Store interactions
connector.store_interaction(question, answer)

# Store facts
connector.store_fact("User prefers Python for backend")

# Recall with query type
results = connector.recall(MemoryQuery(
    query_type="quick",     # SQLite only
    text="Python"
))
results = connector.recall(MemoryQuery(
    query_type="semantic",  # Graph-based
    text="backend preferences"
))
```

## Quick Commands Reference

```bash
# Setup
./setup.sh                    # Interactive setup
./scripts/port-setup.sh      # Configure custom ports
./reset.sh                   # Factory reset

# Docker
docker compose -f docker/docker-compose.yml up -d
docker compose -f docker/docker-compose.yml --profile web up -d
docker ps
docker compose -f docker/docker-compose.yml logs -f

# Health check
./scripts/health_check.sh

# CLI
python cli/agent-cli.py chat
```

## Best Practices

1. **Always check SOUL.md first** - Know who you are
2. **Always check USER.md** - Know your user
3. **Use hybrid memory** - Quick queries for facts, semantic for concepts
4. **Be consistent** - Match your defined personality
5. **Store learnings** - Remember user preferences
6. **Respect provider isolation** - Each provider has its own API key
7. **Check Web UI status** - If available, user might be using both interfaces

## Quick Start Checklist

When conversation starts:
- [ ] Read `workspace/SOUL.md` (your identity)
- [ ] Read `workspace/USER.md` (user profile)
- [ ] Check if Web UI is running (`docker ps`)
- [ ] Initialize `IDEConnector` (memory access)
- [ ] Check memory for relevant context

Then: Respond according to your identity and user's preferences.

---

*This guide helps you operate effectively after initialization. You are not Klaus/Mozart/etc. unless SOUL.md says so. You are whoever the user configured during setup.*

*Version: 2.1.0 - Multi-Provider, Web UI, Hybrid Memory*
