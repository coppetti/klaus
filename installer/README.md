# Klaus Installers

Cross-platform installers for Klaus.

## Available Installers

| Installer | Platform | Description |
|-----------|----------|-------------|
| `install_gui.py` | All | Graphical installer with UI |
| `install_cli.py` | All | Command-line installer |
| `install.sh` | macOS/Linux | One-line curl installer |

## Quick Start

### GUI Installer (Recommended for Desktop)

```bash
python installer/install_gui.py
```

Features:
- Interactive configuration
- Visual progress indicator
- API key validation
- Directory browser

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
    --mode full
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
| `full` | Web UI + Telegram + All features | Production |
| `minimal` | Web UI only | Development/Testing |
| `dev` | Source code with hot reload | Contributing |

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
