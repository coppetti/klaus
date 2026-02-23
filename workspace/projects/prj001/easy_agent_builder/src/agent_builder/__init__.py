"""
Easy Agent Builder - Framework for building and deploying AI agents on GCP.
"""

__version__ = "0.1.0"
__author__ = "AI Solutions Architect"

from agent_builder.registry import AgentRegistry
from agent_builder.deployer import GCPDeployer
from agent_builder.orchestration import RouterPattern, SequentialWorkflow, ParallelWorkflow

__all__ = [
    "AgentRegistry",
    "GCPDeployer", 
    "RouterPattern",
    "SequentialWorkflow",
    "ParallelWorkflow",
]
