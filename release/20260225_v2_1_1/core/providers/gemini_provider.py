"""
Gemini Provider
===============
Google Gemini models via Vertex AI or Gemini API.
"""

import json
from typing import AsyncIterator, Dict, List, Optional, Any
import httpx
from .base import BaseProvider, Message, GenerationConfig, ProviderType

class GeminiProvider(BaseProvider):
    """Google Gemini provider."""
    
    def __init__(self, api_key: str, model: str = "gemini-1.5-pro", config: Dict = None):
        super().__init__(api_key, model, config)
        self.provider_type = ProviderType.GEMINI
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"
        
    def _convert_messages(self, messages: List[Message]) -> List[Dict]:
        """Convert to Gemini format."""
        gemini_contents = []
        
        for msg in messages:
            if msg.role == "system":
                # Gemini handles system as part of first user message or model config
                continue
            
            role = "user" if msg.role == "user" else "model"
            gemini_contents.append({
                "role": role,
                "parts": [{"text": msg.content}]
            })
        
        return gemini_contents
    
    async def generate(
        self,
        messages: List[Message],
        config: Optional[GenerationConfig] = None
    ) -> AsyncIterator[str]:
        """Stream response from Gemini."""
        config = config or GenerationConfig()
        
        # Extract system instruction
        system_instruction = None
        chat_messages = []
        
        for msg in messages:
            if msg.role == "system":
                system_instruction = msg.content
            else:
                chat_messages.append(msg)
        
        headers = {
            "Content-Type": "application/json"
        }
        
        contents = self._convert_messages(chat_messages)
        
        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": config.temperature,
                "maxOutputTokens": config.max_tokens,
                "topP": config.top_p
            }
        }
        
        if system_instruction:
            payload["systemInstruction"] = {
                "parts": [{"text": system_instruction}]
            }
        
        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/models/{self.model}:streamGenerateContent?key={self.api_key}",
                headers=headers,
                json=payload,
                timeout=120.0
            ) as response:
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        try:
                            data = json.loads(line[6:])
                            if candidates := data.get("candidates", []):
                                if content := candidates[0].get("content", {}):
                                    if parts := content.get("parts", []):
                                        if text := parts[0].get("text"):
                                            yield text
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
        models = {
            "gemini-1.5-pro": {
                "max_tokens": 2000000,
                "description": "Most capable Gemini model"
            },
            "gemini-1.5-flash": {
                "max_tokens": 1000000,
                "description": "Fast Gemini model"
            }
        }
        return models.get(self.model, {"max_tokens": 2000000})
