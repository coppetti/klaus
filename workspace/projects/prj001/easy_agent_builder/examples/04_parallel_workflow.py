"""
Exemplo 4: Parallel Workflow
============================

Análise concorrente de múltiplos aspectos.
"""

from google.adk.agents import LlmAgent, ParallelAgent, SequentialAgent

# Agentes de análise especializados
sentiment_agent = LlmAgent(
    model="gemini-2.0-flash-exp",
    name="sentiment_analyzer",
    description="Analisa sentimento do texto",
    instruction="Analise o sentimento (positivo/negativo/neutro) e forneça score.",
)

entity_agent = LlmAgent(
    model="gemini-2.0-flash-exp",
    name="entity_extractor",
    description="Extrai entidades nomeadas",
    instruction="Extraia pessoas, empresas, locais e datas mencionadas.",
)

topic_agent = LlmAgent(
    model="gemini-2.0-flash-exp",
    name="topic_classifier",
    description="Classifica tópicos principais",
    instruction="Identifique os principais tópicos e temas do texto.",
)

# Agregador
aggregator = LlmAgent(
    model="gemini-2.0-flash-exp",
    name="aggregator",
    description="Consolida resultados das análises",
    instruction="Combine as análises de sentimento, entidades e tópicos em um relatório unificado.",
)

# Workflow paralelo com agregação
analysis_workflow = SequentialAgent(
    name="content_analysis",
    description="Análise completa de conteúdo",
    sub_agents=[
        ParallelAgent(
            name="parallel_analysis",
            sub_agents=[sentiment_agent, entity_agent, topic_agent],
        ),
        aggregator,
    ],
)

if __name__ == "__main__":
    print(f"Workflow criado: {analysis_workflow.name}")
    print("Estrutura: Parallel [3 analyzers] -> Aggregator")
