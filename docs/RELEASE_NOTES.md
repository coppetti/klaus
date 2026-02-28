# Release Notes

---

## v0.143.8 — 2026-02-28

First fully functional release. UAT complete.

### Fixes
- Telegram Start button creates container via Docker SDK when it doesn't exist
- Telegram status endpoint verifies container is running before reporting "Online"
- Orphan `Klaus_Telegaaf` cleanup in stop-services.sh
- Docs and copy updates

### Tags
- `v0.143.7` — code complete
- `v0.143.8` — docs and handoff

---

## v0.143.6 — 2026-02-28

### Blade Runner naming
- `KLAUS_MAIN_kimi` → `Klaus_Nexus_1`
- `Klaus_MAIN_web` → `Klaus_Spinner`
- `Klaus_MAIN_telegram` → `Klaus_Telegaaf`
- `KLAUS_MAIN_network` → `Klaus_MAIN_Offworld`

### Fixes
- `reset.sh` rewritten — correct docker compose profiles, proper cleanup
- Kimi provider sidebar no longer hardcoded "Active"
- `start-services.sh` reads `init.yaml` for telegram enabled state
- `stop-services.sh` includes `--profile telegram`

---

## v0.143.4 — 2026-02-28

### Fixes
- Telegram conditional with docker compose profiles
- Kimi model dropdown: `kimi-k1-5` → `kimi-latest`
- `saveTelegramSettings` validates saved token before overwriting
- `/restart` error message shows correct command
- Cognitive memory graph restored from backup

---

## v0.143.3 — 2026-02-28

### Fixes
- `google-generativeai` → `google-genai` in requirements
- Gemini default model: `gemini-2.5-flash`
- ngrok credentials persisted in `init.yaml` (not session-only)
- kimi-agent Dockerfile rewritten as standalone (`python:3.11-slim`)

---

## v0.143 — 2026-02-28

First merge to main. Milestone: stable baseline.

### Features
- Multi-provider LLM support (Kimi, Anthropic, OpenAI, Google, OpenRouter, Ollama)
- Web UI with chat, memory explorer, settings, themes
- Telegram bot with shared memory
- Hybrid memory (SQLite + cognitive graph)
- CLI and GUI installers
- Safe ports: 12019 (Agent), 12049 (Web UI)

### Architecture
- `init.yaml` as single source of truth for runtime config
- `core/llm_router.py` for provider switching
- Docker volumes for live code mounting (no rebuild needed)
- Themes: Deckard, Rachael, Gaff (light/dark)
