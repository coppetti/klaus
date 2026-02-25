"""
Providers Module
================
Unified interface for multiple LLM providers.

Supported providers:
- Anthropic (Claude)
- OpenRouter (multi-model)
- Google (Gemini)
- Moonshot (Kimi)
"""

from typing import Dict, Any, Optional
from .base import BaseProvider, ProviderType, Message, GenerationConfig, Usage
from .anthropic_provider import AnthropicProvider
from .openrouter_provider import OpenRouterProvider
from .gemini_provider import GeminiProvider
from .kimi_provider import KimiProvider

# Provider registry
PROVIDER_MAP = {
    ProviderType.ANTHROPIC: AnthropicProvider,
    ProviderType.OPENROUTER: OpenRouterProvider,
    ProviderType.GEMINI: GeminiProvider,
    ProviderType.KIMI: KimiProvider,
}

def create_provider(
    provider_name: str,
    api_key: str,
    model: Optional[str] = None,
    config: Optional[Dict] = None
) -> BaseProvider:
    """
    Factory function to create appropriate provider.
    
    Args:
        provider_name: One of 'anthropic', 'openrouter', 'gemini', 'kimi'
        api_key: API key for the provider
        model: Model name (optional, uses default if not specified)
        config: Additional configuration
        
    Returns:
        Configured provider instance
        
    Raises:
        ValueError: If provider_name is not recognized
    """
    provider_map_str = {
        "anthropic": ProviderType.ANTHROPIC,
        "openrouter": ProviderType.OPENROUTER,
        "gemini": ProviderType.GEMINI,
        "kimi": ProviderType.KIMI,
    }
    
    provider_type = provider_map_str.get(provider_name.lower())
    if not provider_type:
        raise ValueError(f"Unknown provider: {provider_name}. "
                        f"Supported: {list(provider_map_str.keys())}")
    
    provider_class = PROVIDER_MAP[provider_type]
    
    # Default models
    default_models = {
        ProviderType.ANTHROPIC: "claude-3-5-sonnet-20241022",
        ProviderType.OPENROUTER: "anthropic/claude-3.5-sonnet",
        ProviderType.GEMINI: "gemini-1.5-pro",
        ProviderType.KIMI: "kimi-k2-5",
    }
    
    if not model:
        model = default_models[provider_type]
    
    return provider_class(api_key=api_key, model=model, config=config)

def get_available_providers() -> list:
    """Get list of available provider names."""
    return ["anthropic", "openrouter", "gemini", "kimi"]

def get_provider_models(provider_name: str) -> Dict[str, Any]:
    """Get available models for a provider."""
    models = {
        "anthropic": {
            "claude-3-opus-20240229": "Most powerful",
            "claude-3-5-sonnet-20241022": "Balanced",
            "claude-3-haiku-20240307": "Fastest"
        },
        "openrouter": {
            "anthropic/claude-3.5-sonnet": "Claude via OpenRouter",
            "openai/gpt-4o": "GPT-4o via OpenRouter",
            "meta-llama/llama-3.1-405b": "Llama 405B",
            "google/gemini-pro-1.5": "Gemini via OpenRouter"
        },
        "gemini": {
            "gemini-1.5-pro": "Most capable",
            "gemini-1.5-flash": "Fastest"
        },
        "kimi": {
            "kimi-k2-5": "Latest stable model (default)",
            "kimi-k1-5": "K1.5 model"
        }
    }
    return models.get(provider_name.lower(), {})

__all__ = [
    'BaseProvider',
    'ProviderType',
    'Message',
    'GenerationConfig',
    'Usage',
    'AnthropicProvider',
    'OpenRouterProvider',
    'GeminiProvider',
    'KimiProvider',
    'create_provider',
    'get_available_providers',
    'get_provider_models',
]
