# Installation Guide

Complete installation instructions for Klaus.

---

## System Requirements

- **OS**: macOS 10.14+, Ubuntu 18.04+, Windows 10/11 (with WSL2)
- **RAM**: 4GB minimum, 8GB recommended
- **Disk**: 2GB free space
- **Python**: 3.11+
- **Docker**: Latest version (optional but recommended)

---

## Option 1: GUI Installer (Recommended)

The easiest way to install Klaus:

```bash
python installer/install_gui.py
```

### What it does:
1. Checks system requirements
2. Detects or installs Docker
3. Configures API keys
4. Sets up workspace directory
5. Creates startup shortcuts

---

## Option 2: CLI Installer

For automated or headless installation:

```bash
# Interactive mode
python installer/install_cli.py

# Automated mode
python installer/install_cli.py \
  --kimi-key sk-your-key \
  --provider kimi \
  --install-dir ~/klaus \
  --yes
```

---

## Option 3: Manual Installation

### Step 1: Clone Repository

```bash
git clone https://github.com/yourusername/klaus.git
cd klaus
```

### Step 2: Configure Environment

```bash
cp .env.example .env
```

Edit `.env` with your preferred editor:

```bash
# Required - at least one provider
KIMI_API_KEY=sk-your-kimi-key
ANTHROPIC_API_KEY=sk-your-anthropic-key
OPENAI_API_KEY=sk-your-openai-key

# Optional - change ports if needed
WEB_UI_PORT=2077
AGENT_PORT=2013
```

### Step 3: Install Dependencies

**With Docker (Recommended):**
```bash
./setup.sh
```

**Without Docker:**
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Step 4: Start Services

```bash
./scripts/start-services.sh
```

---

## Verification

After installation, verify everything works:

```bash
./scripts/verify.sh
```

Expected output:
```
✓ Docker running
✓ kimiklaus-agent container: healthy
✓ kimiklaus-web-ui container: healthy
✓ API responding on port 2013
✓ Web UI accessible on port 2077
```

---

## Access Points

| Service | URL | Description |
|---------|-----|-------------|
| Web UI | http://localhost:2077 | Main chat interface |
| API | http://localhost:2013 | REST API endpoint |
| Memory Graph | http://localhost:2077/memory-graph | Visual memory explorer |

---

## Troubleshooting

### Port Already in Use

```bash
# Find what's using port 2077
lsof -i :2077

# Kill the process or change port in .env
```

### Container Won't Start

```bash
# Check logs
./scripts/logs.sh

# Restart services
./scripts/stop-services.sh
./scripts/start-services.sh
```

### Permission Denied

```bash
# Fix permissions
chmod +x scripts/*.sh
chmod +x *.sh
```

---

## Next Steps

1. Open http://localhost:2077 in your browser
2. Create your first session
3. Try uploading a file
4. Explore the Memory Graph

See [QUICKSTART.md](QUICKSTART.md) for usage examples.
