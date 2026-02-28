#!/usr/bin/env python3
"""
Klaus CLI Installer
===================

Command-line installer for headless environments.
Same flow as GUI but via terminal.

Usage:
    python installer/install_cli.py          # Interactive mode
    python installer/install_cli.py --yes    # Auto-confirm with defaults

"""

import argparse
import os
import sys
import shutil
import subprocess
import getpass
from pathlib import Path
from typing import Optional


class Colors:
    """Terminal colors."""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'


def print_header(text: str):
    """Print a header."""
    print(f"\n{Colors.HEADER}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}{text}{Colors.END}")
    print(f"{Colors.HEADER}{'='*60}{Colors.END}\n")


def print_success(text: str):
    """Print success message."""
    print(f"{Colors.GREEN}✓{Colors.END} {text}")


def print_error(text: str):
    """Print error message."""
    print(f"{Colors.FAIL}✗{Colors.END} {text}")


def print_warning(text: str):
    """Print warning message."""
    print(f"{Colors.WARNING}⚠{Colors.END} {text}")


def print_info(text: str):
    """Print info message."""
    print(f"{Colors.CYAN}ℹ{Colors.END} {text}")


def print_blade_runner(text: str):
    """Print Blade Runner style quote."""
    print(f"{Colors.CYAN}{text}{Colors.END}")


def prompt_input(prompt: str, default: Optional[str] = None) -> str:
    """Prompt for input."""
    if default:
        full_prompt = f"{prompt} [{default}]: "
    else:
        full_prompt = f"{prompt}: "
    
    response = input(full_prompt).strip()
    return response if response else (default or "")


def prompt_password(prompt: str) -> str:
    """Prompt for API key (visible input for easy validation)."""
    return input(f"{prompt}: ")


def prompt_choice(prompt: str, options: list, default: int = 0) -> int:
    """Prompt for choice from list."""
    print(f"\n{Colors.BOLD}{prompt}{Colors.END}")
    for i, (key, desc) in enumerate(options, 1):
        marker = "→" if i - 1 == default else " "
        print(f"  {marker} {i}. {key} - {desc}")
    
    while True:
        choice = input(f"\nSelect (1-{len(options)}) [{default + 1}]: ").strip()
        if not choice:
            return default
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(options):
                return idx
        except ValueError:
            pass
        print_error(f"Please enter a number between 1 and {len(options)}")


def check_prerequisites() -> bool:
    """Check that prerequisites are installed."""
    print_header("Checking Prerequisites")
    
    # Check Docker
    if not shutil.which("docker"):
        print_error("Docker is not installed")
        print_info("Please install Docker: https://docs.docker.com/get-docker/")
        return False
    print_success("Docker installed")
    
    # Check Docker Compose
    result = subprocess.run(
        ["docker", "compose", "version"],
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        print_error("Docker Compose is not available")
        return False
    print_success("Docker Compose available")
    
    return True


def step_welcome():
    """Welcome step."""
    print_header("🧙 Klaus Installer")
    print_blade_runner('"Wake up, time to install!"')
    print()
    print_info("This wizard will configure Klaus with your preferences.")
    print()
    print("You'll need:")
    print("  • Docker & Docker Compose installed")
    print("  • At least one AI provider API key")
    input("\nPress Enter to continue...")


def step_setup_mode() -> str:
    """Setup mode selection."""
    print_header("Setup Mode")
    
    options = [
        ("Web + IDE", "Full experience with browser UI and VS Code integration"),
        ("IDE Only", "Chat directly in VS Code, no browser needed"),
        ("Web Only", "Browser-based workflow"),
    ]
    
    choice = prompt_choice("Choose your setup mode:", options, default=0)
    modes = ['web+ide', 'ide-only', 'web-only']
    return modes[choice]


def step_provider() -> str:
    """AI provider selection."""
    print_header("Choose Your AI Provider")
    
    options = [
        ("Kimi (Recommended)", "Moonshot AI - Fast and reliable"),
        ("Anthropic", "Claude models - Great for coding"),
        ("Google", "Gemini via AI Studio"),
        ("OpenRouter", "Access multiple models"),
        ("Custom (Ollama)", "Local models - runs on your machine"),
    ]
    
    choice = prompt_choice("Select AI provider:", options, default=0)
    providers = ['kimi', 'anthropic', 'google', 'openrouter', 'custom']
    return providers[choice]


def step_api_key(provider: str) -> dict:
    """API key input."""
    print_header("API Configuration")
    
    config = {}
    
    # Helper to get key (allows empty for testing)
    def get_key(prompt_text: str) -> str:
        return prompt_password(prompt_text).strip()
    
    if provider == 'kimi':
        print_info("Get your key at: https://platform.moonshot.cn")
        config['kimi_key'] = get_key("Kimi API Key")
        
    elif provider == 'anthropic':
        print_info("Get your key at: https://console.anthropic.com")
        config['anthropic_key'] = get_key("Anthropic API Key")
        
    elif provider == 'google':
        print_info("Get your key at: https://aistudio.google.com")
        config['google_key'] = get_key("Google AI Studio API Key")
        
    elif provider == 'openrouter':
        print_info("Get your key at: https://openrouter.ai")
        config['openrouter_key'] = get_key("OpenRouter API Key")
        
    elif provider == 'custom':
        print_info("Custom provider (Ollama) configuration")
        config['custom_base_url'] = prompt_input(
            "Base URL", 
            default="http://localhost:11434/v1"
        )
        config['custom_model'] = prompt_input(
            "Model Name", 
            default="llama3.2"
        )
        print_info("Examples: llama3.2, deepseek-r1:14b, mistral")
    
    return config


def step_agent_config() -> dict:
    """Agent configuration."""
    print_header("Agent Configuration")
    
    config = {}
    config['agent_name'] = prompt_input("Agent Name", default="Klaus")
    
    print(f"\n{Colors.BOLD}Available personas:{Colors.END}")
    personas = [
        ("architect", "Solutions Architect"),
        ("developer", "Software Developer"),
        ("finance", "Financial Analyst"),
        ("general", "General Assistant"),
        ("legal", "Legal Assistant"),
        ("marketing", "Marketing Specialist"),
        ("ui", "UI/UX Designer"),
    ]
    
    for i, (key, desc) in enumerate(personas, 1):
        print(f"  {i}. {key:<12} - {desc}")
    
    while True:
        choice = input("\nSelect persona [1]: ").strip()
        if not choice:
            config['agent_persona'] = 'architect'
            break
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(personas):
                config['agent_persona'] = personas[idx][0]
                break
        except ValueError:
            pass
        print_error("Invalid choice")
    
    return config


def step_user_profile() -> dict:
    """User profile configuration."""
    print_header("Your Profile")
    
    config = {}
    config['user_name'] = prompt_input("Your Name")
    config['user_role'] = prompt_input("Your Role")
    print_info("e.g., Developer, Team Lead, Student, etc.")
    
    # Tone
    print(f"\n{Colors.BOLD}Tone of Voice:{Colors.END}")
    tones = ['professional', 'casual', 'enthusiastic', 'direct']
    for i, tone in enumerate(tones, 1):
        print(f"  {i}. {tone}")
    
    while True:
        choice = input("Select [1]: ").strip()
        if not choice:
            config['user_tone'] = 'professional'
            break
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(tones):
                config['user_tone'] = tones[idx]
                break
        except ValueError:
            pass
        print_error("Invalid choice")
    
    # Detail level
    print(f"\n{Colors.BOLD}Detail Level:{Colors.END}")
    details = ['concise', 'balanced', 'detailed', 'exhaustive']
    for i, detail in enumerate(details, 1):
        print(f"  {i}. {detail}")
    
    while True:
        choice = input("Select [2]: ").strip()
        if not choice:
            config['user_detail'] = 'balanced'
            break
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(details):
                config['user_detail'] = details[idx]
                break
        except ValueError:
            pass
        print_error("Invalid choice")
    
    return config


def step_summary(config: dict):
    """Show summary and confirm."""
    print_header("Ready to Install")
    
    print(f"{Colors.BOLD}Configuration Summary:{Colors.END}")
    print(f"  Setup Mode:   {config['setup_mode']}")
    print(f"  Provider:     {config['provider']}")
    print(f"  Agent Name:   {config['agent_name']}")
    print(f"  Persona:      {config['agent_persona']}")
    print(f"  User:         {config['user_name']} ({config['user_role']})")
    print()
    print("This will:")
    print("  ✓ Create workspace/SOUL.md and workspace/init.yaml")
    print("  ✓ Create .env with your API keys")
    print("  ✓ Build and start Docker containers")
    print("  ✓ Open http://localhost:2049 in your browser")
    
    confirm = input(f"\n{Colors.BOLD}Install Klaus? [Y/n]: {Colors.END}").strip().lower()
    return confirm in ('', 'y', 'yes')


def step_install(config: dict):
    """Run installation."""
    print_header("Installing...")
    print_blade_runner('"I\'ve seen things you people wouldn\'t believe..."')
    print()
    
    steps = [
        ("Creating configuration files", create_config_files),
        ("Validating Docker installation", check_docker),
        ("Pulling Docker images", pull_images),
        ("Building containers", build_containers),
        ("Starting services", start_services),
        ("Finalizing setup", finalize_setup),
    ]
    
    for i, (name, func) in enumerate(steps, 1):
        print(f"[{i}/{len(steps)}] {name}...", end=" ")
        if func(config):
            print_success("Done")
        else:
            print_error("Failed")
            return False
    
    return True


def create_config_files(config: dict) -> bool:
    """Create configuration files."""
    try:
        repo_root = Path(__file__).parent.parent
        workspace_dir = repo_root / "workspace"
        workspace_dir.mkdir(exist_ok=True)
        
        # .env
        env_content = f"""# Klaus Configuration
KIMI_API_KEY={config.get('kimi_key', '')}
ANTHROPIC_API_KEY={config.get('anthropic_key', '')}
GOOGLE_API_KEY={config.get('google_key', '')}
OPENROUTER_API_KEY={config.get('openrouter_key', '')}
CUSTOM_BASE_URL={config.get('custom_base_url', 'http://localhost:11434/v1')}
CUSTOM_MODEL={config.get('custom_model', 'llama3.2')}

KIMI_AGENT_PORT=2019
WEB_UI_PORT=2049
KLAUS_MODE={config['setup_mode']}
"""
        (workspace_dir / ".env").write_text(env_content)
        (repo_root / ".env").write_text(env_content)
        
        # init.yaml
        init_content = f"""agent:
  name: {config['agent_name']}
  template: {config['agent_persona']}
  personality:
    style: {config['user_detail']}
    tone: {config['user_tone']}

user:
  name: {config['user_name'] or 'User'}
  role: {config['user_role'] or 'Developer'}

mode:
  primary: hybrid
  ide:
    enabled: true
  telegram:
    enabled: false

provider:
  name: {config['provider']}
  parameters:
    temperature: 0.7
    max_tokens: 4096

defaults:
  provider: {config['provider']}
"""
        (workspace_dir / "init.yaml").write_text(init_content)
        
        # SOUL.md
        soul_content = f"""# {config['agent_name']} - Agent Profile

## User Profile
**Name:** {config['user_name'] or 'User'}
**Role:** {config['user_role'] or 'Developer'}
**Preferences:**
- **Tone:** {config['user_tone']}
- **Detail Level:** {config['user_detail']}

## Agent Configuration
**Name:** {config['agent_name']}
**Persona:** {config['agent_persona']}
**Provider:** {config['provider']}
"""
        (workspace_dir / "SOUL.md").write_text(soul_content)
        
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False


def check_docker(config: dict) -> bool:
    """Check Docker."""
    if not shutil.which("docker"):
        return False
    result = subprocess.run(["docker", "compose", "version"], capture_output=True)
    return result.returncode == 0


def pull_images(config: dict) -> bool:
    """Pull Docker images."""
    try:
        result = subprocess.run(["docker", "pull", "python:3.11-slim"], capture_output=True)
        return result.returncode == 0
    except:
        return False


def build_containers(config: dict) -> bool:
    """Build Docker containers."""
    try:
        repo_root = Path(__file__).parent.parent
        result = subprocess.run(
            ["docker", "compose", "-f", "docker/docker-compose.yml", "build"],
            cwd=repo_root,
            capture_output=True
        )
        return result.returncode == 0
    except Exception as e:
        print(f"Error: {e}")
        return False


def start_services(config: dict) -> bool:
    """Start Docker services."""
    try:
        repo_root = Path(__file__).parent.parent
        setup_mode = config.get('setup_mode', 'web+ide')
        
        # Determine which profile to use
        if setup_mode == 'web-only':
            profile = "web"
        elif setup_mode == 'web+ide':
            profile = "web"
        else:  # ide-only
            # For IDE-only, we still need web for now (simplified)
            profile = "web"
        
        # Start with profile
        result = subprocess.run(
            ["docker", "compose", "-f", "docker/docker-compose.yml", "--profile", profile, "up", "-d"],
            cwd=repo_root,
            capture_output=True
        )
        import time
        time.sleep(5)
        return result.returncode == 0
    except Exception as e:
        print(f"Error: {e}")
        return False


def finalize_setup(config: dict) -> bool:
    """Finalize setup."""
    return True


def step_complete():
    """Installation complete."""
    print_header("Installation Complete! 🎉")
    print_blade_runner('"Like tears in rain... time to code."')
    print()
    print(f"{Colors.GREEN}Klaus is running at:{Colors.END}")
    print(f"  🌐 http://localhost:2049")
    print()
    print("Useful commands:")
    print("  • Logs:    docker logs -f KLAUS_MAIN_web")
    print("  • Stop:    docker compose -f docker/docker-compose.yml down")
    print()
    print_success("Installation successful!")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Klaus CLI Installer')
    parser.add_argument('--yes', action='store_true', help='Auto-confirm with defaults')
    args = parser.parse_args()
    
    # Check prerequisites
    if not check_prerequisites():
        sys.exit(1)
    
    # Welcome
    step_welcome()
    
    # Collect configuration
    config = {}
    config['setup_mode'] = step_setup_mode()
    config['provider'] = step_provider()
    config.update(step_api_key(config['provider']))
    config.update(step_agent_config())
    config.update(step_user_profile())
    
    # Summary and confirm
    if not step_summary(config):
        print_warning("Installation cancelled")
        sys.exit(0)
    
    # Install
    if step_install(config):
        step_complete()
    else:
        print_error("Installation failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
