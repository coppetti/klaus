"""
Kimi Provider
=============
Moonshot AI Kimi models via Anthropic SDK.
"""

from typing import AsyncIterator, Dict, List, Optional, Any
from anthropic import Anthropic
from .base import BaseProvider, Message, GenerationConfig, ProviderType

class KimiProvider(BaseProvider):
    """Kimi (Moonshot AI) provider using Anthropic SDK."""
    
    def __init__(self, api_key: str, model: str = "kimi-k2-5", config: Dict = None):
        super().__init__(api_key, model, config)
        self.provider_type = ProviderType.KIMI
        # Kimi API is compatible with Anthropic SDK
        self.client = Anthropic(
            api_key=api_key,
            base_url="https://api.kimi.com/coding"
        )
        
    async def generate(
        self,
        messages: List[Message],
        system: Optional[str] = None,
        config: Optional[GenerationConfig] = None
    ) -> AsyncIterator[str]:
        """Stream response from Kimi."""
        config = config or GenerationConfig()
        
        # Format messages for Anthropic SDK
        formatted_messages = []
        for msg in messages:
            formatted_messages.append({
                "role": msg.role,
                "content": msg.content
            })
        
        # Build kwargs
        kwargs = {
            "model": self.model if self.model.startswith("kimi-") else "kimi-k2-5",
            "messages": formatted_messages,
            "temperature": config.temperature,
            "max_tokens": config.max_tokens,
            "top_p": config.top_p,
        }
        if system:
            kwargs["system"] = system
        
        # Stream the response
        with self.client.messages.stream(**kwargs) as stream:
            for text in stream.text_stream:
                yield text
    
    async def generate_sync(
        self,
        messages: List[Message],
        system: Optional[str] = None,
        config: Optional[GenerationConfig] = None
    ) -> str:
        """Non-streaming generation."""
        config = config or GenerationConfig()
        
        # Format messages for Anthropic SDK
        formatted_messages = []
        for msg in messages:
            formatted_messages.append({
                "role": msg.role,
                "content": msg.content
            })
        
        # Build kwargs
        kwargs = {
            "model": self.model if self.model.startswith("kimi-") else "kimi-k2-5",
            "messages": formatted_messages,
            "temperature": config.temperature,
            "max_tokens": config.max_tokens,
            "top_p": config.top_p,
        }
        if system:
            kwargs["system"] = system
        
        # Generate response
        response = self.client.messages.create(**kwargs)
        return response.content[0].text
    
    def count_tokens(self, text: str) -> int:
        """Approximate token count."""
        return len(text) // 4
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get model information."""
        return {
            "provider": "kimi",
            "model": self.model,
            "max_tokens": 200000,
            "description": "Kimi model via Moonshot AI"
        }
