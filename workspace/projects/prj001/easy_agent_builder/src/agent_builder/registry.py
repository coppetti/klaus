"""
Registry de Agentes - Gerenciamento centralizado de agentes e workflows.
"""

import importlib
import inspect
from pathlib import Path
from typing import Any, Dict, List, Optional, Type, Union

from google.adk.agents import BaseAgent, LlmAgent
from pydantic import BaseModel, Field


class AgentMetadata(BaseModel):
    """Metadados de um agente registrado."""
    name: str
    type: str
    description: str
    module_path: str
    class_name: Optional[str] = None
    model: Optional[str] = None
    tools: List[str] = Field(default_factory=list)
    sub_agents: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)


class AgentRegistry:
    """
    Registry central para descoberta e gerenciamento de agentes.
    
    Features:
    - Auto-descoberta de agentes no diretório src/agents
    - Registro manual de agentes
    - Busca por tags/tipo
    - Validação de dependências
    """
    
    def __init__(self, agents_dir: Optional[Path] = None):
        self.agents: Dict[str, AgentMetadata] = {}
        self._instances: Dict[str, BaseAgent] = {}
        self.agents_dir = agents_dir or Path("src/agents")
        
    def discover(self) -> List[AgentMetadata]:
        """
        Auto-descobrir agentes no diretório de agentes.
        
        Returns:
            Lista de metadados dos agentes encontrados.
        """
        discovered = []
        
        if not self.agents_dir.exists():
            return discovered
        
        for agent_dir in self.agents_dir.iterdir():
            if not agent_dir.is_dir():
                continue
                
            agent_file = agent_dir / "agent.py"
            init_file = agent_dir / "__init__.py"
            
            if agent_file.exists():
                try:
                    metadata = self._extract_metadata(agent_dir.name, agent_file)
                    self.agents[metadata.name] = metadata
                    discovered.append(metadata)
                except Exception as e:
                    print(f"⚠️ Erro ao carregar agente {agent_dir.name}: {e}")
        
        return discovered
    
    def _extract_metadata(self, name: str, agent_file: Path) -> AgentMetadata:
        """Extrair metadados de um arquivo de agente."""
        # Leitura simples do arquivo para extrair informações
        content = agent_file.read_text()
        
        # Inferir tipo baseado no conteúdo
        agent_type = "llm"
        if "SequentialAgent" in content:
            agent_type = "sequential"
        elif "ParallelAgent" in content:
            agent_type = "parallel"
        elif "LoopAgent" in content:
            agent_type = "loop"
        elif "sub_agents" in content and "router" in content.lower():
            agent_type = "router"
        
        # Extrair modelo
        model = None
        if 'model="' in content:
            start = content.find('model="') + 7
            end = content.find('"', start)
            model = content[start:end]
        
        return AgentMetadata(
            name=name,
            type=agent_type,
            description=f"Agente {name} ({agent_type})",
            module_path=f"src.agents.{name}.agent",
            model=model,
            tools=[],  # TODO: Extrair tools
            sub_agents=[],  # TODO: Extrair sub-agentes
        )
    
    def register(self, name: str, agent: BaseAgent, metadata: Optional[Dict] = None) -> None:
        """
        Registrar um agente manualmente.
        
        Args:
            name: Identificador único do agente
            agent: Instância do agente ADK
            metadata: Metadados adicionais
        """
        self._instances[name] = agent
        
        meta = AgentMetadata(
            name=name,
            type=agent.__class__.__name__,
            description=metadata.get("description", "") if metadata else "",
            module_path=metadata.get("module_path", "") if metadata else "",
        )
        self.agents[name] = meta
    
    def get(self, name: str) -> Optional[BaseAgent]:
        """
        Obter instância de um agente.
        
        Args:
            name: Nome do agente
            
        Returns:
            Instância do agente ou None se não encontrado
        """
        # Retornar instância cacheada
        if name in self._instances:
            return self._instances[name]
        
        # Tentar carregar dinamicamente
        metadata = self.agents.get(name)
        if not metadata:
            return None
        
        try:
            module = importlib.import_module(metadata.module_path)
            
            # Procurar por variável 'agent' ou classes de agente
            if hasattr(module, 'agent'):
                agent = module.agent
                self._instances[name] = agent
                return agent
            
            # Procurar por classes de agente
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if isinstance(attr, BaseAgent):
                    self._instances[name] = attr
                    return attr
                    
        except Exception as e:
            print(f"❌ Erro ao carregar agente {name}: {e}")
            return None
        
        return None
    
    def get_metadata(self, name: str) -> Optional[AgentMetadata]:
        """Obter metadados de um agente."""
        return self.agents.get(name)
    
    def list_agents(
        self, 
        agent_type: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> List[AgentMetadata]:
        """
        Listar agentes com filtros opcionais.
        
        Args:
            agent_type: Filtrar por tipo (llm, sequential, parallel, etc)
            tags: Filtrar por tags
            
        Returns:
            Lista de metadados dos agentes
        """
        results = list(self.agents.values())
        
        if agent_type:
            results = [a for a in results if a.type == agent_type]
        
        if tags:
            results = [a for a in results if any(t in a.tags for t in tags)]
        
        return results
    
    def validate_dependencies(self, name: str) -> Dict[str, Any]:
        """
        Validar dependências de um agente.
        
        Args:
            name: Nome do agente
            
        Returns:
            Dict com status de validação
        """
        metadata = self.agents.get(name)
        if not metadata:
            return {"valid": False, "error": "Agente não encontrado"}
        
        issues = []
        
        # Validar tools
        for tool in metadata.tools:
            # TODO: Verificar se tool existe
            pass
        
        # Validar sub-agentes
        for sub in metadata.sub_agents:
            if sub not in self.agents:
                issues.append(f"Sub-agente '{sub}' não encontrado")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "metadata": metadata
        }
    
    def build_dependency_graph(self) -> Dict[str, List[str]]:
        """
        Construir grafo de dependências entre agentes.
        
        Returns:
            Dict mapeando agente -> lista de dependências
        """
        graph = {}
        for name, metadata in self.agents.items():
            deps = []
            deps.extend(metadata.sub_agents)
            # TODO: Adicionar tools como dependências
            graph[name] = deps
        return graph
    
    def get_root_agents(self) -> List[AgentMetadata]:
        """
        Obter agentes que não são sub-agentes de ninguém.
        
        Returns:
            Lista de agentes root
        """
        all_subs = set()
        for meta in self.agents.values():
            all_subs.update(meta.sub_agents)
        
        return [meta for name, meta in self.agents.items() if name not in all_subs]


# Singleton global
_registry: Optional[AgentRegistry] = None


def get_registry() -> AgentRegistry:
    """Obter instância singleton do registry."""
    global _registry
    if _registry is None:
        _registry = AgentRegistry()
        _registry.discover()
    return _registry
