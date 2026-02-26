# Release Notes - IDE Agent Wizard

## 🎉 Version 2.1.2 - Cognitive Hardening (2026-02-25)

### ✨ Features & Improvements

#### 🧠 Active Relevance Filtration
- **Memory Relevance Gate**: Implemented `core/memory_relevance_gate.py` using LLM evaluation to auto-reject low-value interactions (e.g., "ok", "thanks") from entering the permanent memory and polluting the graph.

#### 🕸️ Kuzu Graph Hardening (CASTLE-2.0 Principles)
- **Strict Semantic Constraints**: Lowered visual noise by enforcing a hard 3-edge maximum for Topics and Entities. Memory connections (`RELATED_TO`) now require a strict Cosine Similarity of `> 0.65`.
- **Temporal Sequences**: Eliminated "orphan nodes" by implementing `FLOWS_INTO` edges. Every parsed memory now linearly connects to the immediate previous interaction, forming a continuous conversation spine.
- **Offline Semantic Embeddings**: True dense integration using local, offline `all-MiniLM-L6-v2` (`sentence-transformers`) for rich relationship mapping without external API dependencies.
- **Enhanced Extraction Taxonomies**: Added CamelCase detection, SCREAMING_SNAKE_CASE (env vars), Portuguese/English synonym mapping, and Project tech terms logic to the `_extract_topics` and `_extract_entities` regex pipelines.

#### 🛡️ Stability & Recovery
- **Durable Sync Queue**: Background graph sync worker now uses a persistent SQLite queue table. Unfinished sync jobs are automatically replayed and flushed on container reboot (Crash Recovery).

---

## 🎉 Version 2.1.1 - Stability, Cleanup & Port Isolation

### ✨ Changes

#### 🧹 Project Cleanup
- Removed `fun-snippets/` dev stash directory
- Removed empty `scripts/optional/` directory
- Removed `core/connectors/demo_memory_flow.py` (dev throwaway with broken import path)
- Removed stale `logs/` directory

#### 🔧 Setup Wizard Refactor
- Simplified CLI setup modes to **2 options only**: IDE only, IDE + Web UI
- Telegram bot configuration is now exclusively handled via the Web UI post-install
- Removed `_configure_telegram()`, `_update_add_telegram()`, `_update_remove_telegram()` methods
- Generated `.env` no longer injects `TELEGRAM_BOT_TOKEN`
- Generated `init.yaml` always sets `telegram.enabled: false` by default

#### 🐳 Port & Container Isolation
- Klaus (live instance) now runs on dedicated ports: `7070` (Kimi Agent), `7072` (Web UI)
- Release builds continue to use standard ports: `8080`/`8082`
- Klaus containers renamed to `KLAUS_MAIN_kimi`, `Klaus_MAIN_web`, `Klaus_MAIN_telegram`
- Klaus Docker network renamed to `Klaus_MAIN_network`

#### 🐛 Bug Fixes
- Fixed default Kimi model inconsistency: `providers/__init__.py` now defaults to `kimi-k2-5` (matching `init.yaml`)
- Updated `AGENTS.md` and `BOOT.md` to reflect correct ports and container names

#### 📝 New Documentation
- Added `BOOT.md`: Agent boot protocol for context restoration after restart
- Added `analisys-and-next-steps.md`: Architectural analysis of the v2.1 clean release

---

## 🎉 Version 2.1.0 - Multi-Provider & Enhanced UX

### ✨ New Features

#### 💬 Enhanced Chat Interface
- **Multi-line Textarea**: 5-line input area with proper handling
  - `Shift+Enter` for new lines
  - `Enter` to send message
- **Model Selector**: Dropdown to switch providers/models without leaving chat
- **Smart Loading**: Configurable message count (5-100 messages)

#### 🔌 Multi-Provider Support
- **6 Providers Supported**:
  - **Kimi** (Moonshot AI) - Default, function calling support
  - **Anthropic** (Claude 3.5 Sonnet, Opus, Haiku)
  - **OpenAI** (GPT-4, GPT-4o, GPT-3.5)
  - **Google** (Gemini Pro, Flash)
  - **OpenRouter** (Multi-model access)
  - **Custom** (Ollama-compatible local LLMs)
- **Provider Isolation**: Each provider uses its own API key
- **Auto-detection**: Only shows configured providers in selector
- **Custom Provider**: Full Ollama support with configurable base URL

#### 🤖 Telegram Bot v2
- **Web UI Configuration**: Configure token and chat ID via Settings
  - Bot Token input (from @BotFather)
  - Chat ID input
  - Save Configuration button
  - Launch/Stop Bot buttons
- **Status Badges**: Real-time status (Offline/Saved/Online/Error)
- **Safe Restart**: Graceful shutdown before restart
- **Unified Context**: Loads SOUL.md + USER.md (same as Web UI)

#### 🧠 Improved Context Compaction
- **Visual Importance Indicators**:
  - 🟢 Green (>70%): High importance
  - 🟠 Orange (40-70%): Medium importance
  - ⚪ Gray (<40%): Low importance
- **Smart Pre-selection**: Messages <60% importance auto-selected
- **Batch Selection**: "Low", "All", "None" buttons for quick selection
- **Fixed Synchronization**: Proper timing between UI and backend

#### 🎯 Simplified Setup
- **3 Setup Modes**:
  - **IDE Only**: Agent runs in IDE (VS Code, Cursor, etc.)
  - **WEB Only**: Browser interface only
  - **IDE + WEB**: Both interfaces with shared memory
- **Telegram via Web UI**: No setup wizard questions for Telegram
- **Streamlined Configuration**: Focus on essential options only

#### 🔔 Improved Feedback
- **Toast Notifications**: Non-intrusive success/warning/error messages
- **Loading States**: Visual feedback during operations
- **No Dialogs**: Replaced intrusive dialogs with toasts

### 🔧 Technical Improvements

#### Backend (Web UI)
- Provider-specific endpoints (`/api/settings/provider/{provider}`)
- Environment variable persistence via `save_env_var()`
- Telegram bot management endpoints
- Context compaction with importance scoring
- System prompt builder (SOUL.md + USER.md)

#### Telegram Bot
- `KimiAgentClient` for backend communication
- Proper SOUL.md and USER.md loading
- Web search integration
- Graceful shutdown handling

#### IDE Agent
- Fixed port configuration (8080 for Docker internal)
- Separate API keys per provider
- Custom provider model display

### 📁 Updated File Structure

```
docker/
├── docker-compose.yml      # Web UI service with 'web' profile
├── web-ui/
│   ├── app.py             # FastAPI with multi-provider support
│   └── static/
│       └── index.html     # Enhanced UI with model selector
bot/
└── telegram_bot.py        # Web UI configurable bot
templates/
├── web-ui/                # Web UI specific templates
│   ├── SOUL.md
│   └── USER.md
└── telegram/              # Telegram specific templates
    ├── SOUL.md
    └── USER.md
```

### 🐛 Bug Fixes
- Fixed context compaction synchronization issues
- Fixed Kimi Agent port for Docker networking (8081→8080)
- Fixed custom provider model display in selector
- Fixed Telegram bot restart behavior

### 📝 Configuration Changes

#### .env.example
```bash
# Required
KIMI_API_KEY=your_key_here

# Optional - Custom Provider (Ollama)
CUSTOM_BASE_URL=http://localhost:11434/v1
CUSTOM_MODEL=llama3.2

# Optional - Other providers
ANTHROPIC_API_KEY=
OPENAI_API_KEY=
GOOGLE_API_KEY=
OPENROUTER_API_KEY=

# Telegram (configured via Web UI)
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_IDS=

# Internal
KIMI_AGENT_URL=http://kimi-agent:8080
```

---

## 🎉 Version 2.0.0 - Hybrid Memory & Web UI

### ✨ New Features

#### 🌐 Web UI (v2.0)
- **Modern Interface** - Shadcn-inspired design with Tailwind CSS
- **Chat Interface** - Markdown rendering with syntax highlighting
- **File Upload** - Support for .txt, .md, .py, .json, .yaml, .csv, .pdf (max 10MB)
- **Session Management** - Create, save, load, rename conversation sessions
- **Settings Panel** - Configure provider, model, temperature, mode presets
- **Memory Explorer** - Search and browse memories (Quick/Smart search)

#### 🧠 Memory Graph Explorer
- **Visual Graph** - Interactive visualization at `/memory-graph`
- **Node Types** - Memories (purple), Topics (green), Entities (orange), Categories (blue)
- **Relationships** - See how memories connect via topics and entities
- **Multiple Layouts** - Force-directed, Hierarchical, Circular
- **Filtering** - Show only specific node types
- **Powered by** - vis.js network visualization

#### 🧠 Hybrid Memory System
- **Dual Storage** - SQLite for speed + Kuzu Graph for intelligence
- **Automatic Relationships** - Memories linked by topics, entities, context
- **Smart Queries** - Quick (SQLite) vs Semantic (Graph) with automatic routing
- **Graph Fallback** - Works with SQLite-only if Graph unavailable

#### 🔌 Multi-Provider Support (Web UI)
- **Kimi** (Moonshot AI) - Default provider
- **Anthropic** (Claude)
- **OpenAI** (GPT-4, GPT-4o)
- **OpenRouter** - Multi-model access
- **Auto-detection** - Only shows providers with configured API keys

### 🐳 Docker Updates
- **Web UI Container** - New `ide-agent-web` service on port 8082
- **Profile Support** - Use `--profile web` to start Web UI
- **Shared Memory** - All containers share Hybrid Memory store

---

## 🎉 Version 1.0.0 - Final Release

### ✨ Features

#### Core Functionality
- ✅ Interactive setup wizard (`setup.sh`)
- ✅ Multi-mode support: IDE, Telegram, Hybrid
- ✅ SQLite-based persistent memory
- ✅ Automatic memory synchronization
- ✅ Template-based agent personalities

#### Telegram Bot
- ✅ Full Telegram bot integration
- ✅ Two-container architecture (Bot + Kimi Agent)
- ✅ Docker Compose orchestration
- ✅ Memory sync between containers
- ✅ User authorization by ID
- ✅ Health check commands

#### Providers
- ✅ Kimi (Moonshot AI)
- ✅ OpenRouter (multi-model)
- ✅ Anthropic (Claude)
- ✅ OpenAI (GPT)
- ✅ Extensible provider system

#### Security
- ✅ `.gitignore` for all sensitive files
- ✅ `.env` for secrets
- ✅ Example templates provided
- ✅ No hardcoded credentials in code

### 🐳 Docker Services

| Service | Image | Port | Purpose |
|---------|-------|------|---------|
| kimi-agent | clawd-agent:latest | 8080 (internal) / 7070 (host) | LLM processing |
| telegram-bot | test-agent-telegram-bot | - | Telegram interface |

### 🔧 Configuration Files

| File | Template | Secrets | Notes |
|------|----------|---------|-------|
| `.env` | `.env.example` | ✅ Yes | API keys, tokens |
| `init.yaml` | `init.yaml.example` | ✅ Yes | Bot config |
| `workspace/SOUL.md` | `templates/*` | ❌ No | Agent identity |
| `workspace/USER.md` | Generated | ❌ No | User profile |

### 🚀 Quick Start

```bash
# 1. Reset (if needed)
./reset.sh

# 2. Setup
./setup.sh

# 3. Done! Docker auto-starts for Telegram mode
```

### 🔒 Security Considerations

1. **API Keys**: Stored in `.env` only
2. **Tokens**: Never hardcoded, always via environment
3. **Git**: Sensitive files in `.gitignore`
4. **Docker**: Containers isolated, no host access needed

### 🐛 Known Limitations

1. **Health Check**: Kimi Agent shows "unhealthy" but works (no curl in container)
2. **IDE Mode**: Requires Kimi Code or compatible IDE
3. **Memory**: SQLite only (no Redis/Postgres options yet)

### 📝 Changelog

#### v2.1.0 (2026-02-23)
- ✅ **Multi-Provider Support** - 6 providers with isolated API keys
- ✅ **Enhanced Chat** - Multi-line input, model selector, improved UX
- ✅ **Telegram via Web UI** - Configure bot through web interface
- ✅ **Context Compaction** - Visual importance indicators, batch selection
- ✅ **Custom Provider** - Full Ollama support for local LLMs
- ✅ **Toast Notifications** - Non-intrusive feedback instead of dialogs

#### v2.0.0 (2026-02-23)
- ✅ **Web UI** - Browser interface with chat, sessions, memory explorer
- ✅ **Hybrid Memory** - SQLite + Kuzu Graph for intelligent relationships
- ✅ **Memory Graph Explorer** - Visualize memory connections
- ✅ **Multi-Provider** - Web UI with multiple LLM providers

#### v1.1.0 (2026-02-22)
- ✅ **Smart Setup Wizard** - Configuration management: add/remove Telegram, edit settings without recreating
- ✅ **AGENTS.md Auto-Load** - Kimi Agent now automatically loads AGENTS.md on startup
- ✅ **Projects Folder** - New `workspace/projects/` folder accessible in both IDE and Telegram modes
- ✅ **Kimi Agent Patch** - Custom Dockerfile to extend clawd-agent with AGENTS.md support
- ✅ **Updated Documentation** - README and docs reflect new features and file paths

#### v1.0.0 (2026-02-22)
- Initial release
- Full Telegram bot support
- Docker Compose setup
- Interactive wizard
- Memory synchronization
- Multi-provider support
- Security hardening

### 🎯 Tested Scenarios

- ✅ Fresh install: IDE only (reset + setup)
- ✅ Fresh install: IDE + Web
- ✅ Fresh install: IDE + Web + Telegram
- ✅ Add Web to existing IDE setup
- ✅ Configure Telegram via Web UI
- ✅ Context compaction with batch selection
- ✅ Multi-provider chat switching
- ✅ Custom provider (Ollama) integration
- ✅ Memory persistence across interfaces
- ✅ Docker auto-start
- ✅ PII protection

### 📦 Dependencies

```
python-telegram-bot>=20.6
pyyaml>=6.0
httpx>=0.25.0
aiohttp>=3.9.0
fastapi>=0.104.0
uvicorn>=0.24.0
kuzu>=0.4.0
pytest>=7.4.0
sentence-transformers>=2.2.0
```

### 🙏 Acknowledgments

- Built for Kimi Code, Claude Code, and other IDEs
- Inspired by Clawd architecture
- Uses Moonshot AI Kimi API

---

**Status**: ✅ Ready for production use

**Next Steps**: Run `./setup.sh` to get started!
