"""
Interactive Setup Wizard for IDE Agent Wizard
============================================
Conversational setup flow - asks questions, generates config.
"""

import os
import sys
import yaml
import json
from pathlib import Path
from typing import Optional, List, Dict
from dataclasses import dataclass

@dataclass
class Template:
    name: str
    description: str
    emoji: str
    best_for: str

def get_available_templates():
    """Get templates that actually exist in templates/ folder."""
    templates_dir = Path("templates")
    available = []
    
    template_info = {
        "general": ("General purpose assistant", "🤖", "Everyday tasks, Q&A"),
        "architect": ("Solutions Architect & AI Specialist", "🏗️", "System design, cloud architecture, AI/ML"),
        "developer": ("Software Engineer", "💻", "Coding, debugging, code review"),
        "finance": ("Financial Analyst", "💰", "Financial analysis, investing, budgeting"),
        "legal": ("Legal Assistant", "⚖️", "Legal research, contracts, compliance"),
        "marketing": ("Marketing & Growth", "📈", "Marketing strategy, copywriting, analytics"),
        "ui": ("UI/UX Designer", "🎨", "Design systems, user experience, prototyping"),
    }
    
    for name, (desc, emoji, best_for) in template_info.items():
        if (templates_dir / name / "SOUL.md").exists():
            available.append(Template(name, desc, emoji, best_for))
    
    return available

# Available templates (detected at runtime)
TEMPLATES = get_available_templates()

class SetupWizard:
    """Interactive setup wizard."""
    
    def __init__(self):
        self.config = {}
        self.answers = {}
        
    def run(self):
        """Run the full setup wizard."""
        print("🧙 Welcome to IDE Agent Wizard Setup!\n")
        
        # Step 1: Check for existing backups
        self._check_backups()
        
        # Step 2: Choose mode (detects existing config)
        self._choose_mode()
        
        action = self.answers.get("action", "new_setup")
        
        if action == "new_setup":
            # Full new setup flow
            self._select_template()
            self._build_profile()
            self._agent_identity()
        elif action == "add_telegram":
            # Telegram already configured in _configure_telegram()
            pass
        elif action == "remove_telegram":
            # Just confirm removal
            pass
        elif action == "edit_settings":
            # Ask what to edit
            self._edit_settings_menu()
        
        # Review and generate
        self._review_and_confirm()
        self._generate_files()
        
        # Final message
        if action == "add_telegram":
            print("\n✅ Telegram added!")
            print("   Start: docker-compose up -d")
        elif action == "remove_telegram":
            print("\n✅ Telegram removed!")
            print("   IDE mode active.")
        elif action == "edit_settings":
            print("\n✅ Settings updated!")
        else:
            print("\n✅ Setup complete! Start chatting with:")
            print("   python agent-cli.py chat")
    
    def _edit_settings_menu(self):
        """Menu for editing specific settings."""
        print("\n⚙️  What would you like to edit?\n")
        
        options = [
            ("1", "Agent Identity", "Name, tone, template", "🤖"),
            ("2", "User Profile", "Your name, role, preferences", "👤"),
            ("3", "Both", "All settings", "🔄"),
        ]
        
        for num, name, desc, emoji in options:
            print(f"  [{num}] {emoji} {name}")
            print(f"      {desc}")
            print()
        
        choice = input("Select [1-3]: ").strip()
        
        if choice == "1":
            self._select_template()
            self._agent_identity()
        elif choice == "2":
            self._build_profile()
        elif choice == "3":
            self._select_template()
            self._build_profile()
            self._agent_identity()
        else:
            print("Invalid choice. No changes made.")
            sys.exit(0)
    
    def _check_backups(self):
        """Check for existing backup to import."""
        backup_dir = Path("./backup")
        if not backup_dir.exists():
            return
            
        backups = list(backup_dir.iterdir())
        if not backups:
            return
            
        print("📦 Backup folder detected!\n")
        print(f"Found {len(backups)} backup(s):")
        for i, backup in enumerate(backups[:5], 1):
            print(f"  [{i}] {backup.name}")
        
        print("\nOptions:")
        print("  [I] Import from backup")
        print("  [S] Start fresh (ignore backups)")
        
        choice = input("\nChoice [I/S]: ").strip().upper()
        
        if choice == "I":
            self._import_backup(backups)
    
    def _import_backup(self, backups: List[Path]):
        """Import configuration from backup."""
        print("\n📥 Import Wizard")
        print("-" * 40)
        
        # Select backup
        if len(backups) == 1:
            selected = backups[0]
        else:
            for i, backup in enumerate(backups, 1):
                print(f"  [{i}] {backup.name}")
            idx = int(input("\nSelect backup: ")) - 1
            selected = backups[idx]
        
        print(f"\nScanning {selected.name}...")
        
        # Detect contents
        found = []
        if (selected / "config.json").exists():
            found.append("✓ Legacy config")
        if (selected / "memory.db").exists():
            size = (selected / "memory.db").stat().st_size
            found.append(f"✓ Memory database ({size//1024}KB)")
        if (selected / "user_profile.yaml").exists():
            found.append("✓ User profile")
            
        print("Found:")
        for item in found:
            print(f"  {item}")
        
        print("\nImport options:")
        print("  [1] Import everything")
        print("  [2] Config only")
        print("  [3] Memory only")
        print("  [4] Skip import")
        
        choice = input("\nChoice: ").strip()
        
        if choice in ["1", "2", "3"]:
            self.answers["import_from"] = str(selected)
            self.answers["import_mode"] = choice
    
    def _choose_mode(self):
        """Select operation mode based on existing config."""
        init_yaml = Path("./init.yaml")
        existing_config = None
        
        if init_yaml.exists():
            try:
                with open(init_yaml) as f:
                    existing_config = yaml.safe_load(f)
            except Exception:
                pass
        
        if existing_config:
            # Existing config detected - management mode
            print("\n🎯 Configuration Management\n")
            print("Existing init.yaml detected!\n")
            
            current_mode = existing_config.get("mode", {}).get("primary", "ide")
            telegram_enabled = existing_config.get("mode", {}).get("telegram", {}).get("enabled", False)
            
            print(f"Current setup: {'IDE + Telegram' if telegram_enabled else 'IDE only'}\n")
            
            options = []
            if not telegram_enabled:
                options.append(("1", "Add Telegram", "Add Telegram bot to existing IDE setup", "📱"))
            else:
                options.append(("1", "Remove Telegram", "Remove Telegram, keep IDE only", "💻"))
            
            options.append(("2", "Edit Settings", "Change profile, template, or other settings", "⚙️"))
            options.append(("3", "Start Fresh", "Delete existing and create new configuration", "🔄"))
            
            for num, name, desc, emoji in options:
                print(f"  [{num}] {emoji} {name}")
                print(f"      {desc}")
                print()
            
            choice = input(f"Select [1-{len(options)}]: ").strip()
            
            if choice == "1":
                if telegram_enabled:
                    self.answers["action"] = "remove_telegram"
                    self.answers["existing_config"] = existing_config
                else:
                    self.answers["action"] = "add_telegram"
                    self.answers["existing_config"] = existing_config
                    self._configure_telegram()
            elif choice == "2":
                self.answers["action"] = "edit_settings"
                self.answers["existing_config"] = existing_config
            elif choice == "3":
                confirm = input("⚠️  This will DELETE your current init.yaml. Continue? [y/N]: ").strip().lower()
                if confirm == "y":
                    self._new_setup_flow()
                else:
                    print("Cancelled.")
                    sys.exit(0)
            else:
                print("Invalid choice. Exiting.")
                sys.exit(1)
        else:
            # No existing config - new setup flow
            self._new_setup_flow()
    
    def _new_setup_flow(self):
        """New configuration setup."""
        print("\n🎯 New Configuration\n")
        
        modes = [
            ("ide_only", "IDE only - Works with Kimi Code, Claude Code, Cursor, etc.", "💻"),
            ("ide_telegram", "IDE + Telegram - Both IDE and Telegram bot", "⭐"),
        ]
        
        for i, (key, desc, emoji) in enumerate(modes, 1):
            print(f"  [{i}] {emoji} {key.replace('_', ' ').title()}")
            print(f"      {desc}")
            print()
        
        choice = input("Select [1-2]: ").strip()
        mode_map = {"1": "ide_only", "2": "ide_telegram"}
        selected = mode_map.get(choice, "ide_only")
        
        self.answers["action"] = "new_setup"
        self.answers["mode"] = "ide" if selected == "ide_only" else "hybrid"
        
        # Configure Telegram if needed
        if selected == "ide_telegram":
            self._configure_telegram()
    
    def _configure_telegram(self):
        """Configure Telegram bot settings."""
        print("\n📱 Telegram Configuration\n")
        
        print("To create a bot:")
        print("  1. Open Telegram and search for @BotFather")
        print("  2. Send /newbot and follow instructions")
        print("  3. Copy the token provided\n")
        
        # Get bot token
        while True:
            token = input("Bot Token (from @BotFather): ").strip()
            if token:
                self.answers["telegram_token"] = token
                break
            print("❌ Token is required for Telegram mode")
        
        # Optional: Authorized User ID
        print("\nAuthorized User ID (optional):")
        print("  - Restrict bot to specific Telegram user only")
        print("  - Leave empty to allow anyone")
        print("  - Get your ID from @userinfobot")
        user_id = input("Your Telegram User ID: ").strip()
        if user_id:
            self.answers["telegram_user_id"] = user_id
            print(f"   ✅ Bot restricted to user ID: {user_id}")
        else:
            print("   ✅ Bot open to all users")
        
        # Optional: Webhook URL
        print("\nWebhook URL (optional, press Enter to skip):")
        print("  - For polling mode (default), leave empty")
        print("  - For webhook, enter your HTTPS URL")
        webhook = input("Webhook URL: ").strip()
        if webhook:
            self.answers["telegram_webhook"] = webhook
        
        # Docker / Kimi Agent Configuration
        print("\n🐳 Docker Configuration")
        print("The Telegram bot uses TWO containers:")
        print("  1. Kimi Agent (port 8081) - Has your API key, processes LLM")
        print("  2. Telegram Bot - Receives messages, manages memory\n")
        
        print("You need a Kimi API key for the Docker agent.")
        print("Get it at: https://platform.moonshot.cn\n")
        
        while True:
            api_key = input("Kimi API Key: ").strip()
            if api_key:
                self.answers["kimi_api_key"] = api_key
                break
            print("❌ API key is required for Kimi Agent")
        
        print("\n✅ Docker will be configured with:")
        print(f"   Kimi Agent: http://localhost:8081")
        print(f"   Shared Memory: ./workspace/memory/")
        
        print("\n✅ Telegram configured!")
        print(f"   Token: {token[:20]}...{token[-10:]}")
        print(f"   Docker: Kimi Agent on port 8081")
        if user_id:
            print(f"   Authorized User: {user_id}")
        if webhook:
            print(f"   Webhook: {webhook}")
        else:
            print("   Mode: Polling (default)")
    
    def _select_template(self):
        """Select agent template."""
        print("\n🎨 Choose Agent Template\n")
        
        # Reload templates to ensure we have current list
        templates = get_available_templates()
        
        if not templates:
            print("⚠️  No templates found! Using 'general' as default.")
            self.answers["template"] = "general"
            return
        
        for i, template in enumerate(templates, 1):
            print(f"  [{i}] {template.emoji} {template.name}")
            print(f"      {template.description}")
            print(f"      Best for: {template.best_for}")
            print()
        
        max_choice = len(templates)
        print(f"Tip: Type 'describe <number>' to learn more (1-{max_choice})")
        
        while True:
            choice = input(f"Select template [1-{max_choice}]: ").strip().lower()
            
            if choice.startswith("describe "):
                try:
                    num = int(choice.split()[1]) - 1
                    if 0 <= num < len(templates):
                        self._show_template_details(templates[num])
                except (ValueError, IndexError):
                    print(f"Invalid description number. Use 1-{max_choice}")
                continue
                
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(templates):
                    self.answers["template"] = templates[idx].name
                    break
            except ValueError:
                pass
                
            print(f"Invalid choice. Please enter 1-{max_choice}.")
    
    def _show_template_details(self, template):
        """Show detailed template info."""
        print(f"\n{template.emoji} {template.name.upper()}")
        print("-" * 40)
        print(f"Description: {template.description}")
        print(f"Best for: {template.best_for}")
        
        # Show SOUL preview
        soul_path = Path(f"templates/{template.name}/SOUL.md")
        if soul_path.exists():
            try:
                content = soul_path.read_text()
                # Extract philosophy (line starting with > )
                for line in content.split('\n'):
                    if line.strip().startswith('> '):
                        philosophy = line.strip()[2:]
                        print(f"\nPhilosophy: \"{philosophy}\"")
                        break
            except Exception:
                pass
        print()
    
    def _build_profile(self):
        """Build user profile."""
        print("\n👤 Tell Me About Yourself\n")
        
        self.answers["user_name"] = input("Your name: ").strip()
        self.answers["user_role"] = input("Your role/title: ").strip()
        
        print("\nExperience level:")
        levels = ["beginner", "intermediate", "advanced", "expert"]
        for i, level in enumerate(levels, 1):
            print(f"  [{i}] {level.capitalize()}")
        
        exp = input("Select [1-4]: ").strip()
        self.answers["experience"] = levels[int(exp)-1] if exp in "1234" else "intermediate"
        
        print("\nCommunication preference:")
        styles = [
            ("concise", "Short and to the point"),
            ("detailed", "Thorough explanations"),
            ("bullet_points", "Structured lists"),
        ]
        for i, (key, desc) in enumerate(styles, 1):
            print(f"  [{i}] {key.replace('_', ' ').title()} - {desc}")
        
        style = input("Select [1-3]: ").strip()
        self.answers["communication"] = styles[int(style)-1][0] if style in "123" else "concise"
    
    def _agent_identity(self):
        """Set agent identity."""
        print("\n🤖 Agent Identity\n")
        
        # Ask for agent name (no default)
        print("\nWhat would you like to name your agent?")
        print("(e.g., Assistant, Helper, or any name you prefer)")
        
        while True:
            name = input("Agent name: ").strip()
            if name:
                self.answers["agent_name"] = name
                break
            print("Please enter a name for your agent.")
        
        print("\nTone:")
        tones = ["professional", "casual", "enthusiastic", "direct"]
        for i, tone in enumerate(tones, 1):
            print(f"  [{i}] {tone.capitalize()}")
        
        tone = input("Select [1-4]: ").strip()
        self.answers["tone"] = tones[int(tone)-1] if tone in "1234" else "professional"
    
    def _review_and_confirm(self):
        """Show summary and confirm."""
        print("\n📋 Configuration Summary\n")
        print("-" * 40)
        
        action = self.answers.get("action", "new_setup")
        
        if action == "add_telegram":
            print("Action: ADD Telegram to existing setup")
            token = self.answers.get('telegram_token', '')
            masked_token = f"{token[:15]}...{token[-10:]}" if len(token) > 25 else "***"
            print(f"Telegram Token: {masked_token}")
            if 'telegram_user_id' in self.answers:
                print(f"Authorized User: {self.answers['telegram_user_id']}")
            if 'telegram_webhook' in self.answers:
                print(f"Webhook: {self.answers['telegram_webhook']}")
        elif action == "remove_telegram":
            print("Action: REMOVE Telegram (keep IDE)")
        elif action == "edit_settings":
            print("Action: EDIT existing settings")
            print(f"Template: {self.answers.get('template', 'unchanged')}")
            print(f"Agent Name: {self.answers.get('agent_name', 'unchanged')}")
        else:
            # New setup
            mode_display = "IDE only" if self.answers.get('mode') == 'ide' else "IDE + Telegram"
            print(f"Mode: {mode_display}")
            
            if self.answers.get('mode') == 'hybrid':
                token = self.answers.get('telegram_token', '')
                masked_token = f"{token[:15]}...{token[-10:]}" if len(token) > 25 else "***"
                print(f"Telegram Token: {masked_token}")
                if 'telegram_user_id' in self.answers:
                    print(f"Authorized User: {self.answers['telegram_user_id']}")
            
            print(f"Template: {self.answers['template']}")
            print(f"Agent Name: {self.answers['agent_name']}")
            print(f"User: {self.answers['user_name']} ({self.answers['user_role']})")
            print(f"Experience: {self.answers['experience']}")
            print(f"Communication: {self.answers['communication']}")
        
        print("-" * 40)
        
        if input("\nProceed? [Y/n]: ").strip().lower() == "n":
            print("Setup cancelled.")
            sys.exit(0)
    
    def _create_fallback_soul(self, dst: Path):
        """Create a basic SOUL.md if template is missing."""
        content = f"""# SOUL - {self.answers["agent_name"]}

## Identity
**Name:** {self.answers["agent_name"]}  
**Role:** AI Assistant  
**Specialization:** General purpose assistance  
**Created:** 2026-02-22

## Core Philosophy
> "Be helpful, be accurate, be kind."

## Personality
**Tone:** {self.answers["tone"]}  
**Style:** balanced  
**Language:** en

## Capabilities
- Answering questions
- Writing and editing
- Coding assistance
- Problem solving

---
*This is a fallback SOUL.md created during setup.*
"""
        dst.write_text(content)
        print(f"  ✓ workspace/SOUL.md created (fallback)")

    def _generate_files(self):
        """Generate or update configuration files."""
        action = self.answers.get("action", "new_setup")
        
        if action == "add_telegram":
            self._update_add_telegram()
        elif action == "remove_telegram":
            self._update_remove_telegram()
        elif action == "edit_settings":
            self._update_edit_settings()
        else:
            self._create_new_config()
    
    def _update_add_telegram(self):
        """Add Telegram to existing config."""
        print("\n📝 Adding Telegram to existing config...")
        
        config = self.answers["existing_config"]
        
        # Update mode
        config["mode"]["primary"] = "hybrid"
        config["mode"]["telegram"]["enabled"] = True
        config["mode"]["telegram"]["bot_token"] = self.answers.get("telegram_token", "")
        config["mode"]["telegram"]["user_id"] = self.answers.get("telegram_user_id", "")
        config["mode"]["telegram"]["webhook_url"] = self.answers.get("telegram_webhook", "")
        
        # Save init.yaml
        with open("./init.yaml", "w") as f:
            yaml.dump(config, f, default_flow_style=False)
        print("  ✓ init.yaml updated with Telegram")
        
        # Update or create .env
        if self.answers.get("kimi_api_key"):
            env_content = f"""# IDE Agent Wizard - Environment Variables
TELEGRAM_BOT_TOKEN={self.answers.get("telegram_token", "")}
KIMI_API_KEY={self.answers.get("kimi_api_key", "")}
KIMI_AGENT_URL=http://localhost:8081
"""
            Path("./.env").write_text(env_content)
            print("  ✓ .env created (for Docker)")
        
        print("\n✅ Telegram added!")
        print("   Start the bot with: docker-compose up -d")
    
    def _update_remove_telegram(self):
        """Remove Telegram from existing config."""
        print("\n📝 Removing Telegram from config...")
        
        config = self.answers["existing_config"]
        
        # Update mode
        config["mode"]["primary"] = "ide"
        config["mode"]["telegram"]["enabled"] = False
        # Keep other telegram settings but disable
        
        # Save init.yaml
        with open("./init.yaml", "w") as f:
            yaml.dump(config, f, default_flow_style=False)
        print("  ✓ init.yaml updated (Telegram disabled)")
        
        print("\n✅ Telegram removed!")
        print("   IDE mode is still active.")
        print("   To completely stop the bot: docker-compose down")
    
    def _update_edit_settings(self):
        """Edit settings in existing config."""
        print("\n📝 Updating settings...")
        
        config = self.answers["existing_config"]
        
        # Update agent settings if changed
        if "agent_name" in self.answers:
            config["agent"]["name"] = self.answers["agent_name"]
        if "template" in self.answers:
            config["agent"]["template"] = self.answers["template"]
        if "tone" in self.answers:
            config["agent"]["personality"]["tone"] = self.answers["tone"]
        
        # Update user settings if changed
        if "user_name" in self.answers:
            config["user"]["name"] = self.answers["user_name"]
        if "user_role" in self.answers:
            config["user"]["role"] = self.answers["user_role"]
        if "experience" in self.answers:
            config["user"]["experience_level"] = self.answers["experience"]
        if "communication" in self.answers:
            config["user"]["preferences"]["communication"] = self.answers["communication"]
        
        # Save init.yaml
        with open("./init.yaml", "w") as f:
            yaml.dump(config, f, default_flow_style=False)
        print("  ✓ init.yaml updated")
        
        # Update SOUL.md if template changed
        if "template" in self.answers:
            self._update_soul_md()
        
        # Update USER.md if user info changed
        if any(k in self.answers for k in ["user_name", "user_role", "experience", "communication"]):
            self._update_user_md()
        
        print("\n✅ Settings updated!")
    
    def _update_soul_md(self):
        """Update SOUL.md from template."""
        template = self.answers.get("template")
        if not template:
            return
            
        soul_src = Path(f"templates/{template}/SOUL.md")
        soul_dst = Path("./workspace/SOUL.md")
        
        if soul_src.exists():
            try:
                content = soul_src.read_text()
                replacements = {
                    "{{agent_name}}": self.answers.get("agent_name", config.get("agent", {}).get("name", "Assistant")),
                    "{{created_date}}": "2026-02-22",
                    "{{tone}}": self.answers.get("tone", config.get("agent", {}).get("personality", {}).get("tone", "professional")),
                    "{{style}}": "balanced",
                    "{{language}}": "en",
                }
                for old, new in replacements.items():
                    content = content.replace(old, new)
                soul_dst.write_text(content)
                print(f"  ✓ workspace/SOUL.md updated (from {template} template)")
            except Exception as e:
                print(f"  ⚠️  Error updating SOUL.md: {e}")
    
    def _update_user_md(self):
        """Update USER.md with new info."""
        config = self.answers["existing_config"]
        
        user_name = self.answers.get("user_name", config.get("user", {}).get("name", "User"))
        user_role = self.answers.get("user_role", config.get("user", {}).get("role", ""))
        experience = self.answers.get("experience", config.get("user", {}).get("experience_level", "intermediate"))
        communication = self.answers.get("communication", config.get("user", {}).get("preferences", {}).get("communication", "concise"))
        
        user_md = f"""# USER - {user_name}

## Profile
**Name:** {user_name}  
**Role:** {user_role}  
**Experience Level:** {experience}

## Preferences
- **Communication:** {communication}
- **Code Style:** clean

---
"""
        Path("./workspace/USER.md").write_text(user_md)
        print("  ✓ workspace/USER.md updated")
    
    def _create_new_config(self):
        """Generate new configuration files."""
        print("\n📝 Generating files...")
        
        # Create directories
        Path("./workspace").mkdir(exist_ok=True)
        Path("./workspace/memory").mkdir(exist_ok=True)
        Path("./workspace/projects").mkdir(exist_ok=True)
        Path("./logs").mkdir(exist_ok=True)
        
        # Generate init.yaml
        config = {
            "agent": {
                "name": self.answers["agent_name"],
                "template": self.answers["template"],
                "personality": {
                    "tone": self.answers["tone"],
                    "style": "balanced",
                    "language": "en"
                }
            },
            "user": {
                "name": self.answers["user_name"],
                "role": self.answers["user_role"],
                "experience_level": self.answers["experience"],
                "preferences": {
                    "communication": self.answers["communication"],
                    "code_style": "clean"
                }
            },
            "mode": {
                "primary": self.answers["mode"],
                "ide": {"enabled": True},
                "telegram": {
                    "enabled": self.answers["mode"] in ["telegram", "hybrid"],
                    "bot_token": self.answers.get("telegram_token", ""),
                    "user_id": self.answers.get("telegram_user_id", ""),
                    "webhook_url": self.answers.get("telegram_webhook", "")
                }
            },
            "provider": {
                "name": "kimi",
                "api_key": "",
                "model": {
                    "kimi": "kimi-k2-5"
                },
                "parameters": {
                    "temperature": 0.7,
                    "max_tokens": 4096,
                    "top_p": 0.9
                }
            }
        }
        
        with open("./init.yaml", "w") as f:
            yaml.dump(config, f, default_flow_style=False)
        
        print("  ✓ init.yaml created")
        
        # Create .env file for Docker
        if self.answers.get("kimi_api_key"):
            env_content = f"""# IDE Agent Wizard - Environment Variables
TELEGRAM_BOT_TOKEN={self.answers.get("telegram_token", "")}
KIMI_API_KEY={self.answers.get("kimi_api_key", "")}
KIMI_AGENT_URL=http://localhost:8081
"""
            Path("./.env").write_text(env_content)
            print("  ✓ .env created (for Docker)")
        
        # Copy template SOUL.md
        template = self.answers["template"]
        soul_src = Path(f"templates/{template}/SOUL.md")
        soul_dst = Path("./workspace/SOUL.md")
        
        if soul_src.exists():
            try:
                content = soul_src.read_text()
                # Replace ALL template variables
                replacements = {
                    "{{agent_name}}": self.answers["agent_name"],
                    "{{created_date}}": "2026-02-22",
                    "{{tone}}": self.answers["tone"],
                    "{{style}}": "balanced",
                    "{{language}}": "en",
                }
                for old, new in replacements.items():
                    content = content.replace(old, new)
                soul_dst.write_text(content)
                print(f"  ✓ workspace/SOUL.md created (from {template} template)")
            except Exception as e:
                print(f"  ⚠️  Error creating SOUL.md: {e}")
                self._create_fallback_soul(soul_dst)
        else:
            print(f"  ⚠️  Template {template} not found, using fallback")
            self._create_fallback_soul(soul_dst)
        
        # Create USER.md
        user_md = f"""# USER - {self.answers['user_name']}

## Profile
**Name:** {self.answers['user_name']}  
**Role:** {self.answers['user_role']}  
**Experience Level:** {self.answers['experience']}

## Preferences
- **Communication:** {self.answers['communication']}
- **Code Style:** clean

---
"""
        Path("./workspace/USER.md").write_text(user_md)
        print("  ✓ workspace/USER.md created")


def main():
    """Entry point."""
    wizard = SetupWizard()
    wizard.run()


if __name__ == "__main__":
    main()
