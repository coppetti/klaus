# Klaus Installers

Cross-platform installers for Klaus - Your AI Solutions Architect.

## Available Installers

| Installer | Platform | Description |
|-----------|----------|-------------|
| `install_gui.py` | All | Graphical installer with step-by-step wizard |
| `install_cli.py` | All | Command-line installer |
| `install.sh` | macOS/Linux | One-line curl installer |

## Quick Start

### GUI Installer (Recommended for Desktop)

```bash
python installer/install_gui.py
```

**Features:**
- 🎨 **Welcome Screen** - "Wake up, time to install!" (Blade Runner inspired)
- 📦 **Setup Mode Selection** - IDE Only / Web + IDE / Web Only
- 🤖 **Multi-Provider Support** - Kimi, Anthropic, Google, OpenRouter, Custom (Ollama)
- ⚙️ **Agent Configuration** - Name your agent, choose a persona/template
- 👤 **User Profile** - Your name, role, tone preference, and detail level
- ✅ **Visual Progress Indicator** - Track installation steps

### CLI Installer (Recommended for Servers)

```bash
# Interactive mode
python installer/install_cli.py

# Automated mode
python installer/install_cli.py --kimi-key YOUR_KEY --yes

# With options
python installer/install_cli.py \
    --dir /opt/klaus \
    --kimi-key KEY1 \
    --anthropic-key KEY2 \
    --mode web+ide
```

### One-Line Install

```bash
# macOS/Linux
curl -fsSL https://raw.githubusercontent.com/yourusername/klaus/main/install.sh | bash

# With API key
curl -fsSL https://raw.githubusercontent.com/yourusername/klaus/main/install.sh | bash -s -- --kimi-key YOUR_KEY
```

## Installation Modes

| Mode | Description | Use Case |
|------|-------------|----------|
| `web+ide` | Web UI + IDE Integration (Recommended) | Full experience |
| `ide-only` | IDE Integration only | VS Code users who prefer chat in editor |
| `web-only` | Web UI only | Browser-based workflow |

## Supported Providers

The installer supports multiple LLM providers:

| Provider | API Key Required | Notes |
|----------|-----------------|-------|
| **Kimi** | ✅ | Default, recommended |
| **Anthropic** | ✅ | Claude models |
| **Google** | ✅ | Gemini models via AI Studio |
| **OpenRouter** | ✅ | Access to multiple models |
| **Custom** | ❌ | Local models via Ollama |

## Configuration Files

The installer creates three main configuration files:

### `.env`
Environment variables including API keys and ports.

### `init.yaml`
Agent and user configuration:
```yaml
agent:
  name: Klaus
  template: solutions-architect
  personality:
    tone: professional
    style: balanced

user:
  name: Your Name
  role: Developer
```

### `SOUL.md`
User context and preferences for personalized interactions.

## Requirements

- Python 3.11+
- Docker 20.10+
- Docker Compose
- 4GB RAM
- 5GB disk space

## Troubleshooting

See [Installation Guide](../docs/INSTALLATION_GUIDE.md) for detailed troubleshooting.

---

For manual installation, see the [Installation Guide](../docs/INSTALLATION_GUIDE.md).
