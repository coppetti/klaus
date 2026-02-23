"""
IDE Agent Wizard - Core Agent
=============================
Main agent class that reads init.yaml and orchestrates everything.
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, List, AsyncIterator
from datetime import datetime

from .providers import create_provider, Message, GenerationConfig
from .memory import MemoryStore

class Agent:
    """
    Main agent class that works with any IDE and LLM provider.
    
    Usage:
        agent = Agent.from_config("init.yaml")
        response = await agent.chat("Hello!")
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.agent_config = config.get('agent', {})
        self.user_config = config.get('user', {})
        self.provider_config = config.get('provider', {})
        self.memory_config = config.get('memory', {})
        
        # Initialize provider
        self.provider = None
        self._init_provider()
        
        # Initialize memory
        self.memory = None
        if self.memory_config.get('enabled', True):
            self._init_memory()
        
        # Load context files
        self.system_prompt = self._build_system_prompt()
        
    def _init_provider(self):
        """Initialize LLM provider from config."""
        provider_name = self.provider_config.get('name', 'anthropic')
        
        # Get API key from env or config
        api_key = self.provider_config.get('api_key', '')
        if not api_key:
            env_var = f"{provider_name.upper()}_API_KEY"
            api_key = os.getenv(env_var, os.getenv('LLM_API_KEY', ''))
        
        if not api_key:
            raise ValueError(f"No API key found for {provider_name}. "
                           f"Set {provider_name.upper()}_API_KEY env var.")
        
        # Get model
        model = self.provider_config.get('model', {}).get(provider_name)
        if not model:
            # Use default
            defaults = {
                'anthropic': 'claude-3-5-sonnet-20241022',
                'openrouter': 'anthropic/claude-3.5-sonnet',
                'gemini': 'gemini-1.5-pro',
                'kimi': 'kimi-latest'
            }
            model = defaults.get(provider_name, 'claude-3-5-sonnet-20241022')
        
        self.provider = create_provider(provider_name, api_key, model)
    
    def _init_memory(self):
        """Initialize memory store."""
        backend = self.memory_config.get('backend', 'sqlite')
        
        if backend == 'sqlite':
            db_path = self.memory_config.get('sqlite', {}).get('path', './memory.db')
            self.memory = MemoryStore(db_path)
        else:
            # Fallback to simple JSON memory
            self.memory = MemoryStore('./memory.json')
    
    def _build_system_prompt(self) -> str:
        """Build system prompt from config and SOUL.md."""
        parts = []
        
        # Load SOUL.md if exists
        soul_path = Path("SOUL.md")
        if soul_path.exists():
            parts.append(soul_path.read_text())
        else:
            # Build from template
            parts.append(self._build_soul_from_config())
        
        # Load USER.md if exists
        user_path = Path("USER.md")
        if user_path.exists():
            parts.append(f"\n\n--- USER PROFILE ---\n{user_path.read_text()}")
        else:
            parts.append(f"\n\n--- USER PROFILE ---\n{self._build_user_from_config()}")
        
        # Add custom instructions
        custom = self.config.get('custom_instructions', '')
        if custom:
            parts.append(f"\n\n--- CUSTOM INSTRUCTIONS ---\n{custom}")
        
        return "\n\n".join(parts)
    
    def _build_soul_from_config(self) -> str:
        """Build SOUL content from config."""
        agent = self.agent_config
        return f"""# SOUL - {agent.get('name', 'Agent')}

## Identity
**Name:** {agent.get('name', 'Agent')}
**Version:** {agent.get('version', '1.0.0')}
**Description:** {agent.get('description', 'AI Assistant')}

## Personality
**Tone:** {agent.get('personality', {}).get('tone', 'professional')}
**Style:** {agent.get('personality', {}).get('style', 'balanced')}
**Language:** {agent.get('personality', {}).get('language', 'en')}

## Guidelines
- Be helpful, accurate, and concise
- Adapt to user's experience level
- Ask clarifying questions when needed
- Explain reasoning when appropriate
"""
    
    def _build_user_from_config(self) -> str:
        """Build USER content from config."""
        user = self.user_config
        return f"""# USER Profile

## Information
**Name:** {user.get('name', 'User')}
**Role:** {user.get('role', 'Unknown')}
**Experience:** {user.get('experience_level', 'intermediate')}

## Preferences
- Communication: {user.get('preferences', {}).get('communication', 'concise')}
- Code Style: {user.get('preferences', {}).get('code_style', 'clean')}
- Working Hours: {user.get('preferences', {}).get('working_hours', '9-18')}
- Timezone: {user.get('preferences', {}).get('timezone', 'UTC')}
"""
    
    async def chat(self, message: str, context: Optional[str] = None) -> AsyncIterator[str]:
        """
        Send message to agent and get streaming response.
        
        Args:
            message: User message
            context: Additional context (e.g., file content)
            
        Yields:
            Response tokens
        """
        # Build messages
        messages = [Message(role="system", content=self.system_prompt)]
        
        # Add context if provided
        if context:
            messages.append(Message(role="system", content=f"Context:\n{context}"))
        
        # Add memories if available
        if self.memory:
            memories = self.memory.recall(message)
            if memories:
                mem_text = "Relevant memories:\n" + "\n".join(
                    f"- {m['content']}" for m in memories[:5]
                )
                messages.append(Message(role="system", content=mem_text))
        
        # Add user message
        messages.append(Message(role="user", content=message))
        
        # Get generation config
        params = self.provider_config.get('parameters', {})
        config = GenerationConfig(
            temperature=params.get('temperature', 0.7),
            max_tokens=params.get('max_tokens', 4096),
            top_p=params.get('top_p', 0.9)
        )
        
        # Stream response
        full_response = []
        async for token in self.provider.generate(messages, config):
            full_response.append(token)
            yield token
        
        # Store memory
        if self.memory:
            response_text = "".join(full_response)
            self.memory.store(
                content=f"User: {message}\nAssistant: {response_text[:200]}...",
                category="conversation",
                importance="medium"
            )
    
    async def chat_sync(self, message: str, context: Optional[str] = None) -> str:
        """Non-streaming chat."""
        parts = []
        async for token in self.chat(message, context):
            parts.append(token)
        return "".join(parts)
    
    @classmethod
    def from_config(cls, config_path: str = "init.yaml") -> "Agent":
        """Create agent from config file."""
        config_file = Path(config_path)
        
        if not config_file.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")
        
        with open(config_file) as f:
            config = yaml.safe_load(f)
        
        return cls(config)
    
    def get_info(self) -> Dict[str, Any]:
        """Get agent information."""
        return {
            "name": self.agent_config.get('name', 'Agent'),
            "provider": self.provider_config.get('name', 'unknown'),
            "model": self.provider.model if self.provider else 'unknown',
            "memory_enabled": self.memory is not None,
            "system_prompt_length": len(self.system_prompt)
        }
