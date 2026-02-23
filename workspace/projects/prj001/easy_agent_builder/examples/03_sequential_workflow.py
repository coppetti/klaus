"""
Exemplo 3: Sequential Workflow
==============================

Pipeline ETL com agentes especialistas em sequência.
"""

from google.adk.agents import LlmAgent, SequentialAgent

# Agente 1: Extração
extractor = LlmAgent(
    model="gemini-2.0-flash-exp",
    name="extractor",
    description="Extrai dados de fontes diversas",
    instruction="Extraia dados relevantes da fonte fornecida. Retorne em formato estruturado.",
)

# Agente 2: Transformação
transformer = LlmAgent(
    model="gemini-2.0-flash-exp",
    name="transformer",
    description="Transforma e limpa dados",
    instruction="Transforme os dados extraídos: normalize, limpe e formate para análise.",
)

# Agente 3: Carga
loader = LlmAgent(
    model="gemini-2.0-flash-exp",
    name="loader",
    description="Carrega dados no destino",
    instruction="Carregue os dados transformados no sistema de destino. Confirme sucesso.",
)

# Criar pipeline
etl_pipeline = SequentialAgent(
    name="etl_pipeline",
    description="Pipeline ETL completo",
    sub_agents=[extractor, transformer, loader],
)

if __name__ == "__main__":
    print(f"Pipeline criado: {etl_pipeline.name}")
    print(f"Passos: {[a.name for a in etl_pipeline.sub_agents]}")
