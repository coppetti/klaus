"""
Configurações compartilhadas para todos os testes.
Fixtures e utilities reutilizáveis.
"""
import pytest
import tempfile
import shutil
import asyncio
from pathlib import Path
from unittest.mock import Mock, AsyncMock

# ============================================================================
# Fixtures de Diretórios
# ============================================================================

@pytest.fixture(scope="session")
def test_workspace():
    """Criar workspace temporário para testes."""
    temp_dir = Path(tempfile.mkdtemp(prefix="eab_test_"))
    
    # Criar estrutura
    (temp_dir / "agents").mkdir()
    (temp_dir / "src" / "agents").mkdir(parents=True)
    (temp_dir / "config").mkdir()
    (temp_dir / "tests").mkdir()
    
    yield temp_dir
    
    # Cleanup
    shutil.rmtree(temp_dir)


@pytest.fixture
def temp_dir(tmp_path):
    """Diretório temporário isolado para cada teste."""
    return tmp_path


# ============================================================================
# Fixtures de Agentes
# ============================================================================

@pytest.fixture
def sample_agent_yaml(test_workspace):
    """Criar arquivo YAML de agente de exemplo válido."""
    yaml_content = """\
name: test_assistant
type: llm
model: gemini-2.0-flash-exp
description: Agente de teste para validação
instruction: |
  Você é um assistente de teste útil e prestativo.
  Sempre responda de forma clara e concisa.
tools:
  - google_search
temperature: 0.7
max_tokens: 2048
"""
    yaml_path = test_workspace / "agents" / "test_assistant.yaml"
    yaml_path.write_text(yaml_content)
    return yaml_path


@pytest.fixture
def sample_router_yaml(test_workspace):
    """Criar arquivo YAML de router agent."""
    yaml_content = """\
name: router_atendimento
type: router
model: gemini-2.0-flash-exp
description: Router para atendimento ao cliente
instruction: |
  Você é um coordenador de atendimento. Analise a solicitação
  e delegue para o agente especialista mais adequado.
sub_agents:
  - suporte_tecnico
  - vendas
  - financeiro
temperature: 0.5
"""
    yaml_path = test_workspace / "agents" / "router_atendimento.yaml"
    yaml_path.write_text(yaml_content)
    return yaml_path


@pytest.fixture
def sample_workflow_yaml(test_workspace):
    """Criar arquivo YAML de workflow."""
    yaml_content = """\
name: pipeline_processamento
type: sequential
description: Pipeline de processamento de dados
steps:
  - agent: extrator
    output_key: dados_extraidos
  - agent: transformador
    output_key: dados_transformados
  - agent: carregador
    output_key: dados_carregados
"""
    yaml_path = test_workspace / "agents" / "pipeline.yaml"
    yaml_path.write_text(yaml_content)
    return yaml_path


@pytest.fixture
def invalid_agent_yaml(test_workspace):
    """Criar arquivo YAML de agente inválido (para testes de erro)."""
    yaml_content = """\
name: a
instruction: curta
"""
    yaml_path = test_workspace / "agents" / "invalid.yaml"
    yaml_path.write_text(yaml_content)
    return yaml_path


# ============================================================================
# Fixtures de Configuração
# ============================================================================

@pytest.fixture
def mock_gcp_credentials(tmp_path):
    """Mock para credenciais GCP."""
    creds_file = tmp_path / "gcp-credentials.json"
    creds_content = {
        "type": "service_account",
        "project_id": "test-project",
        "private_key_id": "test-key-id",
        "private_key": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n",
        "client_email": "test@test-project.iam.gserviceaccount.com",
        "client_id": "123456789",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token"
    }
    import json
    creds_file.write_text(json.dumps(creds_content))
    return str(creds_file)


@pytest.fixture
def mock_env_vars(monkeypatch):
    """Configurar variáveis de ambiente mock."""
    env_vars = {
        "GOOGLE_CLOUD_PROJECT": "test-project",
        "GOOGLE_CLOUD_LOCATION": "us-central1",
        "BIBHA_API_KEY": "bah-sk-test-key",
        "BIBHA_API_HOST": "https://test.bibha.ai",
        "BIBHA_CHATFLOW_ID": "test-flow",
        "ENVIRONMENT": "test"
    }
    
    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)
    
    return env_vars


# ============================================================================
# Fixtures de Mock de Agentes
# ============================================================================

class MockLlmAgent:
    """Mock de agente LLM do ADK."""
    
    def __init__(self, **kwargs):
        self.name = kwargs.get("name", "mock_agent")
        self.model = kwargs.get("model", "gemini-mock")
        self.instruction = kwargs.get("instruction", "")
        self.tools = kwargs.get("tools", [])
        self.description = kwargs.get("description", "")
        self.sub_agents = kwargs.get("sub_agents", [])
        self._run_mock = AsyncMock()
    
    async def run(self, **kwargs):
        return await self._run_mock(**kwargs)
    
    def set_response(self, text: str, session_id: str = "test-session"):
        """Configurar resposta mock."""
        self._run_mock.return_value = {
            "text": text,
            "sessionId": session_id
        }
    
    def set_error(self, exception: Exception):
        """Configurar erro."""
        self._run_mock.side_effect = exception


@pytest.fixture
def mock_agent():
    """Criar agente mock."""
    return MockLlmAgent(name="test_agent")


@pytest.fixture
def mock_search_agent():
    """Criar agente de busca mock."""
    agent = MockLlmAgent(
        name="search_agent",
        description="Agente especializado em buscas",
        tools=["google_search"]
    )
    agent.set_response("Resultado da busca mock")
    return agent


@pytest.fixture
def mock_router_agent():
    """Criar router agent mock."""
    return MockLlmAgent(
        name="router",
        type="router",
        sub_agents=["agent_a", "agent_b", "agent_c"]
    )


# ============================================================================
# Fixtures de Circuit Breaker
# ============================================================================

@pytest.fixture(autouse=True)
def reset_circuit_registry():
    """Resetar registry de circuit breakers antes de cada teste."""
    from agent_builder.circuit_breaker import circuit_registry
    circuit_registry.reset_all()
    yield
    circuit_registry.reset_all()


@pytest.fixture
def fast_circuit_config():
    """Configuração de circuit breaker rápida para testes."""
    from agent_builder.circuit_breaker import CircuitBreakerConfig
    return CircuitBreakerConfig(
        failure_threshold=2,
        recovery_timeout=0.1,  # 100ms
        success_threshold=1,
        half_open_max_calls=3
    )


# ============================================================================
# Fixtures de Bibha
# ============================================================================

@pytest.fixture
def bibha_config():
    """Configuração de teste para Bibha."""
    return {
        "api_key": "bah-sk-test-key",
        "api_host": "https://test.bibha.ai",
        "chatflow_id": "test-chatflow"
    }


@pytest.fixture
def sample_bibha_request():
    """Request de exemplo da Bibha."""
    return {
        "question": "Qual o horário de funcionamento?",
        "sessionId": "sess-123-abc",
        "chatflowId": "atendimento-flow",
        "metadata": {
            "channel": "web",
            "user_id": "user-456"
        }
    }


@pytest.fixture
def sample_bibha_response():
    """Resposta de exemplo para Bibha."""
    return {
        "text": "Nosso horário é das 9h às 18h",
        "sessionId": "sess-123-abc",
        "chatflowId": "atendimento-flow",
        "source": "adk_agent"
    }


# ============================================================================
# Fixtures de Clientes HTTP
# ============================================================================

@pytest.fixture
def mock_httpx_client():
    """Mock de cliente HTTPX."""
    mock_client = Mock()
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"status": "ok"}
    mock_response.raise_for_status.return_value = None
    mock_client.post.return_value = mock_response
    mock_client.get.return_value = mock_response
    return mock_client


# ============================================================================
# Event Loop
# ============================================================================

@pytest.fixture(scope="session")
def event_loop():
    """Criar event loop para testes async."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ============================================================================
# Helpers
# ============================================================================

def create_test_agent_yaml(name: str, agent_type: str = "llm", 
                           instruction: str = None) -> str:
    """Helper para criar conteúdo YAML de agente de teste."""
    if instruction is None:
        instruction = f"Você é o agente {name}. Responda de forma útil."
    
    return f"""\
name: {name}
type: {agent_type}
model: gemini-2.0-flash-exp
description: Agente de teste {name}
instruction: |
  {instruction}
tools:
  - google_search
temperature: 0.7
"""


def assert_valid_agent_config(config):
    """Assert que config de agente é válida."""
    assert config is not None
    assert len(config.name) >= 2
    assert len(config.instruction) >= 10
    assert config.type in ["llm", "sequential", "parallel", "router", "loop"]


# ============================================================================
# Marcadores Customizados
# ============================================================================

def pytest_configure(config):
    """Configurar marcadores customizados."""
    config.addinivalue_line("markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')")
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line("markers", "unit: marks tests as unit tests")
    config.addinivalue_line("markers", "circuit_breaker: marks tests as circuit breaker tests")
