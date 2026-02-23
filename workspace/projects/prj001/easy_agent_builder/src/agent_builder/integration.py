"""
Integrações - Conectores para plataformas externas.
"""

import asyncio
import json
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field


class SessionStore(ABC):
    """Interface abstrata para armazenamento de sessões."""
    
    @abstractmethod
    async def get(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Recuperar sessão."""
        pass
    
    @abstractmethod
    async def set(self, session_id: str, data: Dict[str, Any], ttl: int = 3600):
        """Salvar sessão."""
        pass
    
    @abstractmethod
    async def delete(self, session_id: str):
        """Deletar sessão."""
        pass


class InMemorySessionStore(SessionStore):
    """Store em memória (apenas para desenvolvimento)."""
    
    def __init__(self):
        self._data: Dict[str, Dict[str, Any]] = {}
    
    async def get(self, session_id: str) -> Optional[Dict[str, Any]]:
        return self._data.get(session_id)
    
    async def set(self, session_id: str, data: Dict[str, Any], ttl: int = 3600):
        self._data[session_id] = data
    
    async def delete(self, session_id: str):
        self._data.pop(session_id, None)


class RedisSessionStore(SessionStore):
    """Store usando Redis (produção)."""
    
    def __init__(self, host: str = "localhost", port: int = 6379):
        try:
            import redis.asyncio as redis
            self.client = redis.Redis(host=host, port=port, decode_responses=True)
        except ImportError:
            raise ImportError("Instale redis: pip install redis")
    
    async def get(self, session_id: str) -> Optional[Dict[str, Any]]:
        data = await self.client.get(f"session:{session_id}")
        return json.loads(data) if data else None
    
    async def set(self, session_id: str, data: Dict[str, Any], ttl: int = 3600):
        await self.client.setex(
            f"session:{session_id}",
            ttl,
            json.dumps(data)
        )
    
    async def delete(self, session_id: str):
        await self.client.delete(f"session:{session_id}")


class BibhaRequest(BaseModel):
    """Request da Bibha.ai."""
    message: str
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class BibhaResponse(BaseModel):
    """Response para Bibha.ai."""
    message: str
    session_id: str
    actions: List[Dict[str, Any]] = Field(default_factory=list)
    context: Dict[str, Any] = Field(default_factory=dict)


class BibhaAdapter:
    """
    Adaptador para integração com Bibha.ai.
    
    Permite expor agentes ADK como endpoints HTTP que podem ser
    consumidos pela plataforma Bibha.ai via HTTP Tool.
    
    Features:
    - Preservação de contexto entre chamadas
    - Transformação de formato ADK <-> Bibha
    - Error handling e retry
    - Webhooks para eventos
    
    Example:
        ```python
        from google.adk.agents import LlmAgent
        from agent_builder.integration import BibhaAdapter, RedisSessionStore
        
        # Seu agente ADK
        agent = LlmAgent(...)
        
        # Adaptador
        adapter = BibhaAdapter(
            agent=agent,
            session_store=RedisSessionStore(),
            webhook_url="https://bibha.ai/webhooks/agent-response"
        )
        
        # FastAPI app
        app = adapter.create_api()
        ```
    """
    
    def __init__(
        self,
        agent: Any,
        session_store: Optional[SessionStore] = None,
        webhook_url: Optional[str] = None,
        webhook_secret: Optional[str] = None,
        timeout: int = 30,
    ):
        """
        Inicializar adaptador.
        
        Args:
            agent: Agente ADK
            session_store: Store para sessões (default: in-memory)
            webhook_url: URL opcional para webhooks
            webhook_secret: Secret para validar webhooks
            timeout: Timeout para execução do agente
        """
        self.agent = agent
        self.session_store = session_store or InMemorySessionStore()
        self.webhook_url = webhook_url
        self.webhook_secret = webhook_secret
        self.timeout = timeout
        
        # Setup ADK runner
        from google.adk.runners import Runner
        from google.adk.sessions import InMemorySessionService
        
        self.session_service = InMemorySessionService()
        self.runner = Runner(agent=agent, session_service=self.session_service)
    
    def create_api(self) -> FastAPI:
        """
        Criar aplicação FastAPI com endpoints.
        
        Returns:
            App FastAPI configurada
        """
        app = FastAPI(
            title=f"Agent API: {self.agent.name}",
            description=f"API REST para agente {self.agent.name}",
            version="1.0.0"
        )
        
        @app.post("/invoke", response_model=BibhaResponse)
        async def invoke(request: BibhaRequest):
            """Endpoint principal de invocação."""
            return await self._handle_invoke(request)
        
        @app.post("/webhook/bibha")
        async def webhook(request: Request):
            """Receber webhooks da Bibha.ai."""
            payload = await request.json()
            # Processar webhook
            return {"status": "received"}
        
        @app.get("/health")
        async def health():
            """Health check."""
            return {
                "status": "healthy",
                "agent": self.agent.name,
                "agent_type": type(self.agent).__name__
            }
        
        return app
    
    async def _handle_invoke(self, request: BibhaRequest) -> BibhaResponse:
        """
        Processar invocação do agente.
        
        Args:
            request: Request da Bibha.ai
            
        Returns:
            Response formatada para Bibha
        """
        try:
            # Recuperar ou criar sessão
            session_id = request.session_id or self._generate_session_id()
            context = await self.session_store.get(session_id) or {}
            
            # Criar/Recuperar sessão ADK
            adk_session = self.session_service.get_session(
                app_name=self.agent.name,
                user_id=request.user_id or "bibha",
                session_id=session_id
            )
            
            if not adk_session:
                adk_session = self.session_service.create_session(
                    app_name=self.agent.name,
                    user_id=request.user_id or "bibha",
                    state=context
                )
                session_id = adk_session.id
            
            # Executar agente
            events = []
            async for event in self.runner.run_async(
                user_id=request.user_id or "bibha",
                session_id=session_id,
                new_message=request.message
            ):
                events.append(event)
            
            # Extrair resposta
            response_text = self._extract_response(events)
            
            # Salvar contexto atualizado
            updated_context = dict(adk_session.state)
            await self.session_store.set(session_id, updated_context)
            
            # Construir resposta Bibha
            return BibhaResponse(
                message=response_text,
                session_id=session_id,
                context=self._filter_context(updated_context)
            )
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    def _extract_response(self, events: List[Any]) -> str:
        """Extrair texto de resposta dos eventos ADK."""
        if not events:
            return "Nenhuma resposta gerada"
        
        # Pegar último evento com conteúdo
        for event in reversed(events):
            if hasattr(event, 'content') and event.content:
                return str(event.content)
            if hasattr(event, 'text') and event.text:
                return str(event.text)
        
        return "Processamento concluído"
    
    def _filter_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Filtrar contexto para envio (remover dados sensíveis)."""
        # Remover chaves internas do ADK
        filtered = {}
        for key, value in context.items():
            if not key.startswith("_") and key not in ["messages", "events"]:
                filtered[key] = value
        return filtered
    
    def _generate_session_id(self) -> str:
        """Gerar ID de sessão único."""
        import uuid
        return str(uuid.uuid4())
    
    async def send_webhook(self, payload: Dict[str, Any]):
        """Enviar webhook para Bibha.ai."""
        if not self.webhook_url:
            return
        
        import aiohttp
        
        headers = {"Content-Type": "application/json"}
        if self.webhook_secret:
            headers["X-Webhook-Secret"] = self.webhook_secret
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.webhook_url,
                json=payload,
                headers=headers
            ) as response:
                return response.status == 200


class UnifiedAPI:
    """
    API unificada para múltiplos agentes.
    
    Expõe todos os agentes registrados em uma única API
    com routing baseado no path.
    """
    
    def __init__(self, registry: Any):
        self.registry = registry
        self.adapters: Dict[str, BibhaAdapter] = {}
    
    def register_agent(self, name: str, session_store: Optional[SessionStore] = None):
        """Registrar um agente da registry."""
        agent = self.registry.get(name)
        if agent:
            self.adapters[name] = BibhaAdapter(
                agent=agent,
                session_store=session_store
            )
    
    def create_api(self) -> FastAPI:
        """Criar API com todos os agentes."""
        app = FastAPI(title="Easy Agent Builder API")
        
        @app.post("/agents/{agent_name}/invoke")
        async def invoke_agent(agent_name: str, request: BibhaRequest):
            if agent_name not in self.adapters:
                raise HTTPException(status_code=404, detail=f"Agente {agent_name} não encontrado")
            
            adapter = self.adapters[agent_name]
            return await adapter._handle_invoke(request)
        
        @app.get("/agents")
        async def list_agents():
            return {
                "agents": [
                    {
                        "name": name,
                        "type": type(adapter.agent).__name__,
                        "description": getattr(adapter.agent, "description", "")
                    }
                    for name, adapter in self.adapters.items()
                ]
            }
        
        return app
