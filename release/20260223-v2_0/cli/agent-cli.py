#!/usr/bin/env python3
"""
IDE Agent Wizard - CLI
======================
Universal CLI that works with any IDE and LLM provider.

Usage:
    python agent-cli.py [command]
    
Commands:
    chat          Start interactive chat
    config        Show current configuration
    memory        Memory management
    setup         Interactive setup wizard
"""

import os
import sys
import yaml
import asyncio
import argparse
from pathlib import Path
from typing import Optional

# Add core to path
sys.path.insert(0, str(Path(__file__).parent))

from core.agent import Agent
from core.memory import MemoryStore

# Colors for terminal
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'

def print_header(text: str):
    print(f"\n{Colors.HEADER}{'='*60}{Colors.END}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text.center(60)}{Colors.END}")
    print(f"{Colors.HEADER}{'='*60}{Colors.END}\n")

def print_success(text: str):
    print(f"{Colors.GREEN}✓ {text}{Colors.END}")

def print_error(text: str):
    print(f"{Colors.FAIL}✗ {text}{Colors.END}")

def load_config(config_path: str = "init.yaml") -> dict:
    """Load configuration file."""
    config_file = Path(config_path)
    
    if not config_file.exists():
        print_error(f"Config file not found: {config_path}")
        print(f"Run: {Colors.CYAN}python agent-cli.py setup{Colors.END} to create one.")
        sys.exit(1)
    
    with open(config_file) as f:
        return yaml.safe_load(f)

async def interactive_chat(agent: Agent):
    """Run interactive chat session."""
    config = agent.config
    agent_name = config.get('agent', {}).get('name', 'Agent')
    user_name = config.get('user', {}).get('name', 'User')
    
    print_header(f"🤖 {agent_name} - Interactive Mode")
    print(f"Provider: {Colors.CYAN}{agent.provider.provider_type.value}{Colors.END}")
    print(f"Model: {Colors.CYAN}{agent.provider.model}{Colors.END}")
    print(f"Memory: {Colors.GREEN if agent.memory else Colors.FAIL}{'ON' if agent.memory else 'OFF'}{Colors.END}")
    print(f"\nCommands:")
    print(f"  {Colors.CYAN}/quit{Colors.END} or {Colors.CYAN}/q{Colors.END} - Exit")
    print(f"  {Colors.CYAN}/memory{Colors.END} or {Colors.CYAN}/m{Colors.END} - Show memories")
    print(f"  {Colors.CYAN}/clear{Colors.END} or {Colors.CYAN}/c{Colors.END} - Clear screen")
    print(f"  {Colors.CYAN}/context <file>{Colors.END} - Load file context")
    print(f"\nType your message and press Enter...")
    print("=" * 60)
    
    context = None
    
    while True:
        try:
            user_input = input(f"\n{Colors.BLUE}{user_name}:{Colors.END} ").strip()
            
            if not user_input:
                continue
            
            # Commands
            if user_input.lower() in ['/quit', '/q', 'exit']:
                print(f"\n{Colors.GREEN}Goodbye! 👋{Colors.END}")
                break
            
            if user_input.lower() in ['/memory', '/m']:
                if agent.memory:
                    stats = agent.memory.get_stats()
                    print(f"\n{Colors.CYAN}🧠 Memory Stats:{Colors.END}")
                    print(f"  Total: {stats['total']}")
                    for cat, count in stats['categories'].items():
                        print(f"  {cat}: {count}")
                else:
                    print_error("Memory is disabled")
                continue
            
            if user_input.lower() in ['/clear', '/c']:
                os.system('clear' if os.name != 'nt' else 'cls')
                continue
            
            if user_input.startswith('/context '):
                file_path = user_input[9:].strip()
                if Path(file_path).exists():
                    context = Path(file_path).read_text()
                    print_success(f"Loaded context from {file_path}")
                else:
                    print_error(f"File not found: {file_path}")
                continue
            
            # Send message
            print(f"\n{Colors.CYAN}{agent_name}:{Colors.END} ", end='', flush=True)
            
            response_parts = []
            async for token in agent.chat(user_input, context):
                print(token, end='', flush=True)
                response_parts.append(token)
            
            print()  # New line
            
        except KeyboardInterrupt:
            print(f"\n\n{Colors.GREEN}Goodbye! 👋{Colors.END}")
            break
        except Exception as e:
            print_error(f"Error: {e}")

def show_config(config: dict):
    """Display configuration."""
    print_header("Configuration")
    
    agent = config.get('agent', {})
    provider = config.get('provider', {})
    user = config.get('user', {})
    mode = config.get('mode', {})
    
    print(f"{Colors.BOLD}Agent:{Colors.END}")
    print(f"  Name: {agent.get('name', 'N/A')}")
    print(f"  Template: {agent.get('template', 'N/A')}")
    print(f"  Version: {agent.get('version', 'N/A')}")
    
    print(f"\n{Colors.BOLD}Provider:{Colors.END}")
    print(f"  Name: {provider.get('name', 'N/A')}")
    print(f"  Model: {provider.get('model', {}).get(provider.get('name', ''), 'N/A')}")
    
    print(f"\n{Colors.BOLD}User:{Colors.END}")
    print(f"  Name: {user.get('name', 'N/A')}")
    print(f"  Role: {user.get('role', 'N/A')}")
    print(f"  Experience: {user.get('experience_level', 'N/A')}")
    
    print(f"\n{Colors.BOLD}Modes:{Colors.END}")
    print(f"  Primary: {mode.get('primary', 'N/A')}")
    print(f"  IDE: {'✓' if mode.get('ide', {}).get('enabled') else '✗'}")
    print(f"  Telegram: {'✓' if mode.get('telegram', {}).get('enabled') else '✗'}")
    print(f"  API: {'✓' if mode.get('api', {}).get('enabled') else '✗'}")

def setup_wizard():
    """Interactive setup wizard."""
    print_header("🧙 IDE Agent Wizard - Setup")
    
    print("This wizard will help you create your init.yaml configuration.\n")
    
    # Agent info
    agent_name = input(f"{Colors.BLUE}?{Colors.END} Agent name [My Agent]: ").strip() or "My Agent"
    
    # Provider selection
    print(f"\n{Colors.BLUE}?{Colors.END} Select LLM provider:")
    print("  1. Anthropic (Claude)")
    print("  2. OpenRouter (multi-model)")
    print("  3. Google (Gemini)")
    print("  4. Kimi (Moonshot)")
    
    provider_choice = input("Select (1-4) [1]: ").strip() or "1"
    providers = {
        "1": ("anthropic", "claude-3-5-sonnet-20241022"),
        "2": ("openrouter", "anthropic/claude-3.5-sonnet"),
        "3": ("gemini", "gemini-1.5-pro"),
        "4": ("kimi", "kimi-latest")
    }
    provider_name, default_model = providers.get(provider_choice, providers["1"])
    
    # API Key
    api_key = input(f"\n{Colors.BLUE}?{Colors.END} {provider_name.upper()}_API_KEY: ").strip()
    
    # User info
    user_name = input(f"\n{Colors.BLUE}?{Colors.END} Your name [User]: ").strip() or "User"
    user_role = input(f"{Colors.BLUE}?{Colors.END} Your role [Developer]: ").strip() or "Developer"
    
    # Mode selection
    print(f"\n{Colors.BLUE}?{Colors.END} Select mode:")
    print("  1. IDE only (VS Code, Claude Code, etc.)")
    print("  2. Telegram only")
    print("  3. Hybrid (IDE + Telegram)")
    mode_choice = input("Select (1-3) [3]: ").strip() or "3"
    modes = {"1": "ide", "2": "telegram", "3": "hybrid"}
    mode = modes.get(mode_choice, "hybrid")
    
    # Build config
    config = {
        "agent": {
            "name": agent_name,
            "version": "1.0.0",
            "description": f"AI assistant powered by {provider_name}",
            "template": "general",
            "personality": {
                "tone": "professional",
                "style": "balanced",
                "language": "en"
            }
        },
        "user": {
            "name": user_name,
            "role": user_role,
            "experience_level": "intermediate",
            "preferences": {
                "communication": "concise",
                "code_style": "clean",
                "working_hours": "9-18",
                "timezone": "UTC"
            }
        },
        "provider": {
            "name": provider_name,
            "api_key": api_key,
            "model": {
                provider_name: default_model
            },
            "parameters": {
                "temperature": 0.7,
                "max_tokens": 4096,
                "top_p": 0.9
            }
        },
        "mode": {
            "primary": mode,
            "ide": {"enabled": mode in ["ide", "hybrid"], "connector": "auto"},
            "telegram": {"enabled": mode in ["telegram", "hybrid"], "bot_token": "", "webhook_url": ""},
            "api": {"enabled": False, "port": 8080, "host": "0.0.0.0"}
        },
        "memory": {
            "enabled": True,
            "backend": "sqlite",
            "sqlite": {"path": "./memory/agent_memory.db"},
            "settings": {"max_memories": 1000, "decay_days": 90, "embedding_model": "local"}
        },
        "tools": {
            "files": {"enabled": True, "allowed_paths": ["./workspace", "./projects"], "blocked_extensions": [".env", ".key"]},
            "web_search": {"enabled": False, "provider": "tavily"},
            "code_execution": {"enabled": False, "sandbox": "docker"},
            "apis": {"enabled": False, "endpoints": []}
        },
        "integrations": {
            "git": {"enabled": True, "auto_commit": False},
            "github": {"enabled": False, "token": ""},
            "notion": {"enabled": False, "token": ""},
            "slack": {"enabled": False, "webhook": ""}
        },
        "advanced": {
            "log_level": "info",
            "log_file": "./logs/agent.log",
            "cache_enabled": True,
            "cache_ttl": 3600,
            "rate_limit": {"requests_per_minute": 60, "tokens_per_minute": 100000},
            "safety_checks": True,
            "max_file_size": "10MB",
            "timeout_seconds": 120
        },
        "custom_instructions": ""
    }
    
    # Save config
    with open("init.yaml", "w") as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)
    
    print_success("\nConfiguration saved to init.yaml!")
    print(f"\n{Colors.CYAN}Next steps:{Colors.END}")
    print("  1. Review init.yaml and customize if needed")
    print("  2. Set API key via environment variable for security:")
    print(f"     export {provider_name.upper()}_API_KEY='your-key'")
    print("  3. Run: python agent-cli.py chat")

def main():
    parser = argparse.ArgumentParser(
        description="IDE Agent Wizard - Universal CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python agent-cli.py setup          # Interactive setup
  python agent-cli.py chat           # Start chat
  python agent-cli.py config         # Show configuration
  python agent-cli.py memory         # Memory management
        """
    )
    
    parser.add_argument(
        "command",
        choices=["setup", "chat", "config", "memory"],
        help="Command to run"
    )
    
    parser.add_argument(
        "--config",
        default="init.yaml",
        help="Path to config file (default: init.yaml)"
    )
    
    args = parser.parse_args()
    
    if args.command == "setup":
        setup_wizard()
    
    elif args.command == "config":
        config = load_config(args.config)
        show_config(config)
    
    elif args.command == "chat":
        config = load_config(args.config)
        
        try:
            agent = Agent(config)
            asyncio.run(interactive_chat(agent))
        except Exception as e:
            print_error(f"Failed to start agent: {e}")
            sys.exit(1)
    
    elif args.command == "memory":
        print_header("Memory Management")
        db_path = "./memory/agent_memory.db"
        
        if not Path(db_path).exists():
            print_error(f"No memory database found at {db_path}")
            return
        
        store = MemoryStore(db_path)
        stats = store.get_stats()
        
        print(f"{Colors.BOLD}Memory Statistics:{Colors.END}")
        print(f"  Total memories: {stats['total']}")
        
        if stats['categories']:
            print(f"\n{Colors.BOLD}By Category:{Colors.END}")
            for cat, count in sorted(stats['categories'].items()):
                print(f"  {cat}: {count}")
        
        action = input(f"\n{Colors.BLUE}?{Colors.END} Clear all memories? [y/N]: ").strip().lower()
        if action == 'y':
            store.clear()
            print_success("All memories cleared!")

if __name__ == "__main__":
    main()
