"""
Template de Integração Privada
==============================

Este arquivo é um TEMPLATE para implementar a integração real com
Bibha.ai (ou qualquer outro orquestrador externo).

⚠️  IMPORTANTE:
- NÃO commite implementações reais se contiverem dados sensíveis
- Use variáveis de ambiente para secrets
- Mantenha a documentação da API em local seguro

ESTRUTURA:
1. Crie sua implementação herdando de ExternalOrchestratorAdapter
2. Implemente os métodos abstratos conforme documentação real
3. Use este arquivo como referência (não commite código real)
"""

from typing import Any, Dict
from fastapi import Request

# Import da camada abstrata
from agent_builder.integration_abstract import (
    ExternalOrchestratorAdapter,
    AgentRequest,
    AgentResponse,
    SessionStore,
)


class BibhaAdapterTemplate(ExternalOrchestratorAdapter):
    """
    TEMPLATE para integração com Bibha.ai.
    
    Quando você tiver acesso à documentação completa:
    1. Copie este arquivo para um diretório privado (fora do git)
    2. Implemente os métodos abstratos
    3. Teste localmente
    4. Deploy sem expor detalhes da API
    """
    
    def __init__(self, agent: Any, session_store: SessionStore = None, config: Dict = None):
        super().__init__(agent, session_store)
        self.config = config or {}
        # Aqui você pode carregar secrets de variáveis de ambiente
        # self.api_key = os.getenv("BIBHA_API_KEY")
    
    def _authenticate(self, request: Request) -> bool:
        """
        TODO: Implementar conforme autenticação da Bibha.ai
        
        Possíveis métodos (verificar doc real):
        - API Key em header
        - HMAC signature
        - JWT token
        - IP whitelist
        """
        # EXEMPLO (não real):
        # api_key = request.headers.get("X-API-Key")
        # return api_key == self.api_key
        
        return True  # Placeholder - IMPLEMENTE!
    
    def _map_incoming_request(self, raw_request: Dict[str, Any]) -> AgentRequest:
        """
        TODO: Mapear request da Bibha.ai para modelo interno.
        
        Perguntas para responder com base na doc:
        - Qual é o formato do JSON recebido?
        - Onde está a mensagem do usuário? (field name)
        - Como é passado o session_id?
        - Há metadata adicional?
        
        EXEMPLO de mapeamento hipotético:
        
        Bibha envia:
        {
            "conversation": {
                "last_message": "Olá",
                "session_id": "abc123"
            },
            "user": {
                "id": "user_456"
            }
        }
        
        Você mapeia para:
        AgentRequest(
            message="Olá",
            session_id="abc123",
            user_id="user_456"
        )
        """
        return AgentRequest(
            message=raw_request.get("message", ""),
            session_id=raw_request.get("session_id"),
            user_id=raw_request.get("user_id"),
            metadata=raw_request.get("metadata", {}),
            # Adicione outros campos conforme necessário
        )
    
    def _map_outgoing_response(
        self,
        internal_response: AgentResponse,
        original_request: AgentRequest
    ) -> Dict[str, Any]:
        """
        TODO: Mapear response interno para formato da Bibha.ai.
        
        Perguntas para responder:
        - Quais campos a Bibha espera receber?
        - Como indicar que deve transferir para outro agente?
        - Como retornar contexto/metadados?
        
        EXEMPLO de mapeamento hipotético:
        
        Você retorna:
        {
            "text": "Resposta do agente",
            "session_id": "abc123",
            "actions": [...],
            "transfer_to": null
        }
        """
        return {
            "message": internal_response.message,
            "session_id": internal_response.session_id,
            "context": internal_response.context,
            "actions": internal_response.actions or [],
            # Adicione campos conforme especificação da Bibha
        }
    
    def _extract_session_context(self, session_id: str) -> Dict[str, Any]:
        """
        TODO: Implementar se Bibha mantém contexto que precisa ser sincronizado.
        
        Se Bibha.ai mantém variáveis de conversação, intenções detectadas,
        ou outros dados de contexto que devem ser passados para o agente,
        implemente a recuperação aqui.
        
        Retorne None se não houver contexto externo.
        """
        # Implementação depende da API da Bibha
        return None
    
    def _pre_process(self, request: AgentRequest) -> AgentRequest:
        """
        HOOK opcional: Modificar request antes de processar.
        
        Útil para:
        - Adicionar informações de contexto
        - Transformar a mensagem
        - Validar/rate limit
        """
        return request
    
    def _post_process(self, response: AgentResponse) -> AgentResponse:
        """
        HOOK opcional: Modificar response antes de enviar.
        
        Útil para:
        - Formatação de texto
        - Adicionar sugestões de ação
        - Marcar para review humano
        """
        return response


# ============================================================================
# USO (após implementar)
# ============================================================================

def create_private_adapter(agent, config: Dict = None):
    """
    Factory para criar adapter com configuração privada.
    
    Use esta função para injetar configurações sem hardcode.
    """
    return BibhaAdapterTemplate(
        agent=agent,
        session_store=None,  # Ou RedisStore(), etc.
        config=config
    )


# ============================================================================
# EXEMPLO DE CONFIGURAÇÃO (não commite valores reais!)
# ============================================================================

PRIVATE_CONFIG_EXAMPLE = {
    # Exemplo de estrutura - substitua por valores reais
    "auth": {
        "type": "api_key",  # ou "hmac", "jwt", etc.
        "header_name": "X-API-Key",
        # "key": "set_via_env_var"
    },
    "mapping": {
        "message_field": "conversation.message",
        "session_field": "conversation.session_id",
        "user_field": "user.id",
    },
    "endpoints": {
        "base": "https://api.bibha.ai",
        # outros endpoints se necessário
    }
}

if __name__ == "__main__":
    print("Este é um template - não execute diretamente.")
    print("Copie para um arquivo privado e implemente conforme documentação.")
