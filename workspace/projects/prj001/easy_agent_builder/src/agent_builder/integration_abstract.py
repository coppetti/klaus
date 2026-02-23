"""
Abstract Integration Layer
==========================

Arquitetura genérica para integração com orquestradores externos
(Bibha.ai ou qualquer outra plataforma).

COMO USAR:
1. Herde de ExternalOrchestratorAdapter
2. Implemente os métodos abstratos mapeando para a API real
3. Não exponha detalhes da implementação no código público

EXEMPLO:
    class BibhaAdapter(ExternalOrchestratorAdapter):
        def _map_incoming_request(self, raw_request: dict) -> AgentRequest:
            # Mapeie aqui conforme documentação da Bibha
            return AgentRequest(...)
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, Optional

from fastapi import FastAPI, Request
from pydantic import BaseModel, Field


# ============================================================================
# Data Models (Genéricos - Independentes de Vendor)
# ============================================================================

@dataclass
class AgentRequest:
    """Request normalizado para o agente."""
    message: str
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    metadata: Dict[str, Any] = None
    # Campos adicionais que você precisar mapear
    context: Optional[Dict[str, Any]] = None
    timestamp: Optional[str] = None


@dataclass  
class AgentResponse:
    """Response normalizado do agente."""
    message: str
    session_id: str
    actions: list = None
    context: Dict[str, Any] = None
    metadata: Dict[str, Any] = None
    # Para controle de fluxo
    transfer_to: Optional[str] = None  # Se quiser transferir para outro agente
    requires_human: bool = False


# ============================================================================
# Abstract Adapter
# ============================================================================

class ExternalOrchestratorAdapter(ABC):
    """
    Adapter abstrato para orquestradores externos.
    
    Implemente esta classe para conectar com Bibha.ai ou qualquer
    outra plataforma de orquestração.
    
    MÉTODOS QUE VOCÊ DEVE IMPLEMENTAR (baseado na doc real):
    - _map_incoming_request(): Mapeia request externo → modelo interno
    - _map_outgoing_response(): Mapeia response interno → formato externo
    - _authenticate(): Valida autenticação da chamada
    - _extract_session_context(): Recupera contexto de sessão
    """
    
    def __init__(self, agent: Any, session_store: Any = None):
        self.agent = agent
        self.session_store = session_store
        self._setup_adk_runner()
    
    def _setup_adk_runner(self):
        """Setup interno do runner ADK."""
        from google.adk.runners import Runner
        from google.adk.sessions import InMemorySessionService
        
        self.session_service = InMemorySessionService()
        self.runner = Runner(agent=self.agent, session_service=self.session_service)
    
    # ========================================================================
    # MÉTODOS ABSTRATOS - IMPLEMENTE CONFORME DOCUMENTAÇÃO REAL
    # ========================================================================
    
    @abstractmethod
    def _authenticate(self, request: Request) -> bool:
        """
        Autenticar request recebido.
        
        Args:
            request: Request HTTP raw
            
        Returns:
            True se autenticado, False caso contrário
        """
        pass
    
    @abstractmethod
    def _map_incoming_request(self, raw_request: Dict[str, Any]) -> AgentRequest:
        """
        Mapear request externo para modelo interno.
        
        AQUI você implementa conforme a estrutura real da Bibha.ai:
        - Quais campos vêm no body?
        - Como é identificada a sessão?
        - Onde está a mensagem do usuário?
        
        Args:
            raw_request: Dict com payload recebido
            
        Returns:
            AgentRequest normalizado
        """
        pass
    
    @abstractmethod
    def _map_outgoing_response(
        self, 
        internal_response: AgentResponse,
        original_request: AgentRequest
    ) -> Dict[str, Any]:
        """
        Mapear response interno para formato externo.
        
        AQUI você formata conforme o esperado pela Bibha.ai:
        - Quais campos ela espera no response?
        - Como indicar transferência para outro agente?
        - Como retornar metadata?
        
        Args:
            internal_response: Resposta do agente ADK
            original_request: Request original (para contexto)
            
        Returns:
            Dict formatado para o orquestrador externo
        """
        pass
    
    @abstractmethod
    def _extract_session_context(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Extrair contexto de sessão do orquestrador externo.
        
        Se Bibha mantém estado de conversação que precisa ser
        sincronizado, implemente aqui.
        
        Args:
            session_id: ID da sessão
            
        Returns:
            Contexto da sessão ou None
        """
        pass
    
    # ========================================================================
    # MÉTODOS OPCIONAIS - Sobrescreva se necessário
    # ========================================================================
    
    def _pre_process(self, request: AgentRequest) -> AgentRequest:
        """
        Hook para pré-processamento do request.
        Útil para adicionar headers, transformar mensagem, etc.
        """
        return request
    
    def _post_process(self, response: AgentResponse) -> AgentResponse:
        """
        Hook para pós-processamento do response.
        Útil para formatação, filtros, etc.
        """
        return response
    
    def _handle_error(self, error: Exception) -> Dict[str, Any]:
        """
        Handler de erros customizado.
        Formate erros conforme o esperado pela plataforma externa.
        """
        return {
            "error": True,
            "message": str(error),
            "type": error.__class__.__name__,
        }
    
    # ========================================================================
    # API HTTP - Não precisa modificar
    # ========================================================================
    
    def create_api(self) -> FastAPI:
        """Criar aplicação FastAPI com endpoints padrão."""
        from fastapi import HTTPException, status
        
        app = FastAPI(
            title=f"Agent Adapter: {self.agent.name}",
            description="API de integração com orquestrador externo",
            version="1.0.0"
        )
        
        @app.post("/invoke")
        async def invoke(request: Request):
            """Endpoint principal de invocação."""
            try:
                # 1. Autenticar
                if not self._authenticate(request):
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Authentication failed"
                    )
                
                # 2. Parse request
                raw_body = await request.json()
                agent_request = self._map_incoming_request(raw_body)
                
                # 3. Pré-processamento
                agent_request = self._pre_process(agent_request)
                
                # 4. Executar agente
                agent_response = await self._execute_agent(agent_request)
                
                # 5. Pós-processamento
                agent_response = self._post_process(agent_response)
                
                # 6. Mapear response
                external_response = self._map_outgoing_response(
                    agent_response, 
                    agent_request
                )
                
                return external_response
                
            except HTTPException:
                raise
            except Exception as e:
                return self._handle_error(e)
        
        @app.get("/health")
        async def health():
            """Health check."""
            return {
                "status": "healthy",
                "agent": self.agent.name,
                "agent_type": type(self.agent).__name__,
            }
        
        @app.get("/info")
        async def info():
            """Informações do agente (para discovery)."""
            return {
                "name": self.agent.name,
                "description": getattr(self.agent, "description", ""),
                "capabilities": self._list_capabilities(),
            }
        
        return app
    
    async def _execute_agent(self, request: AgentRequest) -> AgentResponse:
        """
        Executar agente ADK com request normalizado.
        Não precisa modificar este método.
        """
        # Recuperar/criar sessão
        session_id = request.session_id or self._generate_session_id()
        
        # Contexto externo
        external_context = await self._get_session_context(session_id)
        
        # Criar sessão ADK
        adk_session = self.session_service.get_session(
            app_name=self.agent.name,
            user_id=request.user_id or "external",
            session_id=session_id
        )
        
        if not adk_session:
            state = external_context or {}
            if request.context:
                state.update(request.context)
            
            adk_session = self.session_service.create_session(
                app_name=self.agent.name,
                user_id=request.user_id or "external",
                session_id=session_id,
                state=state
            )
        
        # Executar
        events = []
        async for event in self.runner.run_async(
            user_id=request.user_id or "external",
            session_id=session_id,
            new_message=request.message
        ):
            events.append(event)
        
        # Extrair resposta
        response_text = self._extract_text_from_events(events)
        
        # Persistir contexto
        updated_context = dict(adk_session.state)
        await self._save_session_context(session_id, updated_context)
        
        return AgentResponse(
            message=response_text,
            session_id=session_id,
            context=updated_context,
            metadata={"event_count": len(events)}
        )
    
    def _extract_text_from_events(self, events: list) -> str:
        """Extrair texto dos eventos ADK."""
        if not events:
            return ""
        
        for event in reversed(events):
            if hasattr(event, 'content') and event.content:
                return str(event.content)
            if hasattr(event, 'text') and event.text:
                return str(event.text)
        
        return ""
    
    def _generate_session_id(self) -> str:
        """Gerar ID de sessão."""
        import uuid
        return str(uuid.uuid4())
    
    async def _get_session_context(self, session_id: str) -> Optional[Dict]:
        """Recuperar contexto de sessão."""
        if self.session_store:
            return await self.session_store.get(session_id)
        return None
    
    async def _save_session_context(self, session_id: str, context: Dict):
        """Salvar contexto de sessão."""
        if self.session_store:
            await self.session_store.set(session_id, context)
    
    def _list_capabilities(self) -> list:
        """Listar capacidades do agente."""
        capabilities = []
        
        # Tools
        if hasattr(self.agent, 'tools') and self.agent.tools:
            capabilities.extend([t.__name__ for t in self.agent.tools])
        
        # Sub-agents
        if hasattr(self.agent, 'sub_agents') and self.agent.sub_agents:
            capabilities.extend([f"agent:{a.name}" for a in self.agent.sub_agents])
        
        return capabilities


# ============================================================================
# Session Store Abstrato
# ============================================================================

class SessionStore(ABC):
    """Interface para armazenamento de sessão."""
    
    @abstractmethod
    async def get(self, session_id: str) -> Optional[Dict[str, Any]]:
        pass
    
    @abstractmethod
    async def set(self, session_id: str, data: Dict[str, Any], ttl: int = 3600):
        pass
    
    @abstractmethod
    async def delete(self, session_id: str):
        pass


class InMemorySessionStore(SessionStore):
    """Implementação em memória (dev only)."""
    
    def __init__(self):
        self._data: Dict[str, Dict[str, Any]] = {}
    
    async def get(self, session_id: str) -> Optional[Dict[str, Any]]:
        return self._data.get(session_id)
    
    async def set(self, session_id: str, data: Dict[str, Any], ttl: int = 3600):
        self._data[session_id] = data
    
    async def delete(self, session_id: str):
        self._data.pop(session_id, None)
