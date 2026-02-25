# Klaus - Quick Start Guide

Get up and running with Klaus in 5 minutes.

---

## Installation

### Option 1: GUI Installer (Recommended)

```bash
python installer/install_gui.py
```

### Option 2: One-Line Script

```bash
curl -fsSL https://raw.githubusercontent.com/yourusername/klaus/main/install.sh | bash
```

### Option 3: Manual

```bash
git clone https://github.com/yourusername/klaus.git
cd klaus
cp .env.example .env
# Edit .env with your API keys
./setup.sh
./scripts/start-services.sh
```

---

## First Conversation

1. Open http://localhost:7072
2. Create a new session
3. Start chatting!

---

## Using Sub-Agents

Klaus automatically spawns specialists:

| When you ask... | Klaus spawns... |
|-----------------|-----------------|
| "Review this code" | **Developer Agent** |
| "Design a system" | **Architect Agent** |
| "Calculate costs" | **Finance Agent** |
| "Marketing strategy" | **Marketing Agent** |
| "UI/UX review" | **UI Agent** |

---

## Quick Commands

```bash
# Start Klaus
./scripts/start-services.sh

# Stop Klaus
./scripts/stop-services.sh

# View logs
docker compose logs -f web-ui

# Check health
curl http://localhost:7072/health

# Run tests
pytest
```

---

## Next Steps

- Read the [Installation Guide](docs/INSTALLATION_GUIDE.md)
- Learn about [Testing](docs/TESTING_GUIDE.md)

---

**Enjoy using Klaus!** 🧙‍♂️
