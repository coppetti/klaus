"""
Exemplo 1: Agente Básico
=======================

Criação simples de um agente com o Easy Agent Builder.
"""

from google.adk.agents import LlmAgent
from google.adk.tools import google_search

# Criar agente diretamente
research_agent = LlmAgent(
    model="gemini-2.0-flash-exp",
    name="meu_pesquisador",
    description="Agente de pesquisa simples",
    instruction="""
    Você é um assistente de pesquisa. Use a ferramenta de busca para
    encontrar informações atualizadas e forneça respostas claras.
    """,
    tools=[google_search],
)

# Usar o agente (normalmente via runner)
if __name__ == "__main__":
    print(f"Agente criado: {research_agent.name}")
    print(f"Descrição: {research_agent.description}")
    print(f"Tools: {[t.__name__ for t in research_agent.tools]}")
