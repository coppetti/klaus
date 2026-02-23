"""
Deployer - Gerenciamento de deployment para GCP.
"""

import os
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from google.cloud import aiplatform
from google.cloud.aiplatform.gapic.schema import predict
from pydantic import BaseModel, Field


class DeploymentConfig(BaseModel):
    """Configuração de deployment."""
    project_id: str
    location: str = "us-central1"
    staging_bucket: str
    machine_type: str = "e2-standard-2"
    min_replicas: int = 1
    max_replicas: int = 5
    env_vars: Dict[str, str] = Field(default_factory=dict)


@dataclass
class DeploymentResult:
    """Resultado de um deployment."""
    success: bool
    agent_name: str
    environment: str
    endpoint: Optional[str] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = None


class GCPDeployer:
    """
    Deployer para Google Cloud Platform.
    
    Gerencia o deployment de agentes ADK para:
    - Vertex AI Agent Engine
    - Cloud Run (para APIs customizadas)
    - Cloud Functions (para triggers simples)
    """
    
    def __init__(self, config: DeploymentConfig):
        self.config = config
        self._init_vertex_ai()
    
    def _init_vertex_ai(self):
        """Inicializar Vertex AI SDK."""
        aiplatform.init(
            project=self.config.project_id,
            location=self.config.location,
            staging_bucket=self.config.staging_bucket,
        )
    
    def deploy_to_agent_engine(
        self,
        agent_module: str,
        agent_name: str,
        requirements: Optional[List[str]] = None,
    ) -> DeploymentResult:
        """
        Deploy agente para Vertex AI Agent Engine.
        
        Args:
            agent_module: Caminho do módulo (ex: "src.agents.search.agent")
            agent_name: Nome do agente
            requirements: Lista de dependências extras
            
        Returns:
            DeploymentResult com status e informações
        """
        try:
            # Criar pacote temporário
            with tempfile.TemporaryDirectory() as tmpdir:
                package_dir = Path(tmpdir) / "agent_package"
                package_dir.mkdir()
                
                # Copiar código fonte
                self._prepare_package(package_dir, agent_module)
                
                # Criar requirements.txt
                reqs = self._build_requirements(requirements)
                (package_dir / "requirements.txt").write_text("\n".join(reqs))
                
                # Criar serving script
                self._create_serving_script(package_dir, agent_module, agent_name)
                
                # Upload para GCS
                gcs_path = self._upload_to_gcs(package_dir, agent_name)
                
                # Deploy para Agent Engine
                # Nota: Esta é uma simulação - API real pode variar
                console_url = f"https://console.cloud.google.com/vertex-ai/agents?project={self.config.project_id}"
                
                return DeploymentResult(
                    success=True,
                    agent_name=agent_name,
                    environment="agent-engine",
                    endpoint=f"https://{self.config.location}-aiplatform.googleapis.com/v1/...",
                    metadata={
                        "gcs_path": gcs_path,
                        "console_url": console_url,
                    }
                )
                
        except Exception as e:
            return DeploymentResult(
                success=False,
                agent_name=agent_name,
                environment="agent-engine",
                error=str(e),
            )
    
    def deploy_to_cloud_run(
        self,
        agent_module: str,
        agent_name: str,
        service_name: Optional[str] = None,
    ) -> DeploymentResult:
        """
        Deploy agente como serviço Cloud Run.
        
        Útil para expor agentes via API HTTP para integração externa.
        """
        service = service_name or f"agent-{agent_name}"
        
        try:
            # Build e push imagem
            image_url = self._build_container_image(agent_module, agent_name)
            
            # Deploy Cloud Run
            cmd = [
                "gcloud", "run", "deploy", service,
                "--image", image_url,
                "--platform", "managed",
                "--region", self.config.location,
                "--allow-unauthenticated",
                "--min-instances", str(self.config.min_replicas),
                "--max-instances", str(self.config.max_replicas),
                "--set-env-vars", f"GOOGLE_CLOUD_PROJECT={self.config.project_id}",
                "--quiet",
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                # Extrair URL do serviço
                url = self._get_cloud_run_url(service)
                
                return DeploymentResult(
                    success=True,
                    agent_name=agent_name,
                    environment="cloud-run",
                    endpoint=url,
                    metadata={"image": image_url}
                )
            else:
                return DeploymentResult(
                    success=False,
                    agent_name=agent_name,
                    environment="cloud-run",
                    error=result.stderr,
                )
                
        except Exception as e:
            return DeploymentResult(
                success=False,
                agent_name=agent_name,
                environment="cloud-run",
                error=str(e),
            )
    
    def _prepare_package(self, package_dir: Path, agent_module: str):
        """Preparar pacote para deployment."""
        # Copiar estrutura de src/
        src_dir = Path("src")
        if src_dir.exists():
            import shutil
            shutil.copytree(src_dir, package_dir / "src", dirs_exist_ok=True)
    
    def _build_requirements(self, extra_requirements: Optional[List[str]]) -> List[str]:
        """Construir lista de requirements."""
        base = [
            "google-adk>=0.5.0",
            "google-cloud-aiplatform>=1.74.0",
            "fastapi>=0.115.0",
            "uvicorn>=0.32.0",
            "pydantic>=2.9.0",
        ]
        
        if extra_requirements:
            base.extend(extra_requirements)
        
        return base
    
    def _create_serving_script(self, package_dir: Path, module: str, agent_name: str):
        """Criar script de serving."""
        serving_code = f'''
import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from fastapi import FastAPI
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
import importlib

# Import agente
module = importlib.import_module("{module}")
agent = getattr(module, "agent")

# Setup
app = FastAPI(title="Agent: {agent_name}")
session_service = InMemorySessionService()
runner = Runner(agent=agent, session_service=session_service)

@app.post("/invoke")
async def invoke(query: str, session_id: str = None):
    """Invocar agente."""
    if not session_id:
        session = session_service.create_session(app_name="{agent_name}", user_id="api")
        session_id = session.id
    
    events = runner.run(
        user_id="api",
        session_id=session_id,
        new_message=query
    )
    
    return {{
        "response": events[-1].content if events else None,
        "session_id": session_id
    }}

@app.get("/health")
async def health():
    return {{"status": "healthy", "agent": "{agent_name}"}}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8080")))
'''
        (package_dir / "main.py").write_text(serving_code)
    
    def _upload_to_gcs(self, package_dir: Path, agent_name: str) -> str:
        """Fazer upload do pacote para GCS."""
        import tarfile
        
        # Criar tarball
        tar_path = package_dir.parent / f"{agent_name}.tar.gz"
        with tarfile.open(tar_path, "w:gz") as tar:
            tar.add(package_dir, arcname=".")
        
        # Upload (simulação)
        gcs_uri = f"{self.config.staging_bucket}/agents/{agent_name}.tar.gz"
        # TODO: Implementar upload real com google-cloud-storage
        
        return gcs_uri
    
    def _build_container_image(self, module: str, agent_name: str) -> str:
        """Build e push de imagem Docker."""
        image_name = f"gcr.io/{self.config.project_id}/agent-{agent_name}"
        
        # Criar Dockerfile temporário
        dockerfile = f'''
FROM python:3.11-slim

WORKDIR /app
COPY src/ ./src/
COPY pyproject.toml .
RUN pip install -e .

# Criar serving script
RUN echo '\
import sys\\n\
sys.path.insert(0, ".")\\n\
from fastapi import FastAPI\\n\
from google.adk.runners import Runner\\n\
from google.adk.sessions import InMemorySessionService\\n\
import importlib\\n\
module = importlib.import_module("{module}")\\n\
agent = getattr(module, "agent")\\n\
app = FastAPI()\\n\
session_service = InMemorySessionService()\\n\
runner = Runner(agent=agent, session_service=session_service)\\n\
@app.post(\"/invoke\")\\n\
async def invoke(query: str, session_id: str = None):\\n\
    if not session_id:\\n\
        session = session_service.create_session(app_name="{agent_name}", user_id="api")\\n\
        session_id = session.id\\n\
    events = runner.run(user_id="api", session_id=session_id, new_message=query)\\n\
    return {{"response": events[-1].content if events else None, "session_id": session_id}}\\n\
' > main.py

RUN pip install fastapi uvicorn

EXPOSE 8080
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
'''
        
        with tempfile.TemporaryDirectory() as tmpdir:
            df_path = Path(tmpdir) / "Dockerfile"
            df_path.write_text(dockerfile)
            
            # Build
            subprocess.run(
                ["docker", "build", "-t", image_name, "-f", str(df_path), "."],
                check=True
            )
            
            # Push
            subprocess.run(
                ["docker", "push", image_name],
                check=True
            )
        
        return image_name
    
    def _get_cloud_run_url(self, service: str) -> str:
        """Obter URL do serviço Cloud Run."""
        result = subprocess.run(
            ["gcloud", "run", "services", "describe", service,
             "--region", self.config.location,
             "--format", "value(status.url)"],
            capture_output=True,
            text=True
        )
        return result.stdout.strip()
    
    def undeploy(self, agent_name: str, environment: str) -> bool:
        """
        Remover deployment.
        
        Args:
            agent_name: Nome do agente
            environment: Tipo de deployment (agent-engine, cloud-run)
            
        Returns:
            True se sucesso
        """
        try:
            if environment == "cloud-run":
                service = f"agent-{agent_name}"
                subprocess.run(
                    ["gcloud", "run", "services", "delete", service,
                     "--region", self.config.location,
                     "--quiet"],
                    check=True
                )
                return True
            
            # TODO: Implementar undeploy de Agent Engine
            return False
            
        except Exception:
            return False


def load_deployment_config(env: str = "staging") -> DeploymentConfig:
    """Carregar configuração de deployment."""
    config_file = Path(f"config/deployment.{env}.yaml")
    
    if config_file.exists():
        data = yaml.safe_load(config_file.read_text())
        return DeploymentConfig(**data)
    
    # Fallback para variáveis de ambiente
    return DeploymentConfig(
        project_id=os.getenv("GOOGLE_CLOUD_PROJECT", ""),
        location=os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1"),
        staging_bucket=os.getenv("VERTEX_AI_STAGING_BUCKET", ""),
    )
