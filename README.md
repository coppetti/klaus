# 🧙 Klaus

> **Your AI Team Lead** — One orchestrator, infinite specialists. Hybrid Memory that learns. Sub-agents that deliver.

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg)](https://docker.com)
<a href='https://ko-fi.com/B0B41UXJ9K' target='_blank'><img height='28' style='border:0px;height:28px;' src='https://storage.ko-fi.com/cdn/kofi5.png?v=6' border='0' alt='Buy Me a Coffee at ko-fi.com' /></a>

---

## What is Klaus?

Klaus isn't just another AI assistant. It's a **multi-agent system** with a brain.

Think of Klaus as your personal AI Team Lead: it understands what you need, then delegates to the right specialist — whether that's a code reviewer, financial analyst, legal consultant, or UI designer. All sharing the same memory, all working together.

---

## ✨ Features

### 🧠 Hybrid Memory System
- **Dual Storage**: SQLite for fast facts, Kuzu Graph for semantic intelligence
- **Learns Your Context**: Klaus remembers projects, preferences, past decisions
- **Self-Organizing**: Auto-consolidates memories into a knowledge graph
- **Visual Explorer**: Browse your memory as an interactive graph at `/memory-graph`

### 🤖 Sub-Agents on Demand
Klaus automatically spawns the right specialist:

| You Ask... | Klaus Spawns... |
|------------|-----------------|
| "Review this code" | **Developer Agent** — Code review, debugging, refactoring |
| "Calculate ROI" | **Finance Agent** — Cost analysis, projections, budgeting |
| "Marketing campaign" | **Marketing Agent** — Strategy, copywriting, SEO |
| "Design this UI" | **UI/UX Agent** — Wireframes, user flows, accessibility |
| "Is this contract legal?" | **Legal Agent** — Compliance, terms, risk assessment |
| "Scale this system" | **Architect Agent** — Cloud design, performance, reliability |

### 🔌 Multi-Provider Support
Switch providers instantly. No lock-in.
- **Kimi** (Moonshot AI) — Default, optimized for coding
- **Anthropic Claude** — Reasoning powerhouse
- **OpenAI GPT-4** — General purpose excellence
- **Google Gemini** — Multimodal capabilities
- **OpenRouter** — Access 100+ models
- **Local/Ollama** — Run privately on your hardware

### 💬 Interface Freedom
- **Web UI** — Full-featured chat at http://localhost:2077
- **Telegram Bot** — Chat from anywhere, instant notifications
- **API** — RESTful API for custom integrations

---

## 🚀 Quick Start

### Option 1: GUI Installer (Recommended)

```bash
python installer/install_gui.py
```

### Option 2: One-Line Install

```bash
curl -fsSL https://raw.githubusercontent.com/coppetti/klaus/main/install.sh | bash
```

### Option 3: Manual

```bash
git clone https://github.com/coppetti/klaus.git
cd klaus
cp .env.example .env
# Edit .env with your API keys
./setup.sh
./scripts/start-services.sh
```

Then open http://localhost:2077 — done.

---

## 📁 Project Structure

```
klaus/
├── core/                 # Core modules (memory, providers, agents)
│   ├── agent.py
│   ├── hybrid_memory.py
│   ├── agent_spawner.py
│   └── providers/        # LLM provider implementations
├── docker/               # Docker configuration
│   ├── docker-compose.yml
│   ├── kimi-agent/
│   ├── web-ui/           # FastAPI + static assets
│   └── telegram-bot/
├── templates/            # Agent templates
│   ├── architect/        # Default
│   ├── developer/
│   ├── finance/
│   ├── legal/
│   ├── marketing/
│   └── ui/
├── tests/                # Test suite (pytest)
├── installer/            # GUI + CLI installers
├── scripts/              # Helper scripts
├── docs/                 # Documentation
└── workspace/            # User data (sessions, memory, projects)
```

---

## 📚 Documentation

- [Installation Guide](docs/INSTALLATION_GUIDE.md) — Complete setup instructions
- [Quick Start](docs/QUICKSTART.md) — Your first 5 minutes with Klaus
- [Testing Guide](docs/TESTING_GUIDE.md) — Development and testing

---

## 🧪 Testing

```bash
# Run all tests
pytest

# With coverage
pytest --cov=core --cov-report=html
```

---

## 📝 License

MIT License — See [LICENSE](LICENSE) for details.

---

**Built with ❤️ for developers who want AI that actually understands context.**

---

## 💚 Support Klaus

Klaus is **100% free and open source**. If you find it valuable, consider supporting development:

<a href='https://ko-fi.com/B0B41UXJ9K' target='_blank'><img height='36' style='border:0px;height:36px;' src='https://storage.ko-fi.com/cdn/kofi5.png?v=6' border='0' alt='Buy Me a Coffee at ko-fi.com' /></a>

Your support helps keep Klaus alive and growing! 🙏
