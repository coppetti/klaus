#!/usr/bin/env python3
"""
IDE Agent Wizard - Initialization Script
========================================
Post-setup initialization for the agent.

Usage:
    source .venv/bin/activate && python initialize.py
    
This script loads:
- init.yaml configuration
- SOUL.md (agent identity)
- USER.md (user profile)
- Memory store (SQLite)
- Workspace structure

After running, the agent has full context of:
- Who it is (the agent)
- Who the user is (Mateus)
- Current projects
- Memory system status
"""

import os
import sys
import yaml
from pathlib import Path
from datetime import datetime

# Ensure core is in path
sys.path.insert(0, str(Path(__file__).parent))

def print_header(title):
    """Print formatted header."""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")

def print_section(title):
    """Print section header."""
    print(f"\n📌 {title}")
    print("-" * 50)

def load_config(config_path="init.yaml"):
    """Load init.yaml configuration."""
    path = Path(config_path)
    if not path.exists():
        print(f"❌ Config file not found: {config_path}")
        return None
    
    with open(path) as f:
        return yaml.safe_load(f)

def load_soul():
    """Load SOUL.md (agent identity)."""
    paths = [
        Path("workspace/SOUL.md"),
        Path("SOUL.md"),
    ]
    
    for path in paths:
        if path.exists():
            return path.read_text()
    
    return None

def load_user_profile():
    """Load USER.md (user profile)."""
    paths = [
        Path("workspace/USER.md"),
        Path("USER.md"),
    ]
    
    for path in paths:
        if path.exists():
            return path.read_text()
    
    return None

def scan_workspace():
    """Scan workspace structure."""
    workspace = Path("workspace")
    if not workspace.exists():
        return {}
    
    structure = {
        "root_files": [],
        "projects": [],
        "directories": []
    }
    
    for item in workspace.iterdir():
        if item.is_dir():
            if item.name == "projects":
                # Scan projects
                for proj in item.iterdir():
                    if proj.is_dir():
                        structure["projects"].append(proj.name)
            elif item.name not in ["memory"]:
                structure["directories"].append(item.name)
        else:
            structure["root_files"].append(item.name)
    
    return structure

def initialize_memory(config):
    """Initialize memory store."""
    try:
        from core.memory import MemoryStore
        
        memory_config = config.get('memory', {})
        if not memory_config.get('enabled', True):
            return None, "disabled"
        
        backend = memory_config.get('backend', 'sqlite')
        db_path = memory_config.get('sqlite', {}).get('path', './memory.db')
        
        # Adjust path for workspace
        if not Path(db_path).exists() and Path('workspace').exists():
            db_path = f"workspace/{db_path}"
        
        memory = MemoryStore(db_path)
        stats = memory.get_stats()
        
        return memory, stats
    except Exception as e:
        return None, f"error: {e}"

def initialize_ide_connector(config):
    """Initialize IDE connector."""
    try:
        from core.connectors.ide_connector import IDEConnector
        return IDEConnector("init.yaml")
    except Exception as e:
        print(f"⚠️  IDE Connector not initialized: {e}")
        return None

def main():
    """Main initialization routine."""
    print_header("🧙 IDE Agent Wizard - Initialization")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Working Directory: {Path.cwd()}")
    
    # 1. Load Configuration
    print_section("LOADING CONFIGURATION (init.yaml)")
    config = load_config()
    
    if not config:
        print("❌ Failed to load configuration. Run setup.sh first.")
        sys.exit(1)
    
    agent_config = config.get('agent', {})
    user_config = config.get('user', {})
    mode_config = config.get('mode', {})
    
    print(f"✅ Configuration loaded successfully")
    
    # 2. Agent Identity
    print_section("AGENT IDENTITY")
    print(f"Name: {agent_config.get('name', 'Unknown')}")
    print(f"Template: {agent_config.get('template', 'general')}")
    print(f"Tone: {agent_config.get('personality', {}).get('tone', 'professional')}")
    print(f"Style: {agent_config.get('personality', {}).get('style', 'balanced')}")
    
    # 3. User Profile
    print_section("USER PROFILE")
    print(f"Name: {user_config.get('name', 'Unknown')}")
    print(f"Role: {user_config.get('role', 'Unknown')}")
    print(f"Experience: {user_config.get('experience_level', 'intermediate')}")
    print(f"Communication: {user_config.get('preferences', {}).get('communication', 'concise')}")
    
    # 4. Mode Configuration
    print_section("OPERATION MODE")
    mode = mode_config.get('primary', 'ide')
    print(f"Primary Mode: {mode.upper()}")
    print(f"  IDE: {'✅' if mode_config.get('ide', {}).get('enabled', True) else '❌'}")
    print(f"  Telegram: {'✅' if mode_config.get('telegram', {}).get('enabled', False) else '❌'}")
    print(f"  API: {'✅' if mode_config.get('api', {}).get('enabled', False) else '❌'}")
    
    # 5. Load SOUL.md
    print_section("AGENT SOUL (SOUL.md)")
    soul = load_soul()
    if soul:
        # Extract key philosophy line
        lines = soul.split('\n')
        for line in lines:
            if line.startswith('> '):
                print(f"Philosophy: {line[2:]}")
                break
        print(f"✅ SOUL.md loaded ({len(soul)} characters)")
    else:
        print("⚠️  SOUL.md not found")
    
    # 6. Load USER.md
    print_section("USER PROFILE (USER.md)")
    user_md = load_user_profile()
    if user_md:
        print(f"✅ USER.md loaded ({len(user_md)} characters)")
    else:
        print("⚠️  USER.md not found")
    
    # 6.5 Check AGENTS.md (for AI agent reference)
    agents_md = Path("AGENTS.md")
    if agents_md.exists():
        print(f"📖 AGENTS.md available for AI agent reference")
    
    # 7. Workspace Structure
    print_section("WORKSPACE STRUCTURE")
    structure = scan_workspace()
    
    if structure.get('root_files'):
        print("Root Files:")
        for f in structure['root_files']:
            print(f"  • {f}")
    
    if structure.get('directories'):
        print("Directories:")
        for d in structure['directories']:
            print(f"  • {d}/")
    
    if structure.get('projects'):
        print("Projects:")
        for p in structure['projects']:
            print(f"  • 📁 {p}/")
    else:
        print("Projects: (none yet)")
    
    # 8. Memory System
    print_section("MEMORY SYSTEM")
    memory, stats = initialize_memory(config)
    
    if memory:
        if isinstance(stats, dict):
            print(f"✅ Memory Store: SQLite")
            print(f"   Total memories: {stats.get('total', 0)}")
            print(f"   Categories: {', '.join(stats.get('categories', {}).keys()) or 'none'}")
        else:
            print(f"⚠️  Memory status: {stats}")
    else:
        print("❌ Memory system failed to initialize")
    
    # 9. IDE Connector
    print_section("IDE CONNECTOR")
    connector = initialize_ide_connector(config)
    
    if connector:
        print(f"✅ IDE Connector initialized")
        print(f"   Agent: {connector.agent_name}")
        print(f"   User: {connector.user_name}")
        print(f"   Memory: {'✅' if connector.memory else '❌'}")
    else:
        print("⚠️  IDE Connector not available")
    
    # 10. Summary
    print_header("✅ INITIALIZATION COMPLETE")
    
    print("Agent is ready with full context:")
    print(f"  • Identity: {agent_config.get('name', 'Unknown')} ({agent_config.get('template', 'general')})")
    print(f"  • User: {user_config.get('name', 'Unknown')} ({user_config.get('role', 'Unknown')})")
    print(f"  • Mode: {mode.upper()}")
    print(f"  • Memory: {'Active' if memory else 'Inactive'}")
    print(f"  • Connector: {'Active' if connector else 'Inactive'}")
    
    print("\n🚀 You can now start working!")
    print("\nQuick commands:")
    print("  python agent-cli.py chat    # Interactive chat")
    print("  python agent-cli.py memory  # Memory stats")
    print("  python agent-cli.py config  # Show config")
    
    # Store initialization in memory
    if memory:
        memory.store(
            content=f"System initialized at {datetime.now().isoformat()}. "
                    f"Agent: {agent_config.get('name')}, User: {user_config.get('name')}, "
                    f"Mode: {mode}",
            category="system",
            importance="high",
            metadata={"type": "initialization", "timestamp": datetime.now().isoformat()}
        )

if __name__ == "__main__":
    main()
