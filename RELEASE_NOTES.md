# Klaus v1.0.0 Release Notes

## Overview
First stable release of **Klaus** - AI Solutions Architect with Hybrid Memory.

## Features

### 🤖 AI Capabilities
- **Multi-Provider Support**: Kimi (default), Anthropic, OpenAI, Google, OpenRouter
- **Hybrid Memory System**: SQLite + Kuzu Graph for persistent context
- **Cognitive Memory**: Episodic, semantic, and procedural memory types
- **Memory Consolidation**: Automatic and manual consolidation to knowledge graph

### 💬 Web UI
- Modern chat interface with multi-line input
- Model selector with real-time switching
- Session management and persistence
- Memory explorer and graph visualization
- Context analyzer with compaction tools
- File upload support

### 📱 Telegram Bot
- Full Telegram integration
- Web UI configuration for bot token
- System notifications
- Command support (/status, /consolidate, etc.)

### 🧠 Memory Features
- Episodic memory with VAD emotional modeling
- Knowledge graph with entity extraction
- Semantic memory for user preferences
- Memory decay and strength calculation
- Consolidation preview and selective consolidation

### 🔧 Infrastructure
- Docker Compose setup
- Health checks and monitoring
- Ngrok integration for remote access
- Environment-based configuration

## Quick Start

```bash
# 1. Configure
cp .env.example .env
# Edit .env with your API keys

# 2. Setup
./setup.sh

# 3. Start
./scripts/start-services.sh

# 4. Access
# Web UI: http://localhost:7072
# API: http://localhost:7070
```

## System Requirements
- Docker & Docker Compose
- 4GB RAM minimum
- API key from at least one provider (Kimi recommended)

## Known Limitations
- Memory consolidation requires substantial technical content
- File upload limited to text files
- Ngrok requires authtoken for persistent URLs

---

*Klaus - Design for scale, build for change.*
