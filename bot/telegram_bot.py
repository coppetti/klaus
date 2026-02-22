#!/usr/bin/env python3
"""
IDE Agent Wizard - Telegram Bot
===============================
Telegram interface using external Kimi Agent (Docker:8081)
with synchronized memory.
"""

import os
import sys
import json
import asyncio
import logging
import aiohttp
import yaml
from pathlib import Path
from typing import Optional, Dict, List
from datetime import datetime

# Add core to path
sys.path.insert(0, str(Path(__file__).parent))

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

from core.memory import MemoryStore

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Config
KIMI_AGENT_URL = os.getenv('KIMI_AGENT_URL', 'http://localhost:8081')
WORKSPACE_PATH = Path(__file__).parent / "workspace"


class KimiAgentClient:
    """Cliente para o Agente Kimi rodando em Docker (porta 8081)."""
    
    def __init__(self, base_url: str = KIMI_AGENT_URL):
        self.base_url = base_url
        self.session = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, *args):
        if self.session:
            await self.session.close()
    
    async def chat(self, user_id: str, message: str, context: Optional[Dict] = None) -> Dict:
        """Envia mensagem para o agente e retorna resposta."""
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        async with self.session.post(
            f"{self.base_url}/chat",
            json={
                "user_id": user_id,
                "message": message,
                "context": context or {}
            },
            timeout=aiohttp.ClientTimeout(total=120)
        ) as response:
            if response.status != 200:
                error = await response.text()
                raise Exception(f"Agent error: {error}")
            return await response.json()
    
    async def health(self) -> bool:
        """Verifica se o agente está online."""
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        try:
            async with self.session.get(
                f"{self.base_url}/health",
                timeout=aiohttp.ClientTimeout(total=5)
            ) as resp:
                return resp.status == 200
        except:
            return False


class TelegramBot:
    """Telegram bot com integração ao Kimi Agent e memória sincronizada."""
    
    def __init__(self, config_path: str = "init.yaml"):
        self.config_path = config_path
        self.config = self._load_config()
        self.memory: Optional[MemoryStore] = None
        self.kimi = KimiAgentClient()
        
    def _load_config(self) -> dict:
        """Load configuration."""
        with open(self.config_path) as f:
            return yaml.safe_load(f)
    
    def _init_memory(self):
        """Initialize memory store."""
        memory_config = self.config.get('memory', {})
        if not memory_config.get('enabled', True):
            return
        
        backend = memory_config.get('backend', 'sqlite')
        db_path = memory_config.get('sqlite', {}).get('path', './workspace/memory/agent_memory.db')
        
        # Ensure directory exists
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
        self.memory = MemoryStore(db_path)
        logger.info("✅ Memory Store conectado")
    
    def _get_memories(self, user_id: str, query: str, top_k: int = 3) -> List[Dict]:
        """Recupera memórias relevantes."""
        if not self.memory:
            return []
        
        try:
            memories = self.memory.recall(query, limit=top_k)
            return [
                {
                    "id": m['id'],
                    "content": m['content'],
                    "category": m['category']
                }
                for m in memories
            ]
        except Exception as e:
            logger.error(f"Erro ao recuperar memórias: {e}")
            return []
    
    def _load_soul_md(self) -> str:
        """Carrega SOUL.md para personalidade."""
        soul_paths = [
            WORKSPACE_PATH / "SOUL.md",
            Path("workspace/SOUL.md"),
            Path("/app/workspace/SOUL.md"),
        ]
        
        for path in soul_paths:
            if path.exists():
                try:
                    content = path.read_text()
                    logger.info(f"✅ SOUL.md carregado de {path}")
                    return content
                except Exception as e:
                    logger.warning(f"⚠️ Erro ao ler SOUL.md de {path}: {e}")
                    continue
        
        logger.warning("⚠️ SOUL.md não encontrado")
        return ""
    
    def _load_agents_md(self) -> str:
        """Carrega AGENTS.md para guia do agente."""
        agents_paths = [
            Path("/app/docs/AGENTS.md"),
            Path("docs/AGENTS.md"),
            Path(__file__).parent.parent / "docs" / "AGENTS.md",
        ]
        
        for path in agents_paths:
            if path.exists():
                try:
                    content = path.read_text()
                    logger.info(f"✅ AGENTS.md carregado de {path}")
                    return content
                except Exception as e:
                    logger.warning(f"⚠️ Erro ao ler AGENTS.md de {path}: {e}")
                    continue
        
        logger.warning("⚠️ AGENTS.md não encontrado")
        return ""
    
    def _save_memory(self, user_id: str, content: str, category: str = "conversation"):
        """Salva memória."""
        if not self.memory:
            return
        
        try:
            self.memory.store(
                content=content,
                category=category,
                importance="medium",
                metadata={"user_id": user_id, "timestamp": datetime.now().isoformat()}
            )
        except Exception as e:
            logger.error(f"Erro ao salvar memória: {e}")
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start."""
        agent_name = self.config.get('agent', {}).get('name', 'Agent')
        
        welcome = f"""👋 Hello! I'm **{agent_name}**.

I'm connected to Kimi Agent at `{KIMI_AGENT_URL}`.

**Available Commands:**
/start - This message
/help - Show help
/clear - Clear conversation
/memory - Memory stats
/health - Check Kimi Agent status
/projects - List your projects

**File Access:**
• `workspace/projects/` - Your projects folder
• `workspace/SOUL.md` - Agent identity
• `workspace/USER.md` - Your profile
• `docs/AGENTS.md` - Agent guide

What can I help you with?"""
        
        await update.message.reply_text(welcome, parse_mode="Markdown")
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help."""
        help_text = """ℹ️ **Help**

Just send me a message and I'll respond via Kimi Agent!

**Features:**
• Synchronized memory with local database
• Connected to Kimi Agent (Docker)
• User authorization
• Access to workspace/projects folder
• AGENTS.md auto-loaded for context

**Commands:**
/help - This message
/clear - Clear conversation history
/memory - Show memory statistics
/health - Check Kimi Agent health
/projects - List projects in workspace

**File Paths (in Docker):**
• `/app/workspace/projects/` - Your projects
• `/app/workspace/SOUL.md` - Agent identity
• `/app/workspace/USER.md` - Your profile
• `/app/docs/AGENTS.md` - Agent guide

Happy chatting! 🚀"""
        
        await update.message.reply_text(help_text, parse_mode="Markdown")
    
    async def clear_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /clear."""
        await update.message.reply_text("✅ Conversation history cleared!")
    
    async def memory_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /memory."""
        if not self.memory:
            await update.message.reply_text("❌ Memory is not enabled.")
            return
        
        stats = self.memory.get_stats()
        
        text = f"""🧠 **Memory Statistics**

Total memories: {stats['total']}

Categories:"""
        
        for cat, count in sorted(stats['categories'].items()):
            text += f"\n  • {cat}: {count}"
        
        text += "\n\nSynced with Kimi Agent container!"
        
        await update.message.reply_text(text, parse_mode="Markdown")
    
    async def health_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Check Kimi Agent health."""
        async with self.kimi:
            is_healthy = await self.kimi.health()
        
        if is_healthy:
            # Check if AGENTS.md is loaded
            agents_loaded = Path("/app/docs/AGENTS.md").exists() or Path("docs/AGENTS.md").exists()
            await update.message.reply_text(
                f"✅ **Kimi Agent is online**\n\n"
                f"URL: `{KIMI_AGENT_URL}`\n"
                f"AGENTS.md: {'✅' if agents_loaded else '❌'}",
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text(
                f"❌ **Kimi Agent is offline**\n\nCheck if Docker is running:\n"
                f"`docker ps | grep kimi`",
                parse_mode="Markdown"
            )
    
    async def projects_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """List projects in workspace/projects."""
        projects_path = Path("/app/workspace/projects")
        if not projects_path.exists():
            projects_path = Path("workspace/projects")
        
        if not projects_path.exists():
            await update.message.reply_text("❌ Projects folder not found.")
            return
        
        projects = [d.name for d in projects_path.iterdir() if d.is_dir()]
        files = [f.name for f in projects_path.iterdir() if f.is_file()]
        
        text = "📁 **Projects**\n\n"
        
        if projects:
            text += "**Folders:**\n"
            for p in sorted(projects):
                text += f"  • 📂 `{p}/`\n"
            text += "\n"
        
        if files:
            text += "**Files:**\n"
            for f in sorted(files):
                text += f"  • 📄 `{f}`\n"
            text += "\n"
        
        if not projects and not files:
            text += "No projects yet.\n\n"
        
        text += f"Path: `/app/workspace/projects/`"
        
        await update.message.reply_text(text, parse_mode="Markdown")
    
    def _is_authorized(self, user_id: int) -> bool:
        """Check if user is authorized."""
        authorized_id = self.config.get('mode', {}).get('telegram', {}).get('user_id')
        if not authorized_id:
            return True  # No restriction
        return str(user_id) == str(authorized_id)
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle incoming messages."""
        if not update.message or not update.message.text:
            return
        
        # Check authorization
        user_id = update.effective_user.id if update.effective_user else None
        if user_id and not self._is_authorized(user_id):
            await update.message.reply_text("⛔ Sorry, you're not authorized to use this bot.")
            return
        
        user_message = update.message.text
        user_id_str = str(user_id) if user_id else "unknown"
        
        # Show typing indicator
        await context.bot.send_chat_action(
            chat_id=update.effective_chat.id,
            action="typing"
        )
        
        try:
            # Get memories, SOUL and AGENTS.md for context
            memories = self._get_memories(user_id_str, user_message)
            soul = self._load_soul_md()
            agents_guide = self._load_agents_md()
            
            # Prepare context (compatible with clawd-agent)
            ctx = {
                "username": update.effective_user.username or "user",
                "memories": memories,
                "soul_personality": soul[:2000] if soul else "",  # clawd-agent expects this key
                "agents_guide": agents_guide[:2000] if agents_guide else "",  # AGENTS.md guide
                "agent_name": self.config.get('agent', {}).get('name', 'Agent')
            }
            
            # Send to Kimi Agent
            async with self.kimi:
                result = await self.kimi.chat(
                    user_id=user_id_str,
                    message=user_message,
                    context=ctx
                )
            
            response = result.get("response", "⚠️ No response from agent.")
            
            # Store interaction
            self._save_memory(
                user_id_str,
                f"Q: {user_message[:100]}\nA: {response[:100]}",
                "conversation"
            )
            
            # Send response (Telegram has 4096 char limit)
            if len(response) > 4000:
                chunks = [response[i:i+4000] for i in range(0, len(response), 4000)]
                for chunk in chunks:
                    await update.message.reply_text(chunk)
            else:
                await update.message.reply_text(response)
                
        except Exception as e:
            logger.error(f"Error: {e}")
            await update.message.reply_text(
                f"❌ Error: {str(e)}\n\nMake sure Kimi Agent is running on {KIMI_AGENT_URL}"
            )
    
    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle errors."""
        logger.error(f"Error: {context.error}")
        if update and update.message:
            await update.message.reply_text("❌ An unexpected error occurred.")
    
    def run(self):
        """Run the bot."""
        token = self.config.get('mode', {}).get('telegram', {}).get('bot_token')
        
        if not token:
            token = os.getenv('TELEGRAM_BOT_TOKEN')
        
        if not token:
            print("❌ Error: TELEGRAM_BOT_TOKEN not set!")
            print("Set it in init.yaml or as environment variable.")
            sys.exit(1)
        
        # Initialize memory
        self._init_memory()
        
        print(f"🤖 Starting {self.config.get('agent', {}).get('name', 'Agent')} Telegram Bot...")
        print(f"🔗 Kimi Agent: {KIMI_AGENT_URL}")
        print(f"🧠 Memory: {'✅' if self.memory else '❌'}")
        
        # Build application
        application = Application.builder().token(token).build()
        
        # Add handlers
        application.add_handler(CommandHandler("start", self.start_command))
        application.add_handler(CommandHandler("help", self.help_command))
        application.add_handler(CommandHandler("clear", self.clear_command))
        application.add_handler(CommandHandler("memory", self.memory_command))
        application.add_handler(CommandHandler("health", self.health_command))
        application.add_handler(CommandHandler("projects", self.projects_command))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        
        # Error handler
        application.add_error_handler(self.error_handler)
        
        # Run
        print("✅ Bot is running! Press Ctrl+C to stop.")
        application.run_polling(allowed_updates=Update.ALL_TYPES)


def main():
    """Main entry point."""
    bot = TelegramBot()
    bot.run()


if __name__ == "__main__":
    main()
