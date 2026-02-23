"""
Exemplo 10: Integração REAL com Bibha.ai
========================================

Este exemplo demonstra a integração completa usando
a documentação real da Bibha.ai.

Fluxo:
1. Bibha.ai envia mensagem via HTTP Tool ou Webhook
2. Nosso adapter recebe no formato Bibha
3. Processa via agente ADK
4. Retorna no formato esperado pela Bibha
"""

import os
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

from google.adk.agents import LlmAgent
from google.adk.tools import google_search

from agent_builder.bibha_adapter_real import (
    BibhaExternalAdapter,
    BibhaConfig
)


# ============================================================
# 1. Criar Agente ADK
# ============================================================

sales_agent = LlmAgent(
    model="gemini-2.0-flash-exp",
    name="vendedor_b2b",
    description="Vendedor B2B integrado ao Bibha AgentsHub",
    instruction="""
    Você é um vendedor B2B especialista em soluções empresariais.
    
    CONTEXTO:
    Este agente está integrado à plataforma Bibha.ai AgentsHub.
    As mensagens podem vir de diversos canais (web, whatsapp, etc.)
    via a orquestração da Bibha.
    
    ABORDAGEM DE VENDAS:
    1. Qualificação - Entenda o perfil do lead
    2. Descoberta - Identifique necessidades e dores
    3. Proposta - Apresente soluções relevantes
    4. Fechamento - Direcione para próximo passo
    
    REGRAS:
    - Sempre seja profissional e consultivo
    - Nunca prometa o que não pode cumprir
    - Use busca para informações atualizadas de mercado
    - Qualifique antes de vender
    """,
    tools=[google_search]
)


# ============================================================
# 2. Configurar Adapter
# ============================================================

def create_bibha_adapter():
    """Criar adapter configurado."""
    
    # Configuração (carrega de variáveis de ambiente ou .env)
    config = BibhaConfig(
        api_key=os.getenv("BIBHA_API_KEY", "bah-sk-demo-key"),
        api_host=os.getenv("BIBHA_API_HOST", "https://demo.bibha.ai"),
        chatflow_id=os.getenv("BIBHA_CHATFLOW_ID", "vendas-chatflow")
    )
    
    # Criar adapter
    adapter = BibhaExternalAdapter(
        agent=sales_agent,
        config=config
    )
    
    return adapter


# ============================================================
# 3. Criar API
# ============================================================

def create_app():
    """Criar aplicação FastAPI."""
    adapter = create_bibha_adapter()
    app = adapter.create_api()
    return app


# ============================================================
# 4. Teste Local
# ============================================================

async def test_local():
    """Testar integração localmente."""
    import asyncio
    from agent_builder.bibha_adapter_real import BibhaIncomingRequest
    
    print("🧪 Teste de Integração Bibha.ai")
    print("=" * 50)
    
    # Criar adapter
    adapter = create_bibha_adapter()
    
    # Simular request da Bibha
    test_requests = [
        {
            "question": "Olá, gostaria de saber mais sobre suas soluções",
            "sessionId": "test-session-001",
            "chatflowId": "vendas-chatflow"
        },
        {
            "question": "Quais são os preços?",
            "sessionId": "test-session-001",  # Mesma sessão
            "chatflowId": "vendas-chatflow"
        }
    ]
    
    for i, req_data in enumerate(test_requests, 1):
        print(f"\n{i}. Enviando mensagem:")
        print(f"   Usuário: {req_data['question']}")
        
        request = BibhaIncomingRequest(**req_data)
        
        # Processar
        response = await adapter._process_message(
            chatflow_id=request.chatflowId,
            request=request
        )
        
        print(f"   Agente: {response['text'][:100]}...")
        print(f"   Session: {response['sessionId']}")


# ============================================================
# 5. Instruções de Deploy
# ============================================================

DEPLOY_INSTRUCTIONS = """
🚀 Deploy da Integração Bibha.ai
=================================

1. CONFIGURAR VARIÁVEIS DE AMBIENTE
   Crie arquivo .env:
   
   BIBHA_API_KEY=bah-sk-sua-chave-aqui
   BIBHA_API_HOST=https://sua-instancia.bibha.ai
   BIBHA_CHATFLOW_ID=seu-chatflow-id

2. DEPLOY PARA CLOUD RUN
   
   gcloud run deploy bibha-adapter \
     --source . \
     --set-env-vars BIBHA_API_KEY=bah-sk-xxx \
     --set-env-vars BIBHA_API_HOST=https://xxx.bibha.ai

3. CONFIGURAR NA BIBHA.AI
   
   No Bibha AgentsHub, crie um HTTP Tool:
   
   Nome: ADK Agent Integration
   Method: POST
   URL: https://seu-adapter-url.run.app/api/v1/prediction/{chatflow_id}
   Headers:
     Content-Type: application/json
   
   Body:
   {
     "question": "{{user_message}}",
     "sessionId": "{{session_id}}",
     "chatflowId": "{{chatflow_id}}"
   }

4. TESTAR
   
   Use o chat da Bibha para enviar mensagens.
   O adapter receberá e processará via agente ADK.

📚 MAIS INFORMAÇÕES
   
   - Documentação Bibha API: /api/v1/prediction/{chatflowId}
   - Webhook alternativo: POST /webhook/bibha
   - Health check: GET /health
"""


# ============================================================
# Execução
# ============================================================

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        # Modo teste
        import asyncio
        asyncio.run(test_local())
    elif len(sys.argv) > 1 and sys.argv[1] == "deploy":
        # Mostrar instruções
        print(DEPLOY_INSTRUCTIONS)
    else:
        # Modo servidor
        import uvicorn
        
        app = create_app()
        
        print("🚀 Bibha.ai Adapter - Servidor")
        print("=" * 50)
        print(f"Agente: {sales_agent.name}")
        print(f"Modelo: {sales_agent.model}")
        print()
        print("Endpoints:")
        print("  POST /api/v1/prediction/{chatflow_id}")
        print("  POST /webhook/bibha")
        print("  GET  /health")
        print()
        print("Para testar: python 10_bibha_integration_real.py test")
        print()
        
        uvicorn.run(app, host="0.0.0.0", port=8080)
