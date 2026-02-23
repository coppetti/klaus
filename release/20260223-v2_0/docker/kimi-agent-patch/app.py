"""
Agente Clawd - API Server (Patched for AGENTS.md support)
Integração com Kimi API + Sincronização de Memórias
"""

import os
import json
from typing import Optional, List, Dict
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from anthropic import Anthropic

from session_manager import SessionManager
from sync_api import router as sync_router

# Configuração
KIMI_API_KEY = os.getenv("KIMI_API_KEY", "")
KIMI_MODEL = os.getenv("KIMI_MODEL", "k2p5")
KIMI_BASE_URL = "https://api.kimi.com/coding"
SOUL_MD_PATH = os.getenv("SOUL_MD_PATH", "/app/clawd/workspace/SOUL.md")
USER_MD_PATH = os.getenv("USER_MD_PATH", "/app/clawd/workspace/USER.md")
AGENTS_MD_PATH = os.getenv("AGENTS_MD_PATH", "/app/docs/AGENTS.md")
CLAWD_WORKSPACE = os.getenv("CLAWD_WORKSPACE", "/app/clawd")

# Cliente Anthropic (compatível com API Kimi)
client = Anthropic(
    api_key=KIMI_API_KEY,
    base_url=KIMI_BASE_URL
)

# Gerenciador de sessões
sessions = SessionManager()

app = FastAPI(title="Clawd Agent", version="2.0.0-patched")

# Incluir rotas de sincronização
app.include_router(sync_router, prefix="/api")

def load_workspace_context() -> str:
    """Carrega contexto completo do workspace: INIT.md, SOUL.md, USER.md, STRUCTURE.md, AGENTS.md."""
    parts = []
    
    # Carregar AGENTS.md (guia do agente - PRIMEIRO para prioridade)
    agents_path = Path(AGENTS_MD_PATH)
    if agents_path.exists():
        parts.append("# GUIA DO AGENTE (AGENTS.md)\n")
        parts.append(agents_path.read_text())
        parts.append("\n")
        print(f"✅ AGENTS.md carregado: {agents_path}", flush=True)
    else:
        print(f"⚠️ AGENTS.md não encontrado em {agents_path}", flush=True)
    
    # Carregar INIT.md (documentação técnica completa)
    init_path = Path(CLAWD_WORKSPACE) / "INIT.md"
    if init_path.exists():
        parts.append("# DOCUMENTAÇÃO TÉCNICA (INIT.md)\n")
        parts.append(init_path.read_text())
        print(f"✅ INIT.md carregado: {init_path}", flush=True)
    else:
        print(f"⚠️ INIT.md não encontrado em {init_path}", flush=True)
    
    # Carregar SOUL.md
    soul_path = Path(SOUL_MD_PATH)
    if soul_path.exists():
        parts.append("\n\n# PERSONALIDADE (SOUL.md)\n")
        parts.append(soul_path.read_text())
        print(f"✅ SOUL.md carregado: {SOUL_MD_PATH}", flush=True)
    else:
        print(f"⚠️ SOUL.md não encontrado em {SOUL_MD_PATH}", flush=True)
        parts.append("# Clawd\nVocê é o Clawd, braço direito de código.")
    
    # Carregar USER.md (perfil do usuário)
    user_path = Path(USER_MD_PATH)
    if user_path.exists():
        parts.append("\n\n# PERFIL DO USUÁRIO (USER.md)\n")
        parts.append(user_path.read_text())
        print(f"✅ USER.md carregado: {USER_MD_PATH}", flush=True)
    
    # Carregar STRUCTURE.md (estrutura do workspace)
    structure_path = Path(CLAWD_WORKSPACE) / "STRUCTURE.md"
    if structure_path.exists():
        parts.append("\n\n# ESTRUTURA DO WORKSPACE (STRUCTURE.md)\n")
        parts.append(structure_path.read_text())
        print(f"✅ STRUCTURE.md carregado: {structure_path}", flush=True)
    else:
        print(f"⚠️ STRUCTURE.md não encontrado em {structure_path}", flush=True)
    
    return "\n".join(parts)

# Carregar system prompt completo
SOUL_PROMPT = load_workspace_context()

CLAWD_SYSTEM_PROMPT = f"""{SOUL_PROMPT}

CONTEXTO DA SESSÃO:
- Você tem acesso às últimas 10 mensagens desta conversa
- Quando detectar algo importante (preferências do usuário, fatos relevantes, decisões), sugira salvar na memória
- Seja proativo em lembrar contexto de conversas anteriores quando relevante

REGRAS DE FERRAMENTAS/INTERNET:
- **NUNCA** use ferramentas de busca web a menos que o usuário peça EXPLICITAMENTE
- **NUNCA** pesquise na internet por padrão
- Responda baseado apenas no seu conhecimento interno e contexto da conversa
- Se o usuário quiser buscar algo, ele deve dizer explicitamente: "pesquise...", "busque na web...", "google..."
- Se não souber algo, admita que não sabe ou diga que precisa pesquisar se quiser

REGRAS DE RESPOSTA:
- Responda como se estivesse conversando diretamente com o usuário
- Mantenha o tom definido acima
- Use o contexto disponível para respostas personalizadas"""


# Models
class ChatRequest(BaseModel):
    user_id: str
    message: str
    context: Optional[Dict] = None  # Dados do Clawd local (memórias, preferências)


class ChatResponse(BaseModel):
    response: str
    session_id: str
    messages_in_session: int
    memory_update: Optional[Dict] = None  # Sugestão de memória para salvar


class SessionData(BaseModel):
    user_id: str


@app.get("/health")
def health():
    """Health check."""
    return {
        "status": "ok",
        "model": KIMI_MODEL,
        "provider": "kimi",
        "personality_loaded": Path(SOUL_MD_PATH).exists(),
        "agents_guide_loaded": Path(AGENTS_MD_PATH).exists(),
        "sessions": sessions.get_stats()
    }


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    """
    Processa mensagem do usuário e retorna resposta do Clawd.
    Mantém contexto da sessão automaticamente.
    """
    try:
        # 1. Adicionar mensagem do usuário à sessão
        session = sessions.add_message(
            user_id=request.user_id,
            role="user",
            content=request.message
        )
        
        # 2. Construir contexto completo
        context_parts = []
        
        # Memórias do Clawd local (se vieram no context)
        if request.context and request.context.get("memories"):
            memories = request.context["memories"]
            if memories:
                context_parts.append("MEMÓRIAS DO USUÁRIO:")
                for mem in memories[:3]:  # Top 3 memórias
                    context_parts.append(f"- [{mem.get('type', 'fact')}] {mem.get('content', '')}")
                context_parts.append("")
        
        # Username se disponível
        if request.context and request.context.get("username"):
            context_parts.append(f"Usuário: {request.context['username']}")
        
        context_str = "\n".join(context_parts) if context_parts else ""
        
        # 3. Preparar mensagens para API (formato Anthropic)
        messages = []
        
        # Primeiro, adicionar contexto do sistema como uma mensagem inicial (se houver)
        if context_str:
            context_prefix = f"[Contexto do sistema]\n{context_str}\n\n---\n\n"
        else:
            context_prefix = ""
        
        # Adicionar mensagens da sessão
        for i, msg in enumerate(session.messages):
            content = msg.content
            # Se for a última mensagem (a atual) e tiver contexto, adicionar prefixo
            if i == len(session.messages) - 1 and msg.role == "user" and context_prefix:
                content = context_prefix + content
            
            messages.append({
                "role": msg.role,
                "content": content
            })
        
        # 4. Chamar API do Kimi
        response = client.messages.create(
            model=KIMI_MODEL,
            max_tokens=4096,
            system=CLAWD_SYSTEM_PROMPT,
            messages=messages
        )
        
        response_text = response.content[0].text
        
        # 5. Salvar resposta na sessão
        sessions.add_message(
            user_id=request.user_id,
            role="assistant",
            content=response_text,
            metadata={
                "model": KIMI_MODEL,
                "provider": "kimi",
                "input_tokens": response.usage.input_tokens if response.usage else None,
                "output_tokens": response.usage.output_tokens if response.usage else None
            }
        )
        
        # 6. Detectar sugestão de memória (heurísticas)
        memory_update = detect_memory_update(request.message, response_text)
        
        return ChatResponse(
            response=response_text,
            session_id=session.session_id,
            messages_in_session=len(session.messages),
            memory_update=memory_update
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def detect_memory_update(user_message: str, assistant_response: str) -> Optional[Dict]:
    """
    Detecta se há algo importante para salvar na memória.
    Retorna None se não detectar nada relevante.
    """
    msg_lower = user_message.lower()
    
    # Preferências do usuário
    preference_keywords = [
        "prefiro", "gosto de", "não gosto", "odeio", "sempre uso", 
        "nunca uso", "minha preferência", "eu quero", "eu gosto"
    ]
    if any(kw in msg_lower for kw in preference_keywords):
        return {
            "type": "preference",
            "content": f"Usuário expressou preferência: {user_message}",
            "importance": 0.8
        }
    
    # Decisões arquiteturais
    decision_keywords = [
        "decidi", "vamos usar", "escolhi", "vou adotar", 
        "arquitetura", "padrão", "vamos seguir"
    ]
    if any(kw in msg_lower for kw in decision_keywords):
        return {
            "type": "decision",
            "content": f"Decisão tomada: {user_message}",
            "importance": 0.9
        }
    
    # Fatos importantes
    fact_keywords = [
        "lembre", "anota", "importante", "não esquece",
        "guarda isso", "salva essa info"
    ]
    if any(kw in msg_lower for kw in fact_keywords):
        return {
            "type": "fact",
            "content": user_message,
            "importance": 0.7
        }
    
    # Código importante
    if "```" in user_message and any(kw in msg_lower for kw in ["snippet", "útil", "salvar"]):
        return {
            "type": "code",
            "content": user_message,
            "importance": 0.6
        }
    
    return None


@app.post("/session/clear")
def clear_session(data: SessionData):
    """Limpa sessão do usuário."""
    sessions.clear_session(data.user_id)
    return {"status": "ok", "message": "Sessão limpa"}


@app.get("/session/{user_id}")
def get_session(user_id: str):
    """Retorna dados da sessão (para debug)."""
    session = sessions.get_or_create_session(user_id)
    return {
        "session_id": session.session_id,
        "user_id": session.user_id,
        "messages_count": len(session.messages),
        "created_at": session.created_at,
        "last_activity": session.last_activity,
        "context": session.context_data,
        "messages": [
            {"role": m.role, "content": m.content, "time": m.timestamp}
            for m in session.messages
        ]
    }


@app.get("/stats")
def stats():
    """Estatísticas do sistema."""
    return sessions.get_stats()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
