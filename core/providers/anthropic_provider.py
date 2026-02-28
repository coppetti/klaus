"""
Anthropic Provider
==================
Claude models via Anthropic API.
"""

import os
from typing import AsyncIterator, Dict, List, Optional, Any
import httpx
from .base import BaseProvider, Message, GenerationConfig, ProviderType

class AnthropicProvider(BaseProvider):
    """Anthropic Claude provider."""
    
    def __init__(self, api_key: str, model: str = "claude-sonnet-4-6", config: Dict = None):
        super().__init__(api_key, model, config)
        self.provider_type = ProviderType.ANTHROPIC
        self.base_url = "https://api.anthropic.com/v1"
        
    async def generate(
        self,
        messages: List[Message],
        system: Optional[str] = None,
        config: Optional[GenerationConfig] = None
    ) -> AsyncIterator[str]:
        """Stream response from Claude."""
        config = config or GenerationConfig()
        
        # Separate system message
        system_msg = system or ""
        chat_messages = []
        
        for msg in messages:
            if msg.role == "system":
                if not system_msg:
                    system_msg = msg.content
            else:
                chat_messages.append({
                    "role": msg.role,
                    "content": msg.content
                })
        
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": chat_messages,
            "max_tokens": config.max_tokens,
            "temperature": config.temperature,
            "top_p": config.top_p,
            "stream": True
        }
        
        if system_msg:
            payload["system"] = system_msg
        
        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/messages",
                headers=headers,
                json=payload,
                timeout=120.0
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        if data == "[DONE]":
                            break
                        try:
                            import json
                            chunk = json.loads(data)
                            if chunk.get("type") == "content_block_delta":
                                if delta := chunk.get("delta", {}).get("text"):
                                    yield delta
                        except json.JSONDecodeError:
                            continue
    
    async def generate_sync(
        self,
        messages: List[Message],
        system: Optional[str] = None,
        config: Optional[GenerationConfig] = None
    ) -> str:
        """Non-streaming generation."""
        config = config or GenerationConfig()
        config.stream = False
        
        parts = []
        async for chunk in self.generate(messages, system, config):
            parts.append(chunk)
        return "".join(parts)
    
    def count_tokens(self, text: str) -> int:
        """Approximate token count."""
        # Claude uses ~4 chars per token on average
        return len(text) // 4
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get model information."""
        models = {
            "claude-haiku-4-5-20251001": {
                "max_tokens": 200000,
                "description": "Fastest Claude model (Haiku 4.5)"
            },
            "claude-sonnet-4-6": {
                "max_tokens": 200000,
                "description": "Balanced performance and speed (Sonnet 4.6)"
            },
            "claude-opus-4-6": {
                "max_tokens": 200000,
                "description": "Most powerful Claude model (Opus 4.6)"
            },
        }
        return models.get(self.model, {"max_tokens": 200000})
