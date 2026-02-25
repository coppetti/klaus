# Quick Start Guide

Get started with Klaus in 5 minutes.

---

## Start Klaus

```bash
./scripts/start-services.sh
```

Open http://localhost:2077 in your browser.

---

## Your First Conversation

1. Click **"New Session"** in the sidebar
2. Type: `Create a Python function to calculate factorial`
3. Watch Klaus respond with code and explanation

---

## Upload Files

Drag and drop files onto the chat:
- Code files: `.py`, `.js`, `.ts`, `.java`, etc.
- Documents: `.md`, `.txt`, `.pdf`
- Data: `.json`, `.yaml`, `.csv`

Klaus will analyze and remember the content.

---

## Memory Features

### View Your Memories

1. Click **"Memory Explorer"** in the sidebar
2. Search memories by keyword
3. See connected concepts in the graph

### Memory Consolidation

Type `consolidate` to trigger manual memory consolidation.

---

## Sub-Agents

Klaus auto-detects when to spawn specialist agents:

| Trigger | Agent | Example |
|---------|-------|---------|
| "review this code" | Developer | Review Python function |
| "design system" | Architect | Design microservices |
| "calculate ROI" | Finance | Analyze investment |
| "marketing strategy" | Marketing | Create campaign plan |

---

## Session Management

- **New Session**: Start fresh conversation
- **Save**: Persist to disk
- **Load**: Continue previous chat
- **Rename**: Organize your sessions

---

## Useful Commands

| Command | Description |
|---------|-------------|
| `/save` | Save current session |
| `/clear` | Clear chat history |
| `consolidate` | Trigger memory consolidation |
| `status` | Show system status |

---

## Stop Klaus

```bash
./scripts/stop-services.sh
```

---

## Need Help?

- Check [INSTALLATION_GUIDE.md](INSTALLATION_GUIDE.md) for detailed setup
- Run `./scripts/verify.sh` to diagnose issues
