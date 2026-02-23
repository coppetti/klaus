"""
Kimi Provider
=============
Moonshot AI Kimi models.
"""

import json
from typing import AsyncIterator, Dict, List, Optional, Any
import httpx
from .base import BaseProvider, Message, GenerationConfig, ProviderType

class KimiProvider(BaseProvider):
    """Kimi (Moonshot AI) provider."""
    
    def __init__(self, api_key: str, model: str = "kimi-latest", config: Dict = None):
        super().__init__(api_key, model, config)
        self.provider_type = ProviderType.KIMI
        self.base_url = "https://api.moonshot.cn/v1"
        
    async def generate(
        self,
        messages: List[Message],
        config: Optional[GenerationConfig] = None
    ) -> AsyncIterator[str]:
        """Stream response from Kimi."""
        config = config or GenerationConfig()
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model if self.model.startswith("kimi-") else "kimi-k2-5",
            "messages": self.format_messages(messages),
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
        config: Optional[GenerationConfig] = None
    ) -> str:
        """Non-streaming generation."""
        parts = []
        async for chunk in self.generate(messages, config):
            parts.append(chunk)
        return "".join(parts)
    
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
