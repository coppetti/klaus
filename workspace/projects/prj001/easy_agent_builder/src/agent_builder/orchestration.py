"""
Padrões de Orquestração - Implementações de padrões comuns multi-agent.
"""

from typing import Any, Callable, Dict, List, Optional, Union

from google.adk.agents import (
    BaseAgent,
    LlmAgent,
    LoopAgent,
    ParallelAgent,
    SequentialAgent,
)


class RouterPattern:
    """
    Padrão Router - Coordenador que delega para agentes especialistas.
    
    Use quando:
    - Temos múltiplos agentes especialistas
    - Queremos routing dinâmico baseado em LLM
    - Precisamos de um entry point único
    
    Example:
        ```python
        router = RouterPattern.create(
            name="support_router",
            model="gemini-2.0-flash-exp",
            sub_agents=[
                {"name": "billing", "description": "Handles billing questions"},
                {"name": "tech", "description": "Handles technical issues"},
            ]
        )
        ```
    """
    
    @staticmethod
    def create(
        name: str,
        sub_agents: List[Dict[str, str]],
        model: str = "gemini-2.0-flash-exp",
        description: Optional[str] = None,
        custom_instruction: Optional[str] = None,
    ) -> LlmAgent:
        """
        Criar um agente router.
        
        Args:
            name: Nome do router
            sub_agents: Lista de dicts com 'name' e 'description'
            model: Modelo LLM
            description: Descrição opcional
            custom_instruction: Instrução customizada opcional
            
        Returns:
            LlmAgent configurado como router
        """
        # Criar agentes especialistas
        specialist_agents = []
        agent_descriptions = []
        
        for spec in sub_agents:
            agent = LlmAgent(
                model=model,
                name=spec["name"],
                description=spec.get("description", f"Agente {spec['name']}"),
                instruction=spec.get(
                    "instruction", 
                    f"Você é o especialista em {spec['name']}. "
                    f"Responda apenas perguntas relacionadas a {spec['name']}."
                ),
            )
            specialist_agents.append(agent)
            agent_descriptions.append(
                f"- {spec['name']}: {spec.get('description', 'Especialista')}"
            )
        
        # Instrução padrão do router
        default_instruction = f"""Você é um coordenador inteligente. Sua função é analisar 
a solicitação do usuário e delegar para o agente especialista mais adequado.

AGENTES DISPONÍVEIS:
{"\n".join(agent_descriptions)}

REGRAS DE DELEGAÇÃO:
1. Analise cuidadosamente o intent da mensagem do usuário
2. Escolha o agente MAIS ESPECÍFICO para a tarefa
3. Se nenhum agente for adequado, responda diretamente
4. NÃO delegue para múltiplos agentes simultaneamente
5. Se o usuário apenas cumprimentar, responda amigavelmente

Use sua descrição e a descrição dos sub-agentes para tomar a decisão correta."""

        return LlmAgent(
            model=model,
            name=name,
            description=description or f"Router que coordena {len(sub_agents)} agentes",
            instruction=custom_instruction or default_instruction,
            sub_agents=specialist_agents,
        )


class SequentialWorkflow:
    """
    Padrão Sequential - Pipeline de agentes em sequência.
    
    Use quando:
    - Processo tem etapas bem definidas
    - Output de um agente é input do próximo
    - Precisamos de pipeline determinístico
    
    Example:
        ```python
        workflow = SequentialWorkflow.create(
            name="etl_pipeline",
            steps=[
                {"agent": extract_agent, "output_key": "raw_data"},
                {"agent": transform_agent, "input_key": "raw_data", "output_key": "clean_data"},
                {"agent": load_agent, "input_key": "clean_data"},
            ]
        )
        ```
    """
    
    @staticmethod
    def create(
        name: str,
        steps: List[Dict[str, Any]],
        description: Optional[str] = None,
    ) -> SequentialAgent:
        """
        Criar workflow sequencial.
        
        Args:
            name: Nome do workflow
            steps: Lista de passos com configuração
            description: Descrição opcional
            
        Returns:
            SequentialAgent configurado
        """
        agents = []
        for step in steps:
            agent = step.get("agent") or step.get("agent_instance")
            if agent:
                agents.append(agent)
        
        return SequentialAgent(
            name=name,
            description=description or f"Workflow sequencial com {len(agents)} passos",
            sub_agents=agents,
        )
    
    @staticmethod
    def from_agents(
        name: str,
        agents: List[BaseAgent],
        description: Optional[str] = None,
    ) -> SequentialAgent:
        """Criar workflow simples a partir de lista de agentes."""
        return SequentialAgent(
            name=name,
            description=description or f"Pipeline de {len(agents)} agentes",
            sub_agents=agents,
        )


class ParallelWorkflow:
    """
    Padrão Parallel - Execução concorrente de agentes.
    
    Use quando:
    - Múltiplas tarefas independentes
- Queremos reduzir latência total
    - Resultados são combinados no final
    
    Example:
        ```python
        workflow = ParallelWorkflow.create(
            name="content_analysis",
            agents=[sentiment_agent, entity_agent, topic_agent],
            aggregator=summary_agent
        )
        ```
    """
    
    @staticmethod
    def create(
        name: str,
        agents: List[BaseAgent],
        aggregator: Optional[BaseAgent] = None,
        description: Optional[str] = None,
    ) -> Union[ParallelAgent, SequentialAgent]:
        """
        Criar workflow paralelo.
        
        Args:
            name: Nome do workflow
            agents: Lista de agentes para executar em paralelo
            aggregator: Agente opcional para consolidar resultados
            description: Descrição opcional
            
        Returns:
            ParallelAgent ou SequentialAgent (se houver aggregator)
        """
        parallel = ParallelAgent(
            name=f"{name}_parallel",
            description=f"Execução paralela de {len(agents)} agentes",
            sub_agents=agents,
        )
        
        if aggregator:
            # Se tem aggregator, criar sequência: parallel -> aggregator
            return SequentialAgent(
                name=name,
                description=description or f"Paralelo + Agregação",
                sub_agents=[parallel, aggregator],
            )
        
        return parallel


class LoopWorkflow:
    """
    Padrão Loop - Iteração até critério de parada.
    
    Use quando:
    - Precisamos refinar iterativamente
    - Critério de qualidade deve ser atingido
    - Máximo de iterações como safeguard
    
    Example:
        ```python
        workflow = LoopWorkflow.create(
            name="code_refiner",
            agent=draft_code_agent,
            validator=quality_check_agent,
            max_iterations=5
        )
        ```
    """
    
    @staticmethod
    def create(
        name: str,
        agent: BaseAgent,
        validator: Optional[BaseAgent] = None,
        max_iterations: int = 5,
        description: Optional[str] = None,
    ) -> LoopAgent:
        """
        Criar workflow com loop.
        
        Args:
            name: Nome do workflow
            agent: Agente principal para iterar
            validator: Agente opcional para validar critério de parada
            max_iterations: Máximo de iterações
            description: Descrição opcional
            
        Returns:
            LoopAgent configurado
        """
        sub_agents = [agent]
        if validator:
            sub_agents.append(validator)
        
        return LoopAgent(
            name=name,
            description=description or f"Workflow iterativo (max {max_iterations})",
            sub_agents=sub_agents,
            max_iterations=max_iterations,
        )


class FanOutGatherPattern:
    """
    Padrão Fan-Out/Gather - Distribui e coleta resultados.
    
    Combina Parallel + Sequential de forma otimizada.
    """
    
    @staticmethod
    def create(
        name: str,
        distributor: BaseAgent,
        workers: List[BaseAgent],
        gatherer: BaseAgent,
        description: Optional[str] = None,
    ) -> SequentialAgent:
        """
        Criar padrão fan-out/gather.
        
        Fluxo: distributor -> parallel(workers) -> gatherer
        
        Args:
            name: Nome do workflow
            distributor: Agente que prepara/distribui tarefas
            workers: Lista de agentes workers
            gatherer: Agente que consolida resultados
            description: Descrição opcional
            
        Returns:
            SequentialAgent com estrutura fan-out/gather
        """
        parallel_workers = ParallelAgent(
            name=f"{name}_workers",
            sub_agents=workers,
        )
        
        return SequentialAgent(
            name=name,
            description=description or f"Fan-out/Gather com {len(workers)} workers",
            sub_agents=[distributor, parallel_workers, gatherer],
        )


class EvaluationGatePattern:
    """
    Padrão Evaluation Gate - Quality gate no workflow.
    
    Adiciona checkpoint de qualidade que pode rejeitar ou aprovar.
    """
    
    @staticmethod
    def create(
        name: str,
        producer: BaseAgent,
        evaluator: BaseAgent,
        threshold: float = 0.8,
        max_attempts: int = 3,
        fallback: Optional[BaseAgent] = None,
    ) -> SequentialAgent:
        """
        Criar workflow com gate de avaliação.
        
        Args:
            name: Nome do workflow
            producer: Agente que gera o output
            evaluator: Agente que avalia a qualidade
            threshold: Score mínimo para aprovação
            max_attempts: Máximo de tentativas
            fallback: Agente fallback se todas falharem
            
        Returns:
            SequentialAgent com gate
        """
        # Implementação simplificada
        # Na prática, usar LoopAgent com condição de saída
        return SequentialAgent(
            name=name,
            description=f"Workflow com quality gate (threshold={threshold})",
            sub_agents=[producer, evaluator],
        )


# Factory para criar workflows complexos
class WorkflowBuilder:
    """
    Builder para construção de workflows complexos.
    
    Example:
        ```python
        workflow = (WorkflowBuilder()
            .sequential("main_pipeline")
            .add_step(extract_agent)
            .parallel()
                .add_branch(analysis_agent)
                .add_branch(summarize_agent)
            .end_parallel()
            .add_step(merge_agent)
            .build())
        ```
    """
    
    def __init__(self):
        self.steps: List[BaseAgent] = []
        self.name: str = "workflow"
        
    def sequential(self, name: str) -> "WorkflowBuilder":
        """Iniciar workflow sequencial."""
        self.name = name
        return self
    
    def add_step(self, agent: BaseAgent) -> "WorkflowBuilder":
        """Adicionar passo sequencial."""
        self.steps.append(agent)
        return self
    
    def parallel(self, name: Optional[str] = None) -> "ParallelBuilder":
        """Iniciar seção paralela."""
        return ParallelBuilder(self, name)
    
    def build(self) -> SequentialAgent:
        """Construir o workflow final."""
        return SequentialAgent(
            name=self.name,
            sub_agents=self.steps,
        )


class ParallelBuilder:
    """Builder helper para seções paralelas."""
    
    def __init__(self, parent: WorkflowBuilder, name: Optional[str] = None):
        self.parent = parent
        self.branches: List[BaseAgent] = []
        self.name = name or f"{parent.name}_parallel"
        
    def add_branch(self, agent: BaseAgent) -> "ParallelBuilder":
        """Adicionar branch paralelo."""
        self.branches.append(agent)
        return self
    
    def end_parallel(self, aggregator: Optional[BaseAgent] = None) -> WorkflowBuilder:
        """Finalizar seção paralela e retornar ao builder pai."""
        if aggregator:
            parallel = ParallelAgent(name=self.name, sub_agents=self.branches)
            self.parent.steps.extend([parallel, aggregator])
        else:
            parallel = ParallelAgent(name=self.name, sub_agents=self.branches)
            self.parent.steps.append(parallel)
        return self.parent
