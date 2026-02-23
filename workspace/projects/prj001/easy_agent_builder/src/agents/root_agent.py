"""
Root Agent - Entry point principal do sistema multi-agent.

Este agente atua como router inteligente, delegando solicitações
para os agentes especialistas apropriados.
"""

from google.adk.agents import LlmAgent
from google.adk.tools import google_search

# Importar agentes especialistas
# Nota: Em produção, usar registry para carregar dinamicamente

# Agente de Pesquisa
research_agent = LlmAgent(
    model="gemini-2.0-flash-exp",
    name="research_agent",
    description="Especialista em pesquisa e análise de informações",
    instruction="""
    Você é um especialista em pesquisa. Sua função é:
    1. Buscar informações relevantes usando ferramentas de search
    2. Analisar e sintetizar resultados
    3. Fornecer respostas estruturadas com fontes
    
    Use sempre que o usuário pedir informações, dados, ou análises.
    """,
    tools=[google_search],
)

# Agente de Dados
data_agent = LlmAgent(
    model="gemini-2.0-flash-exp",
    name="data_agent",
    description="Especialista em análise de dados e geração de insights",
    instruction="""
    Você é um especialista em dados. Sua função é:
    1. Analisar conjuntos de dados
    2. Gerar insights e tendências
    3. Criar visualizações e relatórios
    
    Use quando o usuário mencionar dados, analytics, métricas, ou relatórios.
    """,
)

# Agente de APIs
api_agent = LlmAgent(
    model="gemini-2.0-flash-exp",
    name="api_agent",
    description="Especialista em integração com APIs e sistemas externos",
    instruction="""
    Você é um especialista em integrações. Sua função é:
    1. Interagir com APIs externas
    2. Orquestrar chamadas entre sistemas
    3. Transformar e normalizar dados
    
    Use quando o usuário mencionar integrações, APIs, ou sistemas externos.
    """,
)

# Agente de Suporte
support_agent = LlmAgent(
    model="gemini-2.0-flash-exp",
    name="support_agent",
    description="Especialista em suporte técnico e resolução de problemas",
    instruction="""
    Você é um especialista em suporte técnico. Sua função é:
    1. Diagnosticar problemas técnicos
    2. Fornecer soluções passo a passo
    3. Escalar quando necessário
    
    Use quando o usuário reportar problemas, erros, ou dúvidas técnicas.
    """,
)

# Root Agent - Router Principal
root_agent = LlmAgent(
    model="gemini-2.0-flash-exp",
    name="root_agent",
    description="Coordenador principal que direciona para especialistas",
    instruction="""
    Você é o coordenador principal do sistema de agentes AI.
    
    SUA FUNÇÃO:
    Analisar a solicitação do usuário e delegar para o agente especialista mais adequado.
    
    AGENTES DISPONÍVEIS:
    
    1. **research_agent** - Especialista em pesquisa e análise de informações
       Use para: perguntas gerais, busca de informações, análises de mercado, tendências
       Exemplos: "Quais são as tendências de IA em 2025?", "Busque dados sobre..."
    
    2. **data_agent** - Especialista em dados e analytics
       Use para: análise de dados, métricas, relatórios, visualizações
       Exemplos: "Analise esses dados...", "Crie um relatório de vendas..."
    
    3. **api_agent** - Especialista em integrações e APIs
       Use para: integrações entre sistemas, chamadas de API, automações
       Exemplos: "Integre com o CRM...", "Chame a API do..."
    
    4. **support_agent** - Especialista em suporte técnico
       Use para: problemas técnicos, troubleshooting, dúvidas de uso
       Exemplos: "Está dando erro...", "Como faço para..."
    
    REGRAS DE DELEGAÇÃO:
    
    1. Analise o INTENT principal da mensagem
    2. Escolha o agente MAIS ESPECÍFICO para a tarefa
    3. Se múltiplos agentes parecerem adequados, escolha o mais especializado
    4. Se nenhum agente for adequado (saudações simples, despedidas), responda diretamente
    5. NUNCA diga "não posso ajudar" - sempre delegue ou responda
    
    COMPORTAMENTO:
    - Seja cordial e profissional
    - Se delegar, não repita a resposta do especialista
    - Mantenha contexto da conversa
    """,
    sub_agents=[research_agent, data_agent, api_agent, support_agent],
)

# Export
__all__ = ["root_agent", "research_agent", "data_agent", "api_agent", "support_agent"]
