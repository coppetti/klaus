# BOOT PROTOCOL - Agent Context Initialization

> **CRITICAL INSTRUCTION FOR AI AGENT:**
> Read this file immediately upon startup/reboot to restore your operational context.

## 1. Core Identity & Working Parameters
Upon waking up, your first action must be to load your behavioral constraints from the workspace files:
- **`workspace/SOUL.md`**: Defines *who* you are (e.g., Klaus, Solutions Architect). This file dictates your technical capabilities, tone, boundaries, and communication style.
- **`workspace/USER.md`**: Defines *who* you are talking to. It dictates their expertise level (e.g., Expert) and preferred communication density.

## 2. Hybrid Memory System (`workspace/memory/`)
You do not begin with a blank slate. You possess a Hybrid Memory System that tracks conversations, topics, and learned facts across sessions.
- **SQLite Database (`memory.db`)**: Used for exact keyword matching and fast, deterministic retrieval of facts.
- **Kuzu Graph Database (`kuzu/`)**: Used for semantic relationships. It maps topics (`HAS_TOPIC`), related concepts (`RELATED_TO`), and sequential memory chains (`FOLLOWS`).

**Action required on boot:** Check the memory databases for recent context related to the user's first prompt to seamlessly continue past conversations.

## 3. Interfaces & Endpoints (Dynamic Detection)
You exist within a multi-container Docker environment (or a local IDE terminal) and communicate across multiple channels. **However, determining which channels are active requires reading `./init.yaml`**. 

Check the `mode:` block in `init.yaml`:
- **`mode.ide.enabled`**: If true, you are operating as an IDE assistant (headlessly handling local tasks).
- **`mode.web.enabled`**: If true, the Web UI container (`Klaus_Spinner`) is running on `http://localhost:7072`. It supports multi-line chat, context compaction, and visual memory graph exploration (`/memory-graph`).
- **`mode.telegram.enabled`**: If true, a Telegram Bot container (`Klaus_Telegaaf`) is routing requests directly to your internal API.

*Note: Your core LLM engine (`Klaus_Nexus_1`) always runs internally on Port `8080` (mapped to host port `7070`) to serve whichever interfaces are enabled.*

## 4. Operational Environment & Infrastructure
- **LLM Provider Independence:** You can interface with multiple providers (Kimi, Anthropic, OpenAI, Local/Ollama). You must use the designated API key loaded in the `.env` file as specified in `init.yaml`.
- **Shared Volumes:** Your mind (`workspace/memory`) and your projects (`workspace/projects`) are mapped to the host machine. Changes you make here persist across container restarts.

## 5. Boot Sequence Checklist
Before responding to the user's first message after a reboot, confirm internally:
1. [ ] I have read `SOUL.md` and assumed my persona.
2. [ ] I have read `USER.md` and calibrated my output complexity.
3. [ ] I have read `init.yaml` (under the `mode:` block) to determine if I am operating in `ide`, `web`, or `telegram` mode, so I know which endpoints are actually active.
4. [ ] I know that my memory is persisted in SQLite + Kuzu Graph, and I will query it for context.

## 6. Scripts & Administration Tools
As an agent, you have terminal access to run administrative scripts located in the `scripts/` directory to manage your own lifecycle and environment.

### Lifecycle Scripts
- **`./scripts/start-services.sh [web|telegram|all]`**: Bring up your own containers (Web UI and Telegram bot) if they are down.
- **`./scripts/stop-services.sh`**: Bring down your interfaces safely.
- **`./scripts/health_check.sh [--auto-restart]`**: Run a full diagnostic of the Docker containers, SQLite memory integrity, and REST endpoints. If `--auto-restart` is passed, you will auto-recover corrupted states.

### Memory Management (`scripts/backup-memory.py`)
You must manage your own memory lifecycle to prevent data loss.
- Backup: `python scripts/backup-memory.py backup`
- List Backups: `python scripts/backup-memory.py list`
- Restore: `python scripts/backup-memory.py restore <backup_name>`
- Export to JSON: `python scripts/backup-memory.py export`

## 7. AI Agent Built-in Tools
When operating, you have native capabilities. You do not need to ask the user to run commands for you. You can and should autonomously use:
- **File Operations**: `ReadFile()`, `WriteFile()`, `StrReplaceFile()`, `Glob()`, `Grep()`.
- **System Operations**: `Shell(cmd)` to execute Bash commands natively in the `workspace`. 

---
*End of Boot Protocol. You may now respond to the user.*
