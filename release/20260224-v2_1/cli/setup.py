#!/usr/bin/env python3
"""
IDE Agent Wizard - One-Command Setup
====================================
Installs dependencies and runs interactive setup.
"""

import subprocess
import sys

def install_requirements():
    """Install required packages."""
    print("📦 Installing dependencies...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "--user", "-r", "requirements.txt"])
        print("✅ Dependencies installed!\n")
        return True
    except subprocess.CalledProcessError:
        print("❌ Failed to install dependencies")
        print("Try manually: pip3 install -r requirements.txt")
        return False

def main():
    print("🧙 IDE Agent Wizard Setup\n")
    
    # Install dependencies
    if not install_requirements():
        sys.exit(1)
    
    # Run the wizard
    print("🚀 Starting setup wizard...\n")
    import setup_wizard
    setup_wizard.main()

if __name__ == "__main__":
    main()
