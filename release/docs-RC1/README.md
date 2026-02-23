# IDE Agent Wizard - Documentation v1.1.0-RC1

This folder contains comprehensive documentation for the IDE Agent Wizard release candidate.

---

## 📚 Documentation Files

| File | Description | Audience |
|------|-------------|----------|
| `QUICKSTART.md` | 3-minute setup guide | New users |
| `COMPREHENSIVE-GUIDE.md` | Complete reference manual | All users |

### Quick Start
**New to IDE Agent Wizard?** Start here:
1. Read `QUICKSTART.md`
2. Run `./setup.sh`
3. Start building!

### Comprehensive Guide
**Need detailed information?** The comprehensive guide covers:
- Architecture and system design
- All setup options and configuration management
- Memory system internals
- Telegram integration details
- IDE integration patterns
- Template customization
- Provider configuration
- Docker services
- Security best practices
- Troubleshooting guide
- API reference

---

## 📊 Diagrams

Located in `diagrams/` folder. View with [Mermaid Live Editor](https://mermaid.live).

### Setup & Configuration
| Diagram | File | Description |
|---------|------|-------------|
| **Setup Flow** | `setup-flow.mmd` | Visual flowchart of setup wizard |
| **Configuration States** | `configuration-states.mmd` | State machine of config management |
| **Architecture** | `architecture.mmd` | System component overview |
| **Telegram Architecture** | `telegram-architecture.mmd` | Two-container Telegram setup |
| **Data Flow** | `data-flow.mmd` | Sequence diagram of message processing |

### Memory System (Detailed)
| Diagram | File | Description |
|---------|------|-------------|
| **Memory System Overview** | `memory-system.mmd` | High-level memory flow |
| **Database Schema** | `memory-database-schema.mmd` | SQLite table structure + ERD |
| **Memory Architecture** | `memory-architecture-detailed.mmd` | Complete internal architecture |
| **Memory Retrieval Flow** | `memory-retrieval-flow.mmd` | How context is built from memories |
| **Memory Categories** | `memory-categories.mmd` | Types of stored information |
| **What It Is** | `memory-what-it-is.mmd` | Current capabilities vs future options |

### Viewing Diagrams

**Option 1: Mermaid Live Editor**
1. Go to https://mermaid.live
2. Copy contents of `.mmd` file
3. Paste and view

**Option 2: VS Code**
Install "Markdown Preview Mermaid Support" extension.

**Option 3: Export to PNG/SVG**
```bash
# Using mermaid-cli (requires Node.js)
npm install -g @mermaid-js/mermaid-cli
mmdc -i diagrams/architecture.mmd -o architecture.png
```

---

## 🗺️ Documentation Map

```
docs-RC1/
├── README.md                          ← You are here
├── QUICKSTART.md                      ← Start here (3 min)
├── COMPREHENSIVE-GUIDE.md             ← Full reference
└── diagrams/
    │
    ├── SETUP & CONFIGURATION
    │   ├── setup-flow.mmd            ← Setup wizard flow
    │   ├── configuration-states.mmd  ← Config state machine
    │   ├── architecture.mmd          ← System architecture
    │   ├── telegram-architecture.mmd ← Telegram containers
    │   └── data-flow.mmd             ← Message processing
    │
    └── MEMORY SYSTEM (DETAILED)
        ├── memory-system.mmd         ← Memory overview
        ├── memory-database-schema.mmd ← SQLite schema + ERD
        ├── memory-architecture-detailed.mmd ← Internal architecture
        ├── memory-retrieval-flow.mmd ← Context building
        ├── memory-categories.mmd     ← Storage types
        └── memory-what-it-is.mmd     ← Current vs future
```

---

## 🔗 Related Documentation

| Location | Content |
|----------|---------|
| `../docs/README.md` | Main project documentation |
| `../docs/AGENTS.md` | Guide for AI assistants |
| `../docs/RELEASE_NOTES.md` | Version history |
| `../docs/CHECKLIST.md` | Release checklist |
| `../PACKAGE.txt` | Package information |

---

## 📖 Reading Guide

### For New Users
1. `QUICKSTART.md` - Get up and running
2. `COMPREHENSIVE-GUIDE.md` - Understand the system
3. `diagrams/architecture.mmd` - Visual overview

### For Developers
1. `COMPREHENSIVE-GUIDE.md` - API reference
2. `diagrams/data-flow.mmd` - Understand processing
3. `diagrams/memory-architecture-detailed.mmd` - Memory internals
4. `diagrams/memory-database-schema.mmd` - Database structure
5. `../docs/AGENTS.md` - AI assistant guide

### For System Administrators
1. `COMPREHENSIVE-GUIDE.md` - Security section
2. `diagrams/telegram-architecture.mmd` - Deployment
3. `../docs/CHECKLIST.md` - Production readiness

---

## 🆘 Getting Help

**Quick questions?** See `QUICKSTART.md` troubleshooting section.

**Detailed issues?** See `COMPREHENSIVE-GUIDE.md` troubleshooting chapter.

**AI assistant help?** See `../docs/AGENTS.md`.

---

**Version:** v1.1.0-RC1  
**Date:** 2026-02-23  
**Status:** Release Candidate
