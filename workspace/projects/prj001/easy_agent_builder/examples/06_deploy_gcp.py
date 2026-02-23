"""
Exemplo 6: Deploy em GCP
========================

Deploy de agente para Vertex AI Agent Engine.
"""

import os

from google.adk.agents import LlmAgent
from google.adk.tools import google_search

from agent_builder.deployer import DeploymentConfig, GCPDeployer

# Criar agente
agent = LlmAgent(
    model="gemini-2.0-flash-exp",
    name="deployed_agent",
    description="Agente em produção",
    instruction="Você é um assistente de IA em produção. Seja útil e preciso.",
    tools=[google_search],
)

# Configurar deployment
config = DeploymentConfig(
    project_id=os.getenv("GOOGLE_CLOUD_PROJECT", "seu-projeto"),
    location="us-central1",
    staging_bucket=f"gs://{os.getenv('GOOGLE_CLOUD_PROJECT', 'seu-projeto')}-agent-staging",
    machine_type="e2-standard-2",
    min_replicas=1,
    max_replicas=3,
)

# Criar deployer
deployer = GCPDeployer(config)

# Deploy
if __name__ == "__main__":
    print("Iniciando deploy para GCP...")
    
    # Opção 1: Agent Engine
    result = deployer.deploy_to_agent_engine(
        agent_module="examples.06_deploy_gcp",
        agent_name="deployed_agent",
    )
    
    if result.success:
        print(f"✅ Deploy bem-sucedido!")
        print(f"   Endpoint: {result.endpoint}")
        print(f"   Console: {result.metadata.get('console_url')}")
    else:
        print(f"❌ Erro: {result.error}")
    
    # Opção 2: Cloud Run (para API HTTP)
    result_cr = deployer.deploy_to_cloud_run(
        agent_module="examples.06_deploy_gcp",
        agent_name="deployed_agent",
    )
    
    if result_cr.success:
        print(f"\n✅ Deploy Cloud Run bem-sucedido!")
        print(f"   URL: {result_cr.endpoint}")
