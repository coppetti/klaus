"""
Web UI for IDE Agent Wizard
============================
Simple web interface that talks to Kimi Agent (port 8081)
"""

import os
import json
import httpx
from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from pathlib import Path
import yaml

app = FastAPI(title="IDE Agent Wizard - Web UI")

# Config
KIMI_AGENT_URL = os.getenv("KIMI_AGENT_URL", "http://kimi-agent:8081")
WEB_UI_PORT = int(os.getenv("WEB_UI_PORT", "8082"))

# Load agent info from init.yaml (if exists)
def load_agent_info():
    """Load agent name and personality from init.yaml."""
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
                    config = yaml.safe_load(f)
                    return {
                        "name": config.get("agent", {}).get("name", "Assistant"),
                        "template": config.get("agent", {}).get("template", "general"),
                    }
            except Exception:
                pass
    
    return {"name": "Assistant", "template": "general"}

@app.get("/", response_class=HTMLResponse)
async def get_chat_page():
    """Serve the chat interface."""
    agent_info = load_agent_info()
    
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{agent_name}} - Web Chat</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            height: 100vh;
            display: flex;
            flex-direction: column;
        }}
        
        .header {{
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            padding: 1rem 2rem;
            color: white;
            border-bottom: 1px solid rgba(255, 255, 255, 0.2);
        }}
        
        .header h1 {{
            font-size: 1.5rem;
            font-weight: 600;
        }}
        
        .header .subtitle {{
            font-size: 0.875rem;
            opacity: 0.8;
            margin-top: 0.25rem;
        }}
        
        .chat-container {{
            flex: 1;
            overflow-y: auto;
            padding: 2rem;
            display: flex;
            flex-direction: column;
            gap: 1rem;
        }}
        
        .message {{
            max-width: 70%;
            padding: 1rem 1.25rem;
            border-radius: 1rem;
            animation: fadeIn 0.3s ease;
        }}
        
        @keyframes fadeIn {{
            from {{ opacity: 0; transform: translateY(10px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}
        
        .message.user {{
            background: white;
            color: #333;
            align-self: flex-end;
            border-bottom-right-radius: 0.25rem;
        }}
        
        .message.assistant {{
            background: rgba(255, 255, 255, 0.95);
            color: #333;
            align-self: flex-start;
            border-bottom-left-radius: 0.25rem;
        }}
        
        .message .sender {{
            font-size: 0.75rem;
            font-weight: 600;
            margin-bottom: 0.25rem;
            opacity: 0.6;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        
        .input-container {{
            background: white;
            padding: 1rem 2rem;
            border-top: 1px solid #e0e0e0;
            display: flex;
            gap: 0.75rem;
        }}
        
        #message-input {{
            flex: 1;
            padding: 0.875rem 1.25rem;
            border: 2px solid #e0e0e0;
            border-radius: 0.75rem;
            font-size: 1rem;
            outline: none;
            transition: border-color 0.2s;
        }}
        
        #message-input:focus {{
            border-color: #667eea;
        }}
        
        #send-btn {{
            padding: 0.875rem 1.5rem;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 0.75rem;
            font-size: 1rem;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s;
        }}
        
        #send-btn:hover {{
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
        }}
        
        #send-btn:active {{
            transform: translateY(0);
        }}
        
        #send-btn:disabled {{
            opacity: 0.6;
            cursor: not-allowed;
        }}
        
        .typing {{
            display: none;
            align-self: flex-start;
            background: rgba(255, 255, 255, 0.7);
            padding: 1rem 1.5rem;
            border-radius: 1rem;
            border-bottom-left-radius: 0.25rem;
        }}
        
        .typing.visible {{
            display: block;
        }}
        
        .typing-dots {{
            display: flex;
            gap: 0.25rem;
        }}
        
        .typing-dots span {{
            width: 8px;
            height: 8px;
            background: #667eea;
            border-radius: 50%;
            animation: typing 1.4s infinite;
        }}
        
        .typing-dots span:nth-child(2) {{
            animation-delay: 0.2s;
        }}
        
        .typing-dots span:nth-child(3) {{
            animation-delay: 0.4s;
        }}
        
        @keyframes typing {{
            0%, 60%, 100% {{ transform: translateY(0); }}
            30% {{ transform: translateY(-10px); }}
        }}
        
        .welcome {{
            text-align: center;
            color: white;
            opacity: 0.9;
            margin-bottom: 1rem;
        }}
        
        .welcome h2 {{
            font-size: 2rem;
            margin-bottom: 0.5rem;
        }}
        
        .welcome p {{
            font-size: 1.1rem;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🧙 {agent_info['name']}</h1>
        <div class="subtitle">Template: {agent_info['template']} | Connected to Kimi Agent</div>
    </div>
    
    <div class="chat-container" id="chat-container">
        <div class="welcome">
            <h2>Welcome!</h2>
            <p>Type a message to start chatting with your AI assistant.</p>
        </div>
    </div>
    
    <div class="typing" id="typing">
        <div class="typing-dots">
            <span></span>
            <span></span>
            <span></span>
        </div>
    </div>
    
    <div class="input-container">
        <input type="text" id="message-input" placeholder="Type your message..." autocomplete="off">
        <button id="send-btn" onclick="sendMessage()">Send</button>
    </div>
    
    <script>
        const chatContainer = document.getElementById('chat-container');
        const messageInput = document.getElementById('message-input');
        const sendBtn = document.getElementById('send-btn');
        const typing = document.getElementById('typing');
        
        // Allow Enter key to send
        messageInput.addEventListener('keypress', (e) => {{
            if (e.key === 'Enter') sendMessage();
        }});
        
        function addMessage(text, sender) {{
            const msgDiv = document.createElement('div');
            msgDiv.className = `message ${{sender}}`;
            msgDiv.innerHTML = `
                <div class="sender">${{sender}}</div>
                <div class="text">${{escapeHtml(text)}}</div>
            `;
            chatContainer.appendChild(msgDiv);
            chatContainer.scrollTop = chatContainer.scrollHeight;
        }}
        
        function escapeHtml(text) {{
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }}
        
        async function sendMessage() {{
            const text = messageInput.value.trim();
            if (!text) return;
            
            // Add user message
            addMessage(text, 'user');
            messageInput.value = '';
            sendBtn.disabled = true;
            
            // Show typing indicator
            typing.classList.add('visible');
            chatContainer.scrollTop = chatContainer.scrollHeight;
            
            try {{
                const response = await fetch('/api/chat', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ message: text }})
                }});
                
                const data = await response.json();
                
                // Hide typing and show response
                typing.classList.remove('visible');
                
                if (data.response) {{
                    addMessage(data.response, 'assistant');
                }} else if (data.error) {{
                    addMessage('Error: ' + data.error, 'assistant');
                }}
            }} catch (error) {{
                typing.classList.remove('visible');
                addMessage('Connection error. Please try again.', 'assistant');
            }}
            
            sendBtn.disabled = false;
            messageInput.focus();
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
        
        # Forward to Kimi Agent
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{KIMI_AGENT_URL}/v1/chat/completions",
                json={
                    "model": "kimi-k2-5",
                    "messages": [
                        {"role": "user", "content": user_message}
                    ],
                    "temperature": 0.7,
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                assistant_message = data.get("choices", [{}])[0].get("message", {}).get("content", "")
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


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "kimi_agent": KIMI_AGENT_URL}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=WEB_UI_PORT)
