"""
IDE Agent Wizard - Core Module
==============================
Universal AI agent that works with any IDE and LLM provider.
"""

__version__ = "1.0.0"
__author__ = "IDE Agent Wizard"

from .agent import Agent
from .memory import MemoryStore
from .providers import (
    create_provider,
    get_available_providers,
    get_provider_models,
    Message,
    GenerationConfig
)

__all__ = [
    'Agent',
    'MemoryStore',
    'create_provider',
    'get_available_providers',
    'get_provider_models',
    'Message',
    'GenerationConfig',
]
