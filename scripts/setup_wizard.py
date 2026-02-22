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
        
        # Step 2: Choose mode
        self._choose_mode()
        
        # Step 3: Select template
        self._select_template()
        
        # Step 4: User profile
        self._build_profile()
        
        # Step 5: Agent identity
        self._agent_identity()
        
        # Step 6: Review and confirm
        self._review_and_confirm()
        
        # Step 7: Generate files
        self._generate_files()
        
        print("\n✅ Setup complete! Start chatting with:")
        print("   python agent-cli.py chat")
    
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
        """Select operation mode."""
        print("\n🎯 Choose Setup Mode\n")
        
        modes = [
            ("IDE", "Works with Kimi Code, Claude Code, Cursor, etc.", "💻"),
            ("Telegram", "Chat via Telegram bot on your phone", "📱"),
            ("Hybrid", "Both IDE and Telegram (shared memory)", "⭐"),
        ]
        
        for i, (name, desc, emoji) in enumerate(modes, 1):
            print(f"  [{i}] {emoji} {name}")
            print(f"      {desc}")
            print()
        
        choice = input("Select mode [1-3]: ").strip()
        mode_map = {"1": "ide", "2": "telegram", "3": "hybrid"}
        self.answers["mode"] = mode_map.get(choice, "ide")
        
        # Configure Telegram if needed
        if self.answers["mode"] in ["telegram", "hybrid"]:
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
        print(f"Mode: {self.answers['mode'].upper()}")
        
        # Show Telegram config if applicable
        if self.answers['mode'] in ['telegram', 'hybrid']:
            token = self.answers.get('telegram_token', '')
            masked_token = f"{token[:15]}...{token[-10:]}" if len(token) > 25 else "***"
            print(f"Telegram Token: {masked_token}")
            if 'kimi_api_key' in self.answers:
                print(f"Docker: Kimi Agent on port 8081")
            if 'telegram_user_id' in self.answers:
                print(f"Authorized User: {self.answers['telegram_user_id']}")
            if 'telegram_webhook' in self.answers:
                print(f"Webhook: {self.answers['telegram_webhook']}")
        
        print(f"Template: {self.answers['template']}")
        print(f"Agent Name: {self.answers['agent_name']}")
        print(f"User: {self.answers['user_name']} ({self.answers['user_role']})")
        print(f"Experience: {self.answers['experience']}")
        print(f"Communication: {self.answers['communication']}")
        print("-" * 40)
        
        if input("\nCreate this configuration? [Y/n]: ").strip().lower() == "n":
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
        """Generate configuration files."""
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
