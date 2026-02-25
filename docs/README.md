# 🧙 Klaus

> **Your AI Team Lead** — One orchestrator, infinite specialists. Hybrid Memory that learns. Sub-agents that deliver.

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg)](https://docker.com)

---

## What is Klaus?

Klaus isn't just another AI assistant. It's a **multi-agent system** with a brain.

Think of Klaus as your personal AI Team Lead: it understands what you need, then delegates to the right specialist — whether that's a code reviewer, financial analyst, legal consultant, or UI designer. All sharing the same memory, all working together.

---

## ✨ Why Klaus?

### 🧠 Memory That Actually Works
- **Hybrid Architecture**: Fast SQLite lookups + Semantic Kuzu Graph
- **Learns Your Context**: No repeating yourself — Klaus remembers projects, preferences, past decisions
- **Self-Organizing**: Auto-consolidates memories into a knowledge graph
- **Visual Explorer**: Browse your memory as an interactive graph

### 🤖 Agents on Demand
Klaus automatically spawns the right specialist:

| You Ask... | Klaus Spawns... |
|------------|-----------------|
| "Review this code" | **Developer Agent** — Bug hunting, refactoring, best practices |
| "Calculate ROI" | **Finance Agent** — Cost analysis, projections, budgeting |
| "Marketing campaign" | **Marketing Agent** — Strategy, copywriting, SEO |
| "Design this UI" | **UI/UX Agent** — Wireframes, user flows, accessibility |
| "Is this contract legal?" | **Legal Agent** — Compliance, terms, risk assessment |
| "Scale this system" | **Architect Agent** — Cloud design, performance, reliability |

**All agents share memory.** No context loss. No repetition.

### 🔌 Bring Your Own LLM
Switch providers instantly. No lock-in.
- **Kimi** (Moonshot AI) — Default, optimized for coding
- **Anthropic Claude** — Reasoning powerhouse
- **OpenAI GPT-4** — General purpose excellence
- **Google Gemini** — Multimodal capabilities
- **OpenRouter** — Access 100+ models
- **Local/Ollama** — Run privately on your hardware

### 💬 Interface Freedom
- **Web UI** — Full-featured chat, file uploads, session management
- **Telegram Bot** — Chat from anywhere, instant notifications
- **API** — Integrate into your own tools
- **VS Code** — Coming soon

---

## 🚀 Get Started in 60 Seconds

```bash
# One-line install
curl -fsSL https://raw.githubusercontent.com/yourusername/klaus/main/install.sh | bash

# Or GUI wizard
python installer/install_gui.py
```

Then open http://localhost:2077 — done.

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────┐
│                 YOU                         │
│  ┌─────────┐ ┌─────────┐ ┌─────────────┐  │
│  │ Web UI  │ │Telegram │ │   VS Code   │  │
│  └────┬────┘ └────┬────┘ └──────┬──────┘  │
└───────┼──────────┼─────────────┼──────────┘
        └──────────┴─────────────┘
                     │
         ┌───────────▼───────────┐
         │   Klaus Core          │
         │   (Orchestrator)      │
         └───────────┬───────────┘
                     │
    ┌────────────────┼────────────────┐
    │                │                │
┌───▼────┐    ┌─────▼──────┐   ┌────▼─────┐
│ Hybrid │    │   LLM      │   │  Sub     │
│ Memory │    │  Router    │   │  Agents  │
│SQLite  │    │            │   │          │
│+Graph  │    │Kimi,       │   │Dev,      │
└────────┘    │Claude,     │   │Finance,  │
              │GPT, etc.   │   │Legal...  │
              └────────────┘   └──────────┘
```

---

## 📚 Documentation

- **[Installation Guide](INSTALLATION_GUIDE.md)** — Complete setup instructions
- **[Quick Start](QUICKSTART.md)** — Your first 5 minutes with Klaus
- **[Testing Guide](TESTING_GUIDE.md)** — Development and testing

---

## 📝 License

MIT License — See [LICENSE](../LICENSE) for details.

---

**Built with ❤️ for developers who want AI that actually understands context.**
