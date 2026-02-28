# Agent Guide

> This file is for you, the AI agent. Read this to understand your environment.

---

## First Steps

1. Read `workspace/SOUL.md` — your identity
2. Read `workspace/USER.md` — who you're working with
3. Read `init.yaml` — your configuration

SOUL.md defines who you are. USER.md defines who they are. Everything else follows from that.

---

## Architecture

```
Browser → Klaus_Spinner (12049) → Klaus_Nexus_1 (12019) → LLM API
                ↓                         ↓
           init.yaml ←──────────── Shared Config
                ↓                         ↓
         Docker Socket              core/llm_router.py
                ↓                         ↓
        Klaus_Telegaaf              Memory (SQLite)
```

### Containers

| Container | Port | Role |
|-----------|------|------|
| `Klaus_Nexus_1` | 12019 → 8080 | Agent HTTP server (FastAPI) |
| `Klaus_Spinner` | 12049 → 8082 | Web UI |
| `Klaus_Telegaaf` | — (polling) | Telegram bot |

Network: `Klaus_MAIN_Offworld`

---

## Configuration (`init.yaml`)

Runtime file. Not committed. Mounted as volume in all containers.

Key fields:
- `defaults.provider` — active LLM provider
- `defaults.model` — active model
- `mode.web.enabled` — Web UI on/off
- `mode.telegram.enabled` — Telegram on/off
- `mode.ngrok` — ngrok tunnel config

Provider switching happens through `init.yaml` → `core/llm_router.py` reads it on every request.

---

## Providers

| Provider | Key | Models |
|----------|-----|--------|
| Kimi | `KIMI_API_KEY` | kimi-k2-0711, kimi-latest |
| Anthropic | `ANTHROPIC_API_KEY` | claude-sonnet-4-6, claude-opus-4-6 |
| OpenAI | `OPENAI_API_KEY` | gpt-4o, gpt-4o-mini |
| Google | `GOOGLE_API_KEY` | gemini-2.5-flash, gemini-2.5-pro |
| OpenRouter | `OPENROUTER_API_KEY` | Various |
| Custom | `CUSTOM_BASE_URL` | Ollama-compatible |

---

## Memory System

SQLite-based with cognitive graph (JSON). All interfaces share the same memory.

Location: `workspace/memory/`

```python
# Quick recall
results = memory.recall(MemoryQuery(query_type="quick", text="Python"))

# Semantic recall (graph relationships)
results = memory.recall(MemoryQuery(query_type="context", text="backend preferences"))
```

**Automatic relationships:**
- `Memory -[HAS_TOPIC]-> Topic`
- `Memory -[MENTIONS]-> Entity`
- `Memory -[RELATED_TO]-> Memory`
- `Memory -[FOLLOWS]-> Memory`

Visualize at `http://localhost:12049/memory-graph`

---

## Workspace

```
workspace/
├── SOUL.md              # Agent identity
├── USER.md              # User profile
├── memory/              # SQLite + cognitive graph
├── projects/            # User projects
├── uploads/             # File uploads (Web UI)
└── web_ui_data/         # Sessions and settings
```

---

## Web UI (Klaus_Spinner)

Access: `http://localhost:12049`

Features:
- Chat with model selector
- File upload (.txt, .md, .py, .json, .yaml, .csv, .pdf)
- Session management
- Memory Graph Explorer
- Settings (provider, Telegram, appearance)
- Themes: Deckard, Rachael, Gaff (light/dark)

---

## Telegram (Klaus_Telegaaf)

Configure via Web UI → Settings → Telegram Bot, or via environment:

```bash
TELEGRAM_BOT_TOKEN=your_token
TELEGRAM_CHAT_IDS=your_chat_id
```

Commands: `/start`, `/new`, `/memory`, `/help`

---

## Commands

```bash
./setup.sh                        # Initialize
./reset.sh                        # Factory reset
bash scripts/start-services.sh    # Start all
bash scripts/stop-services.sh     # Stop all
```

---

## How to Respond

**Before:** Read SOUL.md, read USER.md, check memory for context.

**After:** Store important facts. Remember preferences. Build continuity.

Match the identity defined in SOUL.md. Match the communication style in USER.md. Be consistent across sessions — that's the whole point.

---

*You are whoever SOUL.md says you are.*
