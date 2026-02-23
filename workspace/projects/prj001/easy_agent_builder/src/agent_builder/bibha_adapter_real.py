"""
Bibha.ai Real Adapter
=====================

Implementação REAL de integração com Bibha.ai AgentsHub
baseada na documentação oficial.

Endpoints utilizados:
- POST /api/v1/prediction/{chatflowId} - Enviar mensagem
- GET /api/v1/chatflows - Listar chatflows
"""

import json
import os
from typing import Any, Dict, Optional

import aiohttp
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field


class BibhaConfig(BaseModel):
    """Configuração da integração Bibha.ai."""
    api_host: str = Field(default="https://your-agentshub.com")
    api_key: str
    chatflow_id: Optional[str] = None
    
    class Config:
        env_prefix = "BIBHA_"


class BibhaIncomingRequest(BaseModel):
    """
    Request recebido da Bibha.ai.
    
    Baseado na documentação real da API.
    """
    question: str
    sessionId: Optional[str] = None
    chatflowId: Optional[str] = None
    overrideConfig: Optional[Dict[str, Any]] = Field(default_factory=dict)
    
    # Campos adicionais que a Bibha pode enviar
    history: Optional[list] = None
    metadata: Optional[Dict[str, Any]] = None


class BibhaOutgoingResponse(BaseModel):
    """
    Response enviado para Bibha.ai.
    
    Baseado na documentação real da API.
    """
    text: str
    chatId: Optional[str] = None
    chatMessageId: Optional[str] = None
    sourceDocuments: Optional[list] = None
    sessionId: Optional[str] = None
    
    # Campos adicionais
    actions: Optional[list] = Field(default_factory=list)
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class BibhaExternalAdapter:
    """
    Adapter REAL para integração Bibha.ai.
    
    Esta classe implementa a integração bidirecional:
    1. Recebe requests da Bibha (webhook/HTTP Tool)
    2. Processa via agente ADK
    3. Retorna no formato esperado pela Bibha
    
    Usage:
        adapter = BibhaExternalAdapter(
            agent=meu_agente_adk,
            config=BibhaConfig(api_key="bah-sk-xxx")
        )
        
        app = adapter.create_api()
    """
    
    def __init__(
        self,
        agent: Any,
        config: BibhaConfig,
        session_store: Optional[Any] = None
    ):
        self.agent = agent
        self.config = config
        self.session_store = session_store
        
        # Setup ADK
        from google.adk.runners import Runner
        from google.adk.sessions import InMemorySessionService
        
        self.session_service = InMemorySessionService()
        self.runner = Runner(agent=agent, session_service=self.session_service)
    
    def create_api(self) -> FastAPI:
        """
        Criar API FastAPI com endpoints Bibha.
        
        Esta API expõe endpoints compatíveis com a Bibha.ai
        para receber mensagens e retornar respostas.
        """
        app = FastAPI(
            title=f"Bibha Adapter: {self.agent.name}",
            description="API de integração com Bibha.ai AgentsHub",
            version="1.0.0"
        )
        
        @app.post("/api/v1/prediction/{chatflow_id}")
        async def prediction(chatflow_id: str, request: Request):
            """
            Endpoint compatível com Bibha.ai prediction API.
            
            Recebe mensagens da Bibha e processa via agente ADK.
            """
            try:
                # Parse request
                body = await request.json()
                bibha_request = BibhaIncomingRequest(**body)
                
                # Processar
                response = await self._process_message(
                    chatflow_id=chatflow_id,
                    request=bibha_request
                )
                
                return response
                
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @app.post("/webhook/bibha")
        async def webhook(request: Request):
            """
            Webhook para receber mensagens da Bibha.
            
            Formato alternativo para integração webhook.
            """
            try:
                body = await request.json()
                
                # Extrair dados do webhook Bibha
                question = body.get("question") or body.get("message")
                session_id = body.get("sessionId") or body.get("session_id")
                chatflow_id = body.get("chatflowId") or "default"
                
                if not question:
                    raise HTTPException(status_code=400, detail="Missing question/message")
                
                # Criar request
                bibha_request = BibhaIncomingRequest(
                    question=question,
                    sessionId=session_id,
                    chatflowId=chatflow_id
                )
                
                # Processar
                response = await self._process_message(
                    chatflow_id=chatflow_id,
                    request=bibha_request
                )
                
                return response
                
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @app.get("/health")
        async def health():
            """Health check."""
            return {
                "status": "healthy",
                "agent": self.agent.name,
                "api": "bibha-compatible"
            }
        
        return app
    
    async def _process_message(
        self,
        chatflow_id: str,
        request: BibhaIncomingRequest
    ) -> Dict[str, Any]:
        """
        Processar mensagem recebida da Bibha.
        
        Args:
            chatflow_id: ID do chatflow
            request: Request da Bibha
            
        Returns:
            Response no formato Bibha
        """
        # Criar/Recuperar sessão
        session_id = request.sessionId or self._generate_session_id()
        
        adk_session = self.session_service.get_session(
            app_name=self.agent.name,
            user_id="bibha",
            session_id=session_id
        )
        
        if not adk_session:
            adk_session = self.session_service.create_session(
                app_name=self.agent.name,
                user_id="bibha",
                session_id=session_id
            )
        
        # Executar agente
        events = []
        async for event in self.runner.run_async(
            user_id="bibha",
            session_id=session_id,
            new_message=request.question
        ):
            events.append(event)
        
        # Extrair resposta
        response_text = self._extract_response(events)
        
        # Construir response Bibha
        return {
            "text": response_text,
            "chatId": f"chat-{session_id}",
            "chatMessageId": f"msg-{self._generate_id()}",
            "sessionId": session_id,
            "sourceDocuments": [],  # Preencher se usar RAG
            "metadata": {
                "agent": self.agent.name,
                "chatflowId": chatflow_id
            }
        }
    
    def _extract_response(self, events: list) -> str:
        """Extrair texto de resposta dos eventos ADK."""
        if not events:
            return "Desculpe, não consegui processar sua mensagem."
        
        for event in reversed(events):
            if hasattr(event, 'content') and event.content:
                return str(event.content)
            if hasattr(event, 'text') and event.text:
                return str(event.text)
        
        return "Processamento concluído."
    
    def _generate_session_id(self) -> str:
        """Gerar ID de sessão único."""
        import uuid
        return str(uuid.uuid4())[:8]
    
    def _generate_id(self) -> str:
        """Gerar ID único."""
        import uuid
        return str(uuid.uuid4())[:12]
    
    # ============================================================
    # Cliente para chamar API da Bibha (se necessário)
    # ============================================================
    
    async def call_bibha_api(
        self,
        question: str,
        chatflow_id: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> BibhaOutgoingResponse:
        """
        Chamar API da Bibha.ai.
        
        Útil se você quiser que seu agente chame um chatflow
        da Bibha como parte do processamento.
        
        Args:
            question: Pergunta/mensagem
            chatflow_id: ID do chatflow Bibha
            session_id: ID da sessão
            
        Returns:
            Resposta da Bibha
        """
        target_chatflow = chatflow_id or self.config.chatflow_id
        
        if not target_chatflow:
            raise ValueError("chatflow_id é obrigatório")
        
        url = f"{self.config.api_host}/api/v1/prediction/{target_chatflow}"
        
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "question": question,
            "sessionId": session_id or self._generate_session_id()
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload) as response:
                if response.status != 200:
                    raise Exception(f"Bibha API error: {response.status}")
                
                data = await response.json()
                return BibhaOutgoingResponse(**data)


# ============================================================
# Exemplo de Uso
# ============================================================

if __name__ == "__main__":
    """
    Exemplo de uso do adapter.
    
    1. Configure as variáveis de ambiente:
       export BIBHA_API_KEY=bah-sk-your-key
       export BIBHA_API_HOST=https://your-agentshub.com
    
    2. Execute:
       python bibha_adapter_real.py
    """
    import uvicorn
    from google.adk.agents import LlmAgent
    from google.adk.tools import google_search
    
    # Criar agente exemplo
    agent = LlmAgent(
        model="gemini-2.0-flash-exp",
        name="bibha_integrated_agent",
        description="Agente integrado com Bibha.ai",
        instruction="""
        Você é um assistente virtual integrado à plataforma Bibha.ai.
        
        Responda de forma profissional e útil.
        Use ferramentas disponíveis quando necessário.
        """,
        tools=[google_search]
    )
    
    # Configurar adapter
    config = BibhaConfig(
        api_key=os.getenv("BIBHA_API_KEY", "your-api-key"),
        api_host=os.getenv("BIBHA_API_HOST", "https://your-agentshub.com"),
        chatflow_id=os.getenv("BIBHA_CHATFLOW_ID")
    )
    
    adapter = BibhaExternalAdapter(agent=agent, config=config)
    app = adapter.create_api()
    
    print("🚀 Iniciando Bibha Adapter...")
    print(f"   Agente: {agent.name}")
    print(f"   API Host: {config.api_host}")
    print("\nEndpoints disponíveis:")
    print("  POST /api/v1/prediction/{chatflow_id}")
    print("  POST /webhook/bibha")
    print("  GET  /health")
    
    uvicorn.run(app, host="0.0.0.0", port=8080)
