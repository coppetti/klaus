# Installation Guide

Complete installation guide for Klaus on all platforms.

## Table of Contents

- [System Requirements](#system-requirements)
- [Quick Install (Recommended)](#quick-install-recommended)
- [Platform-Specific Guides](#platform-specific-guides)
  - [macOS](#macos)
  - [Linux](#linux)
  - [Windows](#windows)
- [Manual Installation](#manual-installation)
- [Post-Installation](#post-installation)
- [Troubleshooting](#troubleshooting)

---

## System Requirements

### Minimum Requirements

| Component | Requirement |
|-----------|-------------|
| **OS** | macOS 11+, Ubuntu 20.04+, Windows 10+ |
| **RAM** | 4 GB (8 GB recommended) |
| **Disk** | 5 GB free space |
| **Docker** | 20.10+ with Docker Compose |
| **Network** | Internet connection for API calls |

### Required Software

Before installing Klaus, ensure you have:

1. **Docker Desktop** (macOS/Windows) or **Docker Engine** (Linux)
   - [Download Docker](https://docs.docker.com/get-docker/)

2. **API Key** from at least one provider:
   - [Kimi](https://platform.moonshot.cn) (Recommended)
   - [Anthropic](https://console.anthropic.com)
   - [OpenAI](https://platform.openai.com)

---

## Quick Install (Recommended)

### Option 1: GUI Installer (Interactive)

```bash
# Download the installer
git clone https://github.com/yourusername/klaus.git
cd klaus

# Run GUI installer
python installer/install_gui.py
```

### Option 2: CLI Installer (Automated)

```bash
# Download and install with one command
curl -fsSL https://raw.githubusercontent.com/yourusername/klaus/main/install.sh | bash

# Or with specific options
python installer/install_cli.py --kimi-key YOUR_KEY --yes
```

---

## Platform-Specific Guides

### macOS

#### Prerequisites

```bash
# Install Homebrew (if not installed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Docker Desktop
brew install --cask docker

# Or download from: https://docs.docker.com/desktop/install/mac-install/
```

#### Installation

**Method 1: Using GUI Installer**

```bash
git clone https://github.com/yourusername/klaus.git
cd klaus
python3 installer/install_gui.py
```

**Method 2: Using CLI**

```bash
git clone https://github.com/yourusername/klaus.git
cd klaus
python3 installer/install_cli.py
```

**Method 3: Manual Installation**

```bash
# 1. Clone repository
git clone https://github.com/yourusername/klaus.git ~/Klaus
cd ~/Klaus

# 2. Configure environment
cp .env.example .env
# Edit .env with your API keys

# 3. Run setup
./setup.sh

# 4. Start Klaus
./scripts/start-services.sh
```

#### Access Klaus

- Web UI: http://localhost:7072
- API: http://localhost:7070

---

### Linux (Ubuntu/Debian)

#### Prerequisites

```bash
# Update system
sudo apt-get update

# Install Docker
sudo apt-get install -y docker.io docker-compose-plugin

# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker

# Verify installation
docker compose version
```

#### Installation

**Method 1: One-Line Install**

```bash
curl -fsSL https://raw.githubusercontent.com/yourusername/klaus/main/install.sh | bash
```

**Method 2: Manual Install**

```bash
# Clone repository
git clone https://github.com/yourusername/klaus.git ~/Klaus
cd ~/Klaus

# Setup
./setup.sh

# Start
./start.sh
```

#### Systemd Service (Optional)

```bash
# Create systemd service
sudo cp scripts/klaus.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable klaus
sudo systemctl start klaus

# Check status
sudo systemctl status klaus
```

---

### Windows

#### Prerequisites

1. Install **Docker Desktop for Windows**
   - Download: https://docs.docker.com/desktop/install/windows-install/
   - Enable WSL 2 backend during installation

2. Install **Python 3.11+**
   - Download: https://www.python.org/downloads/windows/
   - Check "Add Python to PATH" during installation

3. Install **Git for Windows**
   - Download: https://git-scm.com/download/win

#### Installation

**Using PowerShell (Administrator)**

```powershell
# Clone repository
git clone https://github.com/yourusername/klaus.git C:\Klaus
cd C:\Klaus

# Run installer
python installer\install_gui.py
```

**Manual Installation**

```powershell
# 1. Clone
git clone https://github.com/yourusername/klaus.git C:\Klaus
cd C:\Klaus

# 2. Configure
copy .env.example .env
# Edit .env with Notepad or VS Code

# 3. Start
.\start.bat
```

#### Windows-Specific Notes

- Use PowerShell or Command Prompt as Administrator
- If Docker Desktop shows WSL 2 error, follow: https://docs.microsoft.com/windows/wsl/install
- Windows Firewall may prompt - allow Docker and Python

---

## Manual Installation

If you prefer full control over the installation:

### Step 1: Get the Code

```bash
git clone https://github.com/yourusername/klaus.git
cd klaus
```

### Step 2: Configure Environment

```bash
# Copy example configuration
cp .env.example .env

# Edit .env with your favorite editor
nano .env        # Linux/macOS
notepad .env     # Windows
```

**Minimum required in `.env`:**
```bash
KIMI_API_KEY=sk-your-key-here
```

### Step 3: Build Containers

```bash
docker compose -f docker/docker-compose.yml build
```

### Step 4: Initialize

```bash
# Initialize workspace and memory databases
python scripts/initialize.py
```

### Step 5: Start Services

```bash
docker compose -f docker/docker-compose.yml up -d
```

---

## Post-Installation

### Verify Installation

```bash
# Check container status
docker compose ps

# Check health
curl http://localhost:7072/health

# View logs
docker compose logs -f web-ui
```

### First-Time Setup

1. Open http://localhost:7072
2. Create your first session
3. Configure Telegram Bot (optional):
   - Go to Settings → Telegram
   - Add your bot token
   - Configure allowed chat IDs

### Update Klaus

```bash
# Pull latest changes
git pull origin main

# Rebuild containers
docker compose -f docker/docker-compose.yml up -d --build
```

---

## Troubleshooting

### Common Issues

#### Port Already in Use

```bash
# Check what's using port 7072
lsof -i :7072      # macOS/Linux
netstat -ano | findstr :7072  # Windows

# Change ports in .env
WEB_UI_PORT=8082
KIMI_AGENT_PORT=8080
```

#### Permission Denied (Linux/macOS)

```bash
# Fix script permissions
chmod +x setup.sh start.sh scripts/*.sh

# Fix Docker permissions
sudo usermod -aG docker $USER
# Log out and back in
```

#### Docker Not Running

```bash
# macOS
open -a Docker

# Linux
sudo systemctl start docker

# Windows
# Start Docker Desktop from Start Menu
```

#### Memory/Performance Issues

```bash
# Check Docker resource allocation
# Docker Desktop → Settings → Resources

# Recommended minimums:
# - CPUs: 2
# - Memory: 4 GB
# - Swap: 1 GB
```

### Getting Help

If you encounter issues:

1. Check logs: `docker compose logs`
2. Run diagnostics: `./scripts/health_check.sh`
3. Create an issue: https://github.com/yourusername/klaus/issues

---

## Uninstallation

To completely remove Klaus:

```bash
# Stop services
docker compose down

# Remove containers and volumes
docker compose down -v

# Remove installation directory
rm -rf ~/Klaus    # Linux/macOS
rmdir /s /q C:\Klaus  # Windows
```

**Note:** This will delete all conversations and memory data. Back up `workspace/` first if needed.

---

## Next Steps

- Read the [Quick Start Guide](QUICKSTART.md)
- Learn about [Memory Architecture](MEMORY_ARCHITECTURE.md)
- Configure [Telegram Bot](TELEGRAM_SETUP.md)
