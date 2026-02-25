#!/usr/bin/env python3
"""
Klaus CLI Installer
===================

Command-line installer for headless environments.

Usage:
    python installer/install_cli.py [options]

Options:
    --dir PATH          Installation directory (default: ~/Klaus)
    --kimi-key KEY      Kimi API key
    --anthropic-key KEY Anthropic API key
    --openai-key KEY    OpenAI API key
    --mode MODE         Setup mode: full, minimal, dev (default: full)
    --yes               Auto-confirm all prompts
"""

import argparse
import os
import sys
import shutil
import subprocess
import platform
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


def check_prerequisites() -> bool:
    """Check that prerequisites are installed."""
    print_header("Checking Prerequisites")
    
    # Check Python version
    if sys.version_info < (3, 11):
        print_error("Python 3.11+ is required")
        return False
    print_success(f"Python {sys.version_info.major}.{sys.version_info.minor}")
    
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


def prompt_input(prompt: str, default: Optional[str] = None, 
                 secret: bool = False) -> str:
    """Prompt user for input."""
    if default:
        prompt = f"{prompt} [{default}]: "
    else:
        prompt = f"{prompt}: "
    
    if secret:
        import getpass
        value = getpass.getpass(prompt)
    else:
        value = input(prompt)
    
    return value if value else (default or "")


def prompt_yes_no(prompt: str, default: bool = False) -> bool:
    """Prompt yes/no question."""
    suffix = " [Y/n]: " if default else " [y/N]: "
    response = input(f"{prompt}{suffix}").strip().lower()
    
    if not response:
        return default
    
    return response in ['y', 'yes']


def setup_configuration(install_dir: Path, args) -> bool:
    """Setup configuration files."""
    print_header("Setting Up Configuration")
    
    try:
        # Create .env file
        env_content = f"""# Klaus Configuration
KIMI_API_KEY={args.kimi_key or ''}
ANTHROPIC_API_KEY={args.anthropic_key or ''}
OPENAI_API_KEY={args.openai_key or ''}
WEB_UI_PORT=7072
KIMI_AGENT_PORT=7070
"""
        
        env_file = install_dir / ".env"
        env_file.write_text(env_content)
        env_file.chmod(0o600)  # Restrict permissions
        print_success(f"Created {env_file}")
        
        # Create init.yaml
        init_yaml = install_dir / "init.yaml"
        if not init_yaml.exists():
            init_content = """agent:
  name: Klaus
  template: architect
  personality:
    language: en
    style: balanced
    tone: direct

mode:
  primary: hybrid
  ide:
    enabled: true
  telegram:
    enabled: false

provider:
  name: kimi
  model: kimi-k2-0711

defaults:
  provider: kimi
  model: kimi-k2-0711
"""
            init_yaml.write_text(init_content)
            print_success(f"Created {init_yaml}")
        
        return True
    except Exception as e:
        print_error(f"Failed to setup configuration: {e}")
        return False


def create_start_scripts(install_dir: Path) -> bool:
    """Create start/stop scripts."""
    print_header("Creating Start Scripts")
    
    try:
        if platform.system() == "Windows":
            # Windows batch files
            start_bat = install_dir / "start.bat"
            start_bat.write_text("""@echo off
echo Starting Klaus...
docker compose -f docker/docker-compose.yml up -d
echo.
echo Klaus is starting...
echo Web UI: http://localhost:7072
echo API: http://localhost:7070
timeout /t 3 >nul
echo.
echo To view logs: docker compose logs -f
echo To stop: stop.bat
pause
""")
            
            stop_bat = install_dir / "stop.bat"
            stop_bat.write_text("""@echo off
echo Stopping Klaus...
docker compose -f docker/docker-compose.yml down
echo Klaus stopped.
pause
""")
            print_success("Created start.bat and stop.bat")
        
        else:
            # Unix shell scripts
            start_sh = install_dir / "start.sh"
            start_sh.write_text("""#!/bin/bash
echo "🚀 Starting Klaus..."
docker compose -f docker/docker-compose.yml up -d
if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Klaus started successfully!"
    echo ""
    echo "📱 Web UI: http://localhost:7072"
    echo "🔌 API:    http://localhost:7070"
    echo ""
    echo "Useful commands:"
    echo "  View logs:  docker compose logs -f"
    echo "  Stop:       ./stop.sh"
    echo "  Status:     docker compose ps"
else
    echo "❌ Failed to start Klaus"
    exit 1
fi
""")
            start_sh.chmod(0o755)
            
            stop_sh = install_dir / "stop.sh"
            stop_sh.write_text("""#!/bin/bash
echo "🛑 Stopping Klaus..."
docker compose -f docker/docker-compose.yml down
echo "✅ Klaus stopped."
""")
            stop_sh.chmod(0o755)
            
            print_success("Created start.sh and stop.sh")
        
        return True
    except Exception as e:
        print_error(f"Failed to create scripts: {e}")
        return False


def install(args):
    """Main installation function."""
    print_header("🧙 Klaus Installer")
    print(f"Platform: {platform.system()} {platform.release()}")
    print(f"Python: {sys.version.split()[0]}")
    print()
    
    # Check prerequisites
    if not check_prerequisites():
        sys.exit(1)
    
    # Get installation directory
    if args.dir:
        install_dir = Path(args.dir)
    else:
        default_dir = str(Path.home() / "Klaus")
        dir_input = prompt_input("Installation directory", default_dir)
        install_dir = Path(dir_input)
    
    # Check if directory exists
    if install_dir.exists() and any(install_dir.iterdir()):
        print_warning(f"Directory {install_dir} is not empty")
        if not args.yes and not prompt_yes_no("Continue anyway?", False):
            print("Installation cancelled.")
            sys.exit(0)
    
    # Get API keys
    if not args.kimi_key:
        args.kimi_key = prompt_input("Kimi API Key (recommended)", secret=True)
    
    if not args.anthropic_key:
        if prompt_yes_no("Add Anthropic API Key?", False):
            args.anthropic_key = prompt_input("Anthropic API Key", secret=True)
    
    if not args.openai_key:
        if prompt_yes_no("Add OpenAI API Key?", False):
            args.openai_key = prompt_input("OpenAI API Key", secret=True)
    
    # Validate at least one key
    if not any([args.kimi_key, args.anthropic_key, args.openai_key]):
        print_error("At least one API key is required")
        sys.exit(1)
    
    # Confirm installation
    print_header("Installation Summary")
    print(f"Directory: {install_dir}")
    print(f"Mode: {args.mode}")
    print(f"Kimi Key: {'✓' if args.kimi_key else '✗'}")
    print(f"Anthropic Key: {'✓' if args.anthropic_key else '✗'}")
    print(f"OpenAI Key: {'✓' if args.openai_key else '✗'}")
    print()
    
    if not args.yes:
        if not prompt_yes_no("Proceed with installation?", True):
            print("Installation cancelled.")
            sys.exit(0)
    
    # Create directories
    print_header("Creating Directories")
    try:
        install_dir.mkdir(parents=True, exist_ok=True)
        
        # Create workspace structure
        workspace = install_dir / "workspace"
        for subdir in ["memory", "cognitive_memory", "semantic_memory",
                      "projects", "uploads", "web_ui_data"]:
            (workspace / subdir).mkdir(parents=True, exist_ok=True)
        
        print_success(f"Created directory structure at {install_dir}")
    except Exception as e:
        print_error(f"Failed to create directories: {e}")
        sys.exit(1)
    
    # Setup configuration
    if not setup_configuration(install_dir, args):
        sys.exit(1)
    
    # Create start scripts
    if not create_start_scripts(install_dir):
        sys.exit(1)
    
    # Success
    print_header("✅ Installation Complete!")
    print()
    print(f"Klaus has been installed to: {install_dir}")
    print()
    print("To start Klaus:")
    if platform.system() == "Windows":
        print(f"  cd {install_dir}")
        print("  .\\start.bat")
    else:
        print(f"  cd {install_dir}")
        print("  ./start.sh")
    print()
    print("Then open http://localhost:7072 in your browser.")
    print()
    print("Enjoy using Klaus! 🎉")


def main():
    """Parse arguments and run installer."""
    parser = argparse.ArgumentParser(
        description="Klaus CLI Installer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive installation
  python install_cli.py

  # Automated installation with Kimi key
  python install_cli.py --kimi-key sk-xxx --yes

  # Custom directory
  python install_cli.py --dir /opt/klaus
        """
    )
    
    parser.add_argument(
        "--dir",
        help="Installation directory (default: ~/Klaus)"
    )
    parser.add_argument(
        "--kimi-key",
        help="Kimi API key"
    )
    parser.add_argument(
        "--anthropic-key",
        help="Anthropic API key"
    )
    parser.add_argument(
        "--openai-key",
        help="OpenAI API key"
    )
    parser.add_argument(
        "--mode",
        choices=["full", "minimal", "dev"],
        default="full",
        help="Setup mode (default: full)"
    )
    parser.add_argument(
        "--yes", "-y",
        action="store_true",
        help="Auto-confirm all prompts"
    )
    
    args = parser.parse_args()
    
    try:
        install(args)
    except KeyboardInterrupt:
        print("\n\nInstallation cancelled by user.")
        sys.exit(1)


if __name__ == "__main__":
    main()
