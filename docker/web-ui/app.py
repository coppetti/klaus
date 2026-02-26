"""
Klaus - AI Solutions Architect
=================================
Modern Shadcn-inspired interface with chat + config panel
Uses Hybrid Memory (SQLite + Graph) for intelligent context
Features: Settings Panel, Session Management, Web Search
"""

import os
import json
import sys
import httpx
import pickle
import uuid
import re
from datetime import datetime
from typing import Dict, List, Optional, Any
from fastapi import FastAPI, Request, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse, Response
from pathlib import Path
import yaml
from pydantic import BaseModel
import shutil
import tempfile

# Add core to path for hybrid memory
# Path: docker/web-ui/app.py -> core/
core_path = Path(__file__).parent.parent.parent / "core"
if core_path.exists():
    sys.path.insert(0, str(core_path))
else:
    # Fallback for container path
    sys.path.insert(0, "/app/core")

# Try to import hybrid memory
try:
    from hybrid_memory import HybridMemoryStore, MemoryQuery
    HYBRID_AVAILABLE = True
except ImportError:
    HYBRID_AVAILABLE = False
    print("⚠️  Hybrid memory not available, using simple storage")

# Try to import web search
try:
    from core.tools.web_search import WebSearchTool, search_web, get_weather
    WEB_SEARCH_AVAILABLE = True
except ImportError:
    WEB_SEARCH_AVAILABLE = False
    print("⚠️  Web search not available")

# Try to import context manager
try:
    from core.context_manager import SessionContextManager, ContextManager
    from core.context_compactor import SessionContextCompactor, ContextCompactor, ContextAnalyzer
    CONTEXT_MANAGER_AVAILABLE = True
    COMPACTOR_AVAILABLE = True
except ImportError:
    CONTEXT_MANAGER_AVAILABLE = False
    COMPACTOR_AVAILABLE = False
    SessionContextManager = Any  # type: ignore
    SessionContextCompactor = Any  # type: ignore
    print("⚠️  Context manager or compactor not available")

# Try to import llm_router
try:
    from llm_router import chat_with_provider as chat_with_provider_shared
    LLM_ROUTER_AVAILABLE = True
except ImportError:
    LLM_ROUTER_AVAILABLE = False
    print("⚠️  LLM router not available")


def save_env_var(key: str, value: str):
    """Save environment variable to .env file for persistence."""
    env_path = Path(".env")
    if not env_path.exists():
        env_path = Path("/app/.env")  # Container path
    
    if not env_path.exists():
        # Create new .env file
        with open(env_path, 'w') as f:
            f.write(f"{key}={value}\n")
        return
    
    # Read existing .env
    with open(env_path, 'r') as f:
        lines = f.readlines()
    
    # Check if key exists and update it
    key_found = False
    for i, line in enumerate(lines):
        if line.startswith(f"{key}=") or line.startswith(f"{key} ="):
            lines[i] = f"{key}={value}\n"
            key_found = True
            break
    
    # If key not found, append it
    if not key_found:
        lines.append(f"{key}={value}\n")
    
    # Write back
    with open(env_path, 'w') as f:
        f.writelines(lines)


# Initialize tools
web_search_tool = WebSearchTool() if WEB_SEARCH_AVAILABLE else None
session_context_managers: Dict[str, SessionContextManager] = {}
session_compactors: Dict[str, SessionContextCompactor] = {}

app = FastAPI(title="Klaus - AI Solutions Architect")

async def send_telegram_notification(message: str):
    """Send an async admin notification via Telegram."""
    if not settings.telegram_enabled or not settings.telegram_token or not settings.telegram_chat_ids:
        return
        
    url = f"https://api.telegram.org/bot{settings.telegram_token}/sendMessage"
    
    async with httpx.AsyncClient(timeout=5.0) as client:
        for chat_id in settings.telegram_chat_ids:
            try:
                response = await client.post(url, json={
                    "chat_id": chat_id,
                    "text": message,
                    "parse_mode": "HTML"
                })
                print(f"Telegram API response: {response.text}")
            except Exception as e:
                print(f"⚠️ Failed to send Telegram notification to {chat_id}: {e}")

@app.on_event("startup")
async def startup_event():
    """Run tasks on application startup."""
    
    # Notify startup
    startup_msg = "🟢 <b>Klaus Server Started</b>\nWeb UI is online and systems are initializing."
    
    if settings.ngrok_enabled:
        print("🚀 Auto-starting Ngrok tunnel...")
        try:
            url = await restore_ngrok_tunnel()
            print(f"✅ Ngrok tunnel restored: {url}")
            if url:
                startup_msg += f"\n\n🌐 <b>Remote Access Active</b>\nURL: {url}"
        except Exception as e:
            print(f"❌ Failed to restore Ngrok tunnel: {e}")
            startup_msg += f"\n\n⚠️ <b>Remote Access Failed</b>\nCould not restore Ngrok tunnel: {e}"
            
    # Send all notifications asynchronously without blocking startup
    import asyncio
    asyncio.create_task(send_telegram_notification(startup_msg))

# ============================================================================
# SETTINGS & SESSION MODELS
# ============================================================================

class Settings(BaseModel):
    """User settings for the Web UI."""
    provider: str = "kimi"  # kimi, openrouter, anthropic, openai
    model: str = "kimi-k2-0711"
    temperature: float = 0.7
    max_tokens: int = 200000  # Default: 200k, 0 = unlimited (model max)
    mode: str = "balanced"  # fast, balanced, deep
    auto_save: bool = True
    auto_save_interval: int = 10  # messages
    context_token_limit: int = 0  # 0 = unlimited, or set to 100000-1000000
    ngrok_enabled: bool = False
    ngrok_authtoken: str = ""
    ngrok_domain: str = ""
    ngrok_oauth_provider: str = ""  # google, github, etc.
    ngrok_oauth_allow_emails: str = ""  # comma-separated list
    telegram_enabled: bool = False
    telegram_token: str = ""
    telegram_chat_ids: List[str] = []

class Session(BaseModel):
    """Chat session model."""
    id: str
    name: str
    created_at: str
    updated_at: str
    message_count: int = 0
    messages: List[dict] = []
    template: str = "default"  # Template/SOUL used for this session
    # context_limit REMOVED - no message limit, only token limit

# Provider configurations
PROVIDER_MODELS = {
    "kimi": ["kimi-k2-0711", "kimi-latest"],
    "openrouter": ["anthropic/claude-3.5-sonnet", "openai/gpt-4o", "meta-llama/llama-3.1-70b"],
    "anthropic": ["claude-3-5-sonnet-20241022", "claude-3-opus-20240229"],
    "openai": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"],
    "google": ["gemini-pro", "gemini-pro-vision"],
    "custom": []  # Custom provider - models are free text
}

# Mode presets - max_tokens as % of model context
# Kimi: 267k context -> Fast 50k, Balanced 100k, Deep 250k
# Claude: 200k context -> Fast 30k, Balanced 60k, Deep 190k  
# GPT-4: 128k context -> Fast 20k, Balanced 40k, Deep 120k
MODE_PRESETS = {
    "fast": {"temperature": 0.3, "max_tokens_percent": 0.20},    # 20% of context
    "balanced": {"temperature": 0.7, "max_tokens_percent": 0.40}, # 40% of context  
    "deep": {"temperature": 0.9, "max_tokens_percent": 0.95}     # 95% of context
}

# Model context limits
MODEL_CONTEXT_LIMITS = {
    # Kimi (Moonshot)
    "kimi-k2-0711": 267000,
    "kimi-latest": 267000,
    # Anthropic (Claude)
    "claude-3-5-sonnet-20241022": 200000,
    "claude-3-opus-20240229": 200000,
    # OpenAI
    "gpt-4o": 128000,
    "gpt-4o-mini": 128000,
    "gpt-4-turbo": 128000,
    # OpenRouter defaults
    "anthropic/claude-3.5-sonnet": 200000,
    "openai/gpt-4o": 128000,
    "meta-llama/llama-3.1-70b": 128000
}

def get_max_tokens_for_model(model: str, mode: str = "balanced") -> int:
    """Calculate max_tokens based on model context and mode."""
    context_limit = MODEL_CONTEXT_LIMITS.get(model, 128000)  # Default 128k
    percent = MODE_PRESETS[mode]["max_tokens_percent"]
    return int(context_limit * percent)

# Context limit options - REMOVED, using token-based only
# Token limits: 0 = unlimited (model max), 100000 = 100k, 1000000 = 1M
CONTEXT_TOKEN_LIMITS = [0, 100000, 200000, 500000, 1000000]

def get_available_templates():
    """Get list of available agent templates."""
    templates_dir = Path("/app/templates")
    if not templates_dir.exists():
        templates_dir = Path("./templates")
    
    templates = []
    if templates_dir.exists():
        for template_dir in templates_dir.iterdir():
            if template_dir.is_dir():
                soul_file = template_dir / "SOUL.md"
                if soul_file.exists():
                    # Read first line to get template name
                    try:
                        content = soul_file.read_text()
                        # Extract agent name from SOUL.md
                        name_match = re.search(r'^# SOUL - (.+)$', content, re.MULTILINE)
                        name = name_match.group(1) if name_match else template_dir.name
                        
                        # Extract role/description
                        role_match = re.search(r'\*\*Role:\*\* (.+)$', content, re.MULTILINE)
                        role = role_match.group(1) if role_match else "General purpose agent"
                        
                        templates.append({
                            "id": template_dir.name,
                            "name": name.replace("{{agent_name}}", template_dir.name.title()),
                            "role": role,
                            "path": str(soul_file)
                        })
                    except Exception as e:
                        print(f"Warning: Could not read template {template_dir.name}: {e}")
    
    return sorted(templates, key=lambda x: x["id"])

# Config
KIMI_AGENT_URL = os.getenv("KIMI_AGENT_URL", "http://kimi-agent:8080")
WEB_UI_PORT = int(os.getenv("WEB_UI_PORT", "8082"))

def load_config():
    """Load agent info from init.yaml."""
    init_paths = [
        Path("/app/workspace/init.yaml"),
        Path("./workspace/init.yaml"),
        Path("../init.yaml"),
        Path("./init.yaml"),
    ]
    
    for path in init_paths:
        if path.exists():
            try:
                with open(path) as f:
                    return yaml.safe_load(f)
            except Exception:
                pass
    
    return {
        "agent": {"name": "Assistant", "template": "general"},
        "mode": {"telegram": {"enabled": False}, "web": {"enabled": True}}
    }

def get_container_status():
    """Get Docker container status."""
    import subprocess
    try:
        result = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}}|{{.Status}}"],
            capture_output=True, text=True, timeout=5
        )
        containers = {}
        for line in result.stdout.strip().split("\n"):
            if "|" in line:
                name, status = line.split("|", 1)
                containers[name] = status
        return containers
    except:
        return {}

@app.get("/", response_class=HTMLResponse)
async def get_chat_page():
    """Serve the modern chat interface."""
    config = load_config()
    agent_name = config.get("agent", {}).get("name", "Assistant")
    agent_template = config.get("agent", {}).get("template", "general")
    user_name = config.get("user", {}).get("name", "User")
    telegram_enabled = config.get("mode", {}).get("telegram", {}).get("enabled", False)
    
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
    <meta name="theme-color" content="#7c3aed">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <link rel="manifest" href="/manifest.json">
    <link rel="apple-touch-icon" href="https://cdn-icons-png.flaticon.com/512/2103/2103633.png">
    <title>{agent_name}</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Outfit:wght@400;500;600&display=swap" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/github.min.css">
    <style>
        * {{ font-family: 'Inter', sans-serif; }}
        h1, h2, h3, .btn, .font-heading {{ font-family: 'Outfit', sans-serif; }}
        
        /* Shadcn-inspired color palette */
        :root {{
            --background: 0 0% 100%;
            --foreground: 240 10% 3.9%;
            --card: 0 0% 100%;
            --card-foreground: 240 10% 3.9%;
            --popover: 0 0% 100%;
            --popover-foreground: 240 10% 3.9%;
            --primary: 240 5.9% 10%;
            --primary-foreground: 0 0% 98%;
            --secondary: 240 4.8% 95.9%;
            --secondary-foreground: 240 5.9% 10%;
            --muted: 240 4.8% 95.9%;
            --muted-foreground: 240 3.8% 46.1%;
            --accent: 240 4.8% 95.9%;
            --accent-foreground: 240 5.9% 10%;
            --destructive: 0 84.2% 60.2%;
            --destructive-foreground: 0 0% 98%;
            --border: 240 5.9% 90%;
            --input: 240 5.9% 90%;
            --ring: 240 5.9% 10%;
            --radius: 0.5rem;
        }}
        
        body {{
            background-color: hsl(var(--background));
            color: hsl(var(--foreground));
        }}
        
        .chat-bubble-user {{
            background: hsl(var(--primary));
            color: hsl(var(--primary-foreground));
            border-radius: 1rem 1rem 0.25rem 1rem;
        }}
        
        .chat-bubble-assistant {{
            background: hsl(var(--secondary));
            color: hsl(var(--secondary-foreground));
            border-radius: 1rem 1rem 1rem 0.25rem;
        }}
        
        .status-badge {{
            display: inline-flex;
            align-items: center;
            gap: 0.375rem;
            padding: 0.25rem 0.75rem;
            border-radius: 9999px;
            font-size: 0.75rem;
            font-weight: 500;
        }}
        
        .status-badge.online {{
            background: #dcfce7;
            color: #166534;
        }}
        
        .status-badge.offline {{
            background: #fee2e2;
            color: #991b1b;
        }}
        
        .status-badge.warning {{
            background: #fef3c7;
            color: #92400e;
        }}
        
        .sidebar-card {{
            background: hsl(var(--card));
            border: 1px solid hsl(var(--border));
            border-radius: var(--radius);
            padding: 1rem;
        }}
        
        .btn {{
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 0.5rem;
            padding: 0.5rem 1rem;
            border-radius: var(--radius);
            font-size: 0.875rem;
            font-weight: 500;
            transition: all 0.2s;
            cursor: pointer;
            border: none;
        }}
        
        .btn-primary {{
            background: hsl(var(--primary));
            color: hsl(var(--primary-foreground));
        }}
        
        .btn-primary:hover {{
            opacity: 0.9;
        }}
        
        .btn-secondary {{
            background: hsl(var(--secondary));
            color: hsl(var(--secondary-foreground));
        }}
        
        .btn-secondary:hover {{
            background: hsl(var(--muted));
        }}
        
        .btn-destructive {{
            background: hsl(var(--destructive));
            color: hsl(var(--destructive-foreground));
        }}
        
        .btn-destructive:hover {{
            opacity: 0.9;
        }}
        
        .input-field {{
            width: 100%;
            padding: 0.625rem 0.875rem;
            border: 1px solid hsl(var(--border));
            border-radius: var(--radius);
            background: hsl(var(--background));
            color: hsl(var(--foreground));
            font-size: 0.875rem;
            transition: all 0.2s;
        }}
        
        /* Toast animations */
        @keyframes fadeIn {{
            from {{ opacity: 0; transform: translateY(-10px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}
        
        @keyframes fadeOut {{
            from {{ opacity: 1; transform: translateY(0); }}
            to {{ opacity: 0; transform: translateY(-10px); }}
        }}
        
        .input-field:focus {{
            outline: none;
            border-color: hsl(var(--ring));
            box-shadow: 0 0 0 2px hsl(var(--ring) / 0.1);
        }}
        
        .typing-indicator span {{
            display: inline-block;
            width: 6px;
            height: 6px;
            background: hsl(var(--muted-foreground));
            border-radius: 50%;
            margin: 0 2px;
            animation: typing 1.4s infinite;
        }}
        
        .typing-indicator span:nth-child(2) {{ animation-delay: 0.2s; }}
        .typing-indicator span:nth-child(3) {{ animation-delay: 0.4s; }}
        
        @keyframes typing {{
            0%, 60%, 100% {{ transform: translateY(0); }}
            30% {{ transform: translateY(-4px); }}
        }}
        
        .scrollbar-hide::-webkit-scrollbar {{
            width: 8px;
            height: 8px;
        }}
        
        .scrollbar-hide::-webkit-scrollbar-track {{
            background: transparent;
        }}
        
        .scrollbar-hide::-webkit-scrollbar-thumb {{
            background: #d1d5db;
            border-radius: 4px;
        }}
        
        .scrollbar-hide::-webkit-scrollbar-thumb:hover {{
            background: #9ca3af;
        }}
        
        .scrollbar-hide {{
            scrollbar-width: thin;
            scrollbar-color: #d1d5db transparent;
        }}
        
        .divider {{
            height: 1px;
            background: hsl(var(--border));
            margin: 1rem 0;
        }}
        
        /* Markdown Styles */
        .markdown-content h1 {{
            font-size: 1.5rem;
            font-weight: 600;
            margin: 1rem 0 0.5rem;
        }}
        
        .markdown-content h2 {{
            font-size: 1.25rem;
            font-weight: 600;
            margin: 0.875rem 0 0.5rem;
        }}
        
        .markdown-content h3 {{
            font-size: 1.125rem;
            font-weight: 600;
            margin: 0.75rem 0 0.5rem;
        }}
        
        .markdown-content p {{
            margin-bottom: 0.75rem;
            line-height: 1.6;
        }}
        
        .markdown-content ul, .markdown-content ol {{
            margin: 0.5rem 0;
            padding-left: 1.5rem;
        }}
        
        .markdown-content li {{
            margin: 0.25rem 0;
        }}
        
        .markdown-content code {{
            background: rgba(0,0,0,0.05);
            padding: 0.125rem 0.375rem;
            border-radius: 0.25rem;
            font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
            font-size: 0.875em;
        }}
        
        .markdown-content pre {{
            background: #f6f8fa;
            padding: 1rem;
            border-radius: 0.5rem;
            overflow-x: auto;
            margin: 0.75rem 0;
            border: 1px solid #e1e4e8;
        }}
        
        .markdown-content pre code {{
            background: none;
            padding: 0;
            border-radius: 0;
        }}
        
        .markdown-content blockquote {{
            border-left: 4px solid #e1e4e8;
            padding-left: 1rem;
            margin: 0.75rem 0;
            color: #6a737d;
        }}
        
        .markdown-content table {{
            width: 100%;
            border-collapse: collapse;
            margin: 0.75rem 0;
        }}
        
        .markdown-content th, .markdown-content td {{
            border: 1px solid #e1e4e8;
            padding: 0.5rem;
            text-align: left;
        }}
        
        .markdown-content th {{
            background: #f6f8fa;
            font-weight: 600;
        }}

        /* Responsive Styles */
        @media (max-width: 768px) {{
            #left-sidebar, #right-sidebar {{
                position: fixed;
                top: 0;
                bottom: 0;
                z-index: 100;
                width: 85% !important;
                max-width: 320px;
                height: 100vh;
                transform: translateX(-100%);
                opacity: 1 !important;
                display: flex !important;
            }}
            #right-sidebar {{
                right: 0;
                transform: translateX(100%);
                border-left: 1px solid hsl(var(--border));
                border-right: none;
            }}
            #left-sidebar.active {{
                transform: translateX(0);
                padding-top: calc(env(safe-area-inset-top, 44px) + 1rem);
            }}
            #right-sidebar.active {{
                transform: translateX(0);
                padding-top: calc(env(safe-area-inset-top, 44px) + 1rem);
            }}
            .sidebar-overlay {{
                display: none;
                position: fixed;
                inset: 0;
                background: rgba(0,0,0,0.4);
                backdrop-filter: blur(2px);
                z-index: 90;
            }}
            .sidebar-overlay.active {{
                display: block;
            }}
            #tab-content-chat {{
                padding-bottom: env(safe-area-inset-bottom);
            }}
            header {{
                padding-top: calc(env(safe-area-inset-top, 44px) + 1rem) !important;
                padding-left: 1rem;
                padding-right: 1rem;
                min-height: calc(env(safe-area-inset-top, 44px) + 4rem);
                background-color: white;
                z-index: 50;
            }}
            .chat-bubble-assistant, .chat-bubble-user {{
                max-width: 92% !important;
            }}
        }}
    </style>
</head>
<body class="h-screen overflow-hidden bg-gray-50 flex flex-col">
    <!-- Sidebar Overlay for Mobile -->
    <div id="sidebar-overlay" class="sidebar-overlay" onclick="closeAllSidebars()"></div>

    <div class="flex h-full flex-1 min-h-0">
        <!-- Sessions Sidebar (Left) -->
        <div id="left-sidebar" class="w-64 bg-white border-r border-gray-200 flex flex-col transition-all duration-300">
            <div class="p-4 border-b border-gray-200 flex items-center justify-between">
                <h2 class="font-semibold text-gray-900 flex items-center gap-2">
                    <i class="fas fa-history text-gray-400"></i>
                    Sessions
                </h2>
                <button onclick="toggleSidebar('left')" class="text-gray-400 hover:text-gray-600" title="Collapse sidebar">
                    <i class="fas fa-chevron-left"></i>
                </button>
            </div>
            
            <div class="p-3 border-b border-gray-200">
                <button onclick="createNewSession()" class="btn btn-primary w-full text-sm">
                    <i class="fas fa-plus"></i>
                    New Session
                </button>
            </div>
            
            <div id="sessions-list" class="flex-1 overflow-y-auto p-3 space-y-2">
                <!-- Sessions will be loaded here -->
                <div class="text-sm text-gray-500 text-center py-4">Loading sessions...</div>
            </div>
            
            <div class="p-3 border-t border-gray-200 bg-gray-50">
                <div class="text-xs text-gray-500">
                    <span id="current-session-name">Current Session</span>
                </div>
                <div class="text-xs text-gray-400 mt-1">
                    <span id="session-message-count">0</span> messages
                </div>
                <div class="text-xs text-gray-400 mt-1 flex items-center gap-2">
                    <span id="current-session-template" class="px-1.5 py-0.5 bg-gray-200 rounded text-gray-600 hidden"></span>
                    <span id="current-session-context" class="px-1.5 py-0.5 bg-blue-100 rounded text-blue-600 hidden"></span>
                </div>
            </div>
            
            <!-- Context Analyzer Section -->
            <div class="border-t border-gray-200">
                <div class="p-3 bg-gray-50 border-b border-gray-200">
                    <div class="flex items-center justify-between">
                        <h3 class="text-xs font-semibold text-gray-600 flex items-center gap-2 cursor-pointer" onclick="toggleContextAnalyzerPanel()">
                            <i class="fas fa-microscope text-indigo-500"></i>
                            Context Analyzer
                            <i id="context-analyzer-toggle-icon" class="fas fa-chevron-down text-xs ml-auto"></i>
                        </h3>
                        <button onclick="analyzeContext()" class="text-xs text-indigo-600 hover:text-indigo-800" title="Analyze context">
                            <i class="fas fa-play"></i>
                        </button>
                    </div>
                </div>
                
                <div id="context-analyzer-panel" class="hidden">
                    <div class="p-3 space-y-2">
                        <div id="context-analyzer-status" class="text-xs text-gray-500">
                            Click play to analyze context
                        </div>
                        <div id="context-analyzer-stats" class="hidden space-y-2">
                            <!-- Tokens Progress Bar -->
                            <div>
                                <div class="flex justify-between text-xs mb-1">
                                    <span class="text-gray-500">Tokens:</span>
                                    <span id="ca-tokens-text" class="font-medium">-</span>
                                </div>
                                <div class="w-full bg-gray-200 rounded-full h-2">
                                    <div id="ca-tokens-bar" class="bg-indigo-500 h-2 rounded-full transition-all" style="width: 0%"></div>
                                </div>
                            </div>
                            
                            <div class="flex justify-between text-xs">
                                <span class="text-gray-500">Messages:</span>
                                <span id="ca-messages" class="font-medium">-</span>
                            </div>
                            <div class="flex justify-between text-xs">
                                <span class="text-gray-500">Status:</span>
                                <span id="ca-status" class="font-medium">-</span>
                            </div>
                            <div class="mt-2 p-2 bg-indigo-50 rounded text-xs">
                                <p class="font-medium text-indigo-700 mb-1">Top Important:</p>
                                <div id="ca-top-important" class="space-y-1"></div>
                            </div>
                        </div>
                        <div class="flex gap-2">
                            <button onclick="openFullContextAnalyzer()" id="btn-expand-analyzer" class="btn btn-secondary flex-1 text-xs py-1.5 hidden">
                                <i class="fas fa-expand mr-1"></i>Full
                            </button>
                            <button onclick="compactContextNow()" id="btn-compact-context" class="btn btn-warning flex-1 text-xs py-1.5 hidden" style="background: #f59e0b; color: white; border: none; border-radius: 0.375rem;">
                                <i class="fas fa-compress-alt mr-1"></i>Compact
                            </button>
                            <button onclick="resetContextNow()" id="btn-reset-context" class="btn btn-danger flex-1 text-xs py-1.5 hidden" style="background: #ef4444; color: white; border: none; border-radius: 0.375rem;">
                                <i class="fas fa-trash-alt mr-1"></i>Reset
                            </button>
                        </div>
                    </div>
                </div>
                
                <!-- Full Context Analyzer Modal -->
                <div id="full-analyzer-modal" class="fixed inset-0 bg-black/50 hidden items-center justify-center z-50">
                    <div class="bg-white rounded-xl shadow-2xl w-[90vw] h-[90vh] flex flex-col">
                        <div class="flex items-center justify-between p-4 border-b">
                            <h2 class="text-lg font-semibold flex items-center gap-2">
                                <i class="fas fa-microscope text-indigo-500"></i>
                                Context Analysis
                            </h2>
                            <button onclick="closeFullAnalyzer()" class="text-gray-400 hover:text-gray-600">
                                <i class="fas fa-times text-xl"></i>
                            </button>
                        </div>
                        <div class="flex-1 overflow-auto p-4">
                            <div id="full-analyzer-content" class="space-y-4">
                                <!-- Content loaded dynamically -->
                            </div>
                        </div>
                        <div class="p-4 border-t bg-gray-50 flex justify-between">
                            <div id="full-analyzer-stats" class="text-sm text-gray-600"></div>
                            <button onclick="compactSelectedMessages()" class="btn btn-primary">
                                <i class="fas fa-compress-alt mr-2"></i>Compact Selected
                            </button>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Semantic Memory Section (What We Learned) -->
            <div class="border-t border-gray-200">
                <div class="p-3 bg-gray-50 border-b border-gray-200">
                    <div class="flex items-center justify-between">
                        <h3 class="text-xs font-semibold text-gray-600 flex items-center gap-2 cursor-pointer" onclick="toggleSemanticMemoryPanel()">
                            <i class="fas fa-brain text-pink-500"></i>
                            What I Learned
                            <span id="semantic-memory-count" class="ml-1 px-1.5 py-0.5 bg-pink-100 text-pink-700 rounded-full text-[10px]">0</span>
                            <i id="semantic-memory-toggle-icon" class="fas fa-chevron-down text-xs ml-auto"></i>
                        </h3>
                        <button onclick="loadSemanticMemory()" class="text-xs text-pink-600 hover:text-pink-800" title="Refresh memories">
                            <i class="fas fa-sync-alt"></i>
                        </button>
                    </div>
                </div>
                
                <div id="semantic-memory-panel" class="hidden">
                    <div class="p-3 space-y-2">
                        <p class="text-xs text-gray-500">Things I've learned about working with you:</p>
                        <div id="semantic-memory-list" class="space-y-2 max-h-40 overflow-y-auto text-xs">
                            <div class="text-gray-400 text-center py-2">No memories yet. Let us work together!</div>
                        </div>
                        <div class="flex gap-2">
                            <button onclick="consolidateMemory()" class="btn btn-primary flex-1 text-xs py-1" title="Analyze facts and consolidate to long-term memory">
                                <i class="fas fa-compress-arrows-alt mr-1"></i>Consolidar
                            </button>
                            <button onclick="openSemanticMemoryDetails()" class="btn btn-secondary flex-1 text-xs py-1">
                                <i class="fas fa-list-ul mr-1"></i>View All
                            </button>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Semantic Memory Details Modal -->
            <div id="semantic-memory-modal" class="fixed inset-0 bg-black/50 hidden items-center justify-center z-50">
                <div class="bg-white rounded-xl shadow-2xl w-[700px] max-h-[80vh] flex flex-col">
                    <div class="flex items-center justify-between p-4 border-b">
                        <h2 class="text-lg font-semibold flex items-center gap-2">
                            <i class="fas fa-brain text-pink-500"></i>
                            What I've Learned About You
                        </h2>
                        <button onclick="closeSemanticMemoryModal()" class="text-gray-400 hover:text-gray-600">
                            <i class="fas fa-times text-xl"></i>
                        </button>
                    </div>
                    <div class="flex-1 overflow-auto p-4">
                        <div id="semantic-memory-details" class="space-y-4">
                            <!-- Content loaded dynamically -->
                        </div>
                    </div>
                    <div class="p-4 border-t bg-gray-50">
                        <div id="semantic-memory-summary" class="text-sm text-gray-600"></div>
                    </div>
                </div>
            </div>
            
        </div>
        
        <!-- Left Sidebar Toggle (visible when collapsed) -->
        <button id="left-sidebar-toggle" onclick="toggleSidebar('left')" class="hidden fixed left-0 top-1/2 transform -translate-y-1/2 z-50 bg-white border border-gray-200 rounded-r-lg p-2 shadow-lg hover:bg-gray-50" title="Expand Sessions" style="display: none;">
            <i class="fas fa-chevron-right text-gray-600"></i>
        </button>
        
        <!-- Chat Area (flex-1) -->
        <div class="flex-1 flex flex-col bg-white">
            <!-- Header -->
            <header class="px-6 py-3 border-b border-gray-200 bg-white">
                <div class="flex items-center justify-between">
                    <div class="flex items-center gap-3">
                        <div class="w-10 h-10 rounded-full bg-gradient-to-br from-violet-500 to-purple-600 flex items-center justify-center text-white font-semibold text-lg shrink-0">
                            {agent_name[0].upper()}
                        </div>
                        <div class="hidden sm:block">
                            <h1 class="font-semibold text-gray-900 leading-none mb-1">{agent_name}</h1>
                            <p class="text-[10px] text-gray-500 uppercase tracking-wider">{agent_template} agent</p>
                        </div>
                        <div class="md:hidden flex items-center gap-2">
                             <button onclick="toggleSidebarMobile('left')" class="p-2 text-gray-500 bg-gray-100 rounded-lg">
                                <i class="fas fa-history"></i>
                             </button>
                        </div>
                    </div>
                    <!-- Tabs (Mobile Optimized) -->
                    <div class="flex items-center bg-gray-100 rounded-lg p-1 scale-90 sm:scale-100">
                        <button onclick="switchTab('chat')" id="tab-chat" class="px-2 sm:px-4 py-1.5 rounded-md text-sm font-medium bg-white text-gray-900 shadow-sm transition-all">
                            <i class="fas fa-comments sm:mr-2"></i><span class="hidden sm:inline">Chat</span>
                        </button>
                        <button onclick="switchTab('graph')" id="tab-graph" class="px-2 sm:px-4 py-1.5 rounded-md text-sm font-medium text-gray-600 hover:text-gray-900 transition-all">
                            <i class="fas fa-brain sm:mr-2"></i><span class="hidden sm:inline">Memory</span>
                        </button>
                        <button onclick="switchTab('episodic')" id="tab-episodic" class="hidden px-2 sm:px-4 py-1.5 rounded-md text-sm font-medium text-gray-600 hover:text-gray-900 transition-all">
                            <i class="fas fa-history sm:mr-2"></i><span class="hidden sm:inline">Episodic</span>
                        </button>
                    </div>
                    <div class="flex items-center gap-2">
                        <div id="connection-status" class="status-badge warning hidden sm:inline-flex">
                            <i class="fas fa-circle text-xs"></i>
                            <span class="hidden lg:inline">Connecting...</span>
                        </div>
                        <button onclick="showForkModal()" class="px-3 py-1.5 ml-1 bg-violet-50 text-violet-700 hover:bg-violet-100 rounded-lg text-sm font-medium transition-colors inline-flex items-center gap-2 border border-violet-100 shadow-sm" title="Fork Context">
                            <i class="fas fa-code-branch"></i>
                            <span class="hidden lg:inline">Fork Context</span>
                        </button>
                        <button md:hidden onclick="toggleSidebarMobile('right')" class="md:hidden p-2 text-gray-500 bg-gray-100 rounded-lg">
                            <i class="fas fa-sliders"></i>
                        </button>
                    </div>
                </div>
            </header>
            
            <!-- Tab: Chat -->
            <div id="tab-content-chat" class="flex-1 flex flex-col min-h-0">
                <!-- Chat Messages -->
                <div id="chat-messages" class="flex-1 overflow-y-auto p-6 space-y-4 scrollbar-hide bg-gray-50/50 min-h-0">
                    <div class="text-center py-12">
                        <div class="w-16 h-16 mx-auto mb-4 rounded-2xl bg-gradient-to-br from-violet-500 to-purple-600 flex items-center justify-center text-white text-2xl">
                            <i class="fas fa-wand-magic-sparkles"></i>
                        </div>
                        <h2 class="text-xl font-semibold text-gray-900 mb-2">Welcome to {agent_name}</h2>
                        <p class="text-gray-500 max-w-md mx-auto">Start a conversation with your AI assistant. Your context and memory are preserved across sessions.</p>
                    </div>
                </div>
                
                <!-- Typing Indicator -->
                <div id="typing-indicator" class="hidden px-6 py-2 bg-gray-50/50">
                    <div class="chat-bubble-assistant inline-flex items-center gap-2 px-4 py-2">
                        <div class="typing-indicator">
                            <span></span><span></span><span></span>
                        </div>
                    </div>
                </div>
                
                <!-- Input Area -->
                <div class="p-4 bg-white border-t border-gray-200 shrink-0">
                <!-- File Attachment Preview -->
                <div id="file-attachment" class="hidden mb-3 p-2 bg-violet-50 border border-violet-200 rounded-lg">
                    <div class="flex items-center justify-between">
                        <div class="flex items-center gap-2 text-sm text-violet-700">
                            <i class="fas fa-file"></i>
                            <span id="file-name" class="font-medium"></span>
                            <span id="file-size" class="text-xs text-violet-500"></span>
                        </div>
                        <button onclick="clearFileAttachment()" class="text-violet-400 hover:text-violet-600">
                            <i class="fas fa-times"></i>
                        </button>
                    </div>
                    <div id="file-preview" class="mt-2 text-xs text-gray-600 max-h-20 overflow-y-auto bg-white p-2 rounded"></div>
                </div>
                
                <!-- Model Selector Bar -->
                <div class="flex items-center gap-2 mb-2">
                    <div class="relative" id="model-selector-container">
                        <button id="model-selector-btn" class="flex items-center gap-2 px-3 py-1.5 bg-white border border-gray-200 rounded-full text-xs text-gray-700 hover:border-violet-300 hover:shadow-sm transition-all group">
                            <span id="model-icon" class="w-2 h-2 rounded-full bg-violet-500"></span>
                            <span id="model-label">Loading...</span>
                            <i class="fas fa-chevron-down text-gray-400 group-hover:text-violet-500 transition-colors"></i>
                        </button>
                        
                        <!-- Dropdown Menu -->
                        <div id="model-dropdown" class="hidden absolute bottom-full left-0 mb-2 w-64 bg-white rounded-xl shadow-lg border border-gray-100 py-2 z-50">
                            <div class="px-3 py-2 text-xs font-medium text-gray-400 uppercase tracking-wider border-b border-gray-100 mb-1">
                                Select Model
                            </div>
                            <div id="model-options" class="max-h-48 overflow-y-auto">
                                <!-- Populated by JS -->
                            </div>
                        </div>
                    </div>
                    <span id="model-context-info" class="text-xs text-gray-400"></span>
                </div>
                
                <!-- Text Area Input -->
                <div class="relative">
                    <textarea 
                        id="message-input" 
                        class="w-full p-3 pr-12 bg-gray-50 border border-gray-200 rounded-xl resize-none focus:outline-none focus:ring-2 focus:ring-violet-500 focus:border-transparent text-sm overflow-y-auto"
                        placeholder="Type your message... (Enter to send, Shift+Enter for new line)"
                        style="min-height: 80px; max-height: 160px;"
                        rows="3"
                    ></textarea>
                    
                    <!-- Send Button inside textarea -->
                    <button id="send-btn" class="absolute bottom-3 right-3 w-8 h-8 bg-violet-600 hover:bg-violet-700 text-white rounded-lg flex items-center justify-center transition-colors shadow-sm">
                        <i id="send-icon" class="fas fa-paper-plane text-xs"></i>
                        <i id="stop-icon" class="fas fa-stop text-xs hidden"></i>
                    </button>
                </div>
                
                <!-- Bottom Toolbar -->
                <div class="flex items-center justify-between mt-2">
                    <div class="flex items-center gap-2">
                        <input type="file" id="file-input" class="hidden" accept=".txt,.md,.py,.js,.json,.yaml,.yml,.csv,.pdf" onchange="handleFileSelect(event)">
                        <button onclick="document.getElementById('file-input').click()" class="text-gray-400 hover:text-gray-600 text-xs flex items-center gap-1 px-2 py-1 rounded hover:bg-gray-100 transition-colors" title="Attach file">
                            <i class="fas fa-paperclip"></i>
                            <span>Attach</span>
                        </button>
                        <span class="text-xs text-gray-300">|</span>
                        <span class="text-xs text-gray-400">Max 10MB</span>
                    </div>
                    <div class="text-xs text-gray-400">
                        Enter to send · Shift+Enter new line
                    </div>
                </div>
            </div>
            </div><!-- End tab-content-chat -->
            
            <!-- Tab: Knowledge Graph -->
            <div id="tab-content-graph" class="flex-1 hidden bg-gray-50">
                <iframe id="iframe-graph" src="/cognitive-memory-graph" class="w-full h-full border-0"></iframe>
            </div>
            
            <!-- Tab: Episodic Memories -->
            <div id="tab-content-episodic" class="flex-1 hidden bg-gray-50">
                <iframe id="iframe-episodic" src="/episodic-memories" class="w-full h-full border-0"></iframe>
            </div>
        </div>
        
        <!-- Config Panel (Right) -->
        <div id="right-sidebar" class="w-96 bg-white border-l border-gray-200 flex flex-col transition-all duration-300 relative">
            <div class="p-4 border-b border-gray-200 flex items-center justify-between">
                <h2 class="font-semibold text-gray-900 flex items-center gap-2">
                    <i class="fas fa-sliders"></i>
                    Settings
                </h2>
                <button onclick="toggleSidebar('right')" class="text-gray-400 hover:text-gray-600" title="Collapse sidebar">
                    <i class="fas fa-chevron-right"></i>
                </button>
            </div>
            
            <div class="flex-1 overflow-y-auto p-4 space-y-4">
                <!-- System Status -->
                <div class="sidebar-card">
                    <h3 class="text-sm font-medium text-gray-900 mb-3 flex items-center gap-2">
                        <i class="fas fa-server text-gray-400"></i>
                        System Status
                    </h3>
                    <div class="space-y-2">
                        <div class="flex items-center justify-between text-sm">
                            <span class="text-gray-600">Kimi Agent</span>
                            <span id="status-kimi" class="status-badge offline">
                                <i class="fas fa-circle text-xs"></i>
                                Checking...
                            </span>
                        </div>
                        <div class="flex items-center justify-between text-sm">
                            <span class="text-gray-600">Web UI</span>
                            <span class="status-badge online">
                                <i class="fas fa-circle text-xs"></i>
                                Online
                            </span>
                        </div>
                        <div class="flex items-center justify-between text-sm">
                            <span class="text-gray-600">Telegram Bot</span>
                            <span id="status-telegram" class="status-badge {'online' if telegram_enabled else 'offline'}">
                                <i class="fas fa-circle text-xs"></i>
                                {'Enabled' if telegram_enabled else 'Disabled'}
                            </span>
                        </div>
                    </div>
                </div>
                
                <!-- Session Info -->
                <div class="sidebar-card">
                    <h3 class="text-sm font-medium text-gray-900 mb-3 flex items-center gap-2">
                        <i class="fas fa-clock-rotate-left text-gray-400"></i>
                        Current Session
                    </h3>
                    <div class="space-y-2">
                        <div class="text-sm">
                            <span class="text-gray-500">Messages:</span>
                            <span id="msg-count" class="font-medium text-gray-900 ml-1">0</span>
                        </div>
                        <div class="text-sm">
                            <span class="text-gray-500">Memory:</span>
                            <span id="memory-status" class="font-medium text-gray-900 ml-1">Active</span>
                        </div>
                    </div>
                </div>
                
                <!-- Actions -->
                <div class="sidebar-card">
                    <h3 class="text-sm font-medium text-gray-900 mb-3 flex items-center gap-2">
                        <i class="fas fa-bolt text-gray-400"></i>
                        Actions
                    </h3>
                    <div class="space-y-2">
                        <button onclick="saveCurrentSession()" class="btn btn-secondary w-full text-sm">
                            <i class="fas fa-save"></i>
                            Save Session
                        </button>
                    </div>
                </div>
                
                <!-- Provider Status Table -->
                <div class="sidebar-card">
                    <h3 class="text-sm font-medium text-gray-900 mb-3 flex items-center gap-2">
                        <i class="fas fa-server text-gray-400"></i>
                        Provider Status
                    </h3>
                    <div class="space-y-2 text-xs">
                        <div class="flex items-center justify-between p-2 bg-green-50 rounded border border-green-200">
                            <div class="flex items-center gap-2">
                                <i class="fas fa-circle text-green-500 text-[8px]"></i>
                                <span class="font-medium text-green-900">Kimi</span>
                            </div>
                            <span class="text-green-600 font-medium">✓ Online</span>
                        </div>
                        <div class="flex items-center justify-between p-2 bg-gray-50 rounded {'opacity-50' if not os.getenv('ANTHROPIC_API_KEY') else 'border border-green-200 bg-green-50'}">
                            <div class="flex items-center gap-2">
                                <i class="fas fa-circle {'text-green-500' if os.getenv('ANTHROPIC_API_KEY') else 'text-gray-300'} text-[8px]"></i>
                                <span class="{'font-medium text-green-900' if os.getenv('ANTHROPIC_API_KEY') else ''}">Anthropic</span>
                            </div>
                            <span class="{'text-green-600 font-medium' if os.getenv('ANTHROPIC_API_KEY') else 'text-gray-400'}">{'✓ Online' if os.getenv('ANTHROPIC_API_KEY') else 'Not set'}</span>
                        </div>
                        <div class="flex items-center justify-between p-2 bg-gray-50 rounded {'opacity-50' if not os.getenv('OPENAI_API_KEY') else 'border border-green-200 bg-green-50'}">
                            <div class="flex items-center gap-2">
                                <i class="fas fa-circle {'text-green-500' if os.getenv('OPENAI_API_KEY') else 'text-gray-300'} text-[8px]"></i>
                                <span class="{'font-medium text-green-900' if os.getenv('OPENAI_API_KEY') else ''}">OpenAI</span>
                            </div>
                            <span class="{'text-green-600 font-medium' if os.getenv('OPENAI_API_KEY') else 'text-gray-400'}">{'✓ Online' if os.getenv('OPENAI_API_KEY') else 'Not set'}</span>
                        </div>
                        <div class="flex items-center justify-between p-2 bg-gray-50 rounded {'opacity-50' if not os.getenv('GOOGLE_API_KEY') else 'border border-green-200 bg-green-50'}">
                            <div class="flex items-center gap-2">
                                <i class="fas fa-circle {'text-green-500' if os.getenv('GOOGLE_API_KEY') else 'text-gray-300'} text-[8px]"></i>
                                <span class="{'font-medium text-green-900' if os.getenv('GOOGLE_API_KEY') else ''}">Google</span>
                            </div>
                            <span class="{'text-green-600 font-medium' if os.getenv('GOOGLE_API_KEY') else 'text-gray-400'}">{'✓ Online' if os.getenv('GOOGLE_API_KEY') else 'Not set'}</span>
                        </div>
                        <div class="flex items-center justify-between p-2 bg-gray-50 rounded {'opacity-50' if not os.getenv('OPENROUTER_API_KEY') else 'border border-green-200 bg-green-50'}">
                            <div class="flex items-center gap-2">
                                <i class="fas fa-circle {'text-green-500' if os.getenv('OPENROUTER_API_KEY') else 'text-gray-300'} text-[8px]"></i>
                                <span class="{'font-medium text-green-900' if os.getenv('OPENROUTER_API_KEY') else ''}">OpenRouter</span>
                            </div>
                            <span class="{'text-green-600 font-medium' if os.getenv('OPENROUTER_API_KEY') else 'text-gray-400'}">{'✓ Online' if os.getenv('OPENROUTER_API_KEY') else 'Not set'}</span>
                        </div>
                    </div>
                    <p class="text-[10px] text-gray-400 mt-2">
                        <i class="fas fa-info-circle mr-1"></i>
                        Online providers are protected. Use "Test" to verify connections.
                    </p>
                </div>
                
                <!-- Provider Settings -->
                <div class="sidebar-card">
                    <h3 class="text-sm font-medium text-gray-900 mb-3 flex items-center gap-2">
                        <i class="fas fa-plug text-gray-400"></i>
                        Configure Provider
                    </h3>
                    <div class="space-y-3">
                        <!-- Provider Selection -->
                        <div>
                            <label class="text-xs text-gray-500 block mb-1">Provider</label>
                            <select id="settings-provider" class="w-full text-sm border border-gray-200 rounded px-2 py-1.5" onchange="updateProviderSettings()">
                                <option value="kimi" selected>Kimi ✓ (Active)</option>
                                <option value="anthropic">Anthropic {'✓' if os.getenv('ANTHROPIC_API_KEY') else '(Not set)'}</option>
                                <option value="openai">OpenAI {'✓' if os.getenv('OPENAI_API_KEY') else '(Not set)'}</option>
                                <option value="google">Google {'✓' if os.getenv('GOOGLE_API_KEY') else '(Not set)'}</option>
                                <option value="openrouter">OpenRouter {'✓' if os.getenv('OPENROUTER_API_KEY') else '(Not set)'}</option>
                                <option value="custom">Custom (Local)</option>
                            </select>
                        </div>
                        
                        <!-- API Key Input -->
                        <div>
                            <label class="text-xs text-gray-500 block mb-1">API Key</label>
                            <input type="password" id="settings-api-key" class="w-full text-sm border border-gray-200 rounded px-2 py-1.5" value="" placeholder="Enter API key...">
                            <p class="text-[10px] text-gray-400 mt-1">
                                <i class="fas fa-shield-alt mr-1"></i>
                                Each provider has its own API key. Leave empty to keep existing.
                            </p>
                        </div>
                        
                        <!-- Model Selection (Dynamic - for standard providers) -->
                        <div id="settings-model-container">
                            <label class="text-xs text-gray-500 block mb-1">Model</label>
                            <select id="settings-model" class="w-full text-sm border border-gray-200 rounded px-2 py-1.5">
                                <option value="kimi-k2-0711" selected>Kimi K2 (Default)</option>
                                <option value="kimi-k1-5">Kimi K1.5</option>
                            </select>
                        </div>
                        
                        <!-- Custom Model Name (for Custom provider only) -->
                        <div id="settings-custom-model-container" class="hidden">
                            <label class="text-xs text-gray-500 block mb-1">Model Name <span class="text-red-500">*</span></label>
                            <input type="text" id="settings-custom-model" class="w-full text-sm border border-gray-200 rounded px-2 py-1.5" placeholder="llama-3.1-70b, gpt4all-j, etc.">
                            <p class="text-[10px] text-gray-400 mt-1">Enter the exact model identifier</p>
                        </div>
                        
                        <!-- Custom URL (for Custom/OpenRouter) -->
                        <div id="settings-custom-url-container" class="hidden">
                            <label class="text-xs text-gray-500 block mb-1">Base URL <span class="text-red-500">*</span></label>
                            <input type="text" id="settings-base-url" class="w-full text-sm border border-gray-200 rounded px-2 py-1.5" placeholder="http://localhost:8080/v1">
                            <p class="text-[10px] text-gray-400 mt-1">OpenAI-compatible API endpoint</p>
                        </div>
                        
                        <div class="flex gap-2">
                            <button onclick="saveProviderSettings()" class="btn btn-primary flex-1 text-xs py-1.5">
                                <i class="fas fa-save mr-1"></i>Save
                            </button>
                            <button onclick="testProviderConnection()" class="btn btn-secondary flex-1 text-xs py-1.5">
                                <i class="fas fa-plug mr-1"></i>Test
                            </button>
                        </div>
                    </div>
                </div>
                
                <!-- Telegram Settings -->
                <div class="sidebar-card">
                    <h3 class="text-sm font-medium text-gray-900 mb-3 flex items-center gap-2">
                        <i class="fab fa-telegram text-gray-400"></i>
                        Telegram Bot
                        <span id="telegram-status-badge" class="ml-auto text-[10px] px-2 py-0.5 rounded-full bg-gray-100 text-gray-400">
                            <i class="fas fa-circle text-[6px] mr-1"></i>Offline
                        </span>
                    </h3>
                    <div class="space-y-3">
                        <!-- Bot Token -->
                        <div>
                            <label class="text-xs text-gray-500 block mb-1">Bot Token</label>
                            <input type="password" id="settings-telegram-token" class="w-full text-sm border border-gray-200 rounded px-2 py-1.5" placeholder="123456789:ABCdefGHIjklMNOpqrsTUVwxyz">
                        </div>
                        
                        <!-- Chat ID -->
                        <div>
                            <label class="text-xs text-gray-500 block mb-1">Your Telegram ID</label>
                            <input type="text" id="settings-telegram-chats" class="w-full text-sm border border-gray-200 rounded px-2 py-1.5" placeholder="123456789">
                        </div>
                        
                        <div class="flex gap-2 pt-2">
                            <button onclick="saveTelegramSettings()" class="btn btn-secondary flex-1 text-xs py-1.5">
                                <i class="fas fa-save mr-1"></i>Save
                            </button>
                            <button onclick="launchTelegramBot()" id="telegram-launch-btn" class="btn btn-primary flex-1 text-xs py-1.5 bg-blue-600 hover:bg-blue-700">
                                <i class="fas fa-play mr-1"></i>Launch
                            </button>
                        </div>
                    </div>
                </div>

                <!-- Remote Access (Ngrok) -->
                <div class="sidebar-card">
                    <h3 class="text-sm font-medium text-gray-900 mb-3 flex items-center gap-2">
                        <i class="fas fa-globe text-gray-400"></i>
                        Remote Access (Ngrok)
                        <span id="ngrok-status-badge" class="ml-auto text-[10px] px-2 py-0.5 rounded-full bg-gray-100 text-gray-400">
                            <i class="fas fa-circle text-[6px] mr-1"></i>Offline
                        </span>
                    </h3>
                    <div class="space-y-3">
                        <div>
                            <label class="text-xs text-gray-500 block mb-1">Ngrok Authtoken</label>
                            <input type="password" id="settings-ngrok-token" class="w-full text-sm border border-gray-200 rounded px-2 py-1.5" placeholder="Enter authtoken...">
                        </div>
                        <div>
                            <label class="text-xs text-gray-500 block mb-1">OAuth Provider</label>
                            <select id="settings-ngrok-oauth" class="w-full text-sm border border-gray-200 rounded px-2 py-1.5">
                                <option value="">None (Public)</option>
                                <option value="google">Google</option>
                                <option value="github">GitHub</option>
                                <option value="microsoft">Microsoft</option>
                            </select>
                        </div>
                        <div>
                            <label class="text-xs text-gray-500 block mb-1">Allowed Emails (CSV)</label>
                            <input type="text" id="settings-ngrok-emails" class="w-full text-sm border border-gray-200 rounded px-2 py-1.5" placeholder="me@gmail.com, you@gmail.com">
                        </div>
                        <div id="ngrok-url-container" class="hidden">
                            <label class="text-xs text-gray-500 block mb-1">Public URL</label>
                            <div class="flex gap-2">
                                <input type="text" id="ngrok-public-url" readonly class="flex-1 text-xs bg-gray-50 border border-gray-200 rounded px-2 py-1.5 font-mono" value="">
                                <button onclick="copyNgrokUrl()" class="p-1.5 text-gray-400 hover:text-blue-600 border border-gray-200 rounded">
                                    <i class="fas fa-copy"></i>
                                </button>
                            </div>
                        </div>
                        <div class="flex gap-2 pt-2">
                            <button onclick="toggleNgrok()" id="ngrok-toggle-btn" class="btn btn-primary flex-1 text-xs py-1.5">
                                Start Tunnel
                            </button>
                        </div>
                    </div>
                </div>
                
            </div>
            
            <!-- Footer -->
            <div class="p-3 border-t border-gray-200 bg-gray-50">
                <p class="text-xs text-gray-500 text-center">
                    Klaus v2.1
                </p>
            </div>
        </div>
        
        <!-- Right Sidebar Toggle (visible when collapsed) -->
        <button id="right-sidebar-toggle" onclick="toggleSidebar('right')" class="fixed right-0 top-1/2 transform -translate-y-1/2 z-50 bg-white border border-gray-200 rounded-l-lg p-2 shadow-lg hover:bg-gray-50" title="Expand Settings" style="display: none;">
            <i class="fas fa-chevron-left text-gray-600"></i>
        </button>
    </div>
    
    <script>
        const AGENT_NAME = "{agent_name}";
        const USER_NAME = "{user_name}";
        const chatMessages = document.getElementById('chat-messages');
        const messageInput = document.getElementById('message-input');
        const sendBtn = document.getElementById('send-btn');
        const typingIndicator = document.getElementById('typing-indicator');
        const connectionStatus = document.getElementById('connection-status');
        const msgCount = document.getElementById('msg-count');
        
        let messageCount = 0;
        
        // Check connection on load
        checkHealth();
        
        // Abort controller for stopping requests
        let currentRequestController = null;
        let isSending = false;
        
        messageInput.addEventListener('keydown', (e) => {{
            // Enter sends message
            if (e.key === 'Enter' && !e.shiftKey && !e.metaKey && !e.ctrlKey) {{
                e.preventDefault();
                sendMessage();
            }}
            // Shift+Enter adds new line (default behavior - no preventDefault)
            // Cmd/Ctrl+Enter also sends
            else if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {{
                e.preventDefault();
                sendMessage();
            }}
        }});
        
        // Auto-resize textarea
        messageInput.addEventListener('input', function() {{
            this.style.height = 'auto';
            const maxHeight = 160; // Match CSS max-height
            const newHeight = Math.min(this.scrollHeight, maxHeight);
            this.style.height = newHeight + 'px';
        }});
        
        sendBtn.addEventListener('click', () => {{
            if (isSending) {{
                // Stop current request
                stopMessage();
            }} else {{
                sendMessage();
            }}
        }});
        
        // Model selector dropdown toggle
        const modelSelectorBtn = document.getElementById('model-selector-btn');
        if (modelSelectorBtn) {{
            modelSelectorBtn.addEventListener('click', (e) => {{
                e.stopPropagation();
                toggleModelDropdown();
            }});
        }}
        
        function addMessage(text, sender, modelInfo = null) {{
            const div = document.createElement('div');
            div.className = 'flex ' + (sender === 'user' ? 'justify-end' : 'justify-start');
            
            const bubble = document.createElement('div');
            bubble.className = sender === 'user' ? 'chat-bubble-user' : 'chat-bubble-assistant';
            bubble.className += ' max-w-[85%] px-4 py-3';
            
            const senderLabel = document.createElement('div');
            senderLabel.className = 'font-medium text-xs opacity-70 mb-2';
            const modelBadge = modelInfo ? `<span class="ml-2 px-1.5 py-0.5 bg-white/20 rounded text-[10px]">${{modelInfo}}</span>` : '';
            senderLabel.innerHTML = (sender === 'user' ? USER_NAME : AGENT_NAME) + modelBadge;
            bubble.appendChild(senderLabel);
            
            const content = document.createElement('div');
            content.className = 'markdown-content text-sm';
            
            if (sender === 'user') {{
                // Plain text for user
                content.innerHTML = escapeHtml(text).replace(/\\n/g, '<br>');
            }} else {{
                // Markdown for assistant
                // Intercept the file write placeholder and style it nicely
                const formattedText = text.replace(
                    /\*\[Arquivo gravado\]\*/g,
                    '<div class="my-2 inline-flex items-center gap-2 px-3 py-1.5 bg-emerald-50 text-emerald-700 rounded-lg border border-emerald-100 text-xs font-medium"><i class="fas fa-file-check"></i> Arquivo Salvo</div>'
                );
                content.innerHTML = marked.parse(formattedText);
            }}
            
            bubble.appendChild(content);
            div.appendChild(bubble);
            chatMessages.appendChild(div);
            
            // Only auto-scroll if user is near bottom (within 100px)
            const isNearBottom = chatMessages.scrollHeight - chatMessages.scrollTop - chatMessages.clientHeight < 100;
            if (isNearBottom) {{
                chatMessages.scrollTop = chatMessages.scrollHeight;
            }}
            
            // Apply syntax highlighting
            if (sender === 'assistant') {{
                content.querySelectorAll('pre code').forEach((block) => {{
                    hljs.highlightElement(block);
                }});
            }}
            
            messageCount++;
            msgCount.textContent = messageCount;
        }}
        
        // Toast notification system
        function showToast(message, type = 'info') {{
            // Remove existing toast
            const existing = document.getElementById('toast-notification');
            if (existing) existing.remove();
            
            const colors = {{
                'success': 'bg-green-500',
                'error': 'bg-red-500',
                'warning': 'bg-yellow-500',
                'info': 'bg-blue-500'
            }};
            
            const icons = {{
                'success': 'fa-check-circle',
                'error': 'fa-exclamation-circle',
                'warning': 'fa-exclamation-triangle',
                'info': 'fa-info-circle'
            }};
            
            const toast = document.createElement('div');
            toast.id = 'toast-notification';
            toast.className = `fixed top-4 right-4 ${{colors[type]}} text-white px-4 py-3 rounded-lg shadow-lg z-50 flex items-center gap-2 text-sm animate-fade-in`;
            toast.style.animation = 'fadeIn 0.3s ease-out';
            toast.innerHTML = `
                <i class="fas ${{icons[type]}}"></i>
                <span>${{message}}</span>
            `;
            
            document.body.appendChild(toast);
            
            // Auto remove after 3 seconds
            setTimeout(() => {{
                toast.style.animation = 'fadeOut 0.3s ease-out';
                setTimeout(() => toast.remove(), 300);
            }}, 3000);
        }}
        
        // Button feedback utilities
        function setButtonLoading(btn, text = 'Loading...') {{
            btn.dataset.originalHtml = btn.innerHTML;
            btn.dataset.originalClass = btn.className;
            btn.innerHTML = `<i class="fas fa-circle-notch fa-spin mr-1"></i>${{text}}`;
            btn.disabled = true;
            btn.classList.add('opacity-75', 'cursor-not-allowed');
        }}
        
        function setButtonSuccess(btn, text = 'Saved!') {{
            btn.innerHTML = `<i class="fas fa-check mr-1"></i>${{text}}`;
            btn.classList.remove('btn-primary', 'btn-secondary', 'bg-violet-600', 'bg-blue-600');
            btn.classList.add('bg-green-500', 'text-white');
            
            // Flash effect
            btn.style.boxShadow = '0 0 15px rgba(34, 197, 94, 0.5)';
            setTimeout(() => {{
                btn.style.boxShadow = '';
                restoreButton(btn);
            }}, 1500);
        }}
        
        function setButtonError(btn, text = 'Failed') {{
            btn.innerHTML = `<i class="fas fa-exclamation-circle mr-1"></i>${{text}}`;
            btn.classList.remove('btn-primary', 'btn-secondary', 'bg-violet-600', 'bg-blue-600');
            btn.classList.add('bg-red-500', 'text-white');
            
            setTimeout(() => restoreButton(btn), 2000);
        }}
        
        function restoreButton(btn) {{
            if (btn.dataset.originalHtml) {{
                btn.innerHTML = btn.dataset.originalHtml;
                btn.className = btn.dataset.originalClass || btn.className;
                btn.disabled = false;
                btn.classList.remove('opacity-75', 'cursor-not-allowed');
            }}
        }}
        
        function escapeHtml(text) {{
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }}
        
        // ===== SIDEBAR TOGGLE =====
        let leftSidebarCollapsed = false;
        let rightSidebarCollapsed = false;
        
        function toggleSidebar(side) {{
            const leftSidebar = document.getElementById('left-sidebar');
            const rightSidebar = document.getElementById('right-sidebar');
            const leftToggle = document.getElementById('left-sidebar-toggle');
            const rightToggle = document.getElementById('right-sidebar-toggle');
            
            if (side === 'left') {{
                leftSidebarCollapsed = !leftSidebarCollapsed;
                if (leftSidebarCollapsed) {{
                    leftSidebar.style.width = '0';
                    leftSidebar.style.minWidth = '0';
                    leftSidebar.style.overflow = 'hidden';
                    leftSidebar.style.opacity = '0';
                    if (leftToggle) leftToggle.style.display = 'flex';
                }} else {{
                    leftSidebar.style.width = '16rem'; // w-64
                    leftSidebar.style.minWidth = '16rem';
                    leftSidebar.style.overflow = '';
                    leftSidebar.style.opacity = '1';
                    if (leftToggle) leftToggle.style.display = 'none';
                }}
            }} else if (side === 'right') {{
                rightSidebarCollapsed = !rightSidebarCollapsed;
                if (rightSidebarCollapsed) {{
                    rightSidebar.style.width = '0';
                    rightSidebar.style.minWidth = '0';
                    rightSidebar.style.overflow = 'hidden';
                    rightSidebar.style.opacity = '0';
                    if (rightToggle) rightToggle.style.display = 'flex';
                }} else {{
                    rightSidebar.style.width = '24rem'; // w-96
                    rightSidebar.style.minWidth = '24rem';
                    rightSidebar.style.overflow = '';
                    rightSidebar.style.opacity = '1';
                    if (rightToggle) rightToggle.style.display = 'none';
                }}
            }}
        }}
        
        // ===== TAB SYSTEM =====
        function switchTab(tabName) {{
            // Hide all tab contents
            document.getElementById('tab-content-chat').classList.add('hidden');
            document.getElementById('tab-content-graph').classList.add('hidden');
            document.getElementById('tab-content-episodic').classList.add('hidden');
            
            // Show selected tab
            document.getElementById('tab-content-' + tabName).classList.remove('hidden');
            
            // Update tab buttons
            const tabs = ['chat', 'graph', 'episodic'];
            tabs.forEach(t => {{
                const btn = document.getElementById('tab-' + t);
                let classes = '';
                
                if (t === tabName) {{
                    classes = 'px-2 sm:px-4 py-1.5 rounded-md text-sm font-medium bg-white text-gray-900 shadow-sm transition-all';
                }} else {{
                    classes = 'px-2 sm:px-4 py-1.5 rounded-md text-sm font-medium text-gray-600 hover:text-gray-900 transition-all';
                }}
                
                if (t === 'episodic') {{
                    classes = 'hidden ' + classes;
                }}
                
                btn.className = classes;
            }});
            
            // Refresh iframes when switching to them
            if (tabName === 'graph') {{
                const iframe = document.getElementById('iframe-graph');
                if (iframe && iframe.contentWindow) iframe.contentWindow.location.reload();
            }} else if (tabName === 'episodic') {{
                const iframe = document.getElementById('iframe-episodic');
                if (iframe && iframe.contentWindow) iframe.contentWindow.location.reload();
            }}
        }}
        
        function openMemoryTab(type) {{
            switchTab(type === 'graph' ? 'graph' : 'episodic');
        }}
        
        // Configure marked options
        marked.setOptions({{
            breaks: true,
            highlight: function(code, lang) {{
                const language = hljs.getLanguage(lang) ? lang : 'plaintext';
                return hljs.highlight(code, {{ language }}).value;
            }}
        }});
        
        function toggleSidebarMobile(side) {{
            const sidebar = document.getElementById(side === 'left' ? 'left-sidebar' : 'right-sidebar');
            const overlay = document.getElementById('sidebar-overlay');
            sidebar.classList.toggle('active');
            overlay.classList.toggle('active');
        }}
        
        function closeAllSidebars() {{
            document.getElementById('left-sidebar').classList.remove('active');
            document.getElementById('right-sidebar').classList.remove('active');
            document.getElementById('sidebar-overlay').classList.remove('active');
        }}

        // Service Worker Registration for PWA
        if ('serviceWorker' in navigator) {{
            window.addEventListener('load', () => {{
                navigator.serviceWorker.register('/sw.js')
                    .then(reg => console.log('SW Registered!', reg))
                    .catch(err => console.log('SW Fail:', err));
            }});
        }}
        // File attachment state (declared before functions that use it)
        let currentAttachment = null;
        
        function setSendButtonState(sending) {{
            isSending = sending;
            const sendIcon = document.getElementById('send-icon');
            const stopIcon = document.getElementById('stop-icon');
            
            if (sending) {{
                sendBtn.classList.remove('btn-primary');
                sendBtn.classList.add('btn-destructive');
                sendIcon.classList.add('hidden');
                stopIcon.classList.remove('hidden');
                messageInput.placeholder = 'Sending... (Click stop to cancel)';
            }} else {{
                sendBtn.classList.add('btn-primary');
                sendBtn.classList.remove('btn-destructive');
                sendIcon.classList.remove('hidden');
                stopIcon.classList.add('hidden');
                messageInput.placeholder = 'Type your message... (Cmd/Ctrl+Enter to send)';
            }}
        }}
        
        function stopMessage() {{
            if (currentRequestController) {{
                currentRequestController.abort();
                currentRequestController = null;
            }}
            typingIndicator.classList.add('hidden');
            setSendButtonState(false);
            addMessage('⏹️ Message stopped by user.', 'assistant');
        }}
        
        async function sendMessage() {{
            console.log('sendMessage called');
            const text = messageInput.value.trim();
            console.log('Text:', text);
            
            // Allow sending if there's text OR file attachment
            if (!text && !currentAttachment) return;
            
            // Create abort controller for this request
            currentRequestController = new AbortController();
            
            // Build message content
            let fullMessage = text;
            if (currentAttachment) {{
                const fileContext = String.fromCharCode(10) + String.fromCharCode(10) + 
                    '[Attached file: ' + currentAttachment.filename + ']' + 
                    String.fromCharCode(10) + '```' + 
                    String.fromCharCode(10) + 
                    currentAttachment.content.substring(0, 8000) + 
                    String.fromCharCode(10) + '```';
                fullMessage = text ? text + fileContext : fileContext;
                
                // Show file in message
                const attachmentIndicator = '[📎 ' + currentAttachment.filename + ']';
                const messageWithAttachment = text ? text + String.fromCharCode(10) + String.fromCharCode(10) + attachmentIndicator : attachmentIndicator;
                addMessage(messageWithAttachment, 'user');
            }} else {{
                addMessage(text, 'user');
            }}
            
            messageInput.value = '';
            setSendButtonState(true);
            typingIndicator.classList.remove('hidden');
            
            // Clear attachment after sending
            clearFileAttachment();
            
            try {{
                // Use selected model from dropdown (or current settings as fallback)
                let provider = currentChatProvider || currentSettings?.provider || 'kimi';
                let model = currentChatModel || currentSettings?.model || 'kimi-k2-0711';
                
                const response = await fetch('/api/chat', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ 
                        message: fullMessage,
                        provider: provider,
                        model: model
                    }}),
                    signal: currentRequestController.signal
                }});
                
                typingIndicator.classList.add('hidden');
                
                const data = await response.json();
                if (data.response) {{
                    const modelInfo = data.model_used ? `${{data.provider}}/${{data.model_used}}` : null;
                    addMessage(data.response, 'assistant', modelInfo);
                    
                    // Context facts refresh disabled (section removed from UI)
                }} else if (data.error) {{
                    addMessage('Error: ' + data.error, 'assistant');
                    updateConnectionStatus('error');
                }}
            }} catch (error) {{
                typingIndicator.classList.add('hidden');
                if (error.name === 'AbortError') {{
                    // Request was cancelled - message already shown by stopMessage
                }} else {{
                    addMessage('Connection error. Please try again.', 'assistant');
                    updateConnectionStatus('error');
                }}
            }} finally {{
                setSendButtonState(false);
                currentRequestController = null;
                messageInput.focus();
            }}
        }}
        
        async function checkHealth() {{
            console.log('checkHealth called');
            try {{
                const response = await fetch('/health');
                const data = await response.json();
                
                if (data.kimi_agent_status === 'ok') {{
                    updateConnectionStatus('connected');
                    document.getElementById('status-kimi').className = 'status-badge online';
                    document.getElementById('status-kimi').innerHTML = '<i class="fas fa-circle text-xs"></i> Online';
                }} else {{
                    updateConnectionStatus('error');
                    document.getElementById('status-kimi').className = 'status-badge offline';
                    document.getElementById('status-kimi').innerHTML = '<i class="fas fa-circle text-xs"></i> Offline';
                }}
            }} catch (error) {{
                updateConnectionStatus('error');
                document.getElementById('status-kimi').className = 'status-badge offline';
                document.getElementById('status-kimi').innerHTML = '<i class="fas fa-circle text-xs"></i> Offline';
            }}
        }}
        
        function updateConnectionStatus(status) {{
            if (status === 'connected') {{
                connectionStatus.className = 'status-badge online';
                connectionStatus.innerHTML = '<i class="fas fa-circle text-xs"></i> Connected';
            }} else if (status === 'error') {{
                connectionStatus.className = 'status-badge offline';
                connectionStatus.innerHTML = '<i class="fas fa-circle text-xs"></i> Error';
            }}
        }}
        
        // Store messages for compaction
        let sessionMessages = [];
        
        async function handleFileSelect(event) {{
            const file = event.target.files[0];
            if (!file) return;
            
            // Check file size (10MB max)
            if (file.size > 10 * 1024 * 1024) {{
                alert('File too large. Max size: 10MB');
                return;
            }}
            
            // Upload file
            const formData = new FormData();
            formData.append('file', file);
            
            try {{
                const response = await fetch('/api/upload', {{
                    method: 'POST',
                    body: formData
                }});
                
                const data = await response.json();
                
                if (data.error) {{
                    alert('Upload error: ' + data.error);
                    return;
                }}
                
                // Store attachment
                currentAttachment = {{
                    filename: data.filename,
                    content: data.content,
                    preview: data.preview,
                    type: data.type
                }};
                
                // Show attachment preview
                document.getElementById('file-attachment').classList.remove('hidden');
                document.getElementById('file-name').textContent = data.filename;
                document.getElementById('file-size').textContent = `(${{Math.round(data.size / 1024)}}KB)`;
                document.getElementById('file-preview').textContent = data.preview;
                
            }} catch (error) {{
                console.error('Upload error:', error);
                alert('Failed to upload file');
            }}
        }}
        
        function clearFileAttachment() {{
            currentAttachment = null;
            document.getElementById('file-attachment').classList.add('hidden');
            document.getElementById('file-input').value = '';
        }}
        
        async function compactContext() {{
            console.log('compactContext called');
            
            if (sessionMessages.length === 0) {{
                alert('No messages to compact yet. Start a conversation first!');
                return;
            }}
            
            if (!confirm('Compact context? This will extract important information and save it to memory.')) {{
                return;
            }}
            
            try {{
                const response = await fetch('/api/compact', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }}
                }});
                
                const data = await response.json();
                
                if (data.error) {{
                    alert('Error: ' + data.error);
                }} else {{
                    // Clear local session
                    sessionMessages = [];
                    
                    // Show success message
                    const factsList = data.facts ? data.facts.map(f => "• " + f).join(String.fromCharCode(10)) : "None";
                    const msg = "Context compacted!" + String.fromCharCode(10) + String.fromCharCode(10) +
                          "Messages processed: " + data.messages_processed + String.fromCharCode(10) +
                          "Facts extracted: " + data.facts_extracted + String.fromCharCode(10) + String.fromCharCode(10) +
                          "Saved facts:";
                    alert(msg);
                    if (factsList !== "None") alert(factsList);
                    
                    // Reset the chat visually
                    resetSession();
                }}
            }} catch (error) {{
                console.error('Compact error:', error);
                alert('Failed to compact context. Check console for details.');
            }}
        }}
        
        function resetSession() {{
            if (confirm('Reset session? This will clear the conversation history.')) {{
                chatMessages.innerHTML = `
                    <div class="text-center py-12">
                        <div class="w-16 h-16 mx-auto mb-4 rounded-2xl bg-gradient-to-br from-violet-500 to-purple-600 flex items-center justify-center text-white text-2xl">
                            <i class="fas fa-wand-magic-sparkles"></i>
                        </div>
                        <h2 class="text-xl font-semibold text-gray-900 mb-2">Session Reset</h2>
                        <p class="text-gray-500">Start a new conversation.</p>
                    </div>
                `;
                messageCount = 0;
                msgCount.textContent = 0;
                sessionMessages = [];
                
                // Clear important messages widget
                const topImportantEl = document.getElementById('ca-top-important');
                if (topImportantEl) {{
                    topImportantEl.innerHTML = '<div class="text-gray-400">No messages yet</div>';
                }}
                
                // Reset context analyzer status
                const caStatus = document.getElementById('ca-status');
                const caTokens = document.getElementById('ca-tokens');
                const caProgress = document.getElementById('ca-progress');
                if (caStatus) caStatus.textContent = 'Idle';
                if (caTokens) caTokens.textContent = '0 / 200,000 (0%)';
                if (caProgress) caProgress.style.width = '0%';
            }}
        }}
        
        // ============================================================================
        // SETTINGS MANAGEMENT
        // ============================================================================
        
        let currentSettings = {{}};
        let providerModels = {{}};
        let allProviders = {{}};
        let providerAvailability = {{}};
        let modelContextLimits = {{}};
        let modePresets = {{}};
        
        async function loadSettings() {{
            try {{
                // Load settings
                const settingsRes = await fetch('/api/settings');
                currentSettings = await settingsRes.json();
                
                // Load providers
                const providersRes = await fetch('/api/settings/providers');
                const providersData = await providersRes.json();
                providerModels = providersData.models;
                allProviders = providersData.all_models;
                providerAvailability = providersData.available;
                modelContextLimits = providersData.model_context_limits || {{}};
                modePresets = providersData.mode_presets || {{}};
                
                // Populate chat model selector (async)
                await populateChatModelSelector(providersData);
                
                // Safely update UI elements
                const safeSet = (id, value) => {{
                    const el = document.getElementById(id);
                    if (el) {{
                        if (el.type === 'checkbox') el.checked = !!value;
                        else el.value = value;
                        return true;
                    }}
                    return false;
                }};
                
                const safeText = (id, text) => {{
                    const el = document.getElementById(id);
                    if (el) el.textContent = text;
                }};

                const providerSelect = document.getElementById('settings-provider');
                if (providerSelect) {{
                    // Populate provider dropdown
                    populateProviderDropdown(providersData.providers, providersData.available);
                    
                    // Show info about locked providers
                    showProviderInfo(providersData);
                    
                    // Apply settings to UI
                    providerSelect.value = currentSettings.provider;
                    updateModelOptions();
                    
                    safeSet('settings-model', currentSettings.model);
                    safeSet('settings-temperature', currentSettings.temperature);
                    safeText('temp-value', currentSettings.temperature);
                    safeSet('settings-max-tokens', currentSettings.max_tokens);
                    
                    // Update mode buttons
                    updateModeButtons(currentSettings.mode);

                    // Ngrok settings
                    safeSet('settings-ngrok-token', currentSettings.ngrok_authtoken || '');
                    safeSet('settings-ngrok-oauth', currentSettings.ngrok_oauth_provider || '');
                    safeSet('settings-ngrok-emails', currentSettings.ngrok_oauth_allow_emails || '');
                }}
                
                // Always check statuses
                updateNgrokStatusDisplay();
                checkTelegramStatus();
                
            }} catch (error) {{
                console.error('Failed to load settings:', error);
            }}
        }}
        
        async function updateNgrokStatusDisplay() {{
            try {{
                const res = await fetch('/api/remote/status');
                const status = await res.json();
                
                const badge = document.getElementById('ngrok-status-badge');
                const toggleBtn = document.getElementById('ngrok-toggle-btn');
                const urlContainer = document.getElementById('ngrok-url-container');
                const urlInput = document.getElementById('ngrok-public-url');
                
                if (!badge || !toggleBtn) return;

                if (status.enabled) {{
                    badge.innerHTML = '<i class="fas fa-circle text-[6px] mr-1"></i>Online';
                    badge.className = 'ml-auto text-[10px] px-2 py-0.5 rounded-full bg-green-100 text-green-600';
                    toggleBtn.textContent = 'Stop Tunnel';
                    toggleBtn.className = 'btn btn-secondary flex-1 text-xs py-1.5';
                    if (urlContainer) {{
                        urlContainer.classList.remove('hidden');
                        urlInput.value = status.url;
                    }}
                }} else {{
                    badge.innerHTML = '<i class="fas fa-circle text-[6px] mr-1"></i>Offline';
                    badge.className = 'ml-auto text-[10px] px-2 py-0.5 rounded-full bg-gray-100 text-gray-400';
                    toggleBtn.textContent = 'Start Tunnel';
                    toggleBtn.className = 'btn btn-primary flex-1 text-xs py-1.5';
                    if (urlContainer) urlContainer.classList.add('hidden');
                }}
            }} catch (e) {{
                console.error("Failed to check ngrok status:", e);
            }}
        }}

        async function toggleNgrok() {{
            const toggleBtn = document.getElementById('ngrok-toggle-btn');
            const authtokenField = document.getElementById('settings-ngrok-token');
            const authtoken = authtokenField ? authtokenField.value : '';
            
            if (toggleBtn.textContent.includes('Start')) {{
                if (!authtoken) {{
                    alert("Please enter an Ngrok Authtoken first.");
                    return;
                }}
                
                // Save configs first
                currentSettings.ngrok_authtoken = authtoken;
                currentSettings.ngrok_oauth_provider = document.getElementById('settings-ngrok-oauth').value;
                currentSettings.ngrok_oauth_allow_emails = document.getElementById('settings-ngrok-emails').value;
                await saveSettingsSync();
                
                toggleBtn.disabled = true;
                toggleBtn.textContent = 'Starting...';
                
                try {{
                    const res = await fetch('/api/remote/start', {{ method: 'POST' }});
                    const data = await res.json();
                    if (data.error) throw new Error(data.error);
                }} catch (e) {{
                    alert("Failed to start tunnel: " + e.message);
                }} finally {{
                    toggleBtn.disabled = false;
                    updateNgrokStatusDisplay();
                }}
            }} else {{
                toggleBtn.disabled = true;
                toggleBtn.textContent = 'Stopping...';
                
                try {{
                    const res = await fetch('/api/remote/stop', {{ method: 'POST' }});
                }} catch (e) {{
                    alert("Failed to stop tunnel: " + e.message);
                }} finally {{
                    toggleBtn.disabled = false;
                    updateNgrokStatusDisplay();
                }}
            }}
        }}

        function copyNgrokUrl() {{
            const urlInput = document.getElementById('ngrok-public-url');
            if (urlInput) {{
                urlInput.select();
                document.execCommand('copy');
                alert("URL copied to clipboard!");
            }}
        }}

        async function saveSettingsSync() {{
            try {{
                await fetch('/api/settings', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify(currentSettings)
                }});
            }} catch (e) {{
                console.error("Failed to save settings:", e);
            }}
        }}

        function populateProviderDropdown(enabledProviders, availability) {{
            const select = document.getElementById('settings-provider');
            if (!select) return;
            
            const providerNames = {{
                'kimi': 'Kimi (Moonshot)',
                'openrouter': 'OpenRouter',
                'anthropic': 'Anthropic (Claude)',
                'openai': 'OpenAI'
            }};
            
            let html = '';
            
            // Enabled providers
            enabledProviders.forEach(p => {{
                html += `<option value="${{p}}">${{providerNames[p]}} ✅</option>`;
            }});
            
            // Disabled providers (grayed out)
            Object.keys(availability).forEach(p => {{
                if (!availability[p]) {{
                    html += `<option value="${{p}}" disabled>${{providerNames[p]}} 🔒 (add API key)</option>`;
                }}
            }});
            
            select.innerHTML = html;
        }}
        
        let currentChatProvider = null;
        let currentChatModel = null;
        
        async function populateChatModelSelector(providersData) {{
            const container = document.getElementById('model-options');
            const label = document.getElementById('model-label');
            const icon = document.getElementById('model-icon');
            if (!container) return;
            
            const enabledProviders = providersData.providers || [];
            const allModels = providersData.all_models || {{}};
            const currentModel = currentSettings?.model || 'kimi-k2-0711';
            const currentProvider = currentSettings?.provider || 'kimi';
            
            // Set current chat provider/model
            currentChatProvider = currentProvider;
            currentChatModel = currentModel;
            
            let html = '';
            
            // Fetch custom provider model if needed
            let customModel = null;
            if (enabledProviders.includes('custom')) {{
                try {{
                    const customRes = await fetch('/api/settings/provider/custom');
                    const customData = await customRes.json();
                    customModel = customData.configured_model || 'custom-model';
                }} catch (e) {{
                    customModel = currentModel || 'custom-model';
                }}
            }}
            
            // Build options for each enabled provider
            enabledProviders.forEach(provider => {{
                const models = allModels[provider] || [];
                const providerLabel = provider.charAt(0).toUpperCase() + provider.slice(1);
                
                if (models.length > 0) {{
                    models.forEach(model => {{
                        const isSelected = (provider === currentProvider && model === currentModel);
                        const shortName = model.split('/').pop();
                        const providerColor = provider === 'kimi' ? 'bg-violet-500' : 
                                            provider === 'custom' ? 'bg-blue-500' : 
                                            provider === 'openai' ? 'bg-green-500' : 
                                            provider === 'anthropic' ? 'bg-orange-500' : 'bg-gray-500';
                        
                        html += `
                            <button class="w-full px-3 py-2 flex items-center gap-3 hover:bg-gray-50 transition-colors text-left ${{isSelected ? 'bg-violet-50' : ''}}" 
                                    onclick="selectModel('${{provider}}', '${{model}}', '${{shortName}}', '${{providerLabel}}')">
                                <span class="w-2 h-2 rounded-full ${{providerColor}}"></span>
                                <div class="flex-1">
                                    <div class="text-sm font-medium text-gray-700">${{shortName}}</div>
                                    <div class="text-xs text-gray-400">${{providerLabel}}</div>
                                </div>
                                ${{isSelected ? '<i class="fas fa-check text-violet-500 text-xs"></i>' : ''}}
                            </button>
                        `;
                        
                        if (isSelected) {{
                            label.textContent = shortName;
                            icon.className = `w-2 h-2 rounded-full ${{providerColor}}`;
                        }}
                    }});
                }} else if (provider === 'custom') {{
                    const modelToUse = customModel || 'custom-model';
                    const isSelected = (provider === currentProvider);
                    const shortName = modelToUse;
                    
                    html += `
                        <button class="w-full px-3 py-2 flex items-center gap-3 hover:bg-gray-50 transition-colors text-left ${{isSelected ? 'bg-violet-50' : ''}}" 
                                onclick="selectModel('custom', '${{modelToUse}}', '${{shortName}}', 'Custom')">
                            <span class="w-2 h-2 rounded-full bg-blue-500"></span>
                            <div class="flex-1">
                                <div class="text-sm font-medium text-gray-700">${{shortName}}</div>
                                <div class="text-xs text-gray-400">Custom</div>
                            </div>
                            ${{isSelected ? '<i class="fas fa-check text-violet-500 text-xs"></i>' : ''}}
                        </button>
                    `;
                    
                    if (isSelected) {{
                        label.textContent = shortName;
                        icon.className = 'w-2 h-2 rounded-full bg-blue-500';
                    }}
                }}
            }});
            
            container.innerHTML = html;
        }}
        
        function selectModel(provider, model, shortName, providerLabel) {{
            currentChatProvider = provider;
            currentChatModel = model;
            
            // Update button display
            const label = document.getElementById('model-label');
            const icon = document.getElementById('model-icon');
            if (label) label.textContent = shortName;
            
            const providerColor = provider === 'kimi' ? 'bg-violet-500' : 
                                provider === 'custom' ? 'bg-blue-500' : 
                                provider === 'openai' ? 'bg-green-500' : 
                                provider === 'anthropic' ? 'bg-orange-500' : 'bg-gray-500';
            if (icon) icon.className = `w-2 h-2 rounded-full ${{providerColor}}`;
            
            // Update context info
            updateModelContextInfo(provider, model);
            
            // Hide dropdown
            const dropdown = document.getElementById('model-dropdown');
            if (dropdown) dropdown.classList.add('hidden');
            
            // Update checkmarks in dropdown without full re-render
            const buttons = document.querySelectorAll('#model-options button');
            buttons.forEach(btn => {{
                const onclick = btn.getAttribute('onclick');
                const isSelected = onclick && onclick.includes(`'${{provider}}', '${{model}}'`);
                
                // Remove checkmark from all
                const check = btn.querySelector('.fa-check');
                if (check) check.remove();
                btn.classList.remove('bg-violet-50');
                
                // Add checkmark to selected
                if (isSelected) {{
                    btn.classList.add('bg-violet-50');
                    btn.innerHTML += '<i class="fas fa-check text-violet-500 text-xs ml-auto"></i>';
                }}
            }});
        }}
        
        function toggleModelDropdown() {{
            const dropdown = document.getElementById('model-dropdown');
            dropdown.classList.toggle('hidden');
        }}
        
        // Close dropdown when clicking outside
        document.addEventListener('click', (e) => {{
            const container = document.getElementById('model-selector-container');
            const dropdown = document.getElementById('model-dropdown');
            if (container && dropdown && !container.contains(e.target)) {{
                dropdown.classList.add('hidden');
            }}
        }});
        
        function updateModelContextInfo(provider, model) {{
            const infoEl = document.getElementById('model-context-info');
            if (!infoEl) return;
            
            const limits = {{
                'kimi-k2-0711': '267k',
                'kimi-latest': '267k',
                'claude-3-5-sonnet': '200k',
                'gpt-4o': '128k',
                'hermes3:8b': '8k'
            }};
            
            const shortName = model.split('/').pop();
            const limit = limits[model] || limits[shortName] || 'Unknown';
            infoEl.textContent = `${{shortName}} · ${{limit}} ctx`;
        }}
        
        function showProviderInfo(providersData) {{
            const enabledCount = providersData.providers.length;
            const totalCount = Object.keys(providersData.all_models).length;
            
            if (enabledCount < totalCount) {{
                const infoDiv = document.getElementById('provider-info');
                const infoText = document.getElementById('provider-info-text');
                if (infoDiv && infoText) {{
                    infoDiv.classList.remove('hidden');
                    infoText.textContent = `${{enabledCount}}/${{totalCount}} providers enabled. Add API keys to .env to enable more.`;
                }}
            }}
        }}
        
        function updateModelOptions() {{
            const providerSelect = document.getElementById('settings-provider');
            const modelSelect = document.getElementById('settings-model');
            if (!providerSelect || !modelSelect) return;
            
            const provider = providerSelect.value;
            const models = providerModels[provider] || [];
            
            if (models.length === 0) {{
                modelSelect.innerHTML = '<option value="">No models available</option>';
                return;
            }}
            
            modelSelect.innerHTML = models.map(m => `<option value="${{m}}">${{m}}</option>`).join('');
            
            // Select first model as default if current not in list
            const currentModel = currentSettings.model;
            if (models.includes(currentModel)) {{
                modelSelect.value = currentModel;
            }} else {{
                modelSelect.value = models[0];
                // Update settings with new default model
                currentSettings.model = models[0];
            }}
            
            // Update max tokens based on new model
            updateMaxTokensForCurrentModel();
        }}
        
        // Handle provider change - update models and save
        function setupProviderListener() {{
            const providerSelect = document.getElementById('settings-provider');
            if (providerSelect) {{
                providerSelect.addEventListener('change', () => {{
                    console.log('Provider changed to:', providerSelect.value);
                    updateModelOptions();
                    updateSettings();
                }});
            }}
        }}
        
        // Handle model change - update max tokens and save settings
        function setupModelListener() {{
            const modelSelect = document.getElementById('settings-model');
            if (modelSelect) {{
                modelSelect.addEventListener('change', () => {{
                    console.log('Model changed to:', modelSelect.value);
                    updateMaxTokensForCurrentModel();
                    updateSettings();
                }});
            }}
        }}
        
        function updateTempDisplay() {{
            const tempInput = document.getElementById('settings-temperature');
            const tempValue = document.getElementById('temp-value');
            if (tempInput && tempValue) {{
                tempValue.textContent = tempInput.value;
            }}
        }}
        
        async function updateSettings() {{
            const providerSelect = document.getElementById('settings-provider');
            if (!providerSelect) return;
            
            const getVal = (id, def) => {{
                const el = document.getElementById(id);
                return el ? el.value : def;
            }};
            
            const newSettings = {{
                provider: providerSelect.value,
                model: getVal('settings-model', currentSettings.model),
                temperature: parseFloat(getVal('settings-temperature', 0.7)),
                max_tokens: parseInt(getVal('settings-max-tokens', 100000)),
                mode: currentSettings.mode || 'balanced',
                auto_save: currentSettings.auto_save !== false,
                auto_save_interval: currentSettings.auto_save_interval || 10,
                ngrok_enabled: currentSettings.ngrok_enabled || false,
                ngrok_authtoken: getVal('settings-ngrok-token', currentSettings.ngrok_authtoken),
                ngrok_oauth_provider: getVal('settings-ngrok-oauth', currentSettings.ngrok_oauth_provider),
                ngrok_oauth_allow_emails: getVal('settings-ngrok-emails', currentSettings.ngrok_oauth_allow_emails)
            }};
            
            try {{
                await fetch('/api/settings', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify(newSettings)
                }});
                currentSettings = newSettings;
            }} catch (error) {{
                console.error('Failed to update settings:', error);
            }}
        }}
        
        async function setMode(mode) {{
            try {{
                // Only update if settings elements exist in sidebar
                const modelSelect = document.getElementById('settings-model');
                const tempInput = document.getElementById('settings-temperature');
                const maxTokensInput = document.getElementById('settings-max-tokens');
                
                if (modelSelect) {{
                    // Calculate max tokens for current model and new mode
                    const model = modelSelect.value;
                    const maxTokens = calculateMaxTokens(model, mode);
                    
                    const res = await fetch(`/api/settings/mode/${{mode}}`, {{ method: 'POST' }});
                    const data = await res.json();
                    if (data.settings) {{
                        currentSettings = data.settings;
                        if (tempInput) tempInput.value = currentSettings.temperature;
                        const tempValue = document.getElementById('temp-value');
                        if (tempValue) tempValue.textContent = currentSettings.temperature;
                        if (maxTokensInput) maxTokensInput.value = maxTokens;
                        updateModeButtons(mode);
                        // Update settings with new max_tokens
                        updateSettings();
                    }}
                }}
            }} catch (error) {{
                console.error('Failed to set mode:', error);
            }}
        }}
        
        function updateModeButtons(activeMode) {{
            ['fast', 'balanced', 'deep'].forEach(mode => {{
                const btn = document.getElementById(`mode-${{mode}}`);
                if (btn) {{
                    if (mode === activeMode) {{
                        btn.className = 'flex-1 btn btn-primary text-xs py-1.5';
                    }} else {{
                        btn.className = 'flex-1 btn btn-secondary text-xs py-1.5';
                    }}
                }}
            }});
        }}
        
        function calculateMaxTokens(model, mode) {{
            // Get context limit for model (default 128k)
            const contextLimit = modelContextLimits[model] || 128000;
            // Get percentage for mode (default balanced 40%)
            const percent = (modePresets[mode] && modePresets[mode].max_tokens_percent) || 0.40;
            return Math.floor(contextLimit * percent);
        }}
        
        function updateMaxTokensForCurrentModel() {{
            const modelSelect = document.getElementById('settings-model');
            const maxTokensInput = document.getElementById('settings-max-tokens');
            if (!modelSelect || !maxTokensInput) return;
            
            const model = modelSelect.value;
            const mode = currentSettings.mode || 'balanced';
            const maxTokens = calculateMaxTokens(model, mode);
            maxTokensInput.value = maxTokens;
            updateSettings();
        }}
        
        // ============================================================================
        // SESSIONS MANAGEMENT
        // ============================================================================
        
        async function loadSessions() {{
            try {{
                const res = await fetch('/api/sessions');
                const sessions = await res.json();
                renderSessions(sessions);
                
                // Auto-select first session if none selected
                if (!currentSessionId && sessions.length > 0) {{
                    console.log('Auto-selecting first session:', sessions[0].id);
                    await loadSession(sessions[0].id);
                }}
            }} catch (error) {{
                console.error('Failed to load sessions:', error);
            }}
        }}
        
        function renderSessions(sessions) {{
            const container = document.getElementById('sessions-list');
            
            if (sessions.length === 0) {{
                container.innerHTML = '<div class="text-sm text-gray-400 text-center py-4">No saved sessions</div>';
                // Clear current session if no sessions exist
                currentSessionId = '';
                updateChatHeader(null);
                return;
            }}
            
            container.innerHTML = sessions.map(s => {{
                const isCurrent = s.id === (currentSessionId || '');
                const date = new Date(s.updated_at).toLocaleDateString();
                const templateBadge = s.template && s.template !== 'default' 
                    ? `<span class="ml-1 px-1.5 py-0.5 bg-violet-100 text-violet-600 rounded text-[10px]">${{s.template}}</span>` 
                    : '';
                // context_limit removed - no message limit
                const contextBadge = '';
                return `
                    <div class="group p-2 rounded-lg border ${{isCurrent ? 'border-violet-500 bg-violet-50' : 'border-gray-200 hover:border-gray-300'}} cursor-pointer transition-colors"
                         onclick="loadSession('${{s.id}}')">
                        <div class="flex items-center justify-between">
                            <span class="text-sm font-medium text-gray-900 truncate flex-1">${{s.name}}${{templateBadge}}</span>
                            ${{isCurrent ? '<i class="fas fa-check text-violet-500 text-xs"></i>' : ''}}
                        </div>
                        <div class="flex items-center justify-between mt-1">
                            <span class="text-xs text-gray-500">${{s.message_count}} msgs · ${{date}}${{contextBadge}}</span>
                            <div class="flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                                <button onclick="event.stopPropagation(); renameSession('${{s.id}}', '${{s.name}}')" 
                                        class="text-gray-400 hover:text-blue-500">
                                    <i class="fas fa-edit text-xs"></i>
                                </button>
                                <button onclick="event.stopPropagation(); deleteSession('${{s.id}}')" 
                                        class="text-gray-400 hover:text-red-500">
                                    <i class="fas fa-trash text-xs"></i>
                                </button>
                            </div>
                        </div>
                    </div>
                `;
            }}).join('');
        }}
        
        let currentSessionId = '';
        
        async function createNewSession() {{
            // Load templates and current agent info
            let templates = [];
            let currentAgent = {{name: 'Agent', role: 'AI Assistant'}};
            let providersData = {{}};
            
            try {{
                const [templatesRes, providersRes] = await Promise.all([
                    fetch('/api/templates'),
                    fetch('/api/settings/providers')
                ]);
                const templatesJson = await templatesRes.json();
                templates = templatesJson.templates || [];
                currentAgent = templatesJson.current_agent || currentAgent;
                providersData = await providersRes.json();
            }} catch (e) {{
                console.error('Could not load data:', e);
            }}
            
            // Build template options
            const templateOptions = templates.map(t => 
                `<option value="${{t.id}}">${{t.name}} - ${{t.role}}</option>`
            ).join('');
            
            // Format current agent display
            const currentAgentDisplay = `${{currentAgent.name}} - ${{currentAgent.role}}`;
            
            // Build provider options
            const providers = providersData.providers || ['kimi'];
            const allModels = providersData.all_models || {{}};
            const providerOptions = providers.map(p => 
                `<option value="${{p}}">${{p.charAt(0).toUpperCase() + p.slice(1)}}</option>`
            ).join('');
            
            // Create modal HTML with AI Configuration
            const modalHtml = `
                <div id="new-session-modal" class="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
                    <div class="bg-white rounded-lg p-6 w-[500px] max-w-full max-h-[90vh] overflow-y-auto">
                        <h3 class="text-lg font-semibold mb-4">Create New Session</h3>
                        
                        <!-- Session Name -->
                        <div class="mb-4">
                            <label class="block text-sm text-gray-600 mb-1">Session Name</label>
                            <input type="text" id="new-session-name" placeholder="Session name (optional)" 
                                   class="w-full px-3 py-2 border border-gray-300 rounded-lg">
                        </div>
                        
                        <!-- Agent Template -->
                        <div class="mb-4">
                            <label class="block text-sm text-gray-600 mb-1">Agent Template</label>
                            <select id="new-session-template" class="w-full px-3 py-2 border border-gray-300 rounded-lg">
                                <option value="default">${{currentAgentDisplay}} (Current)</option>
                                ${{templateOptions}}
                            </select>
                        </div>
                        
                        <div class="flex gap-3 mt-6">
                            <button onclick="closeNewSessionModal()" class="flex-1 px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200">
                                Cancel
                            </button>
                            <button onclick="submitNewSession()" class="flex-1 px-4 py-2 bg-violet-600 text-white rounded-lg hover:bg-violet-700">
                                Create
                            </button>
                        </div>
                    </div>
                </div>
            `;
            
            // Show modal
            document.body.insertAdjacentHTML('beforeend', modalHtml);
            
            // Initialize model options
            updateModelOptionsForNewSession();
        }}
        
        function updateModelOptionsForNewSession() {{
            const provider = document.getElementById('new-session-provider').value;
            const modelContainer = document.getElementById('new-session-model')?.parentElement;
            
            // For custom provider, replace select with text input
            if (provider === 'custom') {{
                const modelSelect = document.getElementById('new-session-model');
                if (modelSelect && modelSelect.tagName === 'SELECT') {{
                    const modelInput = document.createElement('input');
                    modelInput.type = 'text';
                    modelInput.id = 'new-session-model';
                    modelInput.className = 'w-full px-3 py-2 border border-gray-300 rounded-lg text-sm';
                    modelInput.placeholder = 'e.g., llama3.1:8b, hermes3:8b';
                    modelSelect.parentElement.replaceChild(modelInput, modelSelect);
                }}
                return;
            }}
            
            // For standard providers, ensure we have a select element
            let modelSelect = document.getElementById('new-session-model');
            if (modelSelect && modelSelect.tagName === 'INPUT') {{
                const newSelect = document.createElement('select');
                newSelect.id = 'new-session-model';
                newSelect.className = 'w-full px-3 py-2 border border-gray-300 rounded-lg text-sm';
                modelSelect.parentElement.replaceChild(newSelect, modelSelect);
                modelSelect = newSelect;
            }}
            
            const models = {{
                'kimi': ['kimi-k2-0711', 'kimi-latest'],
                'anthropic': ['claude-3-5-sonnet-20241022', 'claude-3-opus-20240229'],
                'openai': ['gpt-4o', 'gpt-4o-mini', 'gpt-4-turbo'],
                'openrouter': ['anthropic/claude-3.5-sonnet', 'openai/gpt-4o'],
                'google': ['gemini-pro', 'gemini-pro-vision']
            }};
            
            const providerModels = models[provider] || models['kimi'];
            modelSelect.innerHTML = providerModels.map(m => `<option value="${{m}}">${{m}}</option>`).join('');
        }}
        
        let newSessionMode = 'balanced';
        function setNewSessionMode(mode) {{
            newSessionMode = mode;
            ['fast', 'balanced', 'deep'].forEach(m => {{
                const btn = document.getElementById(`new-mode-${{m}}`);
                if (m === mode) {{
                    btn.className = 'flex-1 px-3 py-2 text-xs bg-violet-600 text-white border border-violet-600 rounded-lg';
                }} else {{
                    btn.className = 'flex-1 px-3 py-2 text-xs border border-gray-300 rounded-lg hover:bg-gray-50';
                }}
            }});
            
            // Update max tokens based on mode
            const maxTokensInput = document.getElementById('new-session-max-tokens');
            const provider = document.getElementById('new-session-provider')?.value || 'kimi';
            const contextLimits = {{
                'kimi-k2-0711': 267000,
                'kimi-latest': 267000,
                'claude-3-5-sonnet-20241022': 200000,
                'gpt-4o': 128000
            }};
            const model = document.getElementById('new-session-model')?.value || 'kimi-k2-0711';
            const limit = contextLimits[model] || 128000;
            
            const percentages = {{ fast: 0.20, balanced: 0.40, deep: 0.95 }};
            maxTokensInput.value = Math.floor(limit * percentages[mode]);
        }}
        
        function closeNewSessionModal() {{
            const modal = document.getElementById('new-session-modal');
            if (modal) modal.remove();
        }}
        
        async function submitNewSession() {{
            const nameInput = document.getElementById('new-session-name');
            const templateInput = document.getElementById('new-session-template');
            
            const name = nameInput.value.trim() || undefined;
            const template = templateInput.value;
            
            closeNewSessionModal();
            
            try {{
                // Create session (uses current settings for AI config)
                const res = await fetch('/api/sessions', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ name, template }})
                }});
                const data = await res.json();
                
                if (data.session) {{
                    currentSessionId = data.session.id;
                    document.getElementById('current-session-name').textContent = data.session.name;
                    document.getElementById('session-message-count').textContent = '0';
                    
                    // Update template and context display
                    const templateEl = document.getElementById('current-session-template');
                    const contextEl = document.getElementById('current-session-context');
                    
                    if (data.session.template && data.session.template !== 'default') {{
                        templateEl.textContent = data.session.template;
                        templateEl.classList.remove('hidden');
                    }} else {{
                        templateEl.classList.add('hidden');
                    }}
                    
                    // context_limit removed - always hide
                    contextEl.classList.add('hidden');
                    
                    // Clear chat
                    chatMessages.innerHTML = `
                        <div class="text-center py-12">
                            <div class="w-16 h-16 mx-auto mb-4 rounded-2xl bg-gradient-to-br from-violet-500 to-purple-600 flex items-center justify-center text-white text-2xl">
                                <i class="fas fa-wand-magic-sparkles"></i>
                            </div>
                            <h2 class="text-xl font-semibold text-gray-900 mb-2">${{data.session.name}}</h2>
                            <p class="text-gray-500">Start a new conversation.</p>
                            ${{data.session.template && data.session.template !== 'default' ? `<p class="text-sm text-violet-600 mt-2"><i class="fas fa-user-circle mr-1"></i>Agent: ${{data.session.template}}</p>` : ''}}
                            <p class="text-xs text-gray-400 mt-1">No message limit</p>
                        </div>
                    `;
                    messageCount = 0;
                    msgCount.textContent = 0;
                    sessionMessages = [];
                    
                    loadSessions();
                }}
            }} catch (error) {{
                console.error('Failed to create session:', error);
            }}
        }}

        async function showForkModal() {{
            if (!currentSessionId) {{
                alert('Please select a session to fork first.');
                return;
            }}
            
            // Load templates
            let templates = [];
            try {{
                const res = await fetch('/api/templates');
                const data = await res.json();
                templates = data.templates || [];
            }} catch (e) {{
                console.error('Could not load templates:', e);
            }}
            
            // Build template options
            const templateOptions = templates.map(t => 
                `<option value="${{t.id}}">${{t.name}} - ${{t.role}}</option>`
            ).join('');
            
            // Create modal HTML
            const modalHtml = `
                <div id="fork-session-modal" class="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
                    <div class="bg-white rounded-lg p-6 w-[400px] max-w-full shadow-xl">
                        <div class="flex items-center gap-3 mb-2">
                            <div class="w-8 h-8 rounded-full bg-violet-100 text-violet-600 flex items-center justify-center">
                                <i class="fas fa-code-branch"></i>
                            </div>
                            <h3 class="text-lg font-semibold text-gray-900">Fork Context to Agent</h3>
                        </div>
                        <p class="text-sm text-gray-500 mb-6">Branch this session's history into a new space where the selected Agent will continue the work.</p>
                        
                        <!-- Agent Template -->
                        <div class="mb-6">
                            <label class="block text-sm font-medium text-gray-700 mb-1">Target Agent Template</label>
                            <select id="fork-session-template" class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-violet-500 focus:border-violet-500 outline-none">
                                <option value="default">Default Assistant</option>
                                ${{templateOptions}}
                            </select>
                        </div>
                        
                        <!-- Actions -->
                        <div class="flex justify-end gap-3 mt-6">
                            <button onclick="closeForkModal()" class="px-4 py-2 text-sm text-gray-600 hover:text-gray-900 font-medium">Cancel</button>
                            <button onclick="submitForkSession()" class="px-4 py-2 text-sm bg-violet-600 text-white rounded-lg hover:bg-violet-700 font-medium transition-colors shadow-sm">
                                Create Fork
                            </button>
                        </div>
                    </div>
                </div>
            `;
            
            document.body.insertAdjacentHTML('beforeend', modalHtml);
        }}
        
        function closeForkModal() {{
            const modal = document.getElementById('fork-session-modal');
            if (modal) modal.remove();
        }}
        
        async function submitForkSession() {{
            const templateInput = document.getElementById('fork-session-template');
            const template = templateInput.value;
            
            closeForkModal();
            
            try {{
                const res = await fetch('/api/sessions/' + currentSessionId + '/fork', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ template }})
                }});
                const data = await res.json();
                
                if (data.session) {{
                    currentSessionId = data.session.id;
                    document.getElementById('current-session-name').textContent = data.session.name;
                    document.getElementById('session-message-count').textContent = data.session.message_count;
                    
                    // Update template and context display
                    const templateEl = document.getElementById('current-session-template');
                    
                    if (data.session.template && data.session.template !== 'default') {{
                        templateEl.textContent = data.session.template;
                        templateEl.classList.remove('hidden');
                    }} else {{
                        templateEl.classList.add('hidden');
                    }}
                    
                    // Render messages locally
                    sessionMessages = data.session.messages || [];
                    messageCount = sessionMessages.length;
                    msgCount.textContent = messageCount;
                    
                    chatMessages.innerHTML = '';
                    sessionMessages.forEach(m => {{
                        const content = m.content || m.text;
                        const role = (m.role === 'user' || m.sender === 'user') ? 'user' : 'bot';
                        if(m.role !== 'system') {{
                            addMessage(content, role);
                        }} else {{
                            // Check if it's an internal command response that should be hidden
                            if (content.startsWith('[SYSTEM:')) {{
                                // Do not render internal file I/O context directly to user
                                return;
                            }}
                            // Otherwise, render system notification bubble natively
                            const systemDiv = document.createElement('div');
                            systemDiv.className = 'flex justify-center my-4';
                            systemDiv.innerHTML = `<div class="bg-violet-50 text-violet-700 px-4 py-2 rounded-full text-xs font-medium border border-violet-100">${{content}}</div>`;
                            chatMessages.appendChild(systemDiv);
                        }}
                    }});
                    
                    loadSessions();
                }}
            }} catch (error) {{
                console.error('Failed to fork session:', error);
                alert('Failed to fork session: ' + error.message);
            }}
        }}

        async function loadSession(sessionId) {{
            try {{
                const res = await fetch(`/api/sessions/${{sessionId}}/load`, {{ method: 'POST' }});
                const data = await res.json();
                
                if (data.session) {{
                    currentSessionId = data.session.id;
                    document.getElementById('current-session-name').textContent = data.session.name;
                    document.getElementById('session-message-count').textContent = data.session.message_count;
                    
                    // Update template and context display
                    const templateEl = document.getElementById('current-session-template');
                    const contextEl = document.getElementById('current-session-context');
                    
                    if (data.session.template && data.session.template !== 'default') {{
                        templateEl.textContent = data.session.template;
                        templateEl.classList.remove('hidden');
                    }} else {{
                        templateEl.classList.add('hidden');
                    }}
                    
                    if (data.session.context_limit) {{
                        contextEl.textContent = `${{data.session.context_limit}} ctx`;
                        contextEl.classList.remove('hidden');
                    }} else {{
                        contextEl.classList.add('hidden');
                    }}
                    
                    // Load messages
                    sessionMessages = data.messages || [];
                    messageCount = sessionMessages.length;
                    msgCount.textContent = messageCount;
                    
                    // Render messages
                    chatMessages.innerHTML = '';
                    sessionMessages.forEach(m => {{
                        const content = m.content || m.text;
                        const role = (m.role === 'user' || m.sender === 'user') ? 'user' : 'bot';
                        if(m.role !== 'system') {{
                            addMessage(content, role);
                        }} else {{
                            // Check if it's an internal command response that should be hidden
                            if (content.startsWith('[SYSTEM:')) {{
                                // Do not render internal file I/O context directly to user
                                return;
                            }}
                            // Otherwise, render system notification bubble natively
                            const systemDiv = document.createElement('div');
                            systemDiv.className = 'flex justify-center my-4';
                            systemDiv.innerHTML = `<div class="bg-violet-50 text-violet-700 px-4 py-2 rounded-full text-xs font-medium border border-violet-100">${{content}}</div>`;
                            chatMessages.appendChild(systemDiv);
                        }}
                    }});
                    
                    // Context facts loading disabled
                    
                    // Refresh semantic memory for this session
                    loadSemanticMemory();
                    
                    loadSessions();
                }}
            }} catch (error) {{
                console.error('Failed to load session:', error);
            }}
        }}
        
        async function renameSession(sessionId, currentName) {{
            const newName = prompt('New session name:', currentName);
            if (newName === null || newName.trim() === '' || newName === currentName) return;
            
            try {{
                const res = await fetch(`/api/sessions/${{sessionId}}/rename`, {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ name: newName.trim() }})
                }});
                
                if (res.ok) {{
                    // Update current session name if it's the same session
                    if (sessionId === currentSessionId) {{
                        document.getElementById('current-session-name').textContent = newName.trim();
                    }}
                    loadSessions();
                }} else {{
                    alert('Failed to rename session');
                }}
            }} catch (error) {{
                console.error('Failed to rename session:', error);
                alert('Failed to rename session');
            }}
        }}
        
        async function deleteSession(sessionId) {{
            if (!confirm('Delete this session?')) return;
            
            try {{
                await fetch(`/api/sessions/${{sessionId}}`, {{ method: 'DELETE' }});
                loadSessions();
            }} catch (error) {{
                console.error('Failed to delete session:', error);
            }}
        }}
        
        async function saveCurrentSession() {{
            try {{
                // Current session is auto-saved, but we can trigger a manual save
                const res = await fetch('/api/session/current');
                const data = await res.json();
                if (data.id) {{
                    alert('Session saved!');
                    loadSessions();
                }}
            }} catch (error) {{
                console.error('Failed to save session:', error);
            }}
        }}
        
        // ============================================================================
        // PROVIDER SETTINGS
        // ============================================================================
        
        const settingsProviderModels = {{
            kimi: [
                {{value: 'kimi-k2-0711', label: 'Kimi K2 (Default)'}},
                {{value: 'kimi-k1-5', label: 'Kimi K1.5'}},
            ],
            anthropic: [
                {{value: 'claude-3-5-sonnet-20241022', label: 'Claude 3.5 Sonnet'}},
                {{value: 'claude-3-opus-20240229', label: 'Claude 3 Opus'}},
                {{value: 'claude-3-sonnet-20240229', label: 'Claude 3 Sonnet'}},
                {{value: 'claude-3-haiku-20240307', label: 'Claude 3 Haiku'}},
            ],
            openai: [
                {{value: 'gpt-4o', label: 'GPT-4o'}},
                {{value: 'gpt-4o-mini', label: 'GPT-4o Mini'}},
                {{value: 'gpt-4-turbo', label: 'GPT-4 Turbo'}},
                {{value: 'gpt-3.5-turbo', label: 'GPT-3.5 Turbo'}},
            ],
            google: [
                {{value: 'gemini-1.5-pro', label: 'Gemini 1.5 Pro'}},
                {{value: 'gemini-1.5-flash', label: 'Gemini 1.5 Flash'}},
                {{value: 'gemini-1.0-pro', label: 'Gemini 1.0 Pro'}},
            ],
            openrouter: [
                {{value: 'anthropic/claude-3.5-sonnet', label: 'Claude 3.5 Sonnet'}},
                {{value: 'openai/gpt-4o', label: 'GPT-4o'}},
                {{value: 'google/gemini-1.5-pro', label: 'Gemini 1.5 Pro'}},
                {{value: 'meta-llama/llama-3.1-405b', label: 'Llama 3.1 405B'}},
            ],
            custom: [
                {{value: 'custom', label: 'Custom Model'}},
            ]
        }};
        
        async function updateProviderSettings() {{
            const provider = document.getElementById('settings-provider').value;
            const modelSelect = document.getElementById('settings-model');
            const customUrlContainer = document.getElementById('settings-custom-url-container');
            const modelContainer = document.getElementById('settings-model-container');
            const customModelContainer = document.getElementById('settings-custom-model-container');
            const apiKeyInput = document.getElementById('settings-api-key');
            
            // Show/hide custom URL field
            if (provider === 'custom' || provider === 'openrouter') {{
                customUrlContainer.classList.remove('hidden');
            }} else {{
                customUrlContainer.classList.add('hidden');
            }}
            
            // For custom provider: hide dropdown, show text input
            if (provider === 'custom') {{
                modelContainer.classList.add('hidden');
                customModelContainer.classList.remove('hidden');
            }} else {{
                modelContainer.classList.remove('hidden');
                customModelContainer.classList.add('hidden');
            }}
            
            // Update model options
            const models = settingsProviderModels[provider] || [];
            modelSelect.innerHTML = models.map(m => 
                `<option value="${{m.value}}">${{m.label}}</option>`
            ).join('');
            
            // Load provider-specific settings from backend
            try {{
                const res = await fetch(`/api/settings/provider/${{provider}}`);
                const providerData = await res.json();
                
                // Update API key placeholder based on whether a key exists
                if (providerData.has_api_key) {{
                    apiKeyInput.placeholder = "•••••••••••••••••••• (configured - enter new to replace)";
                    apiKeyInput.value = "";  // Clear any previous value
                }} else {{
                    apiKeyInput.placeholder = "Enter API key...";
                    apiKeyInput.value = "";
                }}
                
                // Update model selection if a model is configured for this provider
                if (providerData.configured_model) {{
                    if (provider === 'custom') {{
                        document.getElementById('settings-custom-model').value = providerData.configured_model;
                    }} else {{
                        // Try to select the configured model, fallback to first option
                        const modelExists = Array.from(modelSelect.options).some(o => o.value === providerData.configured_model);
                        if (modelExists) {{
                            modelSelect.value = providerData.configured_model;
                        }}
                    }}
                }}
                
                // Update base URL if configured
                if (providerData.base_url) {{
                    document.getElementById('settings-base-url').value = providerData.base_url;
                }} else {{
                    document.getElementById('settings-base-url').value = '';
                }}
                
            }} catch (error) {{
                console.error('Failed to load provider settings:', error);
                apiKeyInput.placeholder = "Enter API key...";
                apiKeyInput.value = "";
            }}
        }}
        
        async function saveProviderSettings() {{
            const btn = document.querySelector('button[onclick="saveProviderSettings()"]');
            const provider = document.getElementById('settings-provider').value;
            let apiKey = document.getElementById('settings-api-key').value;
            let model = document.getElementById('settings-model').value;
            const baseUrl = document.getElementById('settings-base-url').value;
            
            // For custom provider, get model name from text input
            if (provider === 'custom') {{
                model = document.getElementById('settings-custom-model').value;
                if (!model) {{
                    showToast('Please enter a model name', 'error');
                    return;
                }}
                if (!baseUrl) {{
                    showToast('Please enter a base URL', 'error');
                    return;
                }}
            }}
            
            // Don't overwrite if user left the "..." placeholder
            if (apiKey.endsWith('...')) {{
                apiKey = null;  // Signal to backend to keep existing
            }}
            
            setButtonLoading(btn, 'Saving...');
            
            try {{
                const res = await fetch('/api/settings/provider', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{provider, api_key: apiKey, model, base_url: baseUrl}})
                }});
                const data = await res.json();
                if (data.status === 'ok') {{
                    setButtonSuccess(btn, 'Saved!');
                    showToast('Provider settings saved!', 'success');
                    // Reload page to update status table
                    setTimeout(() => location.reload(), 1500);
                }} else {{
                    setButtonError(btn, 'Failed');
                    showToast('Failed: ' + data.error, 'error');
                }}
            }} catch (error) {{
                setButtonError(btn, 'Error');
                showToast('Error saving settings', 'error');
            }}
        }}
        
        async function testProviderConnection() {{
            const btn = document.querySelector('button[onclick="testProviderConnection()"]');
            const provider = document.getElementById('settings-provider').value;
            const apiKey = document.getElementById('settings-api-key').value;
            const baseUrl = document.getElementById('settings-base-url').value;
            
            setButtonLoading(btn, 'Testing...');
            
            try {{
                const res = await fetch('/api/settings/provider/test', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{provider, api_key: apiKey, base_url: baseUrl}})
                }});
                const data = await res.json();
                if (data.status === 'ok') {{
                    setButtonSuccess(btn, 'Connected!');
                    showToast('✓ ' + data.message, 'success');
                }} else if (data.status === 'warning') {{
                    setButtonError(btn, 'Warning');
                    showToast('⚠ ' + data.message, 'warning');
                }} else {{
                    setButtonError(btn, 'Failed');
                    showToast('✗ ' + (data.error || 'Connection failed'), 'error');
                }}
            }} catch (error) {{
                setButtonError(btn, 'Error');
                showToast('✗ Connection failed: ' + error.message, 'error');
            }}
        }}
        
        // ============================================================================
        // TELEGRAM SETTINGS
        // ============================================================================
        
        function toggleTelegramSettings() {{
            const enabled = document.getElementById('settings-telegram-enabled').checked;
            const configDiv = document.getElementById('telegram-config');
            if (enabled) {{
                configDiv.classList.remove('hidden');
            }} else {{
                configDiv.classList.add('hidden');
            }}
        }}
        
        async function saveTelegramSettings() {{
            const btn = document.querySelector('button[onclick="saveTelegramSettings()"]');
            const token = document.getElementById('settings-telegram-token').value;
            const chatIds = document.getElementById('settings-telegram-chats').value;
            
            if (!token || !chatIds) {{
                showToast('Please fill in both Bot Token and Chat ID', 'error');
                return;
            }}
            
            setButtonLoading(btn, 'Saving...');
            
            try {{
                const res = await fetch('/api/settings/telegram', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{
                        enabled: true,
                        token,
                        allowed_chat_ids: chatIds.split(',').map(s => s.trim()).filter(s => s)
                    }})
                }});
                const data = await res.json();
                if (data.status === 'ok') {{
                    setButtonSuccess(btn, 'Saved!');
                    showToast('Telegram settings saved!', 'success');
                    updateTelegramStatusBadge('configured');
                }} else {{
                    setButtonError(btn, 'Failed');
                    showToast('Failed: ' + data.error, 'error');
                }}
            }} catch (error) {{
                setButtonError(btn, 'Error');
                showToast('Error saving settings', 'error');
            }}
        }}
        
        async function launchTelegramBot() {{
            const btn = document.getElementById('telegram-launch-btn');
            const token = document.getElementById('settings-telegram-token').value;
            const chatIds = document.getElementById('settings-telegram-chats').value;
            
            if (!token || !chatIds) {{
                showToast('Please fill in Bot Token and Chat ID first', 'error');
                return;
            }}
            
            setButtonLoading(btn, 'Launching...');
            
            try {{
                // First save the settings
                await fetch('/api/settings/telegram', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{
                        enabled: true,
                        token,
                        allowed_chat_ids: chatIds.split(',').map(s => s.trim()).filter(s => s)
                    }})
                }});
                
                // Then try to launch/check the bot
                const res = await fetch('/api/settings/telegram/launch', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}}
                }});
                const data = await res.json();
                
                if (data.status === 'ok' || data.status === 'online') {{
                    setButtonSuccess(btn, 'Online!');
                    showToast('Bot is online! ✅', 'success');
                    updateTelegramStatusBadge('online', data.bot_info);
                }} else if (data.status === 'error') {{
                    setButtonError(btn, 'Failed');
                    showToast('Bot error: ' + data.error, 'error');
                    updateTelegramStatusBadge('error', data.error);
                }} else {{
                    setButtonError(btn, 'Unknown');
                    showToast('Bot status: ' + data.status, 'warning');
                    updateTelegramStatusBadge(data.status);
                }}
            }} catch (error) {{
                setButtonError(btn, 'Error');
                showToast('Failed to launch bot: ' + error.message, 'error');
                updateTelegramStatusBadge('error', error.message);
            }}
        }}
        
        function updateTelegramStatusBadge(status, info = null) {{
            const badge = document.getElementById('telegram-status-badge');
            const statusDiv = document.getElementById('telegram-last-status');
            if (!badge) return;
            
            const statusConfig = {{
                'offline': {{ class: 'bg-gray-100 text-gray-400', icon: 'fa-circle', text: 'Offline' }},
                'configured': {{ class: 'bg-yellow-100 text-yellow-600', icon: 'fa-check', text: 'Saved' }},
                'online': {{ class: 'bg-green-100 text-green-600', icon: 'fa-check-circle', text: 'Online' }},
                'error': {{ class: 'bg-red-100 text-red-600', icon: 'fa-exclamation-circle', text: 'Error' }},
                'launching': {{ class: 'bg-blue-100 text-blue-600', icon: 'fa-spinner fa-spin', text: 'Launching' }}
            }};
            
            const config = statusConfig[status] || statusConfig['offline'];
            badge.className = `ml-auto text-[10px] px-2 py-0.5 rounded-full ${{config.class}}`;
            badge.innerHTML = `<i class="fas ${{config.icon}} text-[6px] mr-1"></i>${{config.text}}`;
            
            // Show detailed status
            if (statusDiv) {{
                statusDiv.classList.remove('hidden');
                if (info) {{
                    if (typeof info === 'object') {{
                        statusDiv.innerHTML = `<i class="fas fa-robot mr-1"></i>@${{info.username || 'bot'}} • ${{new Date().toLocaleTimeString()}}`;
                    }} else {{
                        statusDiv.innerHTML = `<i class="fas fa-info-circle mr-1"></i>${{info}}`;
                    }}
                }} else {{
                    statusDiv.innerHTML = `<i class="fas fa-clock mr-1"></i>Last checked: ${{new Date().toLocaleTimeString()}}`;
                }}
            }}
        }}
        
        // Check Telegram status on load
        async function checkTelegramStatus() {{
            try {{
                const res = await fetch('/api/settings/telegram/status');
                if (res.ok) {{
                    const data = await res.json();
                    if (data.enabled) {{
                        document.getElementById('settings-telegram-token').placeholder = '•••••••••••• (saved)';
                        document.getElementById('settings-telegram-chats').value = data.chat_ids?.join(', ') || '';
                        updateTelegramStatusBadge(data.status === 'online' ? 'online' : 'configured', data.bot_info);
                    }}
                }}
            }} catch (e) {{
                console.log('Telegram status check failed:', e);
            }}
        }}
        
        // ============================================================================
        // MEMORY EXPLORER
        // ============================================================================
        
        let memoryOffset = 0;
        let memorySearchType = 'quick';
        let currentMemoryQuery = '';
        
        function toggleMemoryPanel() {{
            const panel = document.getElementById('memory-panel');
            const icon = document.getElementById('memory-toggle-icon');
            panel.classList.toggle('hidden');
            icon.classList.toggle('fa-chevron-down');
            icon.classList.toggle('fa-chevron-up');
            
            if (!panel.classList.contains('hidden') && memoryOffset === 0) {{
                loadMemories();
                loadMemoryStats();
            }}
        }}
        
        // Context Facts Panel
        function toggleContextFactsPanel() {{
            const panel = document.getElementById('context-facts-panel');
            const icon = document.getElementById('context-facts-toggle-icon');
            panel.classList.toggle('hidden');
            icon.classList.toggle('fa-chevron-down');
            icon.classList.toggle('fa-chevron-up');
            
            if (!panel.classList.contains('hidden')) {{
                loadContextFacts();
            }}
        }}
        
        // Context Analyzer Panel
        function toggleContextAnalyzerPanel() {{
            const panel = document.getElementById('context-analyzer-panel');
            const icon = document.getElementById('context-analyzer-toggle-icon');
            panel.classList.toggle('hidden');
            icon.classList.toggle('fa-chevron-down');
            icon.classList.toggle('fa-chevron-up');
        }}
        
        async function analyzeContext() {{
            if (!currentSessionId) {{
                alert('No active session');
                return;
            }}
            
            const statusEl = document.getElementById('context-analyzer-status');
            const statsEl = document.getElementById('context-analyzer-stats');
            const compactBtn = document.getElementById('btn-compact-context');
            
            statusEl.textContent = 'Analyzing...';
            
            try {{
                const res = await fetch(`/api/sessions/${{currentSessionId}}/context/analyze`);
                const data = await res.json();
                
                if (data.error) {{
                    statusEl.textContent = 'Error: ' + data.error;
                    return;
                }}
                
                // Clear top important if not enough messages
                const topImportantEl = document.getElementById('ca-top-important');
                if (!data.top_important || data.top_important.length === 0 || data.message_count < 3) {{
                    if (topImportantEl) {{
                        topImportantEl.innerHTML = '<div class="text-gray-400">Not enough data</div>';
                    }}
                }}
                
                statusEl.classList.add('hidden');
                statsEl.classList.remove('hidden');
                
                document.getElementById('ca-messages').textContent = data.message_count;
                
                // Update tokens display with progress bar
                const tokenPct = Math.min(100, (data.estimated_tokens / data.max_tokens) * 100);
                document.getElementById('ca-tokens-text').textContent = `${{data.estimated_tokens.toLocaleString()}} / ${{data.max_tokens.toLocaleString()}} (${{tokenPct.toFixed(0)}}%)`;
                const tokenBar = document.getElementById('ca-tokens-bar');
                tokenBar.style.width = `${{tokenPct}}%`;
                tokenBar.className = `h-2 rounded-full transition-all ${{tokenPct > 80 ? 'bg-red-500' : tokenPct > 60 ? 'bg-orange-500' : 'bg-green-500'}}`;
                
                const statusSpan = document.getElementById('ca-status');
                const expandBtn = document.getElementById('btn-expand-analyzer');
                const resetBtn = document.getElementById('btn-reset-context');
                
                if (data.should_compact) {{
                    statusSpan.textContent = 'Should Compact ⚠️';
                    statusSpan.className = 'font-medium text-orange-600';
                    compactBtn.classList.remove('hidden');
                }} else {{
                    statusSpan.textContent = 'OK ✅';
                    statusSpan.className = 'font-medium text-green-600';
                    compactBtn.classList.add('hidden');
                }}
                expandBtn.classList.remove('hidden');
                resetBtn.classList.remove('hidden');
                
                // Show top important messages (reuse topImportantEl declared earlier)
                if (data.top_important && data.top_important.length > 0) {{
                    topImportantEl.innerHTML = data.top_important.slice(0, 3).map((item, i) => `
                        <div class="text-gray-600 truncate" title="${{item.content}}">
                            ${{i + 1}}. ${{item.content.substring(0, 40)}}... 
                            <span class="text-indigo-600">(${{(item.importance_score * 100).toFixed(0)}}%)</span>
                        </div>
                    `).join('');
                }} else {{
                    topImportantEl.innerHTML = '<div class="text-gray-400">Not enough data</div>';
                }}
                
            }} catch (error) {{
                statusEl.textContent = 'Failed to analyze: ' + error.message;
            }}
        }}
        
        async function compactContextNow() {{
            if (!currentSessionId) return;
            
            if (!confirm('Compact context? This will summarize older messages.')) return;
            
            const btn = document.getElementById('btn-compact-context');
            btn.disabled = true;
            btn.innerHTML = '<i class="fas fa-spinner fa-spin mr-1"></i>Compacting...';
            
            try {{
                const res = await fetch(`/api/sessions/${{currentSessionId}}/context/compact`, {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{preserve_recent: 5, force: true}})
                }});
                
                const data = await res.json();
                
                if (data.status === 'ok') {{
                    alert(`Context compacted!\\nReduced from ${{data.original_count}} to ${{data.new_count}} messages`);
                    analyzeContext(); // Refresh analysis
                    // Force clear and reload chat
                    chatMessages.innerHTML = '';
                    sessionMessages = [];
                    messageCount = 0;
                    if (currentSessionId) {{
                        await loadSession(currentSessionId);
                        // Scroll to bottom
                        chatMessages.scrollTop = chatMessages.scrollHeight;
                    }}
                }} else {{
                    alert('Failed: ' + (data.error || 'Unknown error'));
                }}
            }} catch (error) {{
                alert('Error: ' + error.message);
            }} finally {{
                btn.disabled = false;
                btn.innerHTML = '<i class="fas fa-compress-alt mr-1"></i>Compact';
            }}
        }}
        
        async function resetContextNow() {{
            if (!currentSessionId) return;
            
            if (!confirm('⚠️ WARNING: This will DELETE ALL messages in this session!\\n\\nAre you sure?')) return;
            if (!confirm('Really sure? This cannot be undone.')) return;
            
            const btn = document.getElementById('btn-reset-context');
            btn.disabled = true;
            btn.innerHTML = '<i class="fas fa-spinner fa-spin mr-1"></i>Resetting...';
            
            try {{
                const res = await fetch(`/api/sessions/${{currentSessionId}}/messages`, {{
                    method: 'DELETE'
                }});
                
                if (res.ok) {{
                    alert('Context reset! All messages deleted.');
                    analyzeContext(); // Refresh analysis
                    if (currentSessionId) loadSession(currentSessionId); // Refresh chat (will be empty)
                }} else {{
                    alert('Failed to reset context');
                }}
            }} catch (error) {{
                alert('Error: ' + error.message);
            }} finally {{
                btn.disabled = false;
                btn.innerHTML = '<i class="fas fa-trash-alt mr-1"></i>Reset';
            }}
        }}
        
        // Full Context Analyzer Modal
        let currentAnalysisData = null;
        
        function openFullContextAnalyzer() {{
            const modal = document.getElementById('full-analyzer-modal');
            modal.classList.remove('hidden');
            modal.classList.add('flex');
            loadFullAnalysis();
        }}
        
        function closeFullAnalyzer() {{
            const modal = document.getElementById('full-analyzer-modal');
            modal.classList.add('hidden');
            modal.classList.remove('flex');
        }}
        
        async function loadFullAnalysis() {{
            if (!currentSessionId) return;
            
            const content = document.getElementById('full-analyzer-content');
            content.innerHTML = '<div class="text-center py-8"><i class="fas fa-spinner fa-spin text-2xl text-indigo-500"></i><p class="mt-2 text-gray-500">Analyzing all messages...</p></div>';
            
            try {{
                const res = await fetch(`/api/sessions/${{currentSessionId}}/context/analyze?full=true`);
                const data = await res.json();
                currentAnalysisData = data;
                
                if (data.error) {{
                    content.innerHTML = `<div class="text-red-500">Error: ${{data.error}}</div>`;
                    return;
                }}
                
                // Stats summary
                document.getElementById('full-analyzer-stats').innerHTML = `
                    <span class="font-medium">${{data.message_count}}</span> messages · 
                    <span class="font-medium">${{data.estimated_tokens}}</span> tokens · 
                    <span class="${{data.should_compact ? 'text-orange-600' : 'text-green-600'}}">${{data.should_compact ? 'Should Compact' : 'OK'}}</span>
                `;
                
                // Build full analysis view
                let html = `
                    <div class="grid grid-cols-2 gap-4 mb-4">
                        <div class="p-3 bg-indigo-50 rounded-lg">
                            <p class="text-sm font-medium text-indigo-900">Topics Detected</p>
                            <p class="text-2xl font-bold text-indigo-600">${{data.topics?.length || 0}}</p>
                        </div>
                        <div class="p-3 bg-green-50 rounded-lg">
                            <p class="text-sm font-medium text-green-900">Key Decisions</p>
                            <p class="text-2xl font-bold text-green-600">${{data.decisions?.length || 0}}</p>
                        </div>
                    </div>
                `;
                
                // Topics
                if (data.topics && data.topics.length > 0) {{
                    html += `
                        <div class="mb-4">
                            <h3 class="font-medium text-gray-900 mb-2">Topics</h3>
                            <div class="flex flex-wrap gap-2">
                                ${{data.topics.map(t => `<span class="px-2 py-1 bg-indigo-100 text-indigo-700 rounded text-sm">${{t}}</span>`).join('')}}
                            </div>
                        </div>
                    `;
                }}
                
                // All messages with importance scores
                if (data.all_messages && data.all_messages.length > 0) {{
                    const lowImportanceCount = data.all_messages.filter(m => m.importance_score < 0.6).length;
                    html += `
                        <div>
                            <div class="flex items-center justify-between mb-2">
                                <h3 class="font-medium text-gray-900">Message Importance Analysis</h3>
                                <div class="flex gap-2">
                                    <button onclick="selectLowImportanceMessages()" class="text-xs px-2 py-1 bg-orange-100 text-orange-700 rounded hover:bg-orange-200">
                                        Select Low (${{lowImportanceCount}})
                                    </button>
                                    <button onclick="selectAllMessagesForCompact(true)" class="text-xs px-2 py-1 bg-gray-100 text-gray-700 rounded hover:bg-gray-200">All</button>
                                    <button onclick="selectAllMessagesForCompact(false)" class="text-xs px-2 py-1 bg-gray-100 text-gray-700 rounded hover:bg-gray-200">None</button>
                                </div>
                            </div>
                            <p class="text-xs text-gray-500 mb-2">
                                <span class="text-green-600 font-medium">Green = Keep</span> • 
                                <span class="text-orange-600 font-medium">Orange = Review</span> • 
                                <span class="text-gray-500">Gray = Compact</span>
                            </p>
                            <div class="space-y-2 max-h-[50vh] overflow-y-auto" id="message-compact-list">
                                ${{data.all_messages.map((msg, idx) => `
                                    <div class="flex items-start gap-3 p-3 border rounded hover:bg-gray-50 ${{msg.importance_score > 0.7 ? 'bg-green-50 border-green-200' : msg.importance_score > 0.4 ? 'bg-orange-50 border-orange-200' : 'bg-gray-50 border-gray-200'}}" data-importance="${{msg.importance_score}}">
                                        <input type="checkbox" id="msg-compact-${{idx}}" class="mt-1 compact-msg-checkbox" ${{msg.importance_score < 0.6 ? 'checked' : ''}}>
                                        <div class="flex-1">
                                            <div class="flex items-center gap-2 mb-1">
                                                <span class="text-xs font-medium ${{msg.role === 'user' ? 'text-blue-600' : 'text-gray-600'}}">${{msg.role}}</span>
                                                <span class="text-xs text-gray-400">#${{idx + 1}}</span>
                                                <div class="flex-1"></div>
                                                <span class="text-xs font-medium ${{msg.importance_score > 0.7 ? 'text-green-600' : msg.importance_score > 0.4 ? 'text-orange-600' : 'text-gray-500'}}">${{(msg.importance_score * 100).toFixed(0)}}%</span>
                                            </div>
                                            <p class="text-sm text-gray-700 line-clamp-2">${{msg.content}}</p>
                                        </div>
                                    </div>
                                `).join('')}}
                            </div>
                        </div>
                    `;
                }}
                
                content.innerHTML = html;
                
            }} catch (error) {{
                content.innerHTML = `<div class="text-red-500">Failed to load: ${{error.message}}</div>`;
            }}
        }}
        
        function selectLowImportanceMessages() {{
            const checkboxes = document.querySelectorAll('.compact-msg-checkbox');
            checkboxes.forEach((cb, idx) => {{
                const row = cb.closest('[data-importance]');
                const importance = parseFloat(row?.dataset.importance || 0);
                cb.checked = importance < 0.6;
            }});
        }}
        
        function selectAllMessagesForCompact(select) {{
            const checkboxes = document.querySelectorAll('.compact-msg-checkbox');
            checkboxes.forEach(cb => cb.checked = select);
        }}
        
        async function compactSelectedMessages() {{
            if (!currentSessionId || !currentAnalysisData) return;
            
            // Get selected message indices
            const checkboxes = document.querySelectorAll('.compact-msg-checkbox');
            const selectedIndices = [];
            checkboxes.forEach((cb, idx) => {{
                if (cb.checked) selectedIndices.push(idx);
            }});
            
            if (selectedIndices.length === 0) {{
                alert('No messages selected for compaction');
                return;
            }}
            
            if (!confirm(`Compact ${{selectedIndices.length}} selected messages?`)) return;
            
            try {{
                const res = await fetch(`/api/sessions/${{currentSessionId}}/context/compact`, {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{message_indices: selectedIndices}})
                }});
                
                const data = await res.json();
                
                if (data.status === 'ok') {{
                    alert(`Compacted! ${{data.summary}}`);
                    closeFullAnalyzer();
                    analyzeContext();
                }} else {{
                    alert('Failed: ' + (data.error || 'Unknown error'));
                }}
            }} catch (error) {{
                alert('Error: ' + error.message);
            }}
        }}
        
        async function loadContextFacts_disabled() {{
            if (!currentSessionId) return;
            
            try {{
                const res = await fetch(`/api/sessions/${{currentSessionId}}/facts`);
                const data = await res.json();
                
                const list = document.getElementById('context-facts-list');
                const count = document.getElementById('context-facts-count');
                
                count.textContent = data.count || 0;
                
                const manageBtn = document.getElementById('btn-manage-facts');
                if (!data.facts || data.facts.length === 0) {{
                    list.innerHTML = '<div class="text-gray-400 text-center py-2">No facts extracted yet. Keep chatting!</div>';
                    if (manageBtn) manageBtn.disabled = true;
                }} else {{
                    if (manageBtn) manageBtn.disabled = false;
                    list.innerHTML = data.facts.slice(-10).reverse().map(f => {{
                        const categoryColors = {{
                            'preference': 'bg-purple-100 text-purple-700',
                            'decision': 'bg-green-100 text-green-700',
                            'information': 'bg-blue-100 text-blue-700',
                            'task': 'bg-orange-100 text-orange-700'
                        }};
                        const color = categoryColors[f.category] || 'bg-gray-100 text-gray-700';
                        return `
                            <div class="p-2 bg-white border border-gray-200 rounded">
                                <span class="px-1.5 py-0.5 ${{color}} rounded text-[10px] uppercase">${{f.category}}</span>
                                <p class="mt-1 text-gray-700">${{f.content}}</p>
                            </div>
                        `;
                    }}).join('');
                }}
            }} catch (error) {{
                console.error('Failed to load context facts:', error);
            }}
        }}
        
        // Facts Manager
        let currentFactsData = [];
        
        function openFactsManager() {{
            const modal = document.getElementById('facts-manager-modal');
            modal.classList.remove('hidden');
            modal.classList.add('flex');
            loadFactsForManagement();
        }}
        
        function closeFactsManager() {{
            const modal = document.getElementById('facts-manager-modal');
            modal.classList.add('hidden');
            modal.classList.remove('flex');
        }}
        
        async function loadFactsForManagement() {{
            if (!currentSessionId) return;
            
            const list = document.getElementById('facts-manager-list');
            list.innerHTML = '<div class="text-center py-4"><i class="fas fa-spinner fa-spin text-indigo-500"></i></div>';
            
            try {{
                const res = await fetch(`/api/sessions/${{currentSessionId}}/facts`);
                const data = await res.json();
                currentFactsData = data.facts || [];
                
                if (currentFactsData.length === 0) {{
                    list.innerHTML = '<div class="text-gray-400 text-center py-4">No facts available</div>';
                    return;
                }}
                
                const categoryColors = {{
                    'preference': 'bg-purple-100 text-purple-700',
                    'decision': 'bg-green-100 text-green-700',
                    'information': 'bg-blue-100 text-blue-700',
                    'task': 'bg-orange-100 text-orange-700'
                }};
                
                list.innerHTML = currentFactsData.map((f, idx) => {{
                    const color = categoryColors[f.category] || 'bg-gray-100 text-gray-700';
                    return `
                        <div class="flex items-start gap-3 p-3 border rounded hover:bg-gray-50">
                            <input type="checkbox" id="fact-select-${{idx}}" class="mt-1 fact-checkbox" data-idx="${{idx}}">
                            <div class="flex-1">
                                <span class="px-1.5 py-0.5 ${{color}} rounded text-[10px] uppercase">${{f.category}}</span>
                                <p class="mt-1 text-sm text-gray-700">${{f.content}}</p>
                                <p class="text-xs text-gray-400 mt-1">${{new Date(f.timestamp).toLocaleDateString()}}</p>
                            </div>
                        </div>
                    `;
                }}).join('');
            }} catch (error) {{
                list.innerHTML = `<div class="text-red-500 text-center py-4">Error: ${{error.message}}</div>`;
            }}
        }}
        
        function selectAllFacts() {{
            document.querySelectorAll('.fact-checkbox').forEach(cb => cb.checked = true);
        }}
        
        async function storeFactsToMemory() {{
            const selected = [];
            document.querySelectorAll('.fact-checkbox:checked').forEach(cb => {{
                const idx = parseInt(cb.dataset.idx);
                if (currentFactsData[idx]) selected.push(currentFactsData[idx]);
            }});
            
            if (selected.length === 0) {{
                alert('No facts selected');
                return;
            }}
            
            if (!confirm(`Store ${{selected.length}} facts to long-term memory?`)) return;
            
            try {{
                const res = await fetch(`/api/sessions/${{currentSessionId}}/facts/store`, {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{facts: selected}})
                }});
                
                const data = await res.json();
                
                if (data.status === 'ok') {{
                    alert(`Stored ${{data.stored}} facts to memory!`);
                    closeFactsManager();
                    loadContextFacts();
                }} else {{
                    alert('Failed: ' + (data.error || 'Unknown error'));
                }}
            }} catch (error) {{
                alert('Error: ' + error.message);
            }}
        }}
        
        // ============================================================================
        // SEMANTIC MEMORY - What the AI Learned
        // ============================================================================
        
        function toggleSemanticMemoryPanel() {{
            const panel = document.getElementById('semantic-memory-panel');
            const icon = document.getElementById('semantic-memory-toggle-icon');
            panel.classList.toggle('hidden');
            icon.classList.toggle('fa-chevron-down');
            icon.classList.toggle('fa-chevron-up');
            if (!panel.classList.contains('hidden')) {{
                loadSemanticMemory();
            }}
        }}
        
        async function loadSemanticMemory() {{
            try {{
                // If no session selected, don't try to load
                if (!currentSessionId) {{
                    document.getElementById('semantic-memory-list').innerHTML = 
                        '<div class="text-gray-400 text-center py-2">Select a session first</div>';
                    document.getElementById('semantic-memory-count').textContent = '0';
                    return;
                }}
                
                const res = await fetch(`/api/semantic-memory?session_id=${{currentSessionId}}`);
                const data = await res.json();
                
                const list = document.getElementById('semantic-memory-list');
                const count = document.getElementById('semantic-memory-count');
                
                count.textContent = data.count || 0;
                
                if (!data.memories || data.memories.length === 0) {{
                    list.innerHTML = '<div class="text-gray-400 text-center py-2">No memories yet. Let us work together!</div>';
                    return;
                }}
                
                // Show top 5 most important memories
                const topMemories = data.memories.slice(0, 5);
                
                list.innerHTML = topMemories.map(m => {{
                    const sentimentColor = m.sentiment >= 4 ? 'text-green-600' : 
                                         m.sentiment >= 3 ? 'text-gray-600' : 'text-orange-600';
                    const sentimentIcon = m.sentiment >= 4 ? 'fa-smile' : 
                                        m.sentiment >= 3 ? 'fa-meh' : 'fa-frown';
                    const title = m.topics?.[0] || (m.technologies?.[0] ? `Tech: ${{m.technologies[0]}}` : 'Interaction');
                    const description = (m.summary || m.user_message || 'Interaction recorded').substring(0, 60);
                    
                    return `
                        <div class="p-2 bg-white border border-pink-200 rounded hover:bg-pink-50">
                            <div class="flex items-center gap-2 mb-1">
                                <i class="fas ${{sentimentIcon}} ${{sentimentColor}}"></i>
                                <span class="font-medium text-gray-700">${{title}}</span>
                                <span class="text-xs text-gray-400 ml-auto">${{new Date(m.timestamp).toLocaleDateString()}}</span>
                            </div>
                            <p class="text-gray-600">${{description}}...</p>
                            ${{m.successful ? '<p class="text-xs text-green-600 mt-1"><i class="fas fa-check mr-1"></i>Success</p>' : ''}}
                        </div>
                    `;
                }}).join('');
                
            }} catch (error) {{
                console.error('Failed to load semantic memory:', error);
            }}
        }}
        
        function openSemanticMemoryDetails() {{
            const modal = document.getElementById('semantic-memory-modal');
            modal.classList.remove('hidden');
            modal.classList.add('flex');
            loadSemanticMemoryDetails();
        }}
        
        function closeSemanticMemoryModal() {{
            const modal = document.getElementById('semantic-memory-modal');
            modal.classList.add('hidden');
            modal.classList.remove('flex');
        }}
        
        async function loadSemanticMemoryDetails() {{
            const content = document.getElementById('semantic-memory-details');
            const summary = document.getElementById('semantic-memory-summary');
            
            content.innerHTML = '<div class="text-center py-8"><i class="fas fa-spinner fa-spin text-2xl text-pink-500"></i><p class="mt-2 text-gray-500">Loading memories...</p></div>';
            
            // Show session info in header
            const sessionName = document.getElementById('current-session-name')?.textContent || 'Current Session';
            
            if (!currentSessionId) {{
                content.innerHTML = '<div class="text-gray-400 text-center py-8">Select a session first to view memories</div>';
                summary.textContent = '';
                return;
            }}
            
            try {{
                const res = await fetch(`/api/semantic-memory?session_id=${{currentSessionId}}`);
                const data = await res.json();
                
                if (!data.memories || data.memories.length === 0) {{
                    content.innerHTML = '<div class="text-gray-400 text-center py-8">No memories yet. Let us work together!</div>';
                    summary.textContent = '';
                    return;
                }}
                
                // Build summary
                const sessionName = document.getElementById('current-session-name')?.textContent || 'Current Session';
                summary.innerHTML = `
                    <span class="text-gray-500">Session:</span> <span class="font-medium">${{sessionName}}</span> · 
                    <span class="font-medium">${{data.count}}</span> memories · 
                    <span class="font-medium text-green-600">${{data.positive_count}}</span> positive · 
                    <span class="font-medium">${{data.topics?.length || 0}}</span> topics
                `;
                
                // Build content
                let html = '';
                
                // Topics Section
                if (data.topics && data.topics.length > 0) {{
                    html += `
                        <div class="mb-6">
                            <h3 class="font-semibold text-pink-700 mb-3 flex items-center gap-2">
                                <i class="fas fa-tags"></i> Topics
                            </h3>
                            <div class="flex flex-wrap gap-2">
                                ${{data.topics.map(t => `
                                    <span class="px-2 py-1 bg-pink-50 text-pink-700 rounded-full text-xs">${{t}}</span>
                                `).join('')}}
                            </div>
                        </div>
                    `;
                }}
                
                // Successful Interactions Section
                const successful = data.memories.filter(m => m.successful);
                if (successful.length > 0) {{
                    html += `
                        <div class="mb-6">
                            <h3 class="font-semibold text-green-700 mb-3 flex items-center gap-2">
                                <i class="fas fa-check-circle"></i> Successful Interactions
                            </h3>
                            <div class="space-y-2">
                                ${{successful.slice(0, 5).map(m => `
                                    <div class="p-3 bg-green-50 border border-green-200 rounded">
                                        <p class="text-gray-700 text-sm">${{(m.summary || m.user_message || '').substring(0, 100)}}...</p>
                                        <p class="text-xs text-gray-500 mt-1">${{new Date(m.timestamp).toLocaleDateString()}} · ${{m.outcome_description || 'completed'}}</p>
                                    </div>
                                `).join('')}}
                            </div>
                        </div>
                    `;
                }}
                
                // All Memories Section
                html += '<div class="space-y-4">';
                html += `
                    <div class="border rounded-lg overflow-hidden">
                        <div class="p-3 bg-gray-100 font-medium text-gray-700 flex items-center gap-2">
                            <i class="fas fa-brain text-gray-400"></i>
                            All Memories (${{data.memories.length}})
                        </div>
                        <div class="divide-y">
                            ${{data.memories.slice(0, 10).map(m => `
                                <div class="p-3 hover:bg-gray-50">
                                    <div class="flex items-center gap-2 mb-1">
                                        <span class="text-xs ${{m.sentiment >= 4 ? 'text-green-600' : m.sentiment >= 3 ? 'text-gray-500' : 'text-orange-600'}}">
                                            ${{m.sentiment >= 4 ? '😊' : m.sentiment >= 3 ? '😐' : '😕'}} ${{m.sentiment || 3}}/5
                                        </span>
                                        <span class="text-xs text-gray-400">${{new Date(m.timestamp).toLocaleDateString()}}</span>
                                        ${{m.successful ? '<span class="text-xs text-green-600 ml-2">✓</span>' : ''}}
                                    </div>
                                    <p class="text-gray-700 text-sm">${{(m.summary || m.user_message || '').substring(0, 100)}}...</p>
                                    ${{m.topics?.length ? `<p class="text-xs text-gray-500 mt-1">Topics: ${{m.topics.join(', ')}}</p>` : ''}}
                                </div>
                            `).join('')}}
                        </div>
                    </div>
                `;
                html += '</div>';
                
                content.innerHTML = html;
                
            }} catch (error) {{
                content.innerHTML = `<div class="text-red-500 text-center py-8">Error: ${{error.message}}</div>`;
            }}
        }}
        
        async function consolidateMemory() {{
            if (!currentSessionId) {{
                alert('No active session');
                return;
            }}
            
            const btn = event.target;
            const originalText = btn.innerHTML;
            btn.innerHTML = '<i class="fas fa-spinner fa-spin mr-1"></i>Analisando...';
            btn.disabled = true;
            
            try {{
                // Step 1: Get preview
                const previewRes = await fetch(`/api/sessions/${{currentSessionId}}/consolidate/preview`);
                const previewData = await previewRes.json();
                
                if (previewData.status !== 'ok') {{
                    alert('❌ Erro na análise: ' + (previewData.error || 'Erro desconhecido'));
                    return;
                }}
                
                const preview = previewData.preview;
                
                if (preview.candidates_count === 0) {{
                    alert(`📊 Análise completa\n\n${{preview.total_memories}} memórias analisadas\nNenhuma memória relevante encontrada para consolidar.\n\nCritérios (threshold 0.7):\n• Importância ≥ 0.7, OU\n• 3+ critérios:\n  - Interação bem-sucedida + SUBSTANCIAL (>50 chars)\n  - Tem tecnologias/companhias REAIS\n  - Sentimento muito positivo (≥4)\n  - Conteúdo rico (2+ tópicos)\n\nExemplos que NÃO consolidamos:\n• 'who are you?' (trivial, sem tech específica)\n• Mensagens curtas\n• Apenas 'AI' genérico como tópico`);
                    return;
                }}
                
                // Build preview message
                let previewMsg = `📊 ANÁLISE DA SESSÃO\n`;
                previewMsg += `━━━━━━━━━━━━━━━━━━━━\n\n`;
                previewMsg += `• ${{preview.total_memories}} memórias totais\n`;
                previewMsg += `• ${{preview.candidates_count}} candidatas à consolidação\n`;
                previewMsg += `• ${{preview.rejected_count}} rejeitadas (baixa relevância)\n\n`;
                
                if (preview.unique_entities.technologies.length > 0) {{
                    previewMsg += `💻 Tecnologias: ${{preview.unique_entities.technologies.join(', ')}}\n`;
                }}
                if (preview.unique_entities.topics.length > 0) {{
                    previewMsg += `📌 Tópicos: ${{preview.unique_entities.topics.join(', ')}}\n`;
                }}
                
                previewMsg += `\n━━━━━━━━━━━━━━━━━━━━\n\n`;
                previewMsg += `Top ${{Math.min(3, preview.candidates.length)}} memórias mais relevantes:\n\n`;
                
                preview.candidates.slice(0, 3).forEach((c, i) => {{
                    previewMsg += `${{i + 1}}. ${{c.summary.substring(0, 60)}}...\n`;
                    previewMsg += `   Razões: ${{c.reasons.join(', ')}}\n\n`;
                }});
                
                previewMsg += `\nProsseguir com a consolidação?`;
                
                if (!confirm(previewMsg)) {{
                    return;
                }}
                
                // Step 2: Perform consolidation
                btn.innerHTML = '<i class="fas fa-spinner fa-spin mr-1"></i>Consolidando...';
                
                const res = await fetch(`/api/sessions/${{currentSessionId}}/consolidate`, {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}}
                }});
                
                const data = await res.json();
                
                if (data.status === 'ok') {{
                    let successMsg = `✅ Consolidação completa!\n\n`;
                    successMsg += `• ${{data.facts_analyzed}} memórias analisadas\n`;
                    successMsg += `• ${{data.facts_stored}} movidas para Knowledge Graph\n`;
                    successMsg += `• ${{data.unique_entities}} entidades únicas extraídas\n\n`;
                    successMsg += `💡 As memórias consolidadas não aparecerão mais nesta lista.`;
                    alert(successMsg);
                    loadSemanticMemory(); // Refresh the list (consolidated memories will disappear)
                }} else {{
                    alert('❌ Erro: ' + (data.error || 'Falha na consolidação'));
                }}
            }} catch (error) {{
                alert('❌ Erro: ' + error.message);
            }} finally {{
                btn.innerHTML = originalText;
                btn.disabled = false;
            }}
        }}
        
        async function loadMemoryStats() {{
            try {{
                // Load old memory stats (Hybrid Memory)
                const res = await fetch('/api/memory/stats');
                const data = await res.json();
                
                // Load new cognitive memory stats
                const cognitiveRes = await fetch('/api/cognitive-memory');
                const cognitiveData = await cognitiveRes.json();
                
                const oldCount = data.sqlite?.total || 0;
                const newCount = cognitiveData.episodic_count || 0;
                const entityCount = cognitiveData.semantic_entities || 0;
                
                // Display combined stats
                if (newCount > 0) {{
                    document.getElementById('memory-count').textContent = 
                        `${{newCount}} episodes, ${{entityCount}} entities`;
                    document.getElementById('memory-graph-status').textContent = 
                        '(Cognitive Memory 🧠)';
                }} else {{
                    document.getElementById('memory-count').textContent = 
                        `${{oldCount}} memories`;
                    document.getElementById('memory-graph-status').textContent = 
                        data.graph_available ? '(Graph ✅)' : '(SQLite only)';
                }}
            }} catch (error) {{
                console.error('Failed to load memory stats:', error);
            }}
        }}
        
        async function loadMemories(reset = false) {{
            if (reset) {{
                memoryOffset = 0;
                currentMemoryQuery = '';
            }}
            
            try {{
                const res = await fetch(`/api/memory?limit=10&offset=${{memoryOffset}}`);
                const data = await res.json();
                
                renderMemories(data.memories, reset);
                
                // Show/hide load more button
                const loadMoreBtn = document.getElementById('load-more-memories');
                if (data.memories.length === 10) {{
                    loadMoreBtn.classList.remove('hidden');
                }} else {{
                    loadMoreBtn.classList.add('hidden');
                }}
            }} catch (error) {{
                console.error('Failed to load memories:', error);
            }}
        }}
        
        async function searchMemories() {{
            const query = document.getElementById('memory-search').value.trim();
            if (!query) {{
                loadMemories(true);
                return;
            }}
            
            currentMemoryQuery = query;
            
            try {{
                const res = await fetch('/api/memory/search', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{
                        query: query,
                        type: memorySearchType,
                        limit: 10
                    }})
                }});
                
                const data = await res.json();
                renderMemories(data.memories, true);
                
                // Hide load more for search results
                document.getElementById('load-more-memories').classList.add('hidden');
            }} catch (error) {{
                console.error('Failed to search memories:', error);
            }}
        }}
        
        function renderMemories(memories, reset) {{
            const container = document.getElementById('memories-list');
            
            if (reset) {{
                container.innerHTML = '';
            }}
            
            if (memories.length === 0) {{
                container.innerHTML = '<div class="text-xs text-gray-400 text-center py-2">No memories found</div>';
                return;
            }}
            
            memories.forEach(m => {{
                const div = document.createElement('div');
                div.className = 'p-2 bg-white border border-gray-200 rounded-lg text-xs group hover:border-violet-300 transition-colors';
                
                const content = m.content || m.text || 'No content';
                const preview = content.length > 60 ? content.substring(0, 60) + '...' : content;
                const category = m.category || 'general';
                const date = m.created_at ? new Date(m.created_at).toLocaleDateString() : 'Unknown';
                
                div.innerHTML = `
                    <div class="flex items-start justify-between gap-2">
                        <div class="flex-1">
                            <div class="text-gray-700 leading-tight">${{preview}}</div>
                            <div class="flex items-center gap-2 mt-1.5">
                                <span class="px-1.5 py-0.5 bg-gray-100 rounded text-[10px] text-gray-500">${{category}}</span>
                                <span class="text-[10px] text-gray-400">${{date}}</span>
                            </div>
                        </div>
                        <button onclick="deleteMemory(${{m.id}})" 
                                class="text-gray-300 hover:text-red-500 opacity-0 group-hover:opacity-100 transition-opacity">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                `;
                
                container.appendChild(div);
            }});
            
            memoryOffset += memories.length;
        }}
        
        function setMemorySearchType(type) {{
            memorySearchType = type;
            
            // Update buttons
            document.getElementById('mem-search-quick').className = 
                type === 'quick' ? 'flex-1 btn btn-primary text-[10px] py-1' : 'flex-1 btn btn-secondary text-[10px] py-1';
            document.getElementById('mem-search-semantic').className = 
                type === 'semantic' ? 'flex-1 btn btn-primary text-[10px] py-1' : 'flex-1 btn btn-secondary text-[10px] py-1';
            
            // Re-search if there's a query
            if (currentMemoryQuery) {{
                searchMemories();
            }}
        }}
        
        function loadMoreMemories() {{
            if (currentMemoryQuery) {{
                searchMemories();
            }} else {{
                loadMemories();
            }}
        }}
        
        async function deleteMemory(id) {{
            if (!confirm('Delete this memory?')) return;
            
            try {{
                await fetch(`/api/memory/${{id}}`, {{ method: 'DELETE' }});
                loadMemories(true);
                loadMemoryStats();
            }} catch (error) {{
                console.error('Failed to delete memory:', error);
            }}
        }}
        
        // Initialize
        document.addEventListener('DOMContentLoaded', () => {{
            console.log('DOM loaded, initializing...');
            setupProviderListener();
            setupModelListener();
            loadSettings();
            loadSessions();
            checkTelegramStatus();
        }});
    </script>
</body>
</html>"""
    
    return HTMLResponse(content=html_content)


@app.get("/manifest.json")
async def get_manifest():
    """Serve the PWA manifest."""
    manifest = {
        "name": "Klaus AI",
        "short_name": "Klaus",
        "description": "Klaus AI Assistant - Solutions Architect",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#ffffff",
        "theme_color": "#7c3aed",
        "icons": [
            {
                "src": "https://cdn-icons-png.flaticon.com/512/2103/2103633.png",
                "sizes": "512x512",
                "type": "image/png",
                "purpose": "any maskable"
            }
        ]
    }
    return JSONResponse(content=manifest)


@app.get("/sw.js")
async def get_sw():
    """Serve the PWA service worker."""
    sw_content = """
    const CACHE_NAME = 'klaus-v1';
    const ASSETS = [
      '/',
      '/manifest.json',
      'https://cdn.tailwindcss.com',
      'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css'
    ];

    self.addEventListener('install', event => {
      event.waitUntil(
        caches.open(CACHE_NAME).then(cache => cache.addAll(ASSETS))
      );
    });

    self.addEventListener('fetch', event => {
      event.respondWith(
        caches.match(event.request).then(response => {
          return response || fetch(event.request);
        })
      );
    });
    """
    return Response(content=sw_content, media_type="application/javascript")


def should_use_web_search(message: str) -> tuple[bool, str]:
    """
    Determine if web search should be used for this message.
    Supports English and Portuguese.
    Returns (should_search, search_query)
    """
    message_lower = message.lower()
    
    # Weather queries - English
    weather_patterns = [
        r'weather\s+(?:in|at|for)\s+(.+)',
        r'how\'s\s+(?:the\s+)?weather\s+(?:in|at)?\s*(.*)',
        r'temperature\s+(?:in|at)\s+(.+)',
        r'what\'s\s+(?:the\s+)?weather\s*(?:in|at)?\s*(.*)',
    ]
    
    # Weather queries - Portuguese
    weather_patterns_pt = [
        r'(?:qual|como)\s+(?:é|esta|está)\s+(?:o\s+)?clima\s+(?:em|de|na|no)?\s*(.+)',
        r'(?:qual|como)\s+(?:é|esta|está)\s+(?:o\s+)?tempo\s+(?:em|de|na|no)?\s*(.+)',
        r'temperatura\s+(?:em|de|na|no)\s+(.+)',
        r'clima\s+(?:em|de|na|no)\s+(.+)',
        r'tempo\s+(?:em|de|na|no)\s+(.+)',
        r'faz\s+(?:quente|frio|sol|vento|chuva)\s+(?:em|de|na|no)?\s*(.+)',
    ]
    
    for pattern in weather_patterns + weather_patterns_pt:
        match = re.search(pattern, message_lower)
        if match:
            location = match.group(1).strip() if match.group(1) else "current location"
            return True, f"current weather {location}"
    
    # News/current events - English
    news_patterns = [
        r'(?:latest|recent|current|today\'s)\s+(?:news|events|updates?)',
        r'what\s+happened\s+(?:today|yesterday|recently)',
        r'(?:news|updates?)\s+(?:about|on)\s+(.+)',
    ]
    
    # News/current events - Portuguese
    news_patterns_pt = [
        r'(?:ultimas|últimas|recentes|atuais|novidades)\s+(?:noticias|notícias|eventos)',
        r'(?:noticias|notícias)\s+(?:sobre|de|sobre)\s+(.+)',
        r'o\s+que\s+aconteceu\s+(?:hoje|ontem|recentemente)',
        r'novidades\s+(?:sobre|de)\s+(.+)',
    ]
    
    for pattern in news_patterns + news_patterns_pt:
        if re.search(pattern, message_lower):
            # Extract topic if present
            match = re.search(r'(?:about|on|sobre|de)\s+(.+)', message_lower)
            topic = match.group(1).strip() if match else "current events"
            return True, f"latest news {topic}"
    
    # Stock/crypto prices
    if re.search(r'(?:price|value|preço|valor|cotação)\s+(?:of|for|de|da|do)\s+(.+)', message_lower):
        return True, message
    
    # Sports scores
    if re.search(r'(?:score|result|who won|placar|resultado|quem ganhou)\s+', message_lower):
        return True, message
    
    # General knowledge that might need current info - English + Portuguese
    if any(phrase in message_lower for phrase in [
        # English
        "current president", "current prime minister", "current ceo",
        "latest version", "newest release", "current time",
        "exchange rate", "price of", "cost of",
        # Portuguese
        "presidente atual", "primeiro ministro atual", "ceo atual",
        "versão mais recente", "última versão", "nova versão",
        "cotação", "preço do", "preço da", "custo de",
        "horário atual", "hora atual", "data atual",
    ]):
        return True, message
    
    return False, ""


@app.post("/api/chat")
async def chat(request: Request):
    """Process chat request using the configured provider."""
    global web_messages, current_session, settings, web_search_tool
    
    try:
        body = await request.json()
        user_message = body.get("message", "")
        
        # Allow overriding provider/model per message
        override_provider = body.get("provider")
        override_model = body.get("model")
        
        if not user_message:
            return JSONResponse({"error": "Empty message"}, status_code=400)
        
        # ============================================
        # SUB-AGENT SPAWNER DETECTION
        # Auto-detect when to spawn specialized agents
        # ============================================
        
        spawn_triggers = {
            "developer": ["review this code", "debug this", "refactor", "implement function", "write code", "code review"],
            "architect": ["design system", "architecture review", "scalability", "microservices", "system design"],
            "finance": ["calculate cost", "pricing", "budget", "financial analysis", "cost estimation"],
            "legal": ["review contract", "legal terms", "compliance", "gdpr", "liability"],
            "marketing": ["write copy", "marketing strategy", "seo", "content marketing"],
            "ui": ["design ui", "user interface", "ux review", "wireframe", "mockup"]
        }
        
        user_lower = user_message.lower()
        detected_template = None
        
        for template, triggers in spawn_triggers.items():
            if any(trigger in user_lower for trigger in triggers):
                detected_template = template
                break
        
        # Check if we should spawn a sub-agent
        if detected_template and detected_template != (current_session.template if current_session else "default"):
            # Check if spawner is available
            if spawner:
                try:
                    # Spawn the specialized agent
                    task_id = await spawner.spawn_agent(
                        template=detected_template,
                        task=user_message,
                        context={
                            "parent_template": current_session.template if current_session else "default",
                            "detected_intent": detected_template,
                            "conversation_history": web_messages[-5:] if web_messages else []
                        },
                        parent_session_id=current_session.id if current_session else "unknown",
                        provider=override_provider or settings.provider,
                        model=override_model or settings.model
                    )
                    
                    # Wait for result with shorter timeout
                    result = await spawner.get_result(task_id, timeout=60.0)
                    
                    if result:
                        # Format with agent tag
                        agent_tag = detected_template.title()
                        assistant_message = f"""**Klaus** *[as {agent_tag} Agent]*

{result}

---
*Consultation complete. Returning to main architect context.*"""
                        
                        web_messages.append({"sender": "assistant", "text": assistant_message, "timestamp": datetime.now().isoformat()})
                        
                        return JSONResponse({
                            "response": assistant_message,
                            "model_used": settings.model,
                            "provider": settings.provider,
                            "agent_tag": f"[as {agent_tag} Agent]",
                            "sub_agent": {
                                "template": detected_template,
                                "task_id": task_id,
                                "used": True
                            }
                        })
                        
                except TimeoutError:
                    # Sub-agent is taking too long, continue with main agent
                    pass
                except Exception as e:
                    print(f"Sub-agent spawn error: {e}")
                    # Continue with main agent on error
                    pass
        
        # ============================================
        # COMMAND INTERCEPTOR
        # Handle special commands before sending to LLM
        # ============================================
        
        # /consolidate or /consolidate --preview - Handle memory consolidation
        consolidate_match = re.match(r'^/consolidate(\s+--preview)?$', user_message.strip(), re.IGNORECASE)
        if consolidate_match:
            is_preview = bool(consolidate_match.group(1))
            
            try:
                from core.cognitive_memory import CognitiveMemoryManager, MemoryDecayCalculator
                manager = CognitiveMemoryManager()
                
                # Get current session ID - MUST have a valid session
                session_id = current_session.id if current_session else None
                
                if not session_id:
                    return JSONResponse({
                        "response": "⚠️ **Nenhuma sessão ativa**\n\nInicie uma conversa primeiro antes de consolidar memórias.",
                        "command": "consolidate",
                        "error": "no_session"
                    })
                
                # Check if current session has any messages
                if not web_messages or len(web_messages) == 0:
                    return JSONResponse({
                        "response": f"📭 **Sessão vazia**\n\nSua sessão atual (`{session_id}`) não tem mensagens para consolidar.\n\nEnvie algumas mensagens primeiro antes de usar `/consolidate`.",
                        "command": "consolidate",
                        "session_id": session_id,
                        "error": "empty_session"
                    })
                
                # Count memories FROM THIS SESSION ONLY
                memories_before = [
                    m for m in manager.episodic_memories 
                    if m.session_id == session_id
                ]
                total_before = len(memories_before)
                
                if total_before == 0:
                    return JSONResponse({
                        "response": f"📭 **Nenhuma memória nesta sessão**\n\nSua sessão atual (`{session_id}`) ainda não tem memórias episódicas registradas.\n\nConverse mais com o agente sobre tópicos técnicos para criar memórias.",
                        "command": "consolidate",
                        "session_id": session_id,
                        "error": "no_memories"
                    })
                
                # Calculate which memories would be consolidated (preview logic)
                calculator = MemoryDecayCalculator()
                preview_list = []
                
                for memory in memories_before:
                    # Same criteria as actual consolidation
                    substantial = len(memory.user_message) > 50 and len(memory.assistant_message) > 100
                    has_real_tech = bool(memory.technologies and len(memory.technologies) > 0)
                    has_companies = any('company_' in e for e in memory.entities_involved)
                    rich_content = len(memory.topics or []) >= 2
                    
                    score = (
                        (memory.importance >= 0.7) + 
                        (memory.successful and substantial) + 
                        (has_real_tech or has_companies) + 
                        (memory.sentiment >= 4) +
                        rich_content
                    )
                    
                    would_consolidate = score >= 3 or memory.importance >= 0.9
                    
                    preview_list.append({
                        "memory": memory,
                        "score": score,
                        "would_consolidate": would_consolidate,
                        "criteria_met": {
                            "importance": memory.importance >= 0.7,
                            "substantial": substantial,
                            "tech_or_company": has_real_tech or has_companies,
                            "sentiment": memory.sentiment >= 4,
                            "rich_content": rich_content
                        }
                    })
                
                would_count = sum(1 for p in preview_list if p["would_consolidate"])
                
                # PREVIEW MODE - Show what would happen without doing it
                if is_preview:
                    response = f"""👁️ **PRÉVIA DA CONSOLIDAÇÃO**

📊 **Sessão:** `{session_id}`
• Total de memórias: {total_before}
• Seriam consolidadas: {would_count}
• Taxa de aprovação: {would_count/total_before*100:.0f}%

**Critérios (mínimo 3 de 5 ou importância ≥ 0.9):**
"""
                    for i, p in enumerate(preview_list[:5], 1):
                        m = p["memory"]
                        status = "✅" if p["would_consolidate"] else "❌"
                        response += f"\n{i}. {status} **{m.summary[:50]}...**"
                        response += f"\n   📊 Score: {p['score']}/5 | Importância: {m.importance}"
                        if p["would_consolidate"]:
                            response += f"\n   📌 Techs: {', '.join(m.technologies[:3]) or 'N/A'}"
                    
                    if len(preview_list) > 5:
                        response += f"\n\n... e mais {len(preview_list) - 5} memórias"
                    
                    response += f"\n\n💡 Para executar a consolidação real, use `/consolidate` (sem --preview)"
                    
                    return JSONResponse({
                        "response": response,
                        "command": "consolidate",
                        "preview": True,
                        "would_consolidate": would_count,
                        "total": total_before
                    })
                
                # ACTUAL CONSOLIDATION
                consolidated = manager.consolidate_memories(
                    session_id=session_id,
                    importance_threshold=0.7
                )
                
                if len(consolidated) == 0:
                    return JSONResponse({
                        "response": f"📭 **Nenhuma memória para consolidar**\n\nAnalisei {total_before} memórias, mas nenhuma atingiu o critério de importância (threshold: 0.7).\n\n**Critérios usados (mínimo 3 de 5):**\n• Importância ≥ 0.7\n• Conteúdo substancial (>50 chars user, >100 assistant)\n• Tecnologias ou empresas identificadas\n• Sentimento positivo (≥4)\n• Tópicos ricos (≥2)\n\n_Tente ter conversas mais técnicas ou específicas sobre tecnologias, arquitetura, ou decisões importantes._",
                        "command": "consolidate",
                        "total_checked": total_before
                    })
                
                # Build detailed response
                response = f"""✅ **Consolidação concluída!**

📊 **Resumo da sessão atual ({session_id}):**
• {len(consolidated)} de {total_before} memórias consolidadas
• Threshold de importância: 0.7
• ⚠️ Apenas memórias desta sessão foram analisadas

**Critérios usados (mínimo 3 de 5 ou importância ≥ 0.9):**
✓ Importância ≥ 0.7
✓ Conteúdo substancial (>50/100 chars)
✓ Tecnologias/empresas identificadas
✓ Sentimento positivo (≥4)
✓ Tópicos ricos (≥2)

🧠 **Memórias consolidadas:**
"""
                
                for i, mem in enumerate(consolidated[:5], 1):
                    response += f"\n{i}. **{mem.summary[:60]}...**"
                    response += f"\n   📌 Importância: {mem.importance} | Techs: {', '.join(mem.technologies[:3]) or 'N/A'}"
                    if mem.entities_involved:
                        response += f"\n   🔗 Entidades: {len(mem.entities_involved)}"
                
                if len(consolidated) > 5:
                    response += f"\n\n... e mais {len(consolidated) - 5} memórias"
                
                response += "\n\n💡 As memórias consolidadas agora fazem parte da memória de longo prazo e serão usadas para contexto futuro."
                
                return JSONResponse({
                    "response": response,
                    "command": "consolidate",
                    "consolidated": len(consolidated),
                    "total_checked": total_before,
                    "memories": [{"id": m.memory_id, "summary": m.summary, "importance": m.importance} for m in consolidated[:5]]
                })
            except Exception as e:
                import traceback
                print(f"Consolidate error: {e}\n{traceback.format_exc()}")
                return JSONResponse({
                    "response": f"❌ **Erro na consolidação:** {str(e)}",
                    "command": "consolidate",
                    "error": str(e)
                })
        
        # /decay - Show memory decay analysis
        if user_message.strip().lower() == "/decay":
            try:
                from core.cognitive_memory import CognitiveMemoryManager
                manager = CognitiveMemoryManager()
                
                episodes = manager.get_episodic_memories(include_archived=True)
                
                if not episodes:
                    return JSONResponse({
                        "response": "📭 Nenhuma memória encontrada para análise de decay.",
                        "command": "decay"
                    })
                
                # Calculate decay stats
                from core.cognitive_memory import MemoryDecayCalculator
                calculator = MemoryDecayCalculator()
                
                stats = {
                    "total": len(episodes),
                    "high_strength": sum(1 for ep in episodes if calculator.calculate_episodic_strength(ep) > 0.7),
                    "low_strength": sum(1 for ep in episodes if calculator.calculate_episodic_strength(ep) < 0.3),
                    "archived": sum(1 for ep in episodes if ep.archived),
                    "avg_strength": sum(calculator.calculate_episodic_strength(ep) for ep in episodes) / len(episodes)
                }
                
                return JSONResponse({
                    "response": f"📊 **Análise de Decay de Memórias**\n\n🧠 Total: {stats['total']} memórias\n💪 Alta força (>0.7): {stats['high_strength']}\n😴 Baixa força (<0.3): {stats['low_strength']}\n📦 Arquivadas: {stats['archived']}\n📈 Força média: {stats['avg_strength']:.2f}",
                    "command": "decay",
                    "stats": stats
                })
            except Exception as e:
                return JSONResponse({
                    "response": f"❌ **Erro na análise:** {str(e)}",
                    "command": "decay",
                    "error": str(e)
                })
        
        # /search <term> - Semantic search
        search_match = re.match(r'^/search\s+(.+)$', user_message.strip(), re.IGNORECASE)
        if search_match:
            query = search_match.group(1).strip()
            try:
                from core.cognitive_memory import CognitiveMemoryManager
                manager = CognitiveMemoryManager()
                
                results = manager.semantic_search(query, top_k=5)
                
                if not results:
                    return JSONResponse({
                        "response": f"🔍 **Busca: '{query}'**\n\nNenhuma memória encontrada.",
                        "command": "search",
                        "query": query
                    })
                
                response = f"🔍 **Busca semântica: '{query}'**\n\n"
                for i, r in enumerate(results[:3], 1):
                    response += f"{i}. {r.get('summary', 'N/A')[:80]}... (similaridade: {r.get('similarity', 0):.2f})\n"
                
                return JSONResponse({
                    "response": response,
                    "command": "search",
                    "query": query,
                    "results": results
                })
            except Exception as e:
                return JSONResponse({
                    "response": f"❌ **Erro na busca:** {str(e)}",
                    "command": "search",
                    "error": str(e)
                })
        
        # /related <id> - Find related memories
        related_match = re.match(r'^/related\s+(\S+)$', user_message.strip(), re.IGNORECASE)
        if related_match:
            memory_id = related_match.group(1).strip()
            try:
                from core.cognitive_memory import CognitiveMemoryManager
                manager = CognitiveMemoryManager()
                
                related = manager.find_related_memories(memory_id, top_k=5)
                
                if not related:
                    return JSONResponse({
                        "response": f"🔗 **Memórias relacionadas a: {memory_id}**\n\nNenhuma memória relacionada encontrada.",
                        "command": "related",
                        "memory_id": memory_id
                    })
                
                response = f"🔗 **Relacionadas a: {memory_id}**\n\n"
                for i, r in enumerate(related[:3], 1):
                    response += f"{i}. {r.get('summary', 'N/A')[:80]}...\n"
                
                return JSONResponse({
                    "response": response,
                    "command": "related",
                    "memory_id": memory_id,
                    "related": related
                })
            except Exception as e:
                return JSONResponse({
                    "response": f"❌ **Erro:** {str(e)}",
                    "command": "related",
                    "error": str(e)
                })
        
        # Add user message to session
        web_messages.append({"sender": "user", "text": user_message, "timestamp": datetime.now().isoformat()})
        
        # Check if we should do web search
        web_search_results = None
        if web_search_tool:
            should_search, search_query = should_use_web_search(user_message)
            if should_search:
                print(f"🔍 Web search triggered: {search_query}", flush=True)
                try:
                    # Check if it's a weather query
                    if "weather" in search_query.lower():
                        # Extract location
                        location_match = re.search(r'weather\s+(?:in|at|for)?\s*(.+)', search_query, re.I)
                        if location_match:
                            location = location_match.group(1).strip()
                            weather_data = web_search_tool.get_current_weather(location)
                            if "error" not in weather_data:
                                web_search_results = f"""
[WEB SEARCH - CURRENT WEATHER]
Location: {weather_data.get('location', location)}
Temperature: {weather_data.get('temperature', 'N/A')}
Conditions: {weather_data.get('description', 'N/A')}
Humidity: {weather_data.get('humidity', 'N/A')}
Wind: {weather_data.get('wind', 'N/A')}
Source: {weather_data.get('source', 'web search')}
"""
                    
                    # General web search if no weather results
                    if not web_search_results:
                        results = web_search_tool.search(search_query, num_results=5)
                        if results:
                            web_search_results = web_search_tool.format_results_for_llm(results)
                    
                    print(f"✅ Web search completed", flush=True)
                except Exception as e:
                    print(f"⚠️ Web search failed: {e}", flush=True)
        
        # Build messages for the provider
        messages = []
        
        # Add system context if available
        config = load_config()
        default_agent_name = config.get("agent", {}).get("name", "Assistant")
        agent_name = default_agent_name
        
        # Try to load SOUL.md for personality
        # Check if session has a specific template
        soul_loaded = False
        print(f"DEBUG: Session template = {getattr(current_session, 'template', 'None')}")
        
        if current_session and hasattr(current_session, 'template') and current_session.template and current_session.template != "default":
            # Try to load template-specific SOUL
            template_soul_path = Path(f"/app/templates/{current_session.template}/SOUL.md")
            print(f"DEBUG: Trying path 1: {template_soul_path}, exists = {template_soul_path.exists()}")
            if not template_soul_path.exists():
                template_soul_path = Path(f"./templates/{current_session.template}/SOUL.md")
                print(f"DEBUG: Trying path 2: {template_soul_path}, exists = {template_soul_path.exists()}")
            
            if template_soul_path.exists():
                try:
                    soul_content = template_soul_path.read_text()
                    print(f"DEBUG: Loaded SOUL from {template_soul_path}")
                    # Use template name as agent name (capitalized)
                    template_agent_name = current_session.template.capitalize()
                    agent_name = template_agent_name
                    
                    # Replace template variables
                    soul_content = soul_content.replace("{{agent_name}}", agent_name)
                    soul_content = soul_content.replace("{{created_date}}", current_session.created_at[:10] if current_session else "today")
                    system_msg = f"{soul_content}\n\nYou are {agent_name}."
                    soul_loaded = True
                    print(f"DEBUG: soul_loaded = True, agent_name = {agent_name}")
                except Exception as e:
                    print(f"Warning: Could not load template SOUL: {e}")
            else:
                print(f"DEBUG: Template SOUL not found")
        
        if not soul_loaded:
            system_msg = f"You are {agent_name}, a helpful AI assistant."
            print(f"DEBUG: Using default system_msg")
        
        # Fallback to default SOUL.md (only if no template specified)
        if not soul_loaded and (not current_session or not getattr(current_session, 'template', None) or current_session.template == "default"):
            soul_path = Path("/app/workspace/SOUL.md")
            if not soul_path.exists():
                soul_path = Path("./workspace/SOUL.md")
            if soul_path.exists():
                try:
                    soul_content = soul_path.read_text()
                    system_msg = f"{soul_content}\n\nYou are {agent_name}."
                    print(f"DEBUG: Loaded default SOUL from {soul_path}")
                except Exception as e:
                    print(f"DEBUG: Could not load default SOUL: {e}")
        
        # Load USER.md for user context
        user_md_content = None
        user_md_paths = [Path("/app/workspace/USER.md"), Path("./workspace/USER.md")]
        for user_md_path in user_md_paths:
            if user_md_path.exists():
                try:
                    user_md_content = user_md_path.read_text()
                    print(f"DEBUG: Loaded USER.md from {user_md_path}")
                    break
                except Exception as e:
                    print(f"DEBUG: Could not load USER.md from {user_md_path}: {e}")
        
        if user_md_content:
            system_msg += f"\n\n[USER PROFILE]\n{user_md_content}\n[END USER PROFILE]"
        
        # Add file upload instructions if there's an attachment
        if '[Attached file:' in user_message or '[📎' in user_message:
            system_msg += "\n\n[CRITICAL SYSTEM NOTE: The user has uploaded a file. The file IS ALREADY SAVED in the system. The file content is shown below. DO NOT explain storage solutions or say you cannot store files. Simply acknowledge receipt and process/analyze the content as requested.]"
        
        # Add web search capability note
        if web_search_tool:
            system_msg += "\n\n[CAPABILITY: You have access to real-time web search. Use the search results provided to answer questions about current events, weather, news, etc.]"
        
        # Add web search results to system msg if available
        if web_search_results:
            system_msg += "\n\n[WEB SEARCH RESULTS]\n" + web_search_results
        
        # Build conversation messages (without system message - passed separately)
        messages = []
        
        # Add ALL conversation history - NO MESSAGE LIMIT
        # Only limited by model's max_tokens
        for msg in web_messages:
            role = "user" if msg["sender"] == "user" else "assistant"
            messages.append({"role": role, "content": msg["text"]})
        
        # Use override provider/model if provided, otherwise use settings
        chat_provider = override_provider or settings.provider
        chat_model = override_model or settings.model
        
        # Get response from the configured provider
        print(f"🤖 Chat: provider={chat_provider}, model={chat_model}, temp={settings.temperature}, max_tokens={settings.max_tokens}", flush=True)
        
        try:
            assistant_message = await chat_with_provider(
                provider=chat_provider,
                model=chat_model,
                messages=messages,
                system=system_msg,
                temperature=settings.temperature,
                max_tokens=settings.max_tokens
            )
            print(f"✅ Response received from {chat_model}", flush=True)
        except Exception as provider_error:
            # Fallback to Kimi Agent if direct provider fails
            try:
                async with httpx.AsyncClient(timeout=60.0) as client:
                    response = await client.post(
                        f"{KIMI_AGENT_URL}/chat",
                        json={
                            "user_id": "web_user",
                            "message": user_message,
                            "context": {
                                "template": current_session.template if current_session else None,
                                "username": user_name
                            }
                        }
                    )
                    if response.status_code == 200:
                        data = response.json()
                        assistant_message = data.get("response", "")
                    else:
                        raise Exception(f"Kimi Agent error: {response.status_code}")
            except:
                raise provider_error
        
        # Add assistant message to session
        web_messages.append({"sender": "assistant", "text": assistant_message, "timestamp": datetime.now().isoformat()})
        
        # Extract important facts from this exchange (like IDE agents do)
        if CONTEXT_MANAGER_AVAILABLE and current_session:
            try:
                session_id = current_session.id
                if session_id not in session_context_managers:
                    # No message limit - pass 0 for unlimited
                    session_context_managers[session_id] = SessionContextManager(
                        session_id, 
                        max_messages=0  # 0 = unlimited
                    )
                
                context_mgr = session_context_managers[session_id]
                facts = context_mgr.add_exchange(user_message, assistant_message)
                
                if facts:
                    print(f"✅ Extracted {len(facts)} facts from conversation", flush=True)
            except Exception as e:
                print(f"⚠️  Could not extract facts: {e}", flush=True)
        
        # Semantic Memory Analysis - Learn from this interaction
        try:
            from core.semantic_memory import SemanticMemoryExtractor, get_semantic_memory_store
            
            context = {"session_id": current_session.id if current_session else "unknown"}
            memory = SemanticMemoryExtractor.analyze_conversation_exchange(
                user_message, assistant_message, context
            )
            
            if memory:
                store = get_semantic_memory_store()
                store.add_memory(memory)
                print(f"🧠 Created semantic memory: {memory.interaction_type} (sentiment: {memory.sentiment}/5)", flush=True)
        except Exception as e:
            print(f"⚠️  Could not create semantic memory: {e}", flush=True)
        
        # Cognitive Memory - Store in episodic + semantic + procedural
        try:
            from core.cognitive_memory import get_cognitive_memory_manager
            
            # Detect sentiment from user message
            sentiment = 3  # Neutral default
            user_lower = user_message.lower()
            if any(w in user_lower for w in ["excelente", "perfeito", "ótimo", "great", "perfect", "amazing"]):
                sentiment = 5
            elif any(w in user_lower for w in ["bom", "good", "funcionou", "works", "thanks", "obrigado"]):
                sentiment = 4
            elif any(w in user_lower for w in ["ruim", "bad", "não funcionou", "not working"]):
                sentiment = 2
            
            manager = get_cognitive_memory_manager()
            episode = manager.store_interaction(
                user_message=user_message,
                assistant_message=assistant_message,
                session_id=current_session.id if current_session else "unknown",
                sentiment=sentiment,
                successful=(sentiment >= 3)
            )
            
            print(f"🧠 Cognitive memory stored: {len(episode.entities_involved)} entities, topics: {episode.topics}", flush=True)
        except Exception as e:
            print(f"⚠️  Could not store cognitive memory: {e}", flush=True)
        
        # Auto-save session if enabled
        if settings.auto_save and current_session:
            current_session.messages = web_messages
            current_session.message_count = len(web_messages)
            current_session.updated_at =datetime.now().isoformat()
            save_session(current_session)
        
        return JSONResponse({
            "response": assistant_message,
            "model_used": chat_model,
            "provider": chat_provider
        })
                
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# ============================================================================
# PERSISTENCE FUNCTIONS
# ============================================================================

DATA_DIR = Path("/app/workspace/web_ui_data")
DATA_DIR.mkdir(parents=True, exist_ok=True)

SETTINGS_FILE = DATA_DIR / "settings.json"
SESSIONS_DIR = DATA_DIR / "sessions"
SESSIONS_DIR.mkdir(exist_ok=True)
CURRENT_SESSION_FILE = DATA_DIR / "current_session.json"

def load_settings() -> Settings:
    """Load settings from file with fallback to init.yaml."""
    s = Settings()
    if SETTINGS_FILE.exists():
        try:
            with open(SETTINGS_FILE) as f:
                data = json.load(f)
                s = Settings(**data)
        except Exception:
            pass
            
    # Fallback/Sync with init.yaml for credentials
    try:
        init_paths = [Path("init.yaml"), Path("/app/init.yaml"), Path("/app/workspace/init.yaml")]
        for path in init_paths:
            if path.exists():
                with open(path) as f:
                    config = yaml.safe_load(f) or {}
                
                tg = config.get("mode", {}).get("telegram", {})
                if not s.telegram_token:
                    s.telegram_token = tg.get("token") or tg.get("bot_token") or ""
                if not s.telegram_chat_ids:
                    cid = tg.get("allowed_chat_ids") or tg.get("user_id")
                    if cid:
                        s.telegram_chat_ids = cid if isinstance(cid, list) else [str(cid)]
                if not s.telegram_enabled and tg.get("enabled"):
                    s.telegram_enabled = True
                
                # Also fallback for LLM provider if missing
                if not s.provider and config.get("provider", {}).get("name"):
                    s.provider = config["provider"]["name"]
                break
    except Exception as e:
        print(f"Note: Could not fallback to init.yaml: {e}")
        
    return s

def update_init_yaml_settings(settings: Settings):
    """Sync all settings with init.yaml."""
    init_paths = [
        Path("/app/init.yaml"),
        Path("/app/workspace/init.yaml"),
        Path("./init.yaml"),
        Path("../init.yaml")
    ]
    
    for path in init_paths:
        if path.exists():
            try:
                with open(path) as f:
                    config = yaml.safe_load(f) or {}
                
                # Update LLM defaults
                if "defaults" not in config: config["defaults"] = {}
                config["defaults"]["provider"] = settings.provider
                config["defaults"]["model"] = settings.model
                
                # Update Telegram
                if "mode" not in config: config["mode"] = {}
                if "telegram" not in config["mode"]: config["mode"]["telegram"] = {}
                
                config["mode"]["telegram"]["enabled"] = settings.telegram_enabled
                if settings.telegram_token:
                    config["mode"]["telegram"]["token"] = settings.telegram_token
                    config["mode"]["telegram"]["bot_token"] = settings.telegram_token # For compatibility
                if settings.telegram_chat_ids:
                    config["mode"]["telegram"]["allowed_chat_ids"] = settings.telegram_chat_ids
                    config["mode"]["telegram"]["user_id"] = settings.telegram_chat_ids[0] if settings.telegram_chat_ids else "" # For compatibility
                
                # Save back
                with open(path, 'w') as f:
                    yaml.dump(config, f, sort_keys=False, default_flow_style=False)
                
                print(f"✅ Synced settings to {path}")
                return True
            except Exception as e:
                print(f"⚠️ Failed to sync init.yaml at {path}: {e}")
    return False

def save_settings(settings: Settings):
    """Save settings to file and sync with init.yaml."""
    with open(SETTINGS_FILE, 'w') as f:
        json.dump(settings.dict(), f, indent=2)
    
    # Sync with init.yaml
    update_init_yaml_settings(settings)

def load_sessions() -> List[Session]:
    """Load all saved sessions."""
    sessions = []
    if SESSIONS_DIR.exists():
        for session_file in SESSIONS_DIR.glob("*.json"):
            try:
                with open(session_file) as f:
                    sessions.append(Session(**json.load(f)))
            except:
                pass
    return sorted(sessions, key=lambda s: s.updated_at, reverse=True)

def load_session(session_id: str) -> Optional[Session]:
    """Load a specific session."""
    session_file = SESSIONS_DIR / f"{session_id}.json"
    if session_file.exists():
        try:
            with open(session_file) as f:
                return Session(**json.load(f))
        except:
            pass
    return None

def save_session(session: Session):
    """Save a session to file."""
    session_file = SESSIONS_DIR / f"{session.id}.json"
    with open(session_file, 'w') as f:
        json.dump(session.dict(), f, indent=2, default=str)

def delete_session(session_id: str):
    """Delete a session."""
    session_file = SESSIONS_DIR / f"{session_id}.json"
    if session_file.exists():
        session_file.unlink()

def create_session(name: str = None, template: str = "default") -> Session:
    """Create a new session."""
    now = datetime.now().isoformat()
    session = Session(
        id=str(uuid.uuid4())[:8],
        name=name or f"Session {now[:10]}",
        created_at=now,
        updated_at=now,
        message_count=0,
        messages=[],
        template=template
        # context_limit REMOVED - no message limit
    )
    save_session(session)
    return session

# ============================================================================
# INITIALIZE
# ============================================================================

# In-memory message storage for the web session
web_messages = []
current_session: Optional[Session] = None

# Load settings
settings = load_settings()

# Load or create current session
if CURRENT_SESSION_FILE.exists():
    try:
        with open(CURRENT_SESSION_FILE) as f:
            current_id = json.load(f).get("current_session_id")
            if current_id:
                current_session = load_session(current_id)
    except:
        pass

if not current_session:
    current_session = create_session("Current Session")

# Initialize hybrid memory store
hybrid_memory = None
if HYBRID_AVAILABLE:
    try:
        db_path = "/app/workspace/memory/agent_memory.db"
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        hybrid_memory = HybridMemoryStore(db_path)
        print(f"✅ Hybrid memory initialized: {db_path}")
    except Exception as e:
        print(f"⚠️  Hybrid memory init failed: {e}")


@app.post("/api/compact")
async def compact_context(request: Request):
    """Analyze conversation, extract key facts, save to hybrid memory (SQLite + Graph)."""
    global web_messages, hybrid_memory, current_session
    
    if not web_messages:
        return JSONResponse({"message": "No messages to compact", "facts_extracted": 0})
    
    try:
        # Extract key information from the conversation
        facts = extract_important_facts(web_messages)
        
        # Save facts to hybrid memory (both SQLite and Graph)
        saved_count = 0
        if hybrid_memory:
            for fact in facts:
                try:
                    hybrid_memory.store(
                        content=fact,
                        category="conversation_fact",
                        importance="high",
                        metadata={
                            "source": "web_ui_compact",
                            "timestamp": str(datetime.now()),
                            "facts": len(facts)
                        }
                    )
                    saved_count += 1
                except Exception as e:
                    print(f"Failed to store fact: {e}")
        else:
            # Fallback: try to save via Kimi Agent
            async with httpx.AsyncClient(timeout=30.0) as client:
                for fact in facts:
                    try:
                        await client.post(
                            f"{KIMI_AGENT_URL}/api/memory/store",
                            json={
                                "user_id": "web_user",
                                "content": fact,
                                "category": "conversation_fact",
                                "importance": "high"
                            },
                            timeout=5.0
                        )
                        saved_count += 1
                    except:
                        pass
        
        # Also save to graph if available (for relationships)
        if hybrid_memory and hybrid_memory.graph_available:
            # Create relationships between facts and topics
            for i, fact in enumerate(facts):
                # Link related facts
                if i > 0:
                    try:
                        # This creates RELATED_TO edges in the graph
                        pass  # Graph sync happens automatically on store
                    except:
                        pass
        
        # Clear web session messages and update session
        message_count = len(web_messages)
        web_messages = []
        
        if current_session:
            current_session.messages = []
            current_session.message_count = 0
            current_session.updated_at = datetime.now().isoformat()
            save_session(current_session)
        
        # Get memory stats
        memory_stats = {}
        if hybrid_memory:
            try:
                memory_stats = hybrid_memory.get_stats()
            except:
                pass
        
        return JSONResponse({
            "message": "Context compacted successfully",
            "messages_processed": message_count,
            "facts_extracted": len(facts),
            "facts_saved": saved_count,
            "facts": facts,
            "memory_stats": memory_stats
        })
        
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


def extract_important_facts(messages):
    """Extract important facts from conversation history."""
    facts = []
    
    # Keywords that indicate important information
    preference_keywords = ["prefiro", "prefer", "gosto de", "like to", "não gosto", "don't like", 
                          "sempre uso", "always use", "nunca uso", "never use"]
    decision_keywords = ["decidi", "decided", "vamos usar", "let's use", "escolhi", "chose",
                        "vou usar", "will use", "adotar", "adopt"]
    info_keywords = ["meu nome é", "my name is", "eu sou", "i am", "trabalho com", "work with",
                    "minha empresa", "my company", "projeto", "project"]
    
    user_messages = [m["text"] for m in messages if m["sender"] == "user"]
    
    for msg in user_messages:
        msg_lower = msg.lower()
        
        # Check for preferences
        if any(kw in msg_lower for kw in preference_keywords):
            facts.append(f"Preference: {msg[:200]}")
        
        # Check for decisions
        elif any(kw in msg_lower for kw in decision_keywords):
            facts.append(f"Decision: {msg[:200]}")
        
        # Check for personal/professional info
        elif any(kw in msg_lower for kw in info_keywords):
            facts.append(f"Info: {msg[:200]}")
    
    # If no specific facts found, create a summary
    if not facts and len(user_messages) > 0:
        facts.append(f"Conversation about: {user_messages[0][:100]}...")
    
    return facts[:5]  # Max 5 facts


# ============================================================================
# PROVIDERS SETUP
# ============================================================================

# Provider clients
provider_clients = {}

def get_kimi_client():
    """Initialize Kimi client."""
    api_key = os.getenv("KIMI_API_KEY", "")
    if not api_key:
        return None
    try:
        from anthropic import Anthropic
        return Anthropic(api_key=api_key, base_url="https://api.kimi.com/coding")
    except:
        return None

def get_anthropic_client():
    """Initialize Anthropic client."""
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        return None
    try:
        from anthropic import Anthropic
        return Anthropic(api_key=api_key)
    except:
        return None

def get_openai_client():
    """Initialize OpenAI client."""
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        return None
    try:
        from openai import OpenAI
        return OpenAI(api_key=api_key)
    except:
        return None

def get_openrouter_client():
    """Initialize OpenRouter client."""
    api_key = os.getenv("OPENROUTER_API_KEY", "")
    if not api_key:
        return None
    try:
        from openai import OpenAI
        return OpenAI(
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1"
        )
    except:
        return None

async def chat_with_provider(provider: str, model: str, messages: list, system: str, temperature: float, max_tokens: int):
    """Send chat completion request to the selected provider using shared router."""
    if LLM_ROUTER_AVAILABLE:
        try:
            return await chat_with_provider_shared(
                messages=messages,
                system=system,
                provider=provider,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens
            )
        except Exception as e:
            print(f"ERROR in shared llm_router: {e}")
            # Fallback to local implementation if shared fails
            pass

    # Local implementation fallback (legacy logic)
    try:
        from llm_router import _fallback_chat
        return await _fallback_chat(provider, model, messages, system, temperature, max_tokens)
    except Exception as e:
        print(f"ERROR in fallback: {e}")
        raise

# ============================================================================
# SETTINGS & SESSIONS API
# ============================================================================

@app.get("/api/settings")
async def get_settings():
    """Get current settings."""
    return JSONResponse(settings.dict())

@app.post("/api/settings")
async def update_settings(request: Request):
    """Update settings."""
    global settings
    try:
        data = await request.json()
        new_settings = Settings(**data)
        save_settings(new_settings)
        settings = new_settings
        return JSONResponse({"status": "ok", "settings": settings.dict()})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)

@app.get("/api/settings/providers")
async def get_providers():
    """Get available providers and models (only those with API keys)."""
    # Check which providers are available
    available = {
        "kimi": os.getenv("KIMI_API_KEY") is not None,
        "anthropic": os.getenv("ANTHROPIC_API_KEY") is not None,
        "openai": os.getenv("OPENAI_API_KEY") is not None,
        "google": os.getenv("GOOGLE_API_KEY") is not None,
        "openrouter": os.getenv("OPENROUTER_API_KEY") is not None,
        "custom": os.getenv("CUSTOM_API_KEY") is not None or os.getenv("CUSTOM_BASE_URL") is not None
    }
    
    # Always include the current provider from settings (even if env var not set yet)
    if settings.provider and settings.provider not in available:
        available[settings.provider] = True
    elif settings.provider and not available.get(settings.provider):
        available[settings.provider] = True
    
    # Only include providers with API keys (or base URL for custom)
    enabled_providers = [p for p, enabled in available.items() if enabled]
    enabled_models = {p: PROVIDER_MODELS[p] for p in enabled_providers if PROVIDER_MODELS[p]}
    
    return JSONResponse({
        "providers": enabled_providers,  # Only enabled
        "models": enabled_models,  # Only enabled
        "all_providers": list(PROVIDER_MODELS.keys()),  # All for reference
        "all_models": PROVIDER_MODELS,  # All for reference
        "available": available,  # Status of each
        "modes": list(MODE_PRESETS.keys()),
        "mode_presets": MODE_PRESETS,
        "model_context_limits": MODEL_CONTEXT_LIMITS,
        "message": "Add API keys to .env to enable more providers" if len(enabled_providers) < 4 else None
    })

@app.get("/api/settings/provider/{provider}")
async def get_provider_settings(provider: str):
    """Get settings for a specific provider (e.g. if key is set)."""
    env_key = f"{provider.upper()}_API_KEY"
    if provider == "kimi":
        api_key = os.getenv("KIMI_API_KEY")
    elif provider == "anthropic":
        api_key = os.getenv("ANTHROPIC_API_KEY")
    elif provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY")
    elif provider == "google":
        api_key = os.getenv("GOOGLE_API_KEY")
    elif provider == "openrouter":
        api_key = os.getenv("OPENROUTER_API_KEY")
    else:
        api_key = os.getenv(env_key)
    
    # Hide key values but confirm they exist
    has_key = api_key is not None and api_key != ""
    
    # Custom base URL support
    base_url = ""
    if provider == "custom":
        base_url = os.getenv("CUSTOM_BASE_URL", "")
        
    return JSONResponse({
        "provider": provider,
        "has_key": has_key,
        "base_url": base_url,
        "current_model": settings.model if settings.provider == provider else None
    })


@app.post("/api/settings/mode/{mode}")
async def set_mode(mode: str):
    """Set mode preset (fast, balanced, deep)."""
    global settings
    if mode not in MODE_PRESETS:
        return JSONResponse({"error": f"Unknown mode: {mode}"}, status_code=400)
    
    preset = MODE_PRESETS[mode]
    settings.temperature = preset["temperature"]
    settings.max_tokens = get_max_tokens_for_model(settings.model, mode)
    settings.mode = mode
    save_settings(settings)
    return JSONResponse({"status": "ok", "settings": settings.dict()})

# Session endpoints
@app.get("/api/sessions")
async def get_sessions():
    """Get all saved sessions."""
    sessions = load_sessions()
    return JSONResponse([s.dict() for s in sessions])


def get_current_agent_info():
    """Get current agent info from workspace SOUL.md."""
    soul_paths = [
        Path("/app/workspace/SOUL.md"),
        Path("./workspace/SOUL.md"),
    ]
    
    for soul_path in soul_paths:
        if soul_path.exists():
            try:
                content = soul_path.read_text()
                # Extract name
                name_match = re.search(r'^# SOUL - (.+)$', content, re.MULTILINE)
                name = name_match.group(1).strip() if name_match else "Agent"
                
                # Extract role
                role_match = re.search(r'\*\*Role:\*\* (.+)$', content, re.MULTILINE)
                role = role_match.group(1).strip() if role_match else "AI Assistant"
                
                return {"name": name, "role": role}
            except Exception as e:
                print(f"Warning: Could not read SOUL.md: {e}")
    
    return {"name": "Agent", "role": "AI Assistant"}


@app.get("/api/agent/current")
async def get_current_agent():
    """Get current agent information."""
    return JSONResponse(get_current_agent_info())


@app.get("/api/templates")
async def get_templates():
    """Get available agent templates."""
    templates = get_available_templates()
    current_agent = get_current_agent_info()
    return JSONResponse({
        "templates": templates,
        "context_token_limits": CONTEXT_TOKEN_LIMITS,  # Token-based limits (0 = unlimited)
        "current_agent": current_agent
    })


@app.get("/api/templates/{template_id}/soul")
async def get_template_soul(template_id: str):
    """Get SOUL.md content for a specific template."""
    templates = get_available_templates()
    template = next((t for t in templates if t["id"] == template_id), None)
    
    if not template:
        return JSONResponse({"error": "Template not found"}, status_code=404)
    
    try:
        soul_content = Path(template["path"]).read_text()
        return JSONResponse({
            "template_id": template_id,
            "soul_content": soul_content
        })
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.post("/api/sessions")
async def create_new_session(request: Request):
    """Create a new session."""
    global current_session, web_messages
    try:
        data = await request.json()
        name = data.get("name", f"Session {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        template = data.get("template", "default")
        # context_limit REMOVED - no message limit
        
        # Save current session first
        if current_session:
            current_session.messages = web_messages
            current_session.message_count = len(web_messages)
            current_session.updated_at = datetime.now().isoformat()
            save_session(current_session)
        
        # Create new session with template (no message limit)
        current_session = create_session(name, template=template)
        web_messages = []
        
        # Save current session ID
        with open(CURRENT_SESSION_FILE, 'w') as f:
            json.dump({"current_session_id": current_session.id}, f)
        
        return JSONResponse({"status": "ok", "session": current_session.dict()})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/api/sessions/{session_id}")
async def get_session(session_id: str):
    """Get a specific session."""
    session = load_session(session_id)
    if session:
        return JSONResponse(session.dict())
    return JSONResponse({"error": "Session not found"}, status_code=404)

@app.post("/api/sessions/{session_id}/fork")
async def fork_session(session_id: str, request: Request):
    """Fork an existing session and start a new one with its context."""
    global current_session, web_messages
    try:
        data = await request.json()
        template = data.get("template", "default")
        
        # Load the source session
        source_session = load_session(session_id)
        if not source_session:
            return JSONResponse({"error": "Source session not found"}, status_code=404)
        
        # Save current session first if active
        if current_session:
            current_session.messages = web_messages
            current_session.message_count = len(web_messages)
            current_session.updated_at = datetime.now().isoformat()
            save_session(current_session)
            
        # Create new session
        import uuid
        fork_name = f"Fork: {source_session.name} -> {template.capitalize()}"
        current_session = create_session(fork_name, template=template)
        
        # Clone messages from source
        web_messages = source_session.messages.copy()
        
        # Add system cue to context
        web_messages.append({
            "role": "system",
            "content": f"[SYSTEM NOTIFICATION] Session forked from '{source_session.template}'. As a '{template}', please analyze the preceding context and assume your role to proceed with the specific tasks.",
            "timestamp": datetime.now().isoformat(),
            "id": str(uuid.uuid4())
        })
        
        current_session.messages = web_messages
        current_session.message_count = len(web_messages)
        save_session(current_session)
        
        # Save current session ID
        with open(CURRENT_SESSION_FILE, 'w') as f:
            json.dump({"current_session_id": current_session.id}, f)
            
        return JSONResponse({"status": "ok", "session": current_session.dict()})
        
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.post("/api/sessions/{session_id}/load")
async def load_session_endpoint(session_id: str):
    """Load a session as current."""
    global current_session, web_messages
    session = load_session(session_id)
    if not session:
        return JSONResponse({"error": "Session not found"}, status_code=404)
    
    # Save current session first
    if current_session:
        current_session.messages = web_messages
        current_session.message_count = len(web_messages)
        current_session.updated_at = datetime.now().isoformat()
        save_session(current_session)
    
    # Load new session
    current_session = session
    web_messages = session.messages.copy()
    
    # Save current session ID
    with open(CURRENT_SESSION_FILE, 'w') as f:
        json.dump({"current_session_id": current_session.id}, f)
    
    return JSONResponse({
        "status": "ok", 
        "session": current_session.dict(),
        "messages": web_messages
    })

@app.post("/api/sessions/{session_id}/rename")
async def rename_session_endpoint(session_id: str, request: Request):
    """Rename a session."""
    global current_session
    
    try:
        data = await request.json()
        new_name = data.get("name", "").strip()
        
        if not new_name:
            return JSONResponse({"error": "Name cannot be empty"}, status_code=400)
        
        # Load session
        session = load_session(session_id)
        if not session:
            return JSONResponse({"error": "Session not found"}, status_code=404)
        
        # Update name
        session.name = new_name
        session.updated_at = datetime.now().isoformat()
        save_session(session)
        
        # Update current session if it's the same
        if current_session and current_session.id == session_id:
            current_session.name = new_name
        
        return JSONResponse({"status": "ok", "session": session.dict()})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.delete("/api/sessions/{session_id}")
async def delete_session_endpoint(session_id: str):
    """Delete a session."""
    global current_session, web_messages
    
    if current_session and current_session.id == session_id:
        # Can't delete current session, create new one first
        current_session = create_session("Current Session")
        web_messages = []
        with open(CURRENT_SESSION_FILE, 'w') as f:
            json.dump({"current_session_id": current_session.id}, f)
    
    delete_session(session_id)
    return JSONResponse({"status": "ok"})


@app.get("/api/sessions/{session_id}/facts")
async def get_session_facts(session_id: str):
    """Get extracted facts for a session."""
    if not CONTEXT_MANAGER_AVAILABLE:
        return JSONResponse({"facts": [], "message": "Context manager not available"})
    
    try:
        if session_id not in session_context_managers:
            session_context_managers[session_id] = SessionContextManager(session_id)
        
        mgr = session_context_managers[session_id]
        facts = mgr.export_facts()
        
        return JSONResponse({
            "facts": facts,
            "count": len(facts),
            "summary": mgr.get_facts_summary()
        })
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/api/sessions/{session_id}/facts/clear")
async def clear_session_facts(session_id: str):
    """Clear extracted facts for a session."""
    if not CONTEXT_MANAGER_AVAILABLE:
        return JSONResponse({"message": "Context manager not available"})
    
    try:
        if session_id in session_context_managers:
            session_context_managers[session_id].clear_facts()
        
        return JSONResponse({"status": "ok", "message": "Facts cleared"})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/api/sessions/{session_id}/facts/store")
async def store_facts_to_memory(session_id: str, request: Request):
    """Store selected facts to long-term memory (Hybrid Memory)."""
    try:
        data = await request.json()
        facts = data.get("facts", [])
        
        if not facts:
            return JSONResponse({"error": "No facts provided"}, status_code=400)
        
        stored_count = 0
        
        # Store to hybrid memory if available
        if HYBRID_AVAILABLE:
            memory = HybridMemoryStore()
            for fact in facts:
                memory.remember(
                    content=f"[{fact['category'].upper()}] {fact['content']}",
                    source=f"session:{session_id}",
                    importance=0.8,
                    metadata={
                        "category": fact["category"],
                        "timestamp": fact.get("timestamp"),
                        "type": "extracted_fact"
                    }
                )
                stored_count += 1
        else:
            # Fallback: save to a JSON file
            facts_file = WEB_UI_DATA / "stored_facts" / f"{session_id}.json"
            facts_file.parent.mkdir(parents=True, exist_ok=True)
            
            existing = []
            if facts_file.exists():
                with open(facts_file) as f:
                    existing = json.load(f)
            
            for fact in facts:
                fact["stored_at"] = datetime.now().isoformat()
                existing.append(fact)
            
            with open(facts_file, 'w') as f:
                json.dump(existing, f, indent=2)
            
            stored_count = len(facts)
        
        return JSONResponse({
            "status": "ok",
            "stored": stored_count,
            "message": f"Stored {stored_count} facts to long-term memory"
        })
    except Exception as e:
        import traceback
        return JSONResponse({"error": str(e), "traceback": traceback.format_exc()}, status_code=500)


# ============================================================================
# CONTEXT COMPACTOR API
# ============================================================================

@app.get("/api/sessions/{session_id}/context/analyze")
async def analyze_session_context(session_id: str, request: Request):
    """Analyze context and suggest compaction."""
    if not COMPACTOR_AVAILABLE:
        return JSONResponse({"message": "Context compactor not available"})
    
    try:
        # Check if full analysis requested
        full = request.query_params.get("full", "false").lower() == "true"
        
        session = load_session(session_id)
        if not session:
            return JSONResponse({"error": "Session not found"}, status_code=404)
        
        messages = session.messages
        if len(messages) < 3:
            return JSONResponse({
                "should_compact": False,
                "reason": "Not enough messages to analyze",
                "message_count": len(messages)
            })
        
        # Analyze importance for all messages
        importance_scores = []
        for i, msg in enumerate(messages):
            imp = ContextAnalyzer.analyze_importance(msg, messages)
            imp_dict = imp.to_dict()
            imp_dict["role"] = msg.get("sender", "unknown")
            imp_dict["content"] = msg.get("text", "")[:200]  # Truncate for display
            importance_scores.append(imp_dict)
        
        # Check if should compact
        compactor = ContextCompactor()
        should_compact = compactor.should_compact(messages)
        
        # Get clusters (returns indices, not messages)
        clusters = ContextAnalyzer.cluster_messages(messages)
        
        # Extract topics from clusters
        topics = []
        for cluster in clusters[:5]:  # Top 5 clusters
            if len(cluster) > 0:
                # cluster contains indices, use them to get actual messages
                first_idx = cluster[0]
                if isinstance(first_idx, int) and 0 <= first_idx < len(messages):
                    first_msg = messages[first_idx].get("text", "")[:30]
                    if first_msg:
                        topics.append(first_msg + "...")
        
        # Extract decisions from messages
        decisions = []
        for msg in messages:
            text = msg.get("text", "").lower()
            if any(w in text for w in ["decidi", "decided", "vamos usar", "let's use", "escolhi", "chose"]):
                decisions.append(msg.get("text", "")[:50] + "...")
        
        # Estimate tokens
        total_text = " ".join(m.get("text", "") for m in messages)
        estimated_tokens = compactor.estimate_tokens(total_text)
        
        response = {
            "should_compact": should_compact,
            "message_count": len(messages),
            "estimated_tokens": estimated_tokens,
            "max_tokens": compactor.max_tokens,
            "clusters": len(clusters),
            "topics": topics,
            "decisions": decisions[:5],  # Top 5 decisions
            "importance_scores": importance_scores[-10:] if not full else [],  # Last 10 for simple view
            "top_important": sorted(importance_scores, key=lambda x: x["importance_score"], reverse=True)[:5]
        }
        
        # Full analysis includes all messages
        if full:
            response["all_messages"] = importance_scores
        
        return JSONResponse(response)
    except Exception as e:
        import traceback
        return JSONResponse({"error": str(e), "traceback": traceback.format_exc()}, status_code=500)


@app.post("/api/sessions/{session_id}/context/compact")
async def compact_session_context(session_id: str, request: Request):
    """Compact session context."""
    if not COMPACTOR_AVAILABLE:
        return JSONResponse({"message": "Context compactor not available"})
    
    try:
        data = await request.json()
        preserve_recent = data.get("preserve_recent", 5)
        force = data.get("force", False)
        message_indices = data.get("message_indices", None)  # Specific indices to compact
        
        global current_session, web_messages
        
        # Sync current session messages before compacting (in case auto-save is off)
        if current_session and current_session.id == session_id and web_messages:
            current_session.messages = web_messages
            current_session.message_count = len(web_messages)
            save_session(current_session)
        
        session = load_session(session_id)
        if not session:
            return JSONResponse({"error": "Session not found"}, status_code=404)
        
        messages = session.messages.copy()
        
        if not messages:
            return JSONResponse({"message": "No messages to compact", "original_count": 0, "new_count": 0})
        
        # Initialize compactor for this session
        if session_id not in session_compactors:
            session_compactors[session_id] = SessionContextCompactor(session_id)
        
        compactor = session_compactors[session_id]
        
        if message_indices:
            # Compact specific messages by indices
            selected_msgs = [messages[i] for i in message_indices if i < len(messages)]
            other_msgs = [m for i, m in enumerate(messages) if i not in message_indices]
            
            # Generate summary of selected messages
            from core.context_compactor import ContextAnalyzer
            summary = ContextAnalyzer._generate_summary(selected_msgs)
            
            # Create compacted message
            compacted_msg = {
                "sender": "system",
                "text": f"[Previous discussion summary]: {summary}",
                "timestamp": datetime.now().isoformat(),
                "compacted": True,
                "original_count": len(selected_msgs)
            }
            
            new_messages = [compacted_msg] + other_msgs
            sub_ctx = None
            
        elif force:
            new_messages, sub_ctx = compactor.force_compact(messages, preserve_recent)
        else:
            new_messages = compactor.check_and_compact(messages)
            sub_ctx = None
        
        # Update session
        session.messages = new_messages
        session.message_count = len(new_messages)
        save_session(session)
        
        # Update current session if active
        if current_session and current_session.id == session_id:
            web_messages = new_messages
            current_session = session
        
        result = {
            "status": "ok",
            "original_count": len(messages),
            "new_count": len(new_messages),
            "reduction": len(messages) - len(new_messages),
            "summary": f"Reduced from {len(messages)} to {len(new_messages)} messages",
            "stats": compactor.get_stats()
        }
        
        if sub_ctx:
            result["sub_context"] = sub_ctx.to_dict()
        
        return JSONResponse(result)
    except Exception as e:
        import traceback
        return JSONResponse({"error": str(e), "traceback": traceback.format_exc()}, status_code=500)


@app.delete("/api/sessions/{session_id}/messages")
async def delete_session_messages(session_id: str):
    """Delete all messages from a session (reset context)."""
    try:
        session = load_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Clear messages
        original_count = len(session.messages)
        session.messages = []
        session.message_count = 0
        save_session(session)
        
        # Update current session if active
        global current_session, web_messages
        if current_session and current_session.id == session_id:
            web_messages = []
            current_session = session
        
        return JSONResponse({
            "status": "ok",
            "deleted_count": original_count,
            "message": f"Deleted {original_count} messages"
        })
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        return JSONResponse({"error": str(e), "traceback": traceback.format_exc()}, status_code=500)


@app.get("/api/sessions/{session_id}/context/stats")
async def get_compaction_stats(session_id: str):
    """Get context compaction stats."""
    if not COMPACTOR_AVAILABLE:
        return JSONResponse({"message": "Context compactor not available"})
    
    try:
        if session_id not in session_compactors:
            return JSONResponse({
                "compactions_performed": 0,
                "message": "No compaction performed yet"
            })
        
        return JSONResponse(session_compactors[session_id].get_stats())
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

# ============================================================================
# SESSION MEMORY CONSOLIDATION API
# ============================================================================

@app.get("/api/sessions/{session_id}/consolidate/preview")
async def preview_consolidation(session_id: str):
    """Preview what would be consolidated for this session."""
    try:
        sys.path.insert(0, '/app/core')
        from cognitive_memory import get_cognitive_memory_manager
        
        manager = get_cognitive_memory_manager()
        preview = manager.get_consolidation_preview(session_id=session_id, importance_threshold=0.7)
        
        return JSONResponse({
            "status": "ok",
            "preview": preview
        })
        
    except Exception as e:
        print(f"Error generating preview: {e}")
        import traceback
        return JSONResponse({
            "status": "error",
            "error": str(e),
            "traceback": traceback.format_exc()
        }, status_code=500)


@app.post("/api/sessions/{session_id}/consolidate")
async def consolidate_session_memory(session_id: str):
    """Consolidate session's episodic memories into knowledge graph."""
    try:
        # Import cognitive memory modules
        sys.path.insert(0, '/app/core')
        from cognitive_memory import get_cognitive_memory_manager
        
        # Get the cognitive memory manager
        manager = get_cognitive_memory_manager()
        
        # Get preview first for accurate stats
        preview = manager.get_consolidation_preview(session_id=session_id, importance_threshold=0.6)
        
        if preview["candidates_count"] == 0:
            return JSONResponse({
                "status": "ok",
                "facts_analyzed": preview["total_memories"],
                "facts_stored": 0,
                "entities_extracted": 0,
                "message": "No relevant memories found to consolidate in this session"
            })
        
        # Perform consolidation ONLY for this session
        consolidated = manager.consolidate_memories(session_id=session_id, importance_threshold=0.7)
        
        return JSONResponse({
            "status": "ok",
            "facts_analyzed": preview["total_memories"],
            "facts_stored": len(consolidated),
            "unique_entities": preview["unique_entities"]["total_unique"],
            "technologies": preview["unique_entities"]["technologies"],
            "topics": preview["unique_entities"]["topics"],
            "message": f"Consolidated {len(consolidated)} of {preview['total_memories']} memories from this session"
        })
        
    except Exception as e:
        print(f"Error consolidating memory: {e}")
        import traceback
        return JSONResponse({
            "status": "error",
            "error": str(e),
            "traceback": traceback.format_exc(),
            "facts_analyzed": 0,
            "facts_stored": 0,
            "entities_extracted": 0,
            "message": "Failed to consolidate memories"
        }, status_code=500)

# ============================================================================
# AGENT SPAWNER API
# ============================================================================

# Initialize spawner
spawner = None

@app.on_event("startup")
async def init_spawner():
    """Initialize agent spawner on startup."""
    global spawner
    try:
        sys.path.insert(0, '/app/core')
        from agent_spawner import AgentSpawner
        spawner = AgentSpawner(mode="api", base_url=f"http://localhost:{WEB_UI_PORT}")
        print("✅ Agent Spawner initialized")
    except Exception as e:
        print(f"⚠️ Agent Spawner not available: {e}")

class SpawnAgentRequest(BaseModel):
    template: str
    task: str
    context: Dict[str, Any] = {}
    provider: str = "kimi"
    model: str = "kimi-k2-0711"

@app.post("/api/agents/spawn")
async def spawn_agent(request: Request, spawn_req: SpawnAgentRequest):
    """Spawn a new sub-agent for a specific task."""
    global spawner
    
    if not spawner:
        return JSONResponse({
            "error": "Agent spawner not available"
        }, status_code=503)
    
    try:
        # Get current session from request context
        session_id = currentSession.id if currentSession else "unknown"
        
        task_id = await spawner.spawn_agent(
            template=spawn_req.template,
            task=spawn_req.task,
            context=spawn_req.context,
            parent_session_id=session_id,
            provider=spawn_req.provider,
            model=spawn_req.model
        )
        
        return JSONResponse({
            "status": "ok",
            "task_id": task_id,
            "message": f"Spawned {spawn_req.template} agent for task"
        })
        
    except Exception as e:
        import traceback
        print(f"Error spawning agent: {e}")
        return JSONResponse({
            "error": str(e),
            "traceback": traceback.format_exc()
        }, status_code=500)

@app.get("/api/agents/tasks/{task_id}")
async def get_task_status_endpoint(task_id: str):
    """Get status of a spawned agent task."""
    global spawner
    
    if not spawner:
        return JSONResponse({"error": "Agent spawner not available"}, status_code=503)
    
    status = spawner.get_task_status(task_id)
    if not status:
        return JSONResponse({"error": "Task not found"}, status_code=404)
    
    return JSONResponse(status)

@app.get("/api/agents/tasks/{task_id}/result")
async def get_task_result(task_id: str, timeout: int = 30):
    """Get result of a task (waits up to timeout seconds)."""
    global spawner
    
    if not spawner:
        return JSONResponse({"error": "Agent spawner not available"}, status_code=503)
    
    try:
        result = await spawner.get_result(task_id, timeout=float(timeout))
        return JSONResponse({
            "status": "ok",
            "task_id": task_id,
            "result": result
        })
    except TimeoutError:
        return JSONResponse({
            "status": "pending",
            "task_id": task_id,
            "message": "Task still running, try again later"
        })
    except Exception as e:
        return JSONResponse({
            "status": "error",
            "error": str(e)
        }, status_code=500)

@app.get("/api/agents/active")
async def get_active_agents(session_id: str = None):
    """Get list of active (running) sub-agents."""
    global spawner
    
    if not spawner:
        return JSONResponse({"error": "Agent spawner not available"}, status_code=503)
    
    active = spawner.get_active_tasks(parent_session_id=session_id)
    return JSONResponse({
        "active_tasks": active,
        "count": len(active)
    })

@app.post("/api/agents/tasks/{task_id}/cancel")
async def cancel_task(task_id: str):
    """Cancel a running sub-agent task."""
    global spawner
    
    if not spawner:
        return JSONResponse({"error": "Agent spawner not available"}, status_code=503)
    
    success = spawner.cancel_task(task_id)
    return JSONResponse({
        "status": "ok" if success else "error",
        "task_id": task_id,
        "cancelled": success
    })

# ============================================================================
# MEMORY EXPLORER API
# ============================================================================

@app.get("/api/memory")
async def get_memories(
    limit: int = 50,
    offset: int = 0,
    category: str = None,
    search: str = None
):
    """Get memories from hybrid memory store with optional filtering."""
    global hybrid_memory
    
    if not hybrid_memory:
        return JSONResponse({
            "memories": [],
            "total": 0,
            "message": "Hybrid memory not available"
        })
    
    try:
        # Get all memories from SQLite
        memories = hybrid_memory.sqlite.get_all_memories(limit=limit + offset)
        
        # Apply category filter
        if category:
            memories = [m for m in memories if m.get("category") == category]
        
        # Apply search filter
        if search:
            search_lower = search.lower()
            memories = [m for m in memories if search_lower in m.get("content", "").lower()]
        
        # Get total count
        total = len(memories)
        
        # Apply pagination
        memories = memories[offset:offset + limit]
        
        # Get unique categories for filter
        categories = list(set(m.get("category", "general") for m in memories))
        
        return JSONResponse({
            "memories": memories,
            "total": total,
            "categories": categories,
            "message": None
        })
    except Exception as e:
        return JSONResponse({
            "memories": [],
            "total": 0,
            "message": str(e)
        }, status_code=500)


# ============================================================================
# SEMANTIC MEMORY APIs - Human-like learning system
# ============================================================================

@app.get("/api/semantic-memory")
async def get_semantic_memory(session_id: str = None):
    """Get semantic memories (what the AI has learned about the user) - from cognitive memory system."""
    try:
        # Import cognitive memory system
        sys.path.insert(0, '/app/core')
        from cognitive_memory import get_cognitive_memory_manager, MemoryDecayCalculator
        
        # Get the cognitive memory manager
        manager = get_cognitive_memory_manager()
        
        # Process episodic memories (filter by session and exclude consolidated)
        all_memories = []
        for memory in manager.episodic_memories:
            # Filter by session_id if provided
            if session_id and memory.session_id != session_id:
                continue
            
            # Skip consolidated memories (already in knowledge graph)
            if getattr(memory, 'consolidated', False):
                continue
            
            # Calculate current strength with decay
            current_strength = MemoryDecayCalculator.calculate_episodic_strength(memory)
            mem_dict = memory.to_dict()
            mem_dict["current_strength"] = round(current_strength, 2)
            all_memories.append((memory, current_strength, mem_dict))
        
        # Sort by current strength
        all_memories.sort(key=lambda x: x[1], reverse=True)
        sorted_memories = [m[2] for m in all_memories]
        
        # Count by strength
        strong_count = sum(1 for _, strength, _ in all_memories if strength >= 0.7)
        weak_count = sum(1 for _, strength, _ in all_memories if strength <= 0.3)
        positive_count = sum(1 for _, _, m in all_memories if m.get('sentiment', 3) >= 4)
        
        # Extract unique topics
        topics = []
        for _, _, m in all_memories:
            if m.get('topics'):
                topics.extend(m['topics'])
        topics = list(set(topics))  # Unique
        
        return JSONResponse({
            "memories": sorted_memories[:50],  # Limit to top 50
            "count": len(all_memories),
            "strong_count": strong_count,
            "weak_count": weak_count,
            "positive_count": positive_count,
            "topics": topics[:10],
            "entity_count": len(manager.knowledge_graph.entities),
            "successful_formats": [],
            "preferred_approaches": [],
            "source": "cognitive_memory",
            "session_id": session_id  # Return which session was queried
        })
        
    except Exception as e:
        import traceback
        print(f"Error getting semantic memory: {e}")
        return JSONResponse({
            "memories": [],
            "count": 0,
            "error": str(e),
            "traceback": traceback.format_exc()
        }, status_code=500)


@app.get("/api/semantic-memory/successful-approaches")
async def get_successful_approaches(topic: str = None):
    """Get approaches that have worked well with this user."""
    try:
        from core.semantic_memory import get_semantic_memory_store
        
        store = get_semantic_memory_store()
        approaches = store.get_successful_approaches(topic)
        
        return JSONResponse({
            "approaches": approaches,
            "topic": topic
        })
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/api/semantic-memory/stats")
async def get_semantic_memory_stats():
    """Get semantic memory statistics including decay info."""
    try:
        from core.semantic_memory import get_semantic_memory_store
        
        store = get_semantic_memory_store()
        
        # Calculate stats
        total = len(store.memories)
        
        # Count by strength
        strong_memories = []
        weak_memories = []
        consolidated = []
        
        for memory in store.memories:
            strength = store._calculate_memory_strength(memory)
            if strength >= 0.7:
                strong_memories.append(memory)
            elif strength <= 0.3:
                weak_memories.append(memory)
            
            # Consolidated memories (very positive + important)
            if memory.sentiment >= 4 and memory.importance_score >= store.CONSOLIDATION_THRESHOLD:
                consolidated.append(memory)
        
        # Age distribution
        from datetime import datetime
        now = datetime.now()
        age_buckets = {"< 1 day": 0, "< 1 week": 0, "< 1 month": 0, "> 1 month": 0}
        
        for memory in store.memories:
            memory_time = datetime.fromisoformat(memory.timestamp)
            days_old = (now - memory_time).days
            
            if days_old < 1:
                age_buckets["< 1 day"] += 1
            elif days_old < 7:
                age_buckets["< 1 week"] += 1
            elif days_old < 30:
                age_buckets["< 1 month"] += 1
            else:
                age_buckets["> 1 month"] += 1
        
        return JSONResponse({
            "total_memories": total,
            "strong_memories": len(strong_memories),
            "weak_memories": len(weak_memories),
            "consolidated_memories": len(consolidated),
            "age_distribution": age_buckets,
            "decay_half_life_days": store.DECAY_HALF_LIFE_DAYS,
            "decay_min_strength": store.DECAY_MIN_STRENGTH,
            "consolidation_threshold": store.CONSOLIDATION_THRESHOLD
        })
    except Exception as e:
        import traceback
        return JSONResponse({
            "error": str(e),
            "traceback": traceback.format_exc()
        }, status_code=500)


@app.get("/api/memory/stats")
async def get_memory_stats():
    """Get memory statistics."""
    global hybrid_memory
    
    if not hybrid_memory:
        return JSONResponse({
            "sqlite": {"total": 0, "categories": {}},
            "graph": {"nodes": 0, "relationships": 0},
            "graph_available": False,
            "message": "Hybrid memory not available"
        })
    
    try:
        stats = hybrid_memory.get_stats()
        return JSONResponse(stats)
    except Exception as e:
        return JSONResponse({
            "sqlite": {"total": 0, "categories": {}},
            "graph": {"nodes": 0, "relationships": 0},
            "graph_available": False,
            "message": str(e)
        })

@app.delete("/api/memory/{memory_id}")
async def delete_memory(memory_id: int):
    """Delete a specific memory."""
    global hybrid_memory
    
    if not hybrid_memory:
        return JSONResponse({"error": "Hybrid memory not available"}, status_code=503)
    
    try:
        success = hybrid_memory.sqlite.delete_memory(memory_id)
        if success:
            return JSONResponse({"status": "ok", "message": f"Memory {memory_id} deleted"})
        else:
            return JSONResponse({"error": "Memory not found"}, status_code=404)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.post("/api/memory/search")
async def search_memories(request: Request):
    """Search memories with semantic/contextual query."""
    global hybrid_memory
    
    if not hybrid_memory:
        return JSONResponse({"memories": [], "message": "Hybrid memory not available"})
    
    try:
        data = await request.json()
        query = data.get("query", "")
        query_type = data.get("type", "quick")  # quick, semantic, context
        limit = data.get("limit", 10)
        
        if not query:
            return JSONResponse({"memories": [], "message": "Empty query"})
        
        # Use hybrid memory recall
        from hybrid_memory import MemoryQuery
        
        mem_query = MemoryQuery(
            query_type=query_type,
            text=query,
            limit=limit
        )
        
        results = hybrid_memory.recall(mem_query)
        
        return JSONResponse({
            "memories": results,
            "query": query,
            "type": query_type,
            "count": len(results)
        })
    except Exception as e:
        return JSONResponse({"memories": [], "message": str(e)}, status_code=500)

@app.get("/api/memory/graph-data")
async def get_memory_graph_data():
    """Fetch nodes and edges directly from the Kuzu Knowledge Graph."""
    global hybrid_memory
    
    if not hybrid_memory or not getattr(hybrid_memory, "_graph_conn", None):
        return JSONResponse({"nodes": [], "edges": [], "error": "Kuzu Graph not available"})
        
    try:
        nodes = []
        edges = []
        
        # 1. Memories
        res = hybrid_memory._graph_conn.execute("MATCH (m:Memory) RETURN m.id, m.content, m.category")
        while res.has_next():
            row = res.get_next()
            content = str(row[1] or '')
            cat = row[2] or 'general'
            nodes.append({
                "id": f"mem-{row[0]}",
                "label": content[:30] + "..." if len(content) > 30 else content,
                "title": content,
                "group": "Memory",
                "category": cat,
                "color": {'background': '#8b5cf6', 'border': '#7c3aed'},
                "shape": 'box',
                "font": {'color': 'white', 'size': 12},
                "data": {"content": content, "category": cat}
            })
            
        # 2. Topics
        res = hybrid_memory._graph_conn.execute("MATCH (t:Topic) RETURN t.name")
        while res.has_next():
            row = res.get_next()
            t_name = row[0]
            nodes.append({
                "id": f"top-{t_name}",
                "label": t_name,
                "title": f"Topic: {t_name}",
                "group": "Topic",
                "color": {'background': '#10b981', 'border': '#059669'},
                "font": {'color': 'white', 'size': 11}
            })
            
        # 3. Entities
        res = hybrid_memory._graph_conn.execute("MATCH (e:Entity) RETURN e.name")
        while res.has_next():
            row = res.get_next()
            e_name = row[0]
            nodes.append({
                "id": f"ent-{e_name}",
                "label": e_name,
                "title": f"Entity: {e_name}",
                "group": "Entity",
                "color": {'background': '#f59e0b', 'border': '#d97706'},
                "font": {'color': 'white', 'size': 11}
            })
            
        # 4. HAS_TOPIC Edges
        res = hybrid_memory._graph_conn.execute("MATCH (m:Memory)-[r:HAS_TOPIC]->(t:Topic) RETURN m.id, t.name")
        while res.has_next():
            row = res.get_next()
            edges.append({
                "from": f"mem-{row[0]}",
                "to": f"top-{row[1]}",
                "label": "TOPIC",
                "arrows": "to",
                "color": {'color': '#9ca3af'}
            })
            
        # 5. MENTIONS Edges
        res = hybrid_memory._graph_conn.execute("MATCH (m:Memory)-[r:MENTIONS]->(e:Entity) RETURN m.id, e.name")
        while res.has_next():
            row = res.get_next()
            edges.append({
                "from": f"mem-{row[0]}",
                "to": f"ent-{row[1]}",
                "label": "MENTIONS",
                "arrows": "to",
                "color": {'color': '#fbbf24'}
            })
            
        # 6. FLOWS_INTO Temporal Edges
        try:
            res = hybrid_memory._graph_conn.execute("MATCH (m1:Memory)-[r:FLOWS_INTO]->(m2:Memory) RETURN m1.id, m2.id")
            while res.has_next():
                row = res.get_next()
                edges.append({
                    "from": f"mem-{row[0]}",
                    "to": f"mem-{row[1]}",
                    "label": "FLOWS_INTO",
                    "arrows": "to",
                    "dashes": True,
                    "color": {'color': '#3b82f6'},
                    "width": 2
                })
        except Exception:
            pass # Maybe schema missing during startup 
            
        # 7. RELATED_TO Semantic Edges
        try:
            res = hybrid_memory._graph_conn.execute("MATCH (m1:Memory)-[r:RELATED_TO]->(m2:Memory) RETURN m1.id, m2.id, r.score")
            while res.has_next():
                row = res.get_next()
                score = float(row[2] or 0)
                edges.append({
                    "from": f"mem-{row[0]}",
                    "to": f"mem-{row[1]}",
                    "label": f"RELATED ({score:.2f})",
                    "arrows": "to",
                    "color": {'color': '#d8b4fe'}
                })
        except Exception:
            pass

        return JSONResponse({"nodes": nodes, "edges": edges})
        
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return JSONResponse({"nodes": [], "edges": [], "error": str(e)})


# ============================================================================
# COGNITIVE MEMORY APIs - Episodic + Semantic + Procedural
# ============================================================================

@app.get("/api/cognitive-memory")
async def get_cognitive_memory():
    """Get all cognitive memory data."""
    try:
        from core.cognitive_memory import get_cognitive_memory_manager
        
        manager = get_cognitive_memory_manager()
        stats = manager.get_stats()
        
        return JSONResponse({
            "status": "ok",
            "stats": stats,
            "episodic_count": stats["episodic"]["total"],
            "semantic_entities": stats["semantic"]["entities"],
            "procedural_patterns": stats["procedural"]["total"]
        })
    except Exception as e:
        import traceback
        return JSONResponse({
            "status": "error",
            "error": str(e),
            "traceback": traceback.format_exc()
        }, status_code=500)


@app.post("/api/cognitive-memory/store")
async def store_cognitive_memory(request: Request):
    """Store a new interaction in cognitive memory."""
    try:
        from core.cognitive_memory import get_cognitive_memory_manager
        
        data = await request.json()
        user_message = data.get("user_message", "")
        assistant_message = data.get("assistant_message", "")
        session_id = data.get("session_id", "default")
        sentiment = data.get("sentiment", 3)
        successful = data.get("successful", True)
        
        if not user_message or not assistant_message:
            return JSONResponse({"error": "Missing messages"}, status_code=400)
        
        manager = get_cognitive_memory_manager()
        episode = manager.store_interaction(
            user_message=user_message,
            assistant_message=assistant_message,
            session_id=session_id,
            sentiment=sentiment,
            successful=successful
        )
        
        return JSONResponse({
            "status": "ok",
            "memory_id": episode.memory_id,
            "entities_extracted": len(episode.entities_involved),
            "topics": episode.topics,
            "technologies": episode.technologies
        })
    except Exception as e:
        import traceback
        return JSONResponse({
            "error": str(e),
            "traceback": traceback.format_exc()
        }, status_code=500)


@app.get("/api/cognitive-memory/retrieve")
async def retrieve_cognitive_memory(query: str = "", session_id: str = None, limit: int = 5):
    """Retrieve relevant cognitive memory context."""
    try:
        from core.cognitive_memory import get_cognitive_memory_manager
        
        manager = get_cognitive_memory_manager()
        results = manager.retrieve_context(query, session_id, limit)
        
        return JSONResponse({
            "status": "ok",
            "query": query,
            "results": results,
            "total_episodic": len(results["episodic"]),
            "total_semantic": len(results["semantic"]["entities"]),
            "total_procedural": len(results["procedural"])
        })
    except Exception as e:
        import traceback
        return JSONResponse({
            "error": str(e),
            "traceback": traceback.format_exc()
        }, status_code=500)


@app.get("/api/cognitive-memory/knowledge-graph")
async def get_knowledge_graph(entity_type: str = None, limit: int = 50):
    """Get knowledge graph data for visualization."""
    try:
        from core.cognitive_memory import get_cognitive_memory_manager, Entity
        
        manager = get_cognitive_memory_manager()
        kg = manager.knowledge_graph
        
        # Get entities
        entities = []
        if entity_type:
            entity_ids = kg.entity_index_by_type.get(entity_type, [])
            entities = [kg.entities[eid].to_dict() for eid in entity_ids[:limit]]
        else:
            entities = [e.to_dict() for e in list(kg.entities.values())[:limit]]
        
        # Get relationships for these entities
        entity_ids = {e["id"] for e in entities}
        relationships = []
        related_episode_ids = set()
        
        for rel in kg.relationships.values():
            if rel.source_id in entity_ids or rel.target_id in entity_ids:
                relationships.append(rel.to_dict())
                # Track conversation nodes (they start with "ep_")
                if rel.source_id.startswith("ep_"):
                    related_episode_ids.add(rel.source_id)
                if rel.target_id.startswith("ep_"):
                    related_episode_ids.add(rel.target_id)
        
        # Add related episodes as Conversation entities
        for episode in manager.episodic_memories:
            if episode.memory_id in related_episode_ids:
                # Create a virtual entity for the episode
                episode_entity = {
                    "id": episode.memory_id,
                    "type": "Conversation",
                    "name": episode.summary[:30] + "..." if len(episode.summary) > 30 else episode.summary,
                    "properties": {
                        "sentiment": episode.sentiment,
                        "successful": episode.successful,
                        "timestamp": episode.timestamp,
                        # New VAD emotion fields
                        "emotion_label": getattr(episode, 'emotion_label', 'neutral'),
                        "emotion_valence": getattr(episode, 'emotion_valence', 0.0),
                        "emotion_arousal": getattr(episode, 'emotion_arousal', 0.5),
                        # New decay metadata
                        "importance": getattr(episode, 'importance', 0.5),
                        "decay_rate": getattr(episode, 'decay_rate', 0.5),
                        "archived": getattr(episode, 'archived', False)
                    },
                    "created_at": episode.timestamp,
                    "updated_at": episode.timestamp
                }
                entities.append(episode_entity)
        
        return JSONResponse({
            "status": "ok",
            "entities": entities,
            "relationships": relationships[:100],  # Limit for performance
            "total_entities": len(kg.entities),
            "total_relationships": len(kg.relationships)
        })
    except Exception as e:
        import traceback
        return JSONResponse({
            "error": str(e),
            "traceback": traceback.format_exc()
        }, status_code=500)


@app.get("/api/cognitive-memory/episodes")
async def get_episodic_memories(session_id: str = None, include_archived: bool = False, limit: int = 50):
    """Get episodic memories with full details including embeddings and VAD emotions."""
    try:
        from core.cognitive_memory import get_cognitive_memory_manager, MemoryDecayCalculator
        
        manager = get_cognitive_memory_manager()
        
        memories = []
        for ep in manager.episodic_memories:
            # Filter by session
            if session_id and ep.session_id != session_id:
                continue
            
            # Filter archived
            if ep.archived and not include_archived:
                continue
            
            # Calculate current strength
            strength = MemoryDecayCalculator.calculate_episodic_strength(ep)
            
            mem_dict = {
                "memory_id": ep.memory_id,
                "session_id": ep.session_id,
                "timestamp": ep.timestamp,
                "summary": ep.summary,
                "user_message": ep.user_message[:200] + "..." if len(ep.user_message) > 200 else ep.user_message,
                "assistant_message": ep.assistant_message[:200] + "..." if len(ep.assistant_message) > 200 else ep.assistant_message,
                "technologies": ep.technologies,
                "topics": ep.topics,
                "sentiment": ep.sentiment,
                "successful": ep.successful,
                # VAD Emotions
                "emotion": {
                    "label": ep.emotion_label,
                    "valence": round(ep.emotion_valence, 2),
                    "arousal": round(ep.emotion_arousal, 2),
                    "dominance": round(ep.emotion_dominance, 2)
                },
                # Decay metadata
                "importance": round(ep.importance, 2),
                "base_importance": round(ep.base_importance, 2),
                "decay_rate": round(ep.decay_rate, 2),
                "current_strength": round(strength, 2),
                "access_count": ep.access_count,
                "created_at": ep.created_at,
                "last_accessed": ep.last_accessed,
                # Status
                "archived": ep.archived,
                "consolidated": ep.consolidated,
                # Embedding (truncated for display)
                "has_embedding": ep.embedding is not None,
                "embedding_model": ep.embedding_model
            }
            memories.append(mem_dict)
        
        # Sort by strength (descending)
        memories.sort(key=lambda x: x["current_strength"], reverse=True)
        
        return JSONResponse({
            "status": "ok",
            "memories": memories[:limit],
            "total": len(manager.episodic_memories),
            "filtered": len(memories),
            "session_id": session_id
        })
    except Exception as e:
        import traceback
        return JSONResponse({
            "error": str(e),
            "traceback": traceback.format_exc()
        }, status_code=500)


@app.post("/api/memory/backfill-embeddings")
async def trigger_backfill_embeddings():
    """Manually trigger semantic embedding backfill for episodic memories."""
    try:
        from core.cognitive_memory import get_cognitive_memory_manager
        manager = get_cognitive_memory_manager()
        count = manager.backfill_embeddings()
        return JSONResponse({
            "status": "ok",
            "backfilled_count": count,
            "message": f"Successfully backfilled {count} memories with semantic embeddings."
        })
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@app.post("/api/memory/scrub-graph")
async def trigger_scrub_graph():
    """Manually trigger a deep clean and rebuild of the Knowledge Graph."""
    try:
        global hybrid_memory
        if not hybrid_memory:
            return JSONResponse({"status": "error", "message": "Memory store not initialized"}, status_code=500)
            
        count = hybrid_memory.scrub_and_rebuild_graph()
        return JSONResponse({
            "status": "ok",
            "reingested_count": count,
            "message": f"Graph scrubbed and rebuilt. Re-ingested {count} relevant memories."
        })
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@app.get("/api/cognitive-memory/entity/{entity_id}")
async def get_entity_details(entity_id: str):
    """Get detailed information about an entity and its relationships."""
    try:
        from core.cognitive_memory import get_cognitive_memory_manager
        
        manager = get_cognitive_memory_manager()
        kg = manager.knowledge_graph
        
        entity = kg.get_entity(entity_id)
        if not entity:
            return JSONResponse({"error": "Entity not found"}, status_code=404)
        
        # Get neighbors
        neighbors = kg.get_neighbors(entity_id)
        neighbor_data = [
            {
                "entity": e.to_dict(),
                "relationship": r.to_dict()
            }
            for e, r in neighbors
        ]
        
        # Get related episodic memories
        related_episodes = [
            ep.to_dict() for ep in manager.episodic_memories
            if entity_id in ep.entities_involved
        ]
        
        return JSONResponse({
            "status": "ok",
            "entity": entity.to_dict(),
            "neighbors": neighbor_data,
            "related_episodes": related_episodes[:10]
        })
    except Exception as e:
        import traceback
        return JSONResponse({
            "error": str(e),
            "traceback": traceback.format_exc()
        }, status_code=500)


# ============================================================================
# FILE UPLOAD API
# ============================================================================

# Allowed file types and max size
ALLOWED_EXTENSIONS = {'.txt', '.md', '.py', '.js', '.json', '.yaml', '.yml', '.csv', '.pdf'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

UPLOAD_DIR = Path("/app/workspace/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

def extract_text_from_file(file_path: Path, extension: str) -> str:
    """Extract text content from various file types."""
    try:
        if extension in {'.txt', '.md', '.py', '.js', '.json', '.yaml', '.yml', '.csv'}:
            # Text files - read directly
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        
        elif extension == '.pdf':
            # PDF - try to extract text
            try:
                import PyPDF2
                text = []
                with open(file_path, 'rb') as f:
                    reader = PyPDF2.PdfReader(f)
                    for page in reader.pages:
                        text.append(page.extract_text())
                return '\n'.join(text)
            except ImportError:
                return "[PDF content - PyPDF2 not installed]"
        
        else:
            return f"[Unsupported file type: {extension}]"
    
    except Exception as e:
        return f"[Error reading file: {str(e)}]"

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    """Upload a file and extract its content."""
    try:
        # Check file extension
        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in ALLOWED_EXTENSIONS:
            return JSONResponse({
                "error": f"File type not allowed. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
            }, status_code=400)
        
        # Save file temporarily
        temp_path = UPLOAD_DIR / f"temp_{datetime.now().timestamp()}_{file.filename}"
        
        with open(temp_path, 'wb') as f:
            content = await file.read()
            if len(content) > MAX_FILE_SIZE:
                return JSONResponse({
                    "error": f"File too large. Max size: {MAX_FILE_SIZE / 1024 / 1024}MB"
                }, status_code=400)
            f.write(content)
        
        # Extract text
        text_content = extract_text_from_file(temp_path, file_ext)
        
        # Move to permanent location
        final_path = UPLOAD_DIR / f"{datetime.now().timestamp()}_{file.filename}"
        shutil.move(str(temp_path), str(final_path))
        
        # Truncate if too long
        preview = text_content[:500] + "..." if len(text_content) > 500 else text_content
        
        return JSONResponse({
            "status": "ok",
            "filename": file.filename,
            "saved_as": str(final_path.name),
            "size": len(content),
            "content": text_content,
            "preview": preview,
            "type": file_ext
        })
    
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/api/upload/list")
async def list_uploaded_files():
    """List all uploaded files."""
    try:
        files = []
        for file_path in UPLOAD_DIR.glob("*"):
            if file_path.is_file():
                stat = file_path.stat()
                files.append({
                    "name": file_path.name,
                    "size": stat.st_size,
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
                })
        
        # Sort by modified date (newest first)
        files.sort(key=lambda x: x["modified"], reverse=True)
        return JSONResponse({"files": files})
    
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.delete("/api/upload/{filename}")
async def delete_uploaded_file(filename: str):
    """Delete an uploaded file."""
    try:
        file_path = UPLOAD_DIR / filename
        # Security check - ensure file is in upload dir
        if not str(file_path.resolve()).startswith(str(UPLOAD_DIR.resolve())):
            return JSONResponse({"error": "Invalid filename"}, status_code=400)
        
        if file_path.exists():
            file_path.unlink()
            return JSONResponse({"status": "ok", "message": f"Deleted {filename}"})
        else:
            return JSONResponse({"error": "File not found"}, status_code=404)
    
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

# ============================================================================
# WORKSPACE FILE MANAGER API
# ============================================================================

WORKSPACE_ROOT = Path("/app/workspace")

class WorkspacePathRequest(BaseModel):
    path: str = ""  # Relative path from workspace root

class WorkspaceWriteRequest(BaseModel):
    path: str
    content: str
    create_dirs: bool = True

def get_secure_workspace_path(relative_path: str) -> tuple[Path, bool]:
    """
    Resolve and validate workspace path.
    Returns (resolved_path, is_valid)
    """
    try:
        # Normalize path - remove leading slashes and dots
        relative_path = relative_path.strip().lstrip('/').lstrip('.')
        if not relative_path:
            relative_path = "."
        
        # Resolve the full path
        resolved = (WORKSPACE_ROOT / relative_path).resolve()
        root_resolved = WORKSPACE_ROOT.resolve()
        
        # Security check: must be within workspace
        if not str(resolved).startswith(str(root_resolved)):
            return (resolved, False)
        
        return (resolved, True)
    except Exception:
        return (WORKSPACE_ROOT, False)

@app.get("/api/workspace/list")
async def workspace_list(path: str = ""):
    """List files and directories in workspace."""
    try:
        target_path, is_valid = get_secure_workspace_path(path)
        if not is_valid:
            return JSONResponse({"error": "Invalid path - access denied"}, status_code=403)
        
        if not target_path.exists():
            return JSONResponse({"error": "Path not found"}, status_code=404)
        
        if target_path.is_file():
            # Return file info
            stat = target_path.stat()
            return JSONResponse({
                "type": "file",
                "name": target_path.name,
                "path": str(target_path.relative_to(WORKSPACE_ROOT)),
                "size": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "is_text": target_path.suffix.lower() in ['.md', '.txt', '.py', '.js', '.json', '.yaml', '.yml', '.csv', '.html', '.css', '.sh', '.env', '.ini', '.cfg']
            })
        
        # List directory contents
        items = []
        for item in sorted(target_path.iterdir(), key=lambda x: (x.is_file(), x.name.lower())):
            try:
                stat = item.stat()
                rel_path = str(item.relative_to(WORKSPACE_ROOT))
                items.append({
                    "name": item.name,
                    "path": rel_path,
                    "type": "directory" if item.is_dir() else "file",
                    "size": stat.st_size if item.is_file() else None,
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
                })
            except (OSError, PermissionError):
                continue
        
        return JSONResponse({
            "type": "directory",
            "path": str(target_path.relative_to(WORKSPACE_ROOT)) if target_path != WORKSPACE_ROOT else "",
            "items": items
        })
    
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/api/workspace/read")
async def workspace_read(path: str):
    """Read a file from workspace."""
    try:
        file_path, is_valid = get_secure_workspace_path(path)
        if not is_valid:
            return JSONResponse({"error": "Invalid path - access denied"}, status_code=403)
        
        if not file_path.exists():
            return JSONResponse({"error": "File not found"}, status_code=404)
        
        if file_path.is_dir():
            return JSONResponse({"error": "Path is a directory, use /api/workspace/list"}, status_code=400)
        
        # Check file size (max 10MB for web reading)
        file_size = file_path.stat().st_size
        if file_size > 10 * 1024 * 1024:
            return JSONResponse({"error": "File too large (max 10MB)"}, status_code=413)
        
        # Try to read as text
        try:
            content = file_path.read_text(encoding='utf-8')
            return JSONResponse({
                "path": str(file_path.relative_to(WORKSPACE_ROOT)),
                "content": content,
                "size": file_size,
                "encoding": "utf-8"
            })
        except UnicodeDecodeError:
            # Binary file - return metadata only
            return JSONResponse({
                "path": str(file_path.relative_to(WORKSPACE_ROOT)),
                "content": None,
                "size": file_size,
                "error": "Binary file - cannot display content"
            })
    
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.post("/api/workspace/write")
async def workspace_write(request: WorkspaceWriteRequest):
    """Write/create a file in workspace."""
    try:
        file_path, is_valid = get_secure_workspace_path(request.path)
        if not is_valid:
            return JSONResponse({"error": "Invalid path - access denied"}, status_code=403)
        
        # Create parent directories if requested
        if request.create_dirs:
            file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write file
        file_path.write_text(request.content, encoding='utf-8')
        
        return JSONResponse({
            "status": "ok",
            "message": f"File saved: {file_path.relative_to(WORKSPACE_ROOT)}",
            "path": str(file_path.relative_to(WORKSPACE_ROOT)),
            "size": file_path.stat().st_size
        })
    
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.delete("/api/workspace/delete")
async def workspace_delete(path: str, recursive: bool = False):
    """Delete a file or directory from workspace."""
    try:
        target_path, is_valid = get_secure_workspace_path(path)
        if not is_valid:
            return JSONResponse({"error": "Invalid path - access denied"}, status_code=403)
        
        if not target_path.exists():
            return JSONResponse({"error": "Path not found"}, status_code=404)
        
        # Prevent deleting critical system files
        critical_paths = ['memory', 'web_ui_data', 'SOUL.md', 'USER.md']
        rel_path = str(target_path.relative_to(WORKSPACE_ROOT))
        if rel_path in critical_paths or rel_path.split('/')[0] in critical_paths:
            return JSONResponse({"error": "Cannot delete critical system paths"}, status_code=403)
        
        if target_path.is_dir():
            if recursive:
                import shutil
                shutil.rmtree(target_path)
                return JSONResponse({"status": "ok", "message": f"Directory deleted: {rel_path}"})
            else:
                target_path.rmdir()  # Only works if empty
                return JSONResponse({"status": "ok", "message": f"Empty directory deleted: {rel_path}"})
        else:
            target_path.unlink()
            return JSONResponse({"status": "ok", "message": f"File deleted: {rel_path}"})
    
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.post("/api/workspace/mkdir")
async def workspace_mkdir(path: str):
    """Create a directory in workspace."""
    try:
        dir_path, is_valid = get_secure_workspace_path(path)
        if not is_valid:
            return JSONResponse({"error": "Invalid path - access denied"}, status_code=403)
        
        dir_path.mkdir(parents=True, exist_ok=True)
        
        return JSONResponse({
            "status": "ok",
            "message": f"Directory created: {dir_path.relative_to(WORKSPACE_ROOT)}",
            "path": str(dir_path.relative_to(WORKSPACE_ROOT))
        })
    
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/api/session/current")
async def get_current_session():
    """Get current session info."""
    global current_session
    if current_session:
        current_session.messages = web_messages
        current_session.message_count = len(web_messages)
        return JSONResponse(current_session.dict())
    return JSONResponse({"error": "No active session"}, status_code=404)

# ============================================================================
# HEALTH CHECK
# ============================================================================

@app.get("/api/providers/status")
async def providers_status():
    """Check which providers are configured."""
    return {
        "kimi": {"available": os.getenv("KIMI_API_KEY") is not None, "configured_model": settings.model if settings.provider == "kimi" else None},
        "anthropic": {"available": os.getenv("ANTHROPIC_API_KEY") is not None},
        "openai": {"available": os.getenv("OPENAI_API_KEY") is not None},
        "openrouter": {"available": os.getenv("OPENROUTER_API_KEY") is not None}
    }

@app.get("/memory-graph", response_class=HTMLResponse)
async def memory_graph_page():
    """Serve the Memory Graph visualization page."""
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Memory Graph Explorer</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <style>
        * { font-family: 'Inter', sans-serif; }
        #graph-container {
            width: 100%;
            height: calc(100vh - 200px);
            border: 1px solid #e5e7eb;
            border-radius: 0.5rem;
            background: #f9fafb;
        }
        .memory-card {
            transition: all 0.2s;
        }
        .memory-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        }
    </style>
</head>
<body class="bg-gray-50 h-screen">
    <div class="h-full flex flex-col">
        <!-- Header -->
        <header class="bg-white border-b border-gray-200 px-6 py-4">
            <div class="flex items-center justify-between">
                <div class="flex items-center gap-3">
                    <a href="/" class="text-gray-500 hover:text-gray-700">
                        <i class="fas fa-arrow-left"></i>
                    </a>
                    <h1 class="text-xl font-semibold text-gray-900">
                        <i class="fas fa-project-diagram text-violet-500 mr-2"></i>
                        Memory Graph Explorer
                    </h1>
                </div>
                <div class="flex items-center gap-4">
                    <div id="stats" class="text-sm text-gray-500">
                        Loading stats...
                    </div>
                    <button onclick="loadGraph()" class="px-4 py-2 bg-violet-600 text-white rounded-lg hover:bg-violet-700 transition-colors">
                        <i class="fas fa-sync-alt mr-2"></i>Refresh
                    </button>
                </div>
            </div>
        </header>
        
        <!-- Main Content -->
        <div class="flex-1 flex overflow-hidden">
            <!-- Sidebar - Memory List -->
            <div class="w-80 bg-white border-r border-gray-200 flex flex-col">
                <div class="p-4 border-b border-gray-200">
                    <h2 class="font-medium text-gray-900">Memories</h2>
                    <p class="text-xs text-gray-500 mt-1">Click to highlight connections</p>
                </div>
                <div id="memory-list" class="flex-1 overflow-y-auto p-4 space-y-3">
                    <div class="text-center text-gray-400 py-8">Loading...</div>
                </div>
            </div>
            
            <!-- Graph View -->
            <div class="flex-1 flex flex-col p-6">
                <!-- Filters -->
                <div class="mb-4 flex gap-4">
                    <select id="node-filter" onchange="filterGraph()" class="px-3 py-2 border border-gray-300 rounded-lg text-sm">
                        <option value="all">All Nodes</option>
                        <option value="Memory">Memories</option>
                        <option value="Topic">Topics</option>
                        <option value="Entity">Entities</option>
                    </select>
                    <select id="layout-select" onchange="changeLayout()" class="px-3 py-2 border border-gray-300 rounded-lg text-sm">
                        <option value="force">Force-directed</option>
                        <option value="hierarchical">Hierarchical</option>
                        <option value="circular">Circular</option>
                    </select>
                    <button onclick="fitGraph()" class="px-3 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 text-sm">
                        <i class="fas fa-compress-arrows-alt mr-1"></i>Fit
                    </button>
                </div>
                
                <!-- Graph Container -->
                <div id="graph-container"></div>
                
                <!-- Selected Node Info -->
                <div id="node-info" class="mt-4 p-4 bg-white rounded-lg border border-gray-200 hidden">
                    <h3 class="font-medium text-gray-900 mb-2" id="selected-node-title"></h3>
                    <p class="text-sm text-gray-600" id="selected-node-content"></p>
                    <div class="mt-2 flex gap-2" id="selected-node-connections"></div>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        let network = null;
        let nodesData = null;
        let edgesData = null;
        let allNodes = [];
        let allEdges = [];
        
        // Color scheme
        const colors = {
            Memory: { background: '#8b5cf6', border: '#7c3aed' },
            Topic: { background: '#10b981', border: '#059669' },
            Entity: { background: '#f59e0b', border: '#d97706' },
            Category: { background: '#3b82f6', border: '#2563eb' }
        };
        
        async function loadGraph() {
            try {
                // Load memories, graph structure, and stats
                const [memoriesRes, graphRes, statsRes] = await Promise.all([
                    fetch('/api/memory?limit=100'),
                    fetch('/api/memory/graph-data'),
                    fetch('/api/memory/stats')
                ]);
                
                const memoriesData = await memoriesRes.json();
                const graphData = await graphRes.json();
                const stats = await statsRes.json();
                
                // Update stats
                document.getElementById('stats').innerHTML = `
                    <span class="font-medium">${stats.sqlite?.total || 0}</span> memories
                    ${stats.graph_available ? 
                        `<span class="mx-2">|</span><span class="font-medium">${stats.graph?.nodes || 0}</span> graph nodes` : 
                        '<span class="mx-2">|</span><span class="text-yellow-600">Graph not available</span>' //
                    }
                `;
                
                // Update memory list (left sidebar)
                renderMemoryList(memoriesData.memories);
                
                // Build the REAL graph!
                buildRealGraph(graphData.nodes || [], graphData.edges || []);
                
            } catch (error) {
                console.error('Failed to load graph:', error);
                document.getElementById('graph-container').innerHTML = 
                    '<div class="flex items-center justify-center h-full text-red-500">Failed to load graph data</div>';
            }
        }
        
        function renderMemoryList(memories) {
            const container = document.getElementById('memory-list');
            if (!memories || memories.length === 0) {
                container.innerHTML = '<div class="text-center text-gray-400 py-8">No memories yet</div>';
                return;
            }
            
            container.innerHTML = memories.map(m => `
                <div class="memory-card p-3 bg-gray-50 rounded-lg cursor-pointer border border-gray-200 hover:border-violet-300"
                     onclick="highlightMemory('${m.id}')">
                    <div class="text-sm text-gray-700 line-clamp-2">${escapeHtml(m.content || m.text || 'No content')}</div>
                    <div class="mt-2 flex items-center gap-2">
                        <span class="px-2 py-0.5 bg-white rounded text-xs text-gray-500 border">${m.category || 'general'}</span>
                    </div>
                </div>
            `).join('');
        }
        
        function buildRealGraph(nodes, edges) {
            allNodes = nodes;
            allEdges = edges;
            
            // Create vis.js dataset
            nodesData = new vis.DataSet(nodes);
            edgesData = new vis.DataSet(edges);
            
            // Network options
            const options = {
                nodes: {
                    borderWidth: 2,
                    shadow: true
                },
                edges: {
                    width: 2,
                    shadow: false,
                    smooth: { type: 'continuous' }
                },
                physics: {
                    forceAtlas2Based: {
                        gravitationalConstant: -50,
                        centralGravity: 0.01,
                        springLength: 100,
                        springConstant: 0.08
                    },
                    maxVelocity: 50,
                    solver: 'forceAtlas2Based',
                    timestep: 0.35,
                    stabilization: { iterations: 150 }
                },
                interaction: {
                    hover: true,
                    tooltipDelay: 200,
                    hideEdgesOnDrag: true
                }
            };
            
            // Create network
            const container = document.getElementById('graph-container');
            network = new vis.Network(container, { nodes: nodesData, edges: edgesData }, options);
            
            // Event handlers
            network.on('click', function(params) {
                if (params.nodes.length > 0) {
                    showNodeInfo(params.nodes[0]);
                } else {
                    hideNodeInfo();
                }
            });
        }
        
        function highlightMemory(memoryId) {
            const nodeId = `mem-${memoryId}`;
            network.selectNodes([nodeId]);
            network.focus(nodeId, { scale: 1.2, animation: true });
            showNodeInfo(nodeId);
        }
        
        function showNodeInfo(nodeId) {
            const node = allNodes.find(n => n.id === nodeId);
            if (!node || !node.data) {
                hideNodeInfo();
                return;
            }
            
            const info = document.getElementById('node-info');
            document.getElementById('selected-node-title').textContent = 
                node.group === 'Memory' ? 'Memory' : node.group;
            document.getElementById('selected-node-content').textContent = 
                node.data.content || node.data.text || node.title || 'No details';
            
            // Show connected nodes
            const connectedEdges = allEdges.filter(e => e.from === nodeId || e.to === nodeId);
            const connectionsHtml = connectedEdges.map(e => {
                const otherId = e.from === nodeId ? e.to : e.from;
                const otherNode = allNodes.find(n => n.id === otherId);
                return `<span class="px-2 py-1 bg-gray-100 rounded text-xs">${otherNode?.label || otherId}</span>`;
            }).join('');
            
            document.getElementById('selected-node-connections').innerHTML = 
                connectionsHtml || '<span class="text-xs text-gray-400">No connections</span>';
            
            info.classList.remove('hidden');
        }
        
        function hideNodeInfo() {
            document.getElementById('node-info').classList.add('hidden');
        }
        
        function filterGraph() {
            const filter = document.getElementById('node-filter').value;
            
            if (filter === 'all') {
                nodesData.clear();
                nodesData.add(allNodes);
                edgesData.clear();
                edgesData.add(allEdges);
            } else {
                const filteredNodes = allNodes.filter(n => n.group === filter);
                const nodeIds = new Set(filteredNodes.map(n => n.id));
                const filteredEdges = allEdges.filter(e => nodeIds.has(e.from) && nodeIds.has(e.to));
                
                nodesData.clear();
                nodesData.add(filteredNodes);
                edgesData.clear();
                edgesData.add(filteredEdges);
            }
        }
        
        function changeLayout() {
            const layout = document.getElementById('layout-select').value;
            let options = {};
            
            if (layout === 'hierarchical') {
                options = {
                    layout: {
                        hierarchical: {
                            direction: 'UD',
                            sortMethod: 'directed'
                        }
                    }
                };
            } else if (layout === 'circular') {
                // Use circular positioning (approximated with fixed positions)
                options = {
                    layout: {
                        hierarchical: false
                    }
                };
            } else {
                // Force-directed (default)
                options = {
                    layout: {
                        hierarchical: false
                    },
                    physics: {
                        enabled: true
                    }
                };
            }
            
            network.setOptions(options);
        }
        
        function fitGraph() {
            network.fit({ animation: true });
        }
        
        function truncate(str, len) {
            if (!str) return '';
            return str.length > len ? str.substring(0, len) + '...' : str;
        }
        
        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }
        
        // Load on startup
        document.addEventListener('DOMContentLoaded', loadGraph);
    </script>
</body>
</html>"""
    return HTMLResponse(content=html_content)


@app.get("/episodic-memories", response_class=HTMLResponse)
async def episodic_memories_page():
    """Serve the Episodic Memories visualization page with VAD emotions and embeddings."""
    html_content = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Episodic Memories Explorer</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <style>
        * { font-family: 'Inter', sans-serif; }
        .emotion-badge { display: inline-flex; align-items: center; gap: 0.25rem; padding: 0.125rem 0.5rem; border-radius: 9999px; font-size: 0.75rem; font-weight: 500; }
        .vad-bar { height: 4px; border-radius: 2px; background: #e5e7eb; overflow: hidden; }
        .vad-fill { height: 100%; border-radius: 2px; transition: width 0.3s; }
    </style>
</head>
<body class="bg-gray-50 min-h-screen">
    <div class="max-w-7xl mx-auto p-6">
        <header class="mb-8">
            <div class="flex items-center justify-between">
                <div class="flex items-center gap-3">
                    <h1 class="text-2xl font-bold text-gray-900"><i class="fas fa-list-ul text-pink-500 mr-2"></i>Episodic Memories</h1>
                    <span class="text-xs bg-blue-100 text-blue-700 px-2 py-1 rounded font-medium">VAD + Embeddings</span>
                </div>
                <div class="flex items-center gap-3">
                    <button onclick="loadMemories()" class="px-4 py-2 bg-pink-600 text-white rounded-lg hover:bg-pink-700"><i class="fas fa-sync-alt mr-2"></i>Refresh</button>
                </div>
            </div>
        </header>
        
        <div id="stats" class="grid grid-cols-4 gap-4 mb-6">
            <div class="bg-white p-4 rounded-lg shadow border"><div class="text-sm text-gray-500">Total Memories</div><div class="text-2xl font-bold text-gray-900" id="stat-total">-</div></div>
            <div class="bg-white p-4 rounded-lg shadow border"><div class="text-sm text-gray-500">With Embeddings</div><div class="text-2xl font-bold text-blue-600" id="stat-embeddings">-</div></div>
            <div class="bg-white p-4 rounded-lg shadow border"><div class="text-sm text-gray-500">High Arousal</div><div class="text-2xl font-bold text-orange-600" id="stat-arousal">-</div></div>
            <div class="bg-white p-4 rounded-lg shadow border"><div class="text-sm text-gray-500">Archived</div><div class="text-2xl font-bold text-gray-400" id="stat-archived">-</div></div>
        </div>
        
        <div class="bg-white p-4 rounded-lg shadow border mb-6">
            <!-- Search Bar -->
            <div class="flex items-center gap-3 mb-4">
                <div class="flex-1 relative">
                    <i class="fas fa-search absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400"></i>
                    <textarea id="search-memories" placeholder="Search memories... (text, topics, technologies, entities)" 
                           class="w-full pl-10 pr-4 py-2 border rounded-lg focus:ring-2 focus:ring-pink-500 focus:border-pink-500 resize-none"
                           rows="1"
                           oninput="filterMemories()"
                           onkeydown="if(event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); filterMemories(); }"></textarea>
                </div>
                <button onclick="clearSearch()" class="px-3 py-2 text-gray-500 hover:text-gray-700" title="Clear search">
                    <i class="fas fa-times"></i>
                </button>
            </div>
            <!-- Filters -->
            <div class="flex items-center gap-4">
                <label class="flex items-center gap-2"><input type="checkbox" id="show-archived" onchange="renderMemories()" class="rounded"><span class="text-sm text-gray-700">Show Archived</span></label>
                <label class="flex items-center gap-2"><input type="checkbox" id="show-consolidated" onchange="renderMemories()" checked class="rounded"><span class="text-sm text-gray-700">Show Consolidated</span></label>
                <select id="sort-by" onchange="renderMemories()" class="ml-auto px-3 py-1 border rounded text-sm"><option value="strength">Sort by Strength</option><option value="date">Sort by Date</option><option value="importance">Sort by Importance</option></select>
            </div>
        </div>
        
        <div id="memories-container" class="grid gap-4"><div class="text-center py-12 text-gray-400">Loading...</div></div>
    </div>
    
    <script>
        let allMemories = [];
        async function loadMemories() {
            const container = document.getElementById("memories-container");
            container.innerHTML = '<div class="text-center py-12"><i class="fas fa-spinner fa-spin text-2xl text-pink-500"></i></div>';
            try {
                const includeArchived = document.getElementById("show-archived").checked;
                const url = `/api/cognitive-memory/episodes?${includeArchived ? "include_archived=true" : ""}&limit=100`;
                const res = await fetch(url);
                const data = await res.json();
                if (data.status !== "ok") { container.innerHTML = `<div class="text-center py-12 text-red-500">Error: ${data.error}</div>`; return; }
                allMemories = data.memories;
                filteredMemories = [...allMemories];
                updateStats(data);
                renderMemories();
            } catch (error) { container.innerHTML = `<div class="text-center py-12 text-red-500">Failed: ${error.message}</div>`; }
        }
        function updateStats(data) {
            document.getElementById("stat-total").textContent = data.total;
            document.getElementById("stat-embeddings").textContent = data.memories.filter(m => m.has_embedding).length;
            document.getElementById("stat-arousal").textContent = data.memories.filter(m => m.emotion.arousal > 0.7).length;
            document.getElementById("stat-archived").textContent = data.memories.filter(m => m.archived).length;
        }
        function renderMemories() {
            const container = document.getElementById("memories-container");
            const showArchived = document.getElementById("show-archived").checked;
            const showConsolidated = document.getElementById("show-consolidated").checked;
            const sortBy = document.getElementById("sort-by").value;
            let memories = [...allMemories];
            if (!showArchived) memories = memories.filter(m => !m.archived);
            if (!showConsolidated) memories = memories.filter(m => !m.consolidated);
            memories.sort((a, b) => { if (sortBy === "strength") return b.current_strength - a.current_strength; if (sortBy === "importance") return b.importance - a.importance; return new Date(b.timestamp) - new Date(a.timestamp); });
            if (memories.length === 0) { container.innerHTML = '<div class="text-center py-12 text-gray-400">No memories</div>'; return; }
            container.innerHTML = memories.map(m => `
                <div class="bg-white rounded-lg shadow border ${m.archived ? "border-gray-300 bg-gray-50" : "border-gray-200"} p-4">
                    <div class="flex items-start justify-between">
                        <div class="flex-1">
                            <div class="flex items-center gap-2 mb-2">
                                <span class="text-xs font-mono text-gray-400">${m.memory_id}</span>
                                ${m.archived ? `<span class="text-xs bg-gray-200 text-gray-600 px-2 py-0.5 rounded">Archived</span>` : ""}
                                ${m.consolidated ? `<span class="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded">Consolidated</span>` : ""}
                                <span class="text-xs text-gray-400">${new Date(m.timestamp).toLocaleString()}</span>
                            </div>
                            <p class="text-gray-900 font-medium mb-2">${m.summary}</p>
                            <div class="flex flex-wrap gap-2 mb-3">${m.technologies.map(t => `<span class="text-xs bg-green-100 text-green-700 px-2 py-1 rounded">${t}</span>`).join("")}${m.topics.map(t => `<span class="text-xs bg-amber-100 text-amber-700 px-2 py-1 rounded">${t}</span>`).join("")}</div>
                            <button onclick="showMemoryInGraph('${m.memory_id}', '${(m.user_message || '').replace(/'/g, "\\'")}')" 
                                    class="text-xs text-pink-600 hover:text-pink-800 flex items-center gap-1">
                                <i class="fas fa-project-diagram"></i> Show in Graph
                            </button>
                        </div>
                        <div class="w-64 ml-4 space-y-3">
                            <div class="bg-gray-50 rounded p-3">
                                <div class="flex items-center justify-between mb-2"><span class="text-xs font-medium text-gray-600">Emotion</span><span class="emotion-badge ${getEmotionColor(m.emotion.label)}">${m.emotion.label}</span></div>
                                <div class="mb-2"><div class="flex justify-between text-xs text-gray-500 mb-1"><span>Valence</span><span>${m.emotion.valence > 0 ? "+" : ""}${m.emotion.valence}</span></div><div class="vad-bar"><div class="vad-fill ${m.emotion.valence >= 0 ? "bg-green-500" : "bg-red-500"}" style="width: ${Math.abs(m.emotion.valence) * 100}%;"></div></div></div>
                                <div class="mb-2"><div class="flex justify-between text-xs text-gray-500 mb-1"><span>Arousal</span><span>${m.emotion.arousal}</span></div><div class="vad-bar"><div class="vad-fill bg-orange-500" style="width: ${m.emotion.arousal * 100}%;"></div></div></div>
                                <div><div class="flex justify-between text-xs text-gray-500 mb-1"><span>Dominance</span><span>${m.emotion.dominance}</span></div><div class="vad-bar"><div class="vad-fill bg-purple-500" style="width: ${m.emotion.dominance * 100}%;"></div></div></div>
                            </div>
                            <div class="bg-gray-50 rounded p-3 text-xs space-y-1">
                                <div class="flex justify-between"><span class="text-gray-500">Strength:</span><span class="font-medium ${m.current_strength < 0.3 ? "text-red-600" : m.current_strength > 0.7 ? "text-green-600" : "text-gray-900"}">${m.current_strength}</span></div>
                                <div class="flex justify-between"><span class="text-gray-500">Importance:</span><span class="font-medium">${m.importance}</span></div>
                                <div class="flex justify-between"><span class="text-gray-500">Decay:</span><span class="font-medium">${m.decay_rate}</span></div>
                                <div class="flex justify-between items-center pt-1 border-t"><span class="text-gray-500">Embedding:</span><span class="${m.has_embedding ? "text-green-600" : "text-gray-400"}"><i class="fas fa-${m.has_embedding ? "check" : "times"}"></i></span></div>
                            </div>
                        </div>
                    </div>
                </div>
            `).join("");
        }
        function getEmotionColor(label) { const colors = { "happy": "bg-green-100 text-green-700", "excited": "bg-orange-100 text-orange-700", "content": "bg-blue-100 text-blue-700", "calm": "bg-gray-100 text-gray-700", "neutral": "bg-gray-100 text-gray-600", "alert": "bg-yellow-100 text-yellow-700", "sad": "bg-indigo-100 text-indigo-700", "angry": "bg-red-100 text-red-700" }; return colors[label] || "bg-gray-100 text-gray-600"; }
        
        // Filter memories based on search query
        let filteredMemories = [];
        function filterMemories() {
            const query = document.getElementById("search-memories").value.toLowerCase().trim();
            if (!query) {
                filteredMemories = [...allMemories];
            } else {
                filteredMemories = allMemories.filter(m => {
                    const searchText = [
                        m.summary || "",
                        m.user_message || "",
                        m.assistant_message || "",
                        ...(m.technologies || []),
                        ...(m.topics || []),
                        ...(m.entities_involved || [])
                    ].join(" ").toLowerCase();
                    return searchText.includes(query);
                });
            }
            renderFilteredMemories();
        }
        
        function clearSearch() {
            document.getElementById("search-memories").value = "";
            filteredMemories = [...allMemories];
            renderFilteredMemories();
        }
        
        function renderFilteredMemories() {
            const container = document.getElementById("memories-container");
            const showArchived = document.getElementById("show-archived").checked;
            const showConsolidated = document.getElementById("show-consolidated").checked;
            const sortBy = document.getElementById("sort-by").value;
            
            let memories = filteredMemories.length > 0 || document.getElementById("search-memories").value.trim() ? [...filteredMemories] : [...allMemories];
            
            if (!showArchived) memories = memories.filter(m => !m.archived);
            if (!showConsolidated) memories = memories.filter(m => !m.consolidated);
            memories.sort((a, b) => { if (sortBy === "strength") return b.current_strength - a.current_strength; if (sortBy === "importance") return b.importance - a.importance; return new Date(b.timestamp) - new Date(a.timestamp); });
            
            if (memories.length === 0) { 
                const isSearching = document.getElementById("search-memories").value.trim() !== "";
                container.innerHTML = `<div class="text-center py-12 text-gray-400">${isSearching ? "No memories match your search" : "No memories"}</div>`; 
                return; 
            }
            
            container.innerHTML = memories.map(m => `
                <div class="bg-white rounded-lg shadow border ${m.archived ? "border-gray-300 bg-gray-50" : "border-gray-200"} p-4">
                    <div class="flex items-start justify-between">
                        <div class="flex-1">
                            <div class="flex items-center gap-2 mb-2">
                                <span class="text-xs font-mono text-gray-400">${m.memory_id}</span>
                                ${m.archived ? `<span class="text-xs bg-gray-200 text-gray-600 px-2 py-0.5 rounded">Archived</span>` : ""}
                                ${m.consolidated ? `<span class="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded">Consolidated</span>` : ""}
                                <span class="text-xs text-gray-400">${new Date(m.timestamp).toLocaleString()}</span>
                            </div>
                            <p class="text-gray-900 font-medium mb-2">${m.summary}</p>
                            <div class="flex flex-wrap gap-2 mb-3">${m.technologies.map(t => `<span class="text-xs bg-green-100 text-green-700 px-2 py-1 rounded">${t}</span>`).join("")}${m.topics.map(t => `<span class="text-xs bg-amber-100 text-amber-700 px-2 py-1 rounded">${t}</span>`).join("")}</div>
                        </div>
                        <div class="w-64 ml-4 space-y-3">
                            <div class="bg-gray-50 rounded p-3">
                                <div class="flex items-center justify-between mb-2"><span class="text-xs font-medium text-gray-600">Emotion</span><span class="emotion-badge ${getEmotionColor(m.emotion.label)}">${m.emotion.label}</span></div>
                                <div class="mb-2"><div class="flex justify-between text-xs text-gray-500 mb-1"><span>Valence</span><span>${m.emotion.valence > 0 ? "+" : ""}${m.emotion.valence}</span></div><div class="vad-bar"><div class="vad-fill ${m.emotion.valence >= 0 ? "bg-green-500" : "bg-red-500"}" style="width: ${Math.abs(m.emotion.valence) * 100}%;"></div></div></div>
                                <div class="mb-2"><div class="flex justify-between text-xs text-gray-500 mb-1"><span>Arousal</span><span>${m.emotion.arousal}</span></div><div class="vad-bar"><div class="vad-fill bg-orange-500" style="width: ${m.emotion.arousal * 100}%;"></div></div></div>
                                <div><div class="flex justify-between text-xs text-gray-500 mb-1"><span>Dominance</span><span>${m.emotion.dominance}</span></div><div class="vad-bar"><div class="vad-fill bg-purple-500" style="width: ${m.emotion.dominance * 100}%;"></div></div></div>
                            </div>
                            <div class="bg-gray-50 rounded p-3 text-xs space-y-1">
                                <div class="flex justify-between"><span class="text-gray-500">Strength:</span><span class="font-medium ${m.current_strength < 0.3 ? "text-red-600" : m.current_strength > 0.7 ? "text-green-600" : "text-gray-900"}">${m.current_strength}</span></div>
                                <div class="flex justify-between"><span class="text-gray-500">Importance:</span><span class="font-medium">${m.importance}</span></div>
                                <div class="flex justify-between"><span class="text-gray-500">Decay:</span><span class="font-medium">${m.decay_rate}</span></div>
                                <div class="flex justify-between items-center pt-1 border-t"><span class="text-gray-500">Embedding:</span><span class="${m.has_embedding ? "text-green-600" : "text-gray-400"}"><i class="fas fa-${m.has_embedding ? "check" : "times"}"></i></span></div>
                            </div>
                        </div>
                    </div>
                </div>
            `).join("");
        }
        
        // Override renderMemories to use filtered list
        const originalRenderMemories = renderMemories;
        renderMemories = function() {
            if (document.getElementById("search-memories").value.trim()) {
                renderFilteredMemories();
            } else {
                filteredMemories = [...allMemories];
                renderFilteredMemories();
            }
        };
        
        document.addEventListener("DOMContentLoaded", loadMemories);
    </script>
</body>
</html>'''
    return HTMLResponse(content=html_content)


@app.get("/cognitive-memory-graph", response_class=HTMLResponse)
async def cognitive_memory_graph_page():
    """Serve the NEW Cognitive Memory Graph visualization page."""
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Cognitive Memory Graph Explorer</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <style>
        * { font-family: 'Inter', sans-serif; }
        #graph-container { width: 100%; height: 100%; min-height: 400px; border: 1px solid #e5e7eb; border-radius: 0.5rem; background: #f9fafb; }
    </style>
</head>
<body class="bg-gray-50 h-[100dvh]">
    <div class="h-full flex flex-col">
        <header class="bg-white border-b border-gray-200 px-4 md:px-6 py-4">
            <div class="flex flex-col md:flex-row md:items-center justify-between gap-3">
                <div class="flex items-center gap-3">
                    <h1 class="text-xl font-semibold text-gray-900 flex items-center">
                        <i class="fas fa-brain text-pink-500 mr-2"></i>Cognitive Memory Graph
                    </h1>
                    <span class="text-xs bg-green-100 text-green-700 px-2 py-1 rounded">NEW</span>
                </div>
                <div class="flex items-center justify-between w-full md:w-auto gap-3">
                    <div id="stats" class="text-sm text-gray-500 flex-1 text-center md:text-right">Loading...</div>
                    <button onclick="loadGraph()" class="px-3 py-1.5 md:px-4 md:py-2 bg-pink-600 text-white rounded-lg hover:bg-pink-700 whitespace-nowrap">
                        <i class="fas fa-sync-alt mr-1 md:mr-2"></i>Refresh
                    </button>
                </div>
            </div>
        </header>
        <div class="flex-1 flex flex-col md:flex-row overflow-hidden min-h-0">
            <div class="w-full md:w-80 h-1/3 md:h-full bg-white border-b md:border-r border-gray-200 flex flex-col shrink-0">
                <div class="p-3 md:p-4 border-b border-gray-200 shrink-0">
                    <h2 class="font-medium text-gray-900 mb-2 md:mb-3">Entities</h2>
                    <div class="relative">
                        <i class="fas fa-search absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400"></i>
                        <input type="text" id="entity-search" placeholder="Filter entities..." 
                               class="w-full pl-9 pr-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-pink-500 focus:border-pink-500"
                               oninput="filterEntities()">
                    </div>
                </div>
                <div id="entity-list" class="flex-1 overflow-y-auto p-3 md:p-4 space-y-2 min-h-0">
                    <div class="text-center text-gray-400 py-4 md:py-8">Loading...</div>
                </div>
            </div>
            <div class="flex-1 flex flex-col p-2 md:p-6 min-h-0 relative">
                <div id="graph-container" class="absolute inset-2 md:inset-6"></div>
            </div>
        </div>
    </div>
    <script>
        let network = null;
        const colors = {
            Person: { background: '#8b5cf6', border: '#7c3aed' },
            Company: { background: '#3b82f6', border: '#2563eb' },
            Technology: { background: '#10b981', border: '#059669' },
            Topic: { background: '#f59e0b', border: '#d97706' },
            Project: { background: '#ec4899', border: '#db2777' },
            Conversation: { background: '#6b7280', border: '#4b5563' }
        };
        
        let allNodes = [];
        let allEdges = [];
        
        async function loadGraph() {
            try {
                const [graphRes, statsRes] = await Promise.all([
                    fetch('/api/memory/graph-data'),
                    fetch('/api/memory/stats')
                ]);
                const graphData = await graphRes.json();
                const stats = await statsRes.json();
                
                document.getElementById('stats').innerHTML = `
                    <span class="font-medium">${stats.graph?.nodes || 0}</span> real nodes
                    <span class="mx-2">|</span>
                    <span class="font-medium">${stats.graph?.relationships || 0}</span> real connections
                `;
                
                allNodes = graphData.nodes || [];
                allEdges = graphData.edges || [];
                
                // Show topics & entities in the side list
                const entitiesAndTopics = allNodes.filter(n => n.group === 'Entity' || n.group === 'Topic');
                renderEntityList(entitiesAndTopics);
                
                buildGraph(allNodes, allEdges);
            } catch (error) {
                console.error('Failed to load:', error);
                document.getElementById('graph-container').innerHTML = '<div class="flex items-center justify-center h-full text-red-500">Failed to load graph data</div>';
            }
        }
        
        function filterEntities() {
            const query = document.getElementById('entity-search').value.toLowerCase().trim();
            const entitiesAndTopics = allNodes.filter(n => n.group === 'Entity' || n.group === 'Topic');
            
            if (!query) {
                renderEntityList(entitiesAndTopics);
                return;
            }
            
            const filtered = entitiesAndTopics.filter(e => 
                e.label.toLowerCase().includes(query) || 
                e.group.toLowerCase().includes(query)
            );
            
            renderEntityList(filtered);
        }
        
        function renderEntityList(items) {
            const container = document.getElementById('entity-list');
            const isFiltering = document.getElementById('entity-search')?.value.trim() !== '';
            
            if (!items || items.length === 0) {
                container.innerHTML = `<div class="text-center text-gray-400 py-8">${isFiltering ? "No items match your search" : "No items"}</div>`;
                return;
            }
            container.innerHTML = items.map(e => `
                <div class="p-2 bg-gray-50 rounded border border-gray-200 hover:border-pink-300 cursor-pointer" onclick="highlight('${e.id}')">
                    <div class="flex items-center gap-2">
                        <span class="w-3 h-3 rounded-full" style="background: ${(e.color && e.color.background) || '#999'}"></span>
                        <span class="font-medium text-sm">${e.label}</span>
                    </div>
                    <div class="text-xs text-gray-500">${e.group}</div>
                </div>
            `).join('');
        }
        
        function buildGraph(nodes, edges) {
            
            network = new vis.Network(
                document.getElementById('graph-container'),
                { nodes: new vis.DataSet(nodes), edges: new vis.DataSet(edges) },
                { nodes: { borderWidth: 2 }, edges: { width: 2 }, physics: { stabilization: { iterations: 150 } } }
            );
        }
        
        function highlight(id) { if (network) { network.selectNodes([id]); network.focus(id, { scale: 1.5, animation: true }); } }
        
        function resetGraph() {
            buildGraph(allNodes, allEdges);
            document.getElementById('stats').innerHTML = document.getElementById('stats').innerHTML.replace(/<button.*<\/button>/, '');
        }
        
        function showMemoryInGraph(memoryId, userMessage) {
            const nodeId = `mem-${memoryId}`;
            
            // If the node exists in our graph dataset, focus it.
            if (allNodes.find(n => n.id === nodeId)) {
                
                // Show reset button if not already shown
                const statsEl = document.getElementById('stats');
                if (!statsEl.innerHTML.includes('Show All')) {
                    statsEl.innerHTML += ` <button onclick="resetGraph()" class="ml-2 text-xs text-blue-600 hover:text-blue-800 underline">Show All</button>`;
                }
                
                highlight(nodeId);
                
                // Switch to graph tab
                if (window.parent && window.parent.switchTab) {
                    window.parent.switchTab('graph');
                }
                
            } else {
                alert('Memory node not found in graph view.');
            }
        }
        
        function resetGraph() {
            const entitiesAndTopics = allNodes.filter(n => n.group === 'Entity' || n.group === 'Topic');
            renderEntityList(entitiesAndTopics);
            buildGraph(allNodes, allEdges);
            const statsEl = document.getElementById('stats');
            const match = statsEl.innerHTML.match(/^(.*?)<button/);
            if (match) {
                statsEl.innerHTML = match[1].trim();
            }
        }
        
        document.addEventListener('DOMContentLoaded', loadGraph);
    </script>
</body>
</html>"""
    return HTMLResponse(content=html_content)


@app.get("/admin", response_class=HTMLResponse)
async def admin_page():
    """Admin page for managing models and Telegram."""
    config = load_config()
    agent_name = config.get("agent", {}).get("name", "Agent")
    telegram_enabled = config.get("mode", {}).get("telegram", {}).get("enabled", False)
    
    # Get available templates
    templates = get_available_templates()
    templates_html = "\n".join([
        f'<option value="{t["id"]}">{t["name"]} - {t["role"]}</option>'
        for t in templates
    ])
    
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Admin - {agent_name}</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>* {{ font-family: 'Inter', sans-serif; }}</style>
</head>
<body class="bg-gray-50 min-h-screen">
    <div class="max-w-4xl mx-auto p-6">
        <!-- Header -->
        <header class="bg-white rounded-lg shadow-sm p-6 mb-6">
            <div class="flex items-center gap-4">
                <a href="/" class="text-gray-500 hover:text-gray-700">
                    <i class="fas fa-arrow-left"></i>
                </a>
                <h1 class="text-2xl font-bold text-gray-900">Admin Panel</h1>
            </div>
            <p class="text-gray-500 mt-2">Manage agent configuration, models, and integrations</p>
        </header>

        <!-- Status Cards -->
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
            <div class="bg-white rounded-lg shadow-sm p-4">
                <div class="flex items-center gap-3">
                    <div class="w-10 h-10 rounded-full bg-green-100 flex items-center justify-center">
                        <i class="fas fa-server text-green-600"></i>
                    </div>
                    <div>
                        <p class="text-sm text-gray-500">Kimi Agent</p>
                        <p class="font-semibold text-green-600">Online</p>
                    </div>
                </div>
            </div>
            <div class="bg-white rounded-lg shadow-sm p-4">
                <div class="flex items-center gap-3">
                    <div class="w-10 h-10 rounded-full bg-{('green' if telegram_enabled else 'gray')}-100 flex items-center justify-center">
                        <i class="fab fa-telegram text-{('blue' if telegram_enabled else 'gray')}-600"></i>
                    </div>
                    <div>
                        <p class="text-sm text-gray-500">Telegram Bot</p>
                        <p class="font-semibold {'text-blue-600' if telegram_enabled else 'text-gray-500'}">{('Enabled' if telegram_enabled else 'Disabled')}</p>
                    </div>
                </div>
            </div>
            <div class="bg-white rounded-lg shadow-sm p-4">
                <div class="flex items-center gap-3">
                    <div class="w-10 h-10 rounded-full bg-violet-100 flex items-center justify-center">
                        <i class="fas fa-brain text-violet-600"></i>
                    </div>
                    <div>
                        <p class="text-sm text-gray-500">Web UI</p>
                        <p class="font-semibold text-violet-600">Active</p>
                    </div>
                </div>
            </div>
        </div>

        <!-- Configuration Sections -->
        <div class="space-y-6">
            <!-- Agent Identity -->
            <div class="bg-white rounded-lg shadow-sm p-6">
                <h2 class="text-lg font-semibold text-gray-900 mb-4">
                    <i class="fas fa-user-circle mr-2 text-violet-500"></i>Agent Identity
                </h2>
                <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                        <label class="block text-sm text-gray-600 mb-1">Agent Name</label>
                        <input type="text" id="admin-agent-name" value="{agent_name}" 
                               class="w-full px-3 py-2 border border-gray-300 rounded-lg">
                    </div>
                    <div>
                        <label class="block text-sm text-gray-600 mb-1">Default Template</label>
                        <select id="admin-default-template" class="w-full px-3 py-2 border border-gray-300 rounded-lg">
                            <option value="">Use workspace/SOUL.md</option>
                            {templates_html}
                        </select>
                    </div>
                </div>
                <div class="mt-4 flex justify-end">
                    <button onclick="saveAgentConfig()" class="px-4 py-2 bg-violet-600 text-white rounded-lg hover:bg-violet-700">
                        <i class="fas fa-save mr-2"></i>Save Identity
                    </button>
                </div>
            </div>

            <!-- Model Configuration -->
            <div class="bg-white rounded-lg shadow-sm p-6">
                <h2 class="text-lg font-semibold text-gray-900 mb-4">
                    <i class="fas fa-robot mr-2 text-blue-500"></i>Model Configuration
                </h2>
                <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div>
                        <label class="block text-sm text-gray-600 mb-1">Default Provider</label>
                        <select id="admin-provider" class="w-full px-3 py-2 border border-gray-300 rounded-lg">
                            <option value="kimi">Kimi (Moonshot)</option>
                            <option value="openrouter">OpenRouter</option>
                            <option value="anthropic">Anthropic (Claude)</option>
                            <option value="openai">OpenAI (GPT)</option>
                        </select>
                    </div>
                    <div>
                        <label class="block text-sm text-gray-600 mb-1">Default Model</label>
                        <select id="admin-model" class="w-full px-3 py-2 border border-gray-300 rounded-lg">
                            <option value="kimi-k2-0711">kimi-k2-0711</option>
                            <option value="kimi-latest">kimi-latest</option>
                        </select>
                    </div>
                    <div>
                        <label class="block text-sm text-gray-600 mb-1">Default Mode</label>
                        <select id="admin-mode" class="w-full px-3 py-2 border border-gray-300 rounded-lg">
                            <option value="fast">Fast</option>
                            <option value="balanced" selected>Balanced</option>
                            <option value="deep">Deep</option>
                        </select>
                    </div>
                </div>
                <div class="mt-4 flex justify-end">
                    <button onclick="saveModelConfig()" class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
                        <i class="fas fa-save mr-2"></i>Save Models
                    </button>
                </div>
            </div>

            <!-- Telegram Configuration -->
            <div class="bg-white rounded-lg shadow-sm p-6">
                <h2 class="text-lg font-semibold text-gray-900 mb-4">
                    <i class="fab fa-telegram mr-2 text-blue-500"></i>Telegram Configuration
                </h2>
                <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                        <label class="block text-sm text-gray-600 mb-1">Bot Token</label>
                        <input type="password" id="admin-telegram-token" placeholder="Enter bot token from @BotFather"
                               class="w-full px-3 py-2 border border-gray-300 rounded-lg">
                    </div>
                    <div>
                        <label class="block text-sm text-gray-600 mb-1">Allowed User ID (optional)</label>
                        <input type="text" id="admin-telegram-userid" placeholder="Restrict to specific user"
                               class="w-full px-3 py-2 border border-gray-300 rounded-lg">
                    </div>
                </div>
                <div class="mt-4 flex items-center justify-between">
                    <div class="flex items-center gap-2">
                        <input type="checkbox" id="admin-telegram-enabled" {'checked' if telegram_enabled else ''} 
                               class="w-4 h-4 text-blue-600 rounded">
                        <label for="admin-telegram-enabled" class="text-sm text-gray-700">Enable Telegram Bot</label>
                    </div>
                    <button onclick="saveTelegramConfig()" class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
                        <i class="fas fa-save mr-2"></i>Save Telegram
                    </button>
                </div>
            </div>

            <!-- Actions -->
            <div class="bg-white rounded-lg shadow-sm p-6">
                <h2 class="text-lg font-semibold text-gray-900 mb-4">
                    <i class="fas fa-tools mr-2 text-orange-500"></i>System Actions
                </h2>
                <div class="flex flex-wrap gap-3">
                    <button onclick="restartServices()" class="px-4 py-2 bg-orange-600 text-white rounded-lg hover:bg-orange-700">
                        <i class="fas fa-redo mr-2"></i>Restart Services
                    </button>
                    <button onclick="clearMemory()" class="px-4 py-2 bg-yellow-600 text-white rounded-lg hover:bg-yellow-700">
                        <i class="fas fa-broom mr-2"></i>Clear Memory
                    </button>
                    <button onclick="exportConfig()" class="px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700">
                        <i class="fas fa-download mr-2"></i>Export Config
                    </button>
                </div>
            </div>
        </div>
    </div>

    <script>
        async function saveAgentConfig() {{
            const name = document.getElementById('admin-agent-name').value;
            const template = document.getElementById('admin-default-template').value;
            
            try {{
                const res = await fetch('/api/admin/config', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{agent: {{name, template}}}})
                }});
                if (res.ok) alert('Agent configuration saved!');
                else alert('Failed to save configuration');
            }} catch (e) {{
                alert('Error: ' + e.message);
            }}
        }}

        async function saveModelConfig() {{
            const provider = document.getElementById('admin-provider').value;
            const model = document.getElementById('admin-model').value;
            const mode = document.getElementById('admin-mode').value;
            
            try {{
                const res = await fetch('/api/admin/settings', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{provider, model, mode}})
                }});
                if (res.ok) alert('Model configuration saved!');
                else alert('Failed to save configuration');
            }} catch (e) {{
                alert('Error: ' + e.message);
            }}
        }}

        async function saveTelegramConfig() {{
            const token = document.getElementById('admin-telegram-token').value;
            const userId = document.getElementById('admin-telegram-userid').value;
            const enabled = document.getElementById('admin-telegram-enabled').checked;
            
            try {{
                const res = await fetch('/api/admin/telegram', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{token, user_id: userId, enabled}})
                }});
                if (res.ok) alert('Telegram configuration saved!');
                else alert('Failed to save configuration');
            }} catch (e) {{
                alert('Error: ' + e.message);
            }}
        }}

        async function restartServices() {{
            if (!confirm('Restart all services? This may take a moment.')) return;
            try {{
                const res = await fetch('/api/admin/restart', {{method: 'POST'}});
                if (res.ok) alert('Services restarted successfully!');
                else alert('Failed to restart services');
            }} catch (e) {{
                alert('Error: ' + e.message);
            }}
        }}

        async function clearMemory() {{
            if (!confirm('Clear all memory? This cannot be undone.')) return;
            try {{
                const res = await fetch('/api/admin/clear-memory', {{method: 'POST'}});
                if (res.ok) alert('Memory cleared successfully!');
                else alert('Failed to clear memory');
            }} catch (e) {{
                alert('Error: ' + e.message);
            }}
        }}

        function exportConfig() {{
            alert('Export feature coming soon!');
        }}
    </script>
</body>
</html>"""
    return HTMLResponse(content=html_content)

@app.get("/health")
async def health():
    """Health check endpoint."""
    kimi_status = "unknown"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            # Try /health first, then fallback to /models (common endpoints)
            for endpoint in ["/health", "/models", "/"]:
                try:
                    response = await client.get(f"{KIMI_AGENT_URL}{endpoint}")
                    if response.status_code in [200, 404]:
                        # 404 means server is up but endpoint doesn't exist
                        kimi_status = "ok"
                        break
                except:
                    continue
            else:
                kimi_status = "offline"
    except Exception as e:
        kimi_status = "offline"
        print(f"DEBUG: Kimi health check failed: {e}")
    
    # Check providers
    providers = await providers_status()
    
    # Check Ngrok status
    ngrok_status = "offline"
    public_url = None
    try:
        from pyngrok import ngrok
        tunnels = ngrok.get_tunnels()
        if tunnels:
            ngrok_status = "online"
            public_url = tunnels[0].public_url
    except:
        pass

    return {
        "status": "healthy",
        "kimi_agent_url": KIMI_AGENT_URL,
        "kimi_agent_status": kimi_status,
        "providers_status": providers,
        "ngrok_status": ngrok_status,
        "ngrok_url": public_url,
        "version": "2.1.0",
        "timestamp": datetime.now().isoformat()
    }

# ============================================================================
# REMOTE ACCESS (NGROK) APIs
# ============================================================================

@app.get("/api/remote/status")
async def get_remote_status():
    """Get Ngrok tunnel status."""
    try:
        from pyngrok import ngrok
        tunnels = ngrok.get_tunnels()
        if tunnels:
            return JSONResponse({
                "enabled": True,
                "url": tunnels[0].public_url,
                "domain": getattr(tunnels[0], 'domain', None)
            })
        return JSONResponse({"enabled": False, "url": None})
    except Exception as e:
        return JSONResponse({"enabled": False, "error": str(e)})

async def restore_ngrok_tunnel():
    """Internal helper to restore Ngrok tunnel from settings."""
    if not settings.ngrok_authtoken:
        return None
        
    from pyngrok import ngrok
    ngrok.set_auth_token(settings.ngrok_authtoken)
    
    kwargs = {"addr": WEB_UI_PORT}
    if settings.ngrok_domain:
        kwargs["domain"] = settings.ngrok_domain
        
    if settings.ngrok_oauth_provider:
        oauth_kwargs = {"provider": settings.ngrok_oauth_provider}
        if settings.ngrok_oauth_allow_emails:
            oauth_kwargs["allow_emails"] = [e.strip() for e in settings.ngrok_oauth_allow_emails.split(",") if e.strip()]
        kwargs["oauth"] = oauth_kwargs
        
    public_url = ngrok.connect(**kwargs).public_url
    return public_url

@app.post("/api/remote/start")
async def start_remote_access():
    """Start Ngrok tunnel."""
    if not settings.ngrok_authtoken:
        return JSONResponse({"error": "Ngrok Authtoken not configured. Go to settings."}, status_code=400)
    
    try:
        public_url = await restore_ngrok_tunnel()
        
        # Update settings
        settings.ngrok_enabled = True
        save_settings(settings)
        
        # Notify Admin
        msg = f"🌐 <b>Ngrok Tunnel Started</b>\nURL: {public_url}"
        if settings.ngrok_oauth_provider:
            msg += f"\n🔓 Provider: {settings.ngrok_oauth_provider}"
        import asyncio
        asyncio.create_task(send_telegram_notification(msg))
        save_settings(settings)
        
        return JSONResponse({"status": "ok", "url": public_url})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.post("/api/remote/stop")
async def stop_remote_access():
    """Stop Ngrok tunnel."""
    try:
        from pyngrok import ngrok
        tunnels = ngrok.get_tunnels()
        for tunnel in tunnels:
            ngrok.disconnect(tunnel.public_url)
        
        # Update settings
        settings.ngrok_enabled = False
        save_settings(settings)
        
        import asyncio
        asyncio.create_task(send_telegram_notification("🔌 <b>Ngrok Tunnel Stopped</b>\nRemote access is now disabled."))
        
        return JSONResponse({"status": "ok"})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# Provider Settings API
@app.post("/api/settings/provider")
async def save_provider_settings(request: Request):
    """Save provider settings."""
    try:
        body = await request.json()
        provider = body.get("provider", "kimi")
        api_key = body.get("api_key", "")
        model = body.get("model", "")
        base_url = body.get("base_url", "")
        
        # Update settings
        settings.provider = provider
        settings.model = model
        
        # Update environment variables only if api_key is provided and not null
        # api_key = null means "keep existing" (user left the placeholder)
        if api_key is not None and api_key != "":
            if provider == "anthropic":
                os.environ["ANTHROPIC_API_KEY"] = api_key
                save_env_var("ANTHROPIC_API_KEY", api_key)
            elif provider == "openai":
                os.environ["OPENAI_API_KEY"] = api_key
                save_env_var("OPENAI_API_KEY", api_key)
            elif provider == "google":
                os.environ["GOOGLE_API_KEY"] = api_key
                save_env_var("GOOGLE_API_KEY", api_key)
            elif provider == "openrouter":
                os.environ["OPENROUTER_API_KEY"] = api_key
                save_env_var("OPENROUTER_API_KEY", api_key)
            elif provider == "kimi":
                os.environ["KIMI_API_KEY"] = api_key
                save_env_var("KIMI_API_KEY", api_key)
            elif provider == "custom":
                os.environ["CUSTOM_API_KEY"] = api_key
                save_env_var("CUSTOM_API_KEY", api_key)
        
        # Save base URL for providers that need it
        if base_url:
            if provider == "openrouter":
                os.environ["OPENROUTER_BASE_URL"] = base_url
                save_env_var("OPENROUTER_BASE_URL", base_url)
            elif provider == "custom":
                os.environ["CUSTOM_BASE_URL"] = base_url
                save_env_var("CUSTOM_BASE_URL", base_url)
        
        # Save model for specific provider
        if model:
            if provider == "anthropic":
                os.environ["ANTHROPIC_MODEL"] = model
                save_env_var("ANTHROPIC_MODEL", model)
            elif provider == "openai":
                os.environ["OPENAI_MODEL"] = model
                save_env_var("OPENAI_MODEL", model)
            elif provider == "google":
                os.environ["GOOGLE_MODEL"] = model
                save_env_var("GOOGLE_MODEL", model)
            elif provider == "openrouter":
                os.environ["OPENROUTER_MODEL"] = model
                save_env_var("OPENROUTER_MODEL", model)
            elif provider == "kimi":
                os.environ["KIMI_MODEL"] = model
                save_env_var("KIMI_MODEL", model)
            elif provider == "custom":
                os.environ["CUSTOM_MODEL"] = model
                save_env_var("CUSTOM_MODEL", model)
        
        # Save to file
        save_settings(settings)
        
        return {"status": "ok", "message": f"Provider {provider} configured"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


# Test Provider Connection API
@app.post("/api/settings/provider/test")
async def test_provider_connection(request: Request):
    """Test connection to a provider."""
    try:
        body = await request.json()
        provider = body.get("provider", "kimi")
        api_key = body.get("api_key", "")
        base_url = body.get("base_url", "")
        
        # Get existing config if not provided
        if not api_key:
            if provider == "anthropic":
                api_key = os.getenv("ANTHROPIC_API_KEY", "")
            elif provider == "openai":
                api_key = os.getenv("OPENAI_API_KEY", "")
            elif provider == "google":
                api_key = os.getenv("GOOGLE_API_KEY", "")
            elif provider == "openrouter":
                api_key = os.getenv("OPENROUTER_API_KEY", "")
            elif provider == "kimi":
                api_key = os.getenv("KIMI_API_KEY", "")
            elif provider == "custom":
                api_key = os.getenv("CUSTOM_API_KEY", "")  # May be empty for local
        
        if not base_url:
            if provider == "openrouter":
                base_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
            elif provider == "custom":
                base_url = os.getenv("CUSTOM_BASE_URL", "")
        
        # Test connection based on provider
        if provider == "kimi":
            # Try to connect to Kimi
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.get(f"{KIMI_AGENT_URL}/health")
                    if response.status_code in [200, 404]:
                        return {"status": "ok", "message": "Kimi Agent is reachable"}
                    else:
                        return {"status": "error", "error": f"HTTP {response.status_code}"}
            except Exception as e:
                return {"status": "error", "error": str(e)}
        
        elif provider == "custom":
            # Test custom/OpenAI-compatible provider
            if not base_url:
                return {"status": "error", "error": "Base URL is required for custom provider"}
            
            # Ensure URL has /v1 path for OpenAI compatibility
            test_url = base_url.rstrip("/")
            if not test_url.endswith("/v1"):
                test_url += "/v1"
            
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    # Try to get models list (common OpenAI endpoint)
                    response = await client.get(
                        f"{test_url}/models",
                        headers={"Authorization": f"Bearer {api_key}"} if api_key else {}
                    )
                    if response.status_code == 200:
                        return {"status": "ok", "message": f"Connected to {provider} at {test_url}"}
                    elif response.status_code == 401:
                        return {"status": "warning", "message": "Authentication required - check API key"}
                    else:
                        # Try a simple chat completion as fallback
                        test_resp = await client.post(
                            f"{test_url}/chat/completions",
                            headers={"Authorization": f"Bearer {api_key}"} if api_key else {},
                            json={"model": "", "messages": [{"role": "user", "content": "hi"}], "max_tokens": 1}
                        )
                        if test_resp.status_code in [200, 400, 422]:  # 400/422 means endpoint works but bad request
                            return {"status": "ok", "message": f"Connected to {provider} at {test_url}"}
                        else:
                            return {"status": "error", "error": f"HTTP {test_resp.status_code}"}
            except Exception as e:
                return {"status": "error", "error": str(e)}
        
        # For other providers, just verify key format
        if not api_key:
            return {"status": "error", "error": "No API key configured"}
        return {"status": "ok", "message": f"{provider} API key format looks valid"}
        
    except Exception as e:
        return {"status": "error", "error": str(e)}


# Telegram Settings API
@app.post("/api/settings/telegram")
async def save_telegram_settings(request: Request):
    """Save Telegram bot settings."""
    try:
        body = await request.json()
        enabled = body.get("enabled", False)
        token = body.get("token", "")
        allowed_chat_ids = body.get("allowed_chat_ids", [])
        
        # Update core settings object
        settings.telegram_enabled = enabled
        if token:
            settings.telegram_token = token
        if allowed_chat_ids:
            settings.telegram_chat_ids = allowed_chat_ids
        
        # Save all settings (this also handles init.yaml and settings.json)
        save_settings(settings)
        
        # Immediate env var update for running processes
        if token:
            os.environ["TELEGRAM_BOT_TOKEN"] = token
            save_env_var("TELEGRAM_BOT_TOKEN", token)
        if allowed_chat_ids:
            os.environ["TELEGRAM_CHAT_IDS"] = ",".join(allowed_chat_ids)
            save_env_var("TELEGRAM_CHAT_IDS", ",".join(allowed_chat_ids))
        
        return {"status": "ok", "message": "Telegram settings saved"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


# Get Telegram Status API
@app.get("/api/settings/telegram/status")
async def get_telegram_status():
    """Get Telegram bot status."""
    try:
        # Load from init.yaml
        init_path = Path("init.yaml")
        config = {}
        if init_path.exists():
            with open(init_path) as f:
                config = yaml.safe_load(f) or {}
        
        telegram_config = config.get("mode", {}).get("telegram", {})
        enabled = telegram_config.get("enabled", False)
        token = telegram_config.get("token", "") or os.getenv("TELEGRAM_BOT_TOKEN", "")
        chat_ids = telegram_config.get("allowed_chat_ids", []) or os.getenv("TELEGRAM_CHAT_IDS", "").split(",")
        
        if not enabled or not token:
            return {
                "enabled": False,
                "status": "offline",
                "message": "Bot not configured"
            }
        
        # Try to get bot info from Telegram API
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"https://api.telegram.org/bot{token}/getMe")
                if response.status_code == 200:
                    data = response.json()
                    if data.get("ok"):
                        bot_info = data.get("result", {})
                        return {
                            "enabled": True,
                            "status": "online",
                            "bot_info": {
                                "username": bot_info.get("username"),
                                "first_name": bot_info.get("first_name"),
                                "id": bot_info.get("id")
                            },
                            "chat_ids": [c for c in chat_ids if c]
                        }
        except Exception as e:
            print(f"Telegram status check failed: {e}")
        
        return {
            "enabled": True,
            "status": "configured",
            "chat_ids": [c for c in chat_ids if c]
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


# Launch Telegram Bot API
@app.post("/api/settings/telegram/launch")
async def launch_telegram_bot():
    """Launch/check Telegram bot status."""
    try:
        token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        if not token:
            # Try to load from init.yaml
            init_path = Path("init.yaml")
            if init_path.exists():
                with open(init_path) as f:
                    config = yaml.safe_load(f) or {}
                token = config.get("mode", {}).get("telegram", {}).get("token", "")
        
        if not token:
            return {"status": "error", "error": "No bot token configured"}
        
        # Test connection to Telegram API
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"https://api.telegram.org/bot{token}/getMe")
            data = response.json()
            
            if response.status_code == 200 and data.get("ok"):
                bot_info = data.get("result", {})
                return {
                    "status": "online",
                    "message": "Bot is running",
                    "bot_info": {
                        "username": bot_info.get("username"),
                        "first_name": bot_info.get("first_name"),
                        "id": bot_info.get("id")
                    }
                }
            else:
                error_desc = data.get("description", "Unknown error")
                return {"status": "error", "error": error_desc}
    
    except httpx.TimeoutException:
        return {"status": "error", "error": "Connection timeout - check internet"}
    except Exception as e:
        return {"status": "error", "error": str(e)}

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=int(os.getenv('PORT', 8082)))
