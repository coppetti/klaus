"""
Web UI for IDE Agent Wizard
============================
Modern Shadcn-inspired interface with chat + config panel
Uses Hybrid Memory (SQLite + Graph) for intelligent context
"""

import os
import json
import sys
import httpx
from datetime import datetime
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from pathlib import Path
import yaml

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

app = FastAPI(title="IDE Agent Wizard - Web UI")

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
    <title>{agent_name} - AI Assistant</title>
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
<body class="h-screen overflow-hidden">
    <div class="flex h-full">
        <!-- Chat Area (2/3) -->
        <div class="flex-1 flex flex-col border-r border-gray-200">
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
                <div class="flex gap-3">
                    <input 
                        type="text" 
                        id="message-input" 
                        class="input-field flex-1" 
                        placeholder="Type your message..."
                        autocomplete="off"
                    >
                    <button id="send-btn" class="btn btn-primary px-4">
                        <i class="fas fa-paper-plane"></i>
                    </button>
                </div>
            </div>
        </div>
        
        <!-- Config Panel (1/3) -->
        <div class="w-96 bg-white flex flex-col">
            <div class="p-6 border-b border-gray-200">
                <h2 class="font-semibold text-gray-900 flex items-center gap-2">
                    <i class="fas fa-sliders"></i>
                    Configuration
                </h2>
            </div>
            
            <div class="flex-1 overflow-y-auto p-6 space-y-6">
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
                        Session
                    </h3>
                    <div class="space-y-3">
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
                        <button onclick="compactContext()" class="btn btn-secondary w-full text-sm">
                            <i class="fas fa-compress"></i>
                            Compact Context
                        </button>
                        <button onclick="resetSession()" class="btn btn-destructive w-full text-sm">
                            <i class="fas fa-rotate-right"></i>
                            Reset Session
                        </button>
                        <button onclick="checkHealth()" class="btn btn-secondary w-full text-sm">
                            <i class="fas fa-stethoscope"></i>
                            Health Check
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
            <div class="p-4 border-t border-gray-200 bg-gray-50">
                <p class="text-xs text-gray-500 text-center">
                    IDE Agent Wizard v1.1.0
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
        
        function addMessage(text, sender) {{
            const div = document.createElement('div');
            div.className = 'flex ' + (sender === 'user' ? 'justify-end' : 'justify-start');
            
            const bubble = document.createElement('div');
            bubble.className = sender === 'user' ? 'chat-bubble-user' : 'chat-bubble-assistant';
            bubble.className += ' max-w-[85%] px-4 py-3';
            
            const senderLabel = document.createElement('div');
            senderLabel.className = 'font-medium text-xs opacity-70 mb-2';
            senderLabel.textContent = sender === 'user' ? USER_NAME : AGENT_NAME;
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
            if (!text) return;
            
            addMessage(text, 'user');
            messageInput.value = '';
            sendBtn.disabled = true;
            typingIndicator.classList.remove('hidden');
            
            try {{
                const response = await fetch('/api/chat', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ message: text }})
                }});
                
                typingIndicator.classList.add('hidden');
                
                const data = await response.json();
                if (data.response) {{
                    addMessage(data.response, 'assistant');
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
            }}
        }}
    </script>
</body>
</html>"""
    
    return HTMLResponse(content=html_content)


@app.post("/api/chat")
async def chat(request: Request):
    """Proxy chat request to Kimi Agent."""
    try:
        body = await request.json()
        user_message = body.get("message", "")
        
        if not user_message:
            return JSONResponse({"error": "Empty message"}, status_code=400)
        
        # Forward to Kimi Agent (endpoint /chat)
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
                return JSONResponse({"response": assistant_message})
            else:
                return JSONResponse(
                    {"error": f"Kimi Agent error: {response.status_code}"},
                    status_code=502
                )
                
    except httpx.ConnectError:
        return JSONResponse(
            {"error": "Cannot connect to Kimi Agent. Is it running?"},
            status_code=503
        )
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# In-memory message storage for the web session
web_messages = []

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
    global web_messages, hybrid_memory
    
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
        
        # Clear web session messages
        message_count = len(web_messages)
        web_messages = []
        
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
    
    return {
        "status": "healthy",
        "kimi_agent_url": KIMI_AGENT_URL,
        "kimi_agent_status": kimi_status
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=WEB_UI_PORT)
