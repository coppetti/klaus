# Release Notes - Klaus

## 🎉 Version 1.0.0 - Initial Release (2026-02-26)

### ✨ Features

#### 🧠 Hybrid Memory System
- **SQLite + Kuzu Graph**: Combines fast raw storage with semantic intelligence
- **Offline Embeddings**: Uses local `sentence-transformers` for dense semantic search
- **Relevance Gate**: Auto-rejects low-value conversational inputs
- **Memory Relationships**: Automatic topic, entity, and temporal linking

#### 💬 Multi-Interface Support
- **IDE Mode**: Direct integration with VS Code, Cursor, etc.
- **Web UI**: Browser interface with full features
- **Telegram Bot**: Mobile access with shared memory

#### 🔌 Multi-Provider LLM Support
- **Kimi** (Moonshot AI) - Default provider
- **Anthropic** (Claude 3.5 Sonnet)
- **OpenAI** (GPT-4, GPT-4o, GPT-3.5)
- **Google** (Gemini)
- **OpenRouter** - Multi-model access
- **Custom** (Ollama-compatible) - Local LLM support

#### 🌐 Web UI Features
- Multi-line textarea with model selector
- File upload support (.txt, .md, .py, .json, .yaml, .csv, .pdf)
- Session management (create, save, load, rename)
- Context compaction with importance visualization
- Memory Graph Explorer at `/memory-graph`
- Real-time service status monitoring
- Telegram bot configuration

#### 🤖 Telegram Bot
- Web UI configuration (token + chat ID)
- Status monitoring badges
- Unified system prompt (SOUL.md + USER.md)
- Graceful restart capability

### 🎮 Easter Eggs
- Default ports: 2013 (Kimi Agent) / 2077 (Web UI) - Cyberpunk reference
- Container names: `KLAUS_MAIN_*`

### 🧪 Testing
- Sanity tests (no Docker required)
- Full Docker integration tests
- Unit test suite with pytest

### 🔒 Security
- API keys stored in `.env` (gitignored)
- Docker container isolation
- PII protection

---

**Ready to start?** Run `./setup.sh` and begin building! 🚀

**Support:** <a href='https://ko-fi.com/B0B41UXJ9K' target='_blank'>Buy Me a Coffee</a>
