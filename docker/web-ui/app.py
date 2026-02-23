"""
Web UI for IDE Agent Wizard v2.1
=================================
Modern Shadcn-inspired interface with chat + config panel
Uses Hybrid Memory (SQLite + Graph) for intelligent context
Features: Settings Panel, Session Management
"""

import os
import json
import sys
import httpx
import pickle
import uuid
from datetime import datetime
from typing import Dict, List, Optional
from fastapi import FastAPI, Request, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse
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

app = FastAPI(title="IDE Agent Wizard - Web UI v2.1")

# ============================================================================
# SETTINGS & SESSION MODELS
# ============================================================================

class Settings(BaseModel):
    """User settings for the Web UI."""
    provider: str = "kimi"  # kimi, openrouter, anthropic, openai
    model: str = "kimi-k2-0711"
    temperature: float = 0.7
    max_tokens: int = 4096
    mode: str = "balanced"  # fast, balanced, deep
    auto_save: bool = True
    auto_save_interval: int = 10  # messages

class Session(BaseModel):
    """Chat session model."""
    id: str
    name: str
    created_at: str
    updated_at: str
    message_count: int = 0
    messages: List[dict] = []

# Provider configurations
PROVIDER_MODELS = {
    "kimi": ["kimi-k2-0711", "kimi-latest"],
    "openrouter": ["anthropic/claude-3.5-sonnet", "openai/gpt-4o", "meta-llama/llama-3.1-70b"],
    "anthropic": ["claude-3-5-sonnet-20241022", "claude-3-opus-20240229"],
    "openai": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"]
}

MODE_PRESETS = {
    "fast": {"temperature": 0.3, "max_tokens": 2048},
    "balanced": {"temperature": 0.7, "max_tokens": 4096},
    "deep": {"temperature": 0.9, "max_tokens": 8192}
}

# Config
KIMI_AGENT_URL = os.getenv("KIMI_AGENT_URL", "http://kimi-agent:8081")
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
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{agent_name} - AI Assistant v2.1</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/github.min.css">
    <style>
        * {{ font-family: 'Inter', sans-serif; }}
        
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
            display: none;
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
    </style>
</head>
<body class="h-screen overflow-hidden bg-gray-50">
    <div class="flex h-full">
        <!-- Sessions Sidebar (Left) -->
        <div class="w-64 bg-white border-r border-gray-200 flex flex-col">
            <div class="p-4 border-b border-gray-200">
                <h2 class="font-semibold text-gray-900 flex items-center gap-2">
                    <i class="fas fa-history text-gray-400"></i>
                    Sessions
                </h2>
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
            </div>
            
            <!-- Memory Explorer Section -->
            <div class="border-t border-gray-200">
                <div class="p-3 bg-gray-50 border-b border-gray-200">
                    <h3 class="text-xs font-semibold text-gray-600 flex items-center gap-2 cursor-pointer" onclick="toggleMemoryPanel()">
                        <i class="fas fa-brain text-gray-400"></i>
                        Memory Explorer
                        <i id="memory-toggle-icon" class="fas fa-chevron-down text-xs ml-auto"></i>
                    </h3>
                </div>
                
                <div id="memory-panel" class="hidden">
                    <div class="p-3 space-y-3">
                        <!-- Memory Stats -->
                        <div class="text-xs text-gray-500 flex justify-between">
                            <span id="memory-count">0 memories</span>
                            <span id="memory-graph-status" class="text-gray-400"></span>
                        </div>
                        
                        <!-- Search -->
                        <div class="relative">
                            <input type="text" id="memory-search" placeholder="Search memories..."
                                   class="input-field text-xs py-2 pl-8"
                                   onkeypress="if(event.key==='Enter') searchMemories()">
                            <i class="fas fa-search absolute left-2.5 top-2.5 text-gray-400 text-xs"></i>
                        </div>
                        
                        <!-- Search Type -->
                        <div class="flex gap-1">
                            <button onclick="setMemorySearchType('quick')" id="mem-search-quick" class="flex-1 btn btn-primary text-[10px] py-1">
                                Quick
                            </button>
                            <button onclick="setMemorySearchType('semantic')" id="mem-search-semantic" class="flex-1 btn btn-secondary text-[10px] py-1">
                                Smart
                            </button>
                        </div>
                        
                        <!-- Memories List -->
                        <div id="memories-list" class="space-y-2 max-h-48 overflow-y-auto">
                            <div class="text-xs text-gray-400 text-center py-2">Click search to load</div>
                        </div>
                        
                        <!-- Load More -->
                        <button onclick="loadMoreMemories()" id="load-more-memories" class="btn btn-secondary w-full text-xs py-1.5 hidden">
                            <i class="fas fa-chevron-down"></i>
                            Load More
                        </button>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Chat Area (flex-1) -->
        <div class="flex-1 flex flex-col bg-white">
            <!-- Header -->
            <header class="px-6 py-4 border-b border-gray-200 bg-white">
                <div class="flex items-center justify-between">
                    <div class="flex items-center gap-3">
                        <div class="w-10 h-10 rounded-full bg-gradient-to-br from-violet-500 to-purple-600 flex items-center justify-center text-white font-semibold text-lg">
                            {agent_name[0].upper()}
                        </div>
                        <div>
                            <h1 class="font-semibold text-gray-900">{agent_name}</h1>
                            <p class="text-sm text-gray-500">Template: {agent_template}</p>
                        </div>
                    </div>
                    <div id="connection-status" class="status-badge warning">
                        <i class="fas fa-circle text-xs"></i>
                        Connecting...
                    </div>
                </div>
            </header>
            
            <!-- Chat Messages -->
            <div id="chat-messages" class="flex-1 overflow-y-auto p-6 space-y-4 scrollbar-hide bg-gray-50/50">
                <div class="text-center py-12">
                    <div class="w-16 h-16 mx-auto mb-4 rounded-2xl bg-gradient-to-br from-violet-500 to-purple-600 flex items-center justify-center text-white text-2xl">
                        <i class="fas fa-wand-magic-sparkles"></i>
                    </div>
                    <h2 class="text-xl font-semibold text-gray-900 mb-2">Welcome to {agent_name}</h2>
                    <p class="text-gray-500 max-w-md mx-auto">Start a conversation with your AI assistant. Your context and memory are preserved across sessions.</p>
                </div>
            </div>
            
            <!-- Typing Indicator -->
            <div id="typing-indicator" class="hidden px-6 py-2">
                <div class="chat-bubble-assistant inline-flex items-center gap-2 px-4 py-2">
                    <div class="typing-indicator">
                        <span></span><span></span><span></span>
                    </div>
                </div>
            </div>
            
            <!-- Input Area -->
            <div class="p-4 bg-white border-t border-gray-200">
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
                
                <div class="flex gap-3">
                    <input 
                        type="text" 
                        id="message-input" 
                        class="input-field flex-1" 
                        placeholder="Type your message..."
                        autocomplete="off"
                    >
                    <input type="file" id="file-input" class="hidden" accept=".txt,.md,.py,.js,.json,.yaml,.yml,.csv,.pdf" onchange="handleFileSelect(event)">
                    <button onclick="document.getElementById('file-input').click()" class="btn btn-secondary px-3" title="Attach file">
                        <i class="fas fa-paperclip"></i>
                    </button>
                    <button id="send-btn" class="btn btn-primary px-4">
                        <i class="fas fa-paper-plane"></i>
                    </button>
                </div>
                <div class="mt-2 text-xs text-gray-400">
                    Allowed: .txt, .md, .py, .js, .json, .yaml, .csv, .pdf (max 10MB)
                </div>
            </div>
        </div>
        
        <!-- Config Panel (Right) -->
        <div class="w-96 bg-white border-l border-gray-200 flex flex-col">
            <div class="p-4 border-b border-gray-200">
                <h2 class="font-semibold text-gray-900 flex items-center gap-2">
                    <i class="fas fa-sliders"></i>
                    Settings
                </h2>
            </div>
            
            <div class="flex-1 overflow-y-auto p-4 space-y-4">
                <!-- AI Settings -->
                <div class="sidebar-card">
                    <h3 class="text-sm font-medium text-gray-900 mb-3 flex items-center gap-2">
                        <i class="fas fa-brain text-gray-400"></i>
                        AI Configuration
                    </h3>
                    
                    <!-- Provider -->
                    <div class="mb-3">
                        <label class="block text-xs text-gray-500 mb-1">Provider</label>
                        <select id="setting-provider" class="input-field text-sm">
                            <!-- Populated by JS based on available providers -->
                        </select>
                        <div id="provider-info" class="mt-2 text-xs text-gray-400 hidden">
                            <i class="fas fa-info-circle"></i>
                            <span id="provider-info-text"></span>
                        </div>
                    </div>
                    
                    <!-- Model -->
                    <div class="mb-3">
                        <label class="block text-xs text-gray-500 mb-1">Model</label>
                        <select id="setting-model" class="input-field text-sm">
                            <!-- Models populated by JS -->
                        </select>
                    </div>
                    
                    <!-- Mode Presets -->
                    <div class="mb-3">
                        <label class="block text-xs text-gray-500 mb-2">Mode</label>
                        <div class="flex gap-2">
                            <button onclick="setMode('fast')" id="mode-fast" class="flex-1 btn btn-secondary text-xs py-1.5">
                                <i class="fas fa-bolt"></i> Fast
                            </button>
                            <button onclick="setMode('balanced')" id="mode-balanced" class="flex-1 btn btn-primary text-xs py-1.5">
                                <i class="fas fa-scale-balanced"></i> Balanced
                            </button>
                            <button onclick="setMode('deep')" id="mode-deep" class="flex-1 btn btn-secondary text-xs py-1.5">
                                <i class="fas fa-brain"></i> Deep
                            </button>
                        </div>
                    </div>
                    
                    <!-- Temperature -->
                    <div class="mb-3">
                        <label class="block text-xs text-gray-500 mb-1">
                            Temperature: <span id="temp-value">0.7</span>
                        </label>
                        <input type="range" id="setting-temperature" min="0" max="2" step="0.1" value="0.7" 
                               class="w-full" oninput="updateTempDisplay(); updateSettings()">
                    </div>
                    
                    <!-- Max Tokens -->
                    <div>
                        <label class="block text-xs text-gray-500 mb-1">Max Tokens</label>
                        <input type="number" id="setting-max-tokens" value="4096" min="256" max="32768" step="256"
                               class="input-field text-sm" onchange="updateSettings()">
                    </div>
                </div>
                
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
                        <button onclick="compactContext()" class="btn btn-secondary w-full text-sm">
                            <i class="fas fa-compress"></i>
                            Compact Context
                        </button>
                        <button onclick="resetSession()" class="btn btn-destructive w-full text-sm">
                            <i class="fas fa-rotate-right"></i>
                            Reset Session
                        </button>
                    </div>
                </div>
                
                <!-- Quick Links -->
                <div class="sidebar-card">
                    <h3 class="text-sm font-medium text-gray-900 mb-3 flex items-center gap-2">
                        <i class="fas fa-link text-gray-400"></i>
                        Quick Links
                    </h3>
                    <div class="space-y-2 text-sm">
                        <a href="http://localhost:8081/health" target="_blank" class="flex items-center gap-2 text-gray-600 hover:text-gray-900 transition-colors">
                            <i class="fas fa-external-link-alt text-xs"></i>
                            Kimi Agent Health
                        </a>
                        <div class="flex items-center gap-2 text-gray-600">
                            <i class="fas fa-folder-open text-xs"></i>
                            <span>Workspace: /workspace</span>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Footer -->
            <div class="p-3 border-t border-gray-200 bg-gray-50">
                <p class="text-xs text-gray-500 text-center">
                    IDE Agent Wizard v2.1.0
                </p>
            </div>
        </div>
    </div>
    
    <script>
        const chatMessages = document.getElementById('chat-messages');
        const messageInput = document.getElementById('message-input');
        const sendBtn = document.getElementById('send-btn');
        const typingIndicator = document.getElementById('typing-indicator');
        const connectionStatus = document.getElementById('connection-status');
        const msgCount = document.getElementById('msg-count');
        
        let messageCount = 0;
        
        // Check connection on load
        checkHealth();
        
        messageInput.addEventListener('keypress', (e) => {{
            if (e.key === 'Enter') sendMessage();
        }});
        
        sendBtn.addEventListener('click', sendMessage);
        
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
                content.innerHTML = marked.parse(text);
            }}
            
            bubble.appendChild(content);
            div.appendChild(bubble);
            chatMessages.appendChild(div);
            chatMessages.scrollTop = chatMessages.scrollHeight;
            
            // Apply syntax highlighting
            if (sender === 'assistant') {{
                content.querySelectorAll('pre code').forEach((block) => {{
                    hljs.highlightElement(block);
                }});
            }}
            
            messageCount++;
            msgCount.textContent = messageCount;
            
            // Store for compaction
            sessionMessages.push({{sender: sender, text: text, timestamp: new Date().toISOString()}});
        }}
        
        function escapeHtml(text) {{
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }}
        
        // Configure marked options
        marked.setOptions({{
            breaks: true,
            gfm: true,
            headerIds: false,
            mangle: false
        }});
        
        async function sendMessage() {{
            console.log('sendMessage called');
            const text = messageInput.value.trim();
            console.log('Text:', text);
            
            // Allow sending if there's text OR file attachment
            if (!text && !currentAttachment) return;
            
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
            sendBtn.disabled = true;
            typingIndicator.classList.remove('hidden');
            
            // Clear attachment after sending
            clearFileAttachment();
            
            try {{
                const response = await fetch('/api/chat', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ message: fullMessage }})
                }});
                
                typingIndicator.classList.add('hidden');
                
                const data = await response.json();
                if (data.response) {{
                    const modelInfo = data.model_used ? `${{data.provider}}/${{data.model_used}}` : null;
                    addMessage(data.response, 'assistant', modelInfo);
                }} else if (data.error) {{
                    addMessage('Error: ' + data.error, 'assistant');
                    updateConnectionStatus('error');
                }}
            }} catch (error) {{
                typingIndicator.classList.add('hidden');
                addMessage('Connection error. Please try again.', 'assistant');
                updateConnectionStatus('error');
            }}
            
            sendBtn.disabled = false;
            messageInput.focus();
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
        const USER_NAME = "{user_name}";
        const AGENT_NAME = "{agent_name}";
        
        // File attachment state
        let currentAttachment = null;
        
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
            }}
        }}
        
        // ============================================================================
        // SETTINGS MANAGEMENT
        // ============================================================================
        
        let currentSettings = {{}};
        let providerModels = {{}};
        let allProviders = {{}};
        let providerAvailability = {{}};
        
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
                
                // Populate provider dropdown
                populateProviderDropdown(providersData.providers, providersData.available);
                
                // Show info about locked providers
                showProviderInfo(providersData);
                
                // Apply settings to UI
                document.getElementById('setting-provider').value = currentSettings.provider;
                updateModelOptions();
                document.getElementById('setting-model').value = currentSettings.model;
                document.getElementById('setting-temperature').value = currentSettings.temperature;
                document.getElementById('temp-value').textContent = currentSettings.temperature;
                document.getElementById('setting-max-tokens').value = currentSettings.max_tokens;
                
                // Update mode buttons
                updateModeButtons(currentSettings.mode);
                
            }} catch (error) {{
                console.error('Failed to load settings:', error);
            }}
        }}
        
        function populateProviderDropdown(enabledProviders, availability) {{
            const select = document.getElementById('setting-provider');
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
        
        function showProviderInfo(providersData) {{
            const enabledCount = providersData.providers.length;
            const totalCount = Object.keys(providersData.all_models).length;
            
            if (enabledCount < totalCount) {{
                const infoDiv = document.getElementById('provider-info');
                const infoText = document.getElementById('provider-info-text');
                infoDiv.classList.remove('hidden');
                infoText.textContent = `${{enabledCount}}/${{totalCount}} providers enabled. Add API keys to .env to enable more.`;
            }}
        }}
        
        function updateModelOptions() {{
            const provider = document.getElementById('setting-provider').value;
            const modelSelect = document.getElementById('setting-model');
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
        }}
        
        // Handle provider change - update models and save
        function setupProviderListener() {{
            const providerSelect = document.getElementById('setting-provider');
            if (providerSelect) {{
                providerSelect.addEventListener('change', () => {{
                    console.log('Provider changed to:', providerSelect.value);
                    updateModelOptions();
                    updateSettings();
                }});
            }}
        }}
        
        // Handle model change - save settings
        function setupModelListener() {{
            const modelSelect = document.getElementById('setting-model');
            if (modelSelect) {{
                modelSelect.addEventListener('change', () => {{
                    console.log('Model changed to:', modelSelect.value);
                    updateSettings();
                }});
            }}
        }}
        
        function updateTempDisplay() {{
            const temp = document.getElementById('setting-temperature').value;
            document.getElementById('temp-value').textContent = temp;
        }}
        
        async function updateSettings() {{
            const newSettings = {{
                provider: document.getElementById('setting-provider').value,
                model: document.getElementById('setting-model').value,
                temperature: parseFloat(document.getElementById('setting-temperature').value),
                max_tokens: parseInt(document.getElementById('setting-max-tokens').value),
                mode: currentSettings.mode || 'balanced',
                auto_save: currentSettings.auto_save !== false,
                auto_save_interval: currentSettings.auto_save_interval || 10
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
                const res = await fetch(`/api/settings/mode/${{mode}}`, {{ method: 'POST' }});
                const data = await res.json();
                if (data.settings) {{
                    currentSettings = data.settings;
                    document.getElementById('setting-temperature').value = currentSettings.temperature;
                    document.getElementById('temp-value').textContent = currentSettings.temperature;
                    document.getElementById('setting-max-tokens').value = currentSettings.max_tokens;
                    updateModeButtons(mode);
                }}
            }} catch (error) {{
                console.error('Failed to set mode:', error);
            }}
        }}
        
        function updateModeButtons(activeMode) {{
            ['fast', 'balanced', 'deep'].forEach(mode => {{
                const btn = document.getElementById(`mode-${{mode}}`);
                if (mode === activeMode) {{
                    btn.className = 'flex-1 btn btn-primary text-xs py-1.5';
                }} else {{
                    btn.className = 'flex-1 btn btn-secondary text-xs py-1.5';
                }}
            }});
        }}
        
        // ============================================================================
        // SESSIONS MANAGEMENT
        // ============================================================================
        
        async function loadSessions() {{
            try {{
                const res = await fetch('/api/sessions');
                const sessions = await res.json();
                renderSessions(sessions);
            }} catch (error) {{
                console.error('Failed to load sessions:', error);
            }}
        }}
        
        function renderSessions(sessions) {{
            const container = document.getElementById('sessions-list');
            
            if (sessions.length === 0) {{
                container.innerHTML = '<div class="text-sm text-gray-400 text-center py-4">No saved sessions</div>';
                return;
            }}
            
            container.innerHTML = sessions.map(s => {{
                const isCurrent = s.id === (currentSessionId || '');
                const date = new Date(s.updated_at).toLocaleDateString();
                return `
                    <div class="group p-2 rounded-lg border ${{isCurrent ? 'border-violet-500 bg-violet-50' : 'border-gray-200 hover:border-gray-300'}} cursor-pointer transition-colors"
                         onclick="loadSession('${{s.id}}')">
                        <div class="flex items-center justify-between">
                            <span class="text-sm font-medium text-gray-900 truncate flex-1">${{s.name}}</span>
                            ${{isCurrent ? '<i class="fas fa-check text-violet-500 text-xs"></i>' : ''}}
                        </div>
                        <div class="flex items-center justify-between mt-1">
                            <span class="text-xs text-gray-500">${{s.message_count}} msgs · ${{date}}</span>
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
            const name = prompt('Session name (optional):');
            if (name === null) return;  // Cancelled
            
            try {{
                const res = await fetch('/api/sessions', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ name: name || undefined }})
                }});
                const data = await res.json();
                
                if (data.session) {{
                    currentSessionId = data.session.id;
                    document.getElementById('current-session-name').textContent = data.session.name;
                    document.getElementById('session-message-count').textContent = '0';
                    
                    // Clear chat
                    chatMessages.innerHTML = `
                        <div class="text-center py-12">
                            <div class="w-16 h-16 mx-auto mb-4 rounded-2xl bg-gradient-to-br from-violet-500 to-purple-600 flex items-center justify-center text-white text-2xl">
                                <i class="fas fa-wand-magic-sparkles"></i>
                            </div>
                            <h2 class="text-xl font-semibold text-gray-900 mb-2">${{data.session.name}}</h2>
                            <p class="text-gray-500">Start a new conversation.</p>
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
        
        async function loadSession(sessionId) {{
            try {{
                const res = await fetch(`/api/sessions/${{sessionId}}/load`, {{ method: 'POST' }});
                const data = await res.json();
                
                if (data.session) {{
                    currentSessionId = data.session.id;
                    document.getElementById('current-session-name').textContent = data.session.name;
                    document.getElementById('session-message-count').textContent = data.session.message_count;
                    
                    // Load messages
                    sessionMessages = data.messages || [];
                    messageCount = sessionMessages.length;
                    msgCount.textContent = messageCount;
                    
                    // Render messages
                    chatMessages.innerHTML = '';
                    sessionMessages.forEach(m => {{
                        addMessage(m.text, m.sender);
                    }});
                    
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
        
        async function loadMemoryStats() {{
            try {{
                const res = await fetch('/api/memory/stats');
                const data = await res.json();
                
                document.getElementById('memory-count').textContent = 
                    `${{data.sqlite_count || 0}} memories`;
                document.getElementById('memory-graph-status').textContent = 
                    data.graph_available ? '(Graph ✅)' : '(SQLite only)';
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
        }});
    </script>
</body>
</html>"""
    
    return HTMLResponse(content=html_content)


@app.post("/api/chat")
async def chat(request: Request):
    """Process chat request using the configured provider."""
    global web_messages, current_session, settings
    
    try:
        body = await request.json()
        user_message = body.get("message", "")
        
        if not user_message:
            return JSONResponse({"error": "Empty message"}, status_code=400)
        
        # Add user message to session
        web_messages.append({"sender": "user", "text": user_message, "timestamp": datetime.now().isoformat()})
        
        # Build messages for the provider
        messages = []
        
        # Add system context if available
        config = load_config()
        agent_name = config.get("agent", {}).get("name", "Assistant")
        system_msg = f"You are {agent_name}, a helpful AI assistant."
        
        # Try to load SOUL.md for personality
        soul_path = Path("/app/workspace/SOUL.md")
        if not soul_path.exists():
            soul_path = Path("./workspace/SOUL.md")
        if soul_path.exists():
            try:
                soul_content = soul_path.read_text()
                system_msg = f"{soul_content}\n\nYou are {agent_name}."
            except:
                pass
        
        # Add file upload instructions if there's an attachment
        if currentAttachment:
            system_msg += "\n\n[CRITICAL SYSTEM NOTE: The user has uploaded a file. The file IS ALREADY SAVED in the system. The file content is shown below. DO NOT explain storage solutions or say you cannot store files. Simply acknowledge receipt and process/analyze the content as requested.]"
        
        messages.append({"role": "system", "content": system_msg})
        
        # Add conversation history (last 10 messages)
        for msg in web_messages[-10:]:
            role = "user" if msg["sender"] == "user" else "assistant"
            messages.append({"role": role, "content": msg["text"]})
        
        # Get response from the configured provider
        print(f"🤖 Chat: provider={settings.provider}, model={settings.model}, temp={settings.temperature}, max_tokens={settings.max_tokens}", flush=True)
        
        try:
            assistant_message = await chat_with_provider(
                provider=settings.provider,
                model=settings.model,
                messages=messages,
                temperature=settings.temperature,
                max_tokens=settings.max_tokens
            )
            print(f"✅ Response received from {settings.model}", flush=True)
        except Exception as provider_error:
            # Fallback to Kimi Agent if direct provider fails
            try:
                async with httpx.AsyncClient(timeout=60.0) as client:
                    response = await client.post(
                        f"{KIMI_AGENT_URL}/chat",
                        json={
                            "user_id": "web_user",
                            "message": user_message,
                            "context": {}
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
        
        # Auto-save session if enabled
        if settings.auto_save and current_session:
            current_session.messages = web_messages
            current_session.message_count = len(web_messages)
            current_session.updated_at = datetime.now().isoformat()
            save_session(current_session)
        
        return JSONResponse({
            "response": assistant_message,
            "model_used": settings.model,
            "provider": settings.provider
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
    """Load settings from file or return defaults."""
    if SETTINGS_FILE.exists():
        try:
            with open(SETTINGS_FILE) as f:
                return Settings(**json.load(f))
        except:
            pass
    return Settings()

def save_settings(settings: Settings):
    """Save settings to file."""
    with open(SETTINGS_FILE, 'w') as f:
        json.dump(settings.dict(), f, indent=2)

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

def create_session(name: str = None) -> Session:
    """Create a new session."""
    now = datetime.now().isoformat()
    session = Session(
        id=str(uuid.uuid4())[:8],
        name=name or f"Session {now[:10]}",
        created_at=now,
        updated_at=now,
        message_count=0,
        messages=[]
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

async def chat_with_provider(provider: str, model: str, messages: list, temperature: float, max_tokens: int):
    """Send chat completion request to the selected provider."""
    
    if provider == "kimi":
        client = get_kimi_client()
        if not client:
            raise Exception("Kimi API key not configured")
        
        response = client.messages.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        return response.content[0].text
    
    elif provider == "anthropic":
        client = get_anthropic_client()
        if not client:
            raise Exception("Anthropic API key not configured")
        
        response = client.messages.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        return response.content[0].text
    
    elif provider == "openai":
        client = get_openai_client()
        if not client:
            raise Exception("OpenAI API key not configured")
        
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        return response.choices[0].message.content
    
    elif provider == "openrouter":
        client = get_openrouter_client()
        if not client:
            raise Exception("OpenRouter API key not configured")
        
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        return response.choices[0].message.content
    
    else:
        raise Exception(f"Unknown provider: {provider}")

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
        "openrouter": os.getenv("OPENROUTER_API_KEY") is not None
    }
    
    # Only include providers with API keys
    enabled_providers = [p for p, enabled in available.items() if enabled]
    enabled_models = {p: PROVIDER_MODELS[p] for p in enabled_providers}
    
    return JSONResponse({
        "providers": enabled_providers,  # Only enabled
        "models": enabled_models,  # Only enabled
        "all_providers": list(PROVIDER_MODELS.keys()),  # All for reference
        "all_models": PROVIDER_MODELS,  # All for reference
        "available": available,  # Status of each
        "modes": list(MODE_PRESETS.keys()),
        "mode_presets": MODE_PRESETS,
        "message": "Add API keys to .env to enable more providers" if len(enabled_providers) < 4 else None
    })

@app.post("/api/settings/mode/{mode}")
async def set_mode(mode: str):
    """Set mode preset (fast, balanced, deep)."""
    global settings
    if mode not in MODE_PRESETS:
        return JSONResponse({"error": f"Unknown mode: {mode}"}, status_code=400)
    
    preset = MODE_PRESETS[mode]
    settings.temperature = preset["temperature"]
    settings.max_tokens = preset["max_tokens"]
    settings.mode = mode
    save_settings(settings)
    return JSONResponse({"status": "ok", "settings": settings.dict()})

# Session endpoints
@app.get("/api/sessions")
async def get_sessions():
    """Get all saved sessions."""
    sessions = load_sessions()
    return JSONResponse([s.dict() for s in sessions])

@app.post("/api/sessions")
async def create_new_session(request: Request):
    """Create a new session."""
    global current_session, web_messages
    try:
        data = await request.json()
        name = data.get("name", f"Session {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        
        # Save current session first
        if current_session:
            current_session.messages = web_messages
            current_session.message_count = len(web_messages)
            current_session.updated_at = datetime.now().isoformat()
            save_session(current_session)
        
        # Create new session
        current_session = create_session(name)
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

@app.get("/api/memory/stats")
async def get_memory_stats():
    """Get memory statistics."""
    global hybrid_memory
    
    if not hybrid_memory:
        return JSONResponse({
            "sqlite_count": 0,
            "graph_available": False,
            "categories": [],
            "message": "Hybrid memory not available"
        })
    
    try:
        stats = hybrid_memory.get_stats()
        return JSONResponse(stats)
    except Exception as e:
        return JSONResponse({
            "sqlite_count": 0,
            "graph_available": False,
            "categories": [],
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

@app.get("/health")
async def health():
    """Health check endpoint."""
    kimi_status = "unknown"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{KIMI_AGENT_URL}/health")
            if response.status_code == 200:
                kimi_status = "ok"
            else:
                kimi_status = "error"
    except:
        kimi_status = "offline"
    
    # Check providers
    providers = await providers_status()
    
    return {
        "status": "healthy",
        "kimi_agent_url": KIMI_AGENT_URL,
        "kimi_agent_status": kimi_status,
        "web_ui_version": "2.1.0",
        "features": ["settings", "sessions", "hybrid_memory", "multi_provider"],
        "current_provider": settings.provider,
        "current_model": settings.model,
        "providers_available": {k: v["available"] for k, v in providers.items()}
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=WEB_UI_PORT)
