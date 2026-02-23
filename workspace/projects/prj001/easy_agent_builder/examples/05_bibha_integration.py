"""
Exemplo 5: Integração Bibha.ai
==============================

Expondo agente ADK como API para consumo pela Bibha.ai.
"""

from google.adk.agents import LlmAgent
from google.adk.tools import google_search

from agent_builder.integration import BibhaAdapter, InMemorySessionStore

# Criar agente especialista
specialist_agent = LlmAgent(
    model="gemini-2.0-flash-exp",
    name="market_researcher",
    description="Especialista em pesquisa de mercado",
    instruction="""
    Você é um especialista em pesquisa de mercado.
    Forneça análises detalhadas sobre mercados, concorrência e tendências.
    Use dados atualizados via busca web.
    """,
    tools=[google_search],
)

# Criar adaptador Bibha
adapter = BibhaAdapter(
    agent=specialist_agent,
    session_store=InMemorySessionStore(),  # Em produção, use Redis
    webhook_url="https://api.bibha.ai/webhooks/agent-response",
    webhook_secret="seu-webhook-secret",
)

# Criar API FastAPI
app = adapter.create_api()

# Para rodar:
# uvicorn examples.05_bibha_integration:app --reload --port 8080

if __name__ == "__main__":
    import uvicorn
    print("Iniciando servidor de integração Bibha.ai...")
    print("Endpoints disponíveis:")
    print("  POST /invoke - Invocar agente")
    print("  GET  /health - Health check")
    uvicorn.run(app, host="0.0.0.0", port=8080)
