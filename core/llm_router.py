import os
import yaml
from pathlib import Path
from typing import List, Dict, Optional, Any
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("llm_router")

def load_config():
    """Load configuration from init.yaml."""
    init_paths = [
        Path("/app/workspace/init.yaml"),
        Path("/app/init.yaml"),
        Path("./workspace/init.yaml"),
        Path("./init.yaml"),
        Path(__file__).parent.parent / "init.yaml",
    ]
    
    for path in init_paths:
        if path.exists():
            try:
                with open(path) as f:
                    return yaml.safe_load(f)
            except Exception as e:
                logger.error(f"Error loading config from {path}: {e}")
    
    return {}

async def chat_with_provider(
    messages: List[Dict[str, str]], 
    system: Optional[str] = None,
    provider: Optional[str] = None, 
    model: Optional[str] = None, 
    temperature: float = 0.7, 
    max_tokens: int = 4096
) -> str:
    """
    Shared routing logic for LLM calls.
    If provider/model are not provided, uses defaults from init.yaml.
    """
    config = load_config()
    defaults = config.get("defaults", {})
    
    # Resolve provider and model
    final_provider = provider or defaults.get("provider", "kimi")
    final_model = model or defaults.get("model", "kimi-k2-0711")
    
    logger.info(f"Routing chat request to {final_provider}/{final_model}")
    
    # Try to use the core.providers system if available
    try:
        from core.providers import create_provider, Message
        
        # Get API key from env or config
        api_key = os.getenv(f"{final_provider.upper()}_API_KEY", "")
        if not api_key and "provider" in config:
             if config["provider"].get("name") == final_provider:
                 api_key = config["provider"].get("api_key", "")
        
        if not api_key:
            # Fallback for Kimi which sometimes uses moonshot prefix or specific env
            if final_provider == "kimi":
                api_key = os.getenv("KIMI_API_KEY", os.getenv("MOONSHOT_API_KEY", ""))
        
        # Format messages for core.providers
        provider_messages = []
        for msg in messages:
            provider_messages.append(Message(role=msg["role"], content=msg["content"]))
            
        # Create provider instance
        llm = create_provider(
            provider_name=final_provider,
            api_key=api_key,
            model=final_model,
            config={"temperature": temperature, "max_tokens": max_tokens}
        )
        
        # Generate response
        response = await llm.generate_sync(messages=provider_messages, system=system)
        return response
        
    except ImportError:
        logger.warning("core.providers not found or failed to import, using fallback logic")
        # Simple fallback for Kimi/Anthropic if core.providers is not fully ready/available in this context
        return await _fallback_chat(final_provider, final_model, messages, system, temperature, max_tokens)
    except Exception as e:
        logger.error(f"Error using core.providers: {e}")
        return await _fallback_chat(final_provider, final_model, messages, system, temperature, max_tokens)

async def _fallback_chat(provider, model, messages, system, temperature, max_tokens):
    """Minimal fallback for essential providers."""
    if provider in ["kimi", "anthropic"]:
        from anthropic import Anthropic
        api_key = os.getenv(f"{provider.upper()}_API_KEY", os.getenv("MOONSHOT_API_KEY", ""))
        base_url = "https://api.kimi.com/coding" if provider == "kimi" else None
        
        client = Anthropic(api_key=api_key, base_url=base_url)
        
        kwargs = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        if system:
            kwargs["system"] = system
            
        # Synchronous-ish streaming fallback
        response = ""
        with client.messages.stream(**kwargs) as stream:
            for text in stream.text_stream:
                response += text
        return response
    
    elif provider == "openai":
        from openai import OpenAI
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))
        
        # Prepend system message
        openai_messages = messages.copy()
        if system:
            openai_messages.insert(0, {"role": "system", "content": system})
            
        response = client.chat.completions.create(
            model=model,
            messages=openai_messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        return response.choices[0].message.content
    
    elif provider in ["google", "gemini"]:
        import google.generativeai as genai
        genai.configure(api_key=os.getenv("GOOGLE_API_KEY", ""))
        
        model_instance = genai.GenerativeModel(model)
        
        # Format messages for Gemini
        gemini_messages = []
        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            if role == "user":
                gemini_messages.append({"role": "user", "parts": [content]})
            else:
                gemini_messages.append({"role": "model", "parts": [content]})
        
        # Start chat and send messages
        chat = model_instance.start_chat(history=gemini_messages[:-1] if len(gemini_messages) > 1 else [])
        
        # Generate response
        generation_config = {
            "temperature": temperature,
            "max_output_tokens": max_tokens
        }
        
        response = chat.send_message(
            gemini_messages[-1]["parts"][0] if gemini_messages else "",
            generation_config=generation_config
        )
        return response.text
    
    elif provider == "openrouter":
        from openai import OpenAI
        client = OpenAI(
            api_key=os.getenv("OPENROUTER_API_KEY", ""),
            base_url="https://openrouter.ai/api/v1"
        )
        
        # Prepend system message
        openrouter_messages = messages.copy()
        if system:
            openrouter_messages.insert(0, {"role": "system", "content": system})
            
        response = client.chat.completions.create(
            model=model,
            messages=openrouter_messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        return response.choices[0].message.content
    
    elif provider == "custom":
        from openai import OpenAI
        
        # Get custom provider config from env
        base_url = os.getenv("CUSTOM_BASE_URL", "http://localhost:11434/v1")
        api_key = os.getenv("CUSTOM_API_KEY", "ollama")  # Ollama doesn't require key but OpenAI client needs something
        
        client = OpenAI(
            api_key=api_key,
            base_url=base_url
        )
        
        # Prepend system message
        custom_messages = messages.copy()
        if system:
            custom_messages.insert(0, {"role": "system", "content": system})
            
        response = client.chat.completions.create(
            model=model or os.getenv("CUSTOM_MODEL", "llama3.2"),
            messages=custom_messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        return response.choices[0].message.content
        
    raise Exception(f"Provider {provider} not supported in fallback and core.providers failed.")
