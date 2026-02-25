"""
OpenRouter Provider
===================
Multi-model provider including Kimi, Claude, GPT, etc.
"""

import json
from typing import AsyncIterator, Dict, List, Optional, Any
import httpx
from .base import BaseProvider, Message, GenerationConfig, ProviderType

class OpenRouterProvider(BaseProvider):
    """OpenRouter provider - access multiple models via one API."""
    
    def __init__(self, api_key: str, model: str = "moonshot-ai/kimi-k2-5", config: Dict = None):
        super().__init__(api_key, model, config)
        self.provider_type = ProviderType.OPENROUTER
        self.base_url = "https://openrouter.ai/api/v1"
        
    async def generate(
        self,
        messages: List[Message],
        system: Optional[str] = None,
        config: Optional[GenerationConfig] = None
    ) -> AsyncIterator[str]:
        """Stream response from OpenRouter."""
        config = config or GenerationConfig()
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/ide-agent-wizard",  # Required by OpenRouter
            "X-Title": "Klaus"  # Optional site name
        }
        
        formatted_messages = self.format_messages(messages)
        if system:
            formatted_messages.insert(0, {"role": "system", "content": system})
            
        payload = {
            "model": self.model,
            "messages": formatted_messages,
            "temperature": config.temperature,
            "max_tokens": config.max_tokens,
            "top_p": config.top_p,
            "stream": True
        }
        
        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=120.0
            ) as response:
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        if data == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data)
                            if choices := chunk.get("choices"):
                                if delta := choices[0].get("delta", {}).get("content"):
                                    yield delta
                        except (json.JSONDecodeError, IndexError, KeyError):
                            continue
    
    async def generate_sync(
        self,
        messages: List[Message],
        system: Optional[str] = None,
        config: Optional[GenerationConfig] = None
    ) -> str:
        """Non-streaming generation."""
        parts = []
        async for chunk in self.generate(messages, system, config):
            parts.append(chunk)
        return "".join(parts)
    
    def count_tokens(self, text: str) -> int:
        """Approximate token count."""
        return len(text) // 4
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get model information."""
        return {
            "provider": "openrouter",
            "model": self.model,
            "max_tokens": 200000,
            "description": f"OpenRouter - {self.model}"
        }
