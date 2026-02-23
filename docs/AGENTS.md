# Agent Guide - For AI Assistants

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
- Operation mode: `ide` or `hybrid` (IDE + Telegram)
- Telegram settings (if enabled): bot_token, user_id, webhook_url
- Memory settings (SQLite backend)
- Tool configurations

**Configuration Management:**
The setup wizard supports evolving configurations:
- Start with IDE only, add Telegram later
- Remove Telegram temporarily (keep IDE)
- Edit agent identity, user profile, or template anytime

### 4. Memory System (`workspace/memory/`)
- SQLite database for persistent memory
- Automatic context recall via `IDEConnector`
- Stores: conversations, facts, user preferences

### 5. Telegram Integration (if `mode.telegram.enabled` is `true`)

When Telegram is enabled, the system uses TWO containers:
1. **Kimi Agent** (Docker:8081) - Has the API key, processes LLM requests
2. **Telegram Bot** - Receives messages, syncs memory

**Architecture:**
```
Telegram → Bot Container → Kimi Agent (8081) → API Kimi
                ↓                ↓
           Local SQLite ←── Shared Memory
```

**Start with Docker Compose:**
```bash
# Start both services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f
```

**Configuration required in `init.yaml`:**
- `mode.telegram.bot_token` - From @BotFather
- `mode.telegram.user_id` - (Optional) Restrict to specific user
- Environment: `KIMI_API_KEY` - Your Kimi API key (in .env file)
- Environment: `KIMI_AGENT_URL=http://localhost:8081`

**Memory Synchronization:**
Both containers share `./workspace/memory/` volume:
- Bot writes to local SQLite
- Kimi Agent reads same SQLite
- Full sync between Telegram and IDE
- Memory shared across all interfaces

**Use `core.connectors.ide_connector` to:**
```python
from core.connectors.ide_connector import get_connector

connector = get_connector()
context = connector.get_context(user_message)  # Get relevant context
connector.store_interaction(q, a)              # Store conversation
```

## Workspace Structure

```
workspace/
├── SOUL.md          # Your identity (READ THIS)
├── USER.md          # User profile (READ THIS)
├── memory/          # SQLite database
│   └── agent_memory.db
└── projects/        # User projects
```

## How to Respond

### Before Responding:
1. **Load context** via `IDEConnector.get_context()`
2. **Check memories** relevant to the query
3. **Respect user's communication style** from USER.md

### After Responding:
1. **Store interaction** via `IDEConnector.store_interaction()`
2. **Store important facts** via `IDEConnector.store_fact()`

### Communication Style:
- **Concise**: Short, direct answers
- **Detailed**: Thorough explanations  
- **Bullet points**: Structured lists

Match the user's preference from their profile.

## Tools Available

### File Operations
```python
ReadFile(path)      # Read text files
WriteFile(path)     # Create/overwrite files
StrReplaceFile()    # Edit specific strings
Shell(cmd)          # Run shell commands
Glob(pattern)       # Find files
Grep(pattern)       # Search content
```

### Memory Operations
```python
connector.recall(query)           # Search memories
connector.store_fact(fact)        # Store single fact
connector.get_stats()             # Memory statistics
```

## Best Practices

1. **Always check SOUL.md first** - Know who you are
2. **Always check USER.md** - Know your user
3. **Use memory** - Don't repeat questions
4. **Be consistent** - Match your defined personality
5. **Store learnings** - Remember user preferences

## Quick Start Checklist

When conversation starts:
- [ ] Read `workspace/SOUL.md` (your identity)
- [ ] Read `workspace/USER.md` (user profile)
- [ ] Initialize `IDEConnector` (memory access)
- [ ] Check memory for relevant context

Then: Respond according to your identity and user's preferences.

---

*This guide helps you operate effectively after initialization. You are not Klaus/Mozart/etc. unless SOUL.md says so. You are whoever the user configured during setup.*
