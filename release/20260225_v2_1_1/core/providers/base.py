"""
Base Provider Interface
=======================
Abstract base class for all LLM providers.
"""

from abc import ABC, abstractmethod
from typing import AsyncIterator, Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

class ProviderType(Enum):
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    OPENROUTER = "openrouter"
    GEMINI = "gemini"
    KIMI = "kimi"

@dataclass
class Message:
    role: str  # system, user, assistant
    content: str
    metadata: Optional[Dict] = None

@dataclass
class GenerationConfig:
    temperature: float = 0.7
    max_tokens: int = 4096
    top_p: float = 0.9
    stream: bool = True
    
@dataclass
class Usage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

class BaseProvider(ABC):
    """Abstract base class for LLM providers."""
    
    def __init__(self, api_key: str, model: str, config: Dict[str, Any] = None):
        self.api_key = api_key
        self.model = model
        self.config = config or {}
        self.provider_type: ProviderType = None
        
    @abstractmethod
    async def generate(
        self,
        messages: List[Message],
        config: Optional[GenerationConfig] = None
    ) -> AsyncIterator[str]:
        """Generate streaming response."""
        pass
    
    @abstractmethod
    async def generate_sync(
        self,
        messages: List[Message],
        config: Optional[GenerationConfig] = None
    ) -> str:
        """Generate non-streaming response."""
        pass
    
    @abstractmethod
    def count_tokens(self, text: str) -> int:
        """Count tokens in text."""
        pass
    
    @abstractmethod
    def get_model_info(self) -> Dict[str, Any]:
        """Get model information."""
        pass
    
    def format_messages(self, messages: List[Message]) -> List[Dict]:
        """Format messages for provider API."""
        return [
            {"role": msg.role, "content": msg.content}
            for msg in messages
        ]
