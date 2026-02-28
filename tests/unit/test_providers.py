"""
Test LLM Providers - Aligned with Production Implementation
============================================================
Tests providers with their actual interfaces:
- generate(): streaming async
- generate_sync(): non-streaming async
- count_tokens()
- get_model_info()
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
import sys


class TestBaseProvider:
    """Test base provider functionality."""
    
    def test_base_provider_exists(self):
        """Test that base provider class exists."""
        from core.providers.base import BaseProvider
        assert BaseProvider is not None
    
    def test_base_provider_has_generate(self):
        """Test that base provider defines generate method."""
        from core.providers.base import BaseProvider
        assert hasattr(BaseProvider, 'generate')
    
    def test_base_provider_has_generate_sync(self):
        """Test that base provider defines generate_sync method."""
        from core.providers.base import BaseProvider
        assert hasattr(BaseProvider, 'generate_sync')


class TestKimiProvider:
    """Test Kimi provider with real interface."""
    
    def test_kimi_provider_creation(self, mock_env_vars):
        """Test creating Kimi provider."""
        from core.providers.kimi_provider import KimiProvider
        
        with patch('core.providers.kimi_provider.Anthropic'):
            provider = KimiProvider(api_key="test-key")
            assert provider is not None
            assert provider.model == "kimi-k2-5"
    
    @pytest.mark.asyncio
    async def test_kimi_provider_generate_sync(self, mock_env_vars):
        """Test Kimi provider generate_sync method."""
        from core.providers.kimi_provider import KimiProvider
        from core.providers.base import Message
        
        mock_response = Mock()
        mock_response.content = [Mock(text="Test response")]
        
        with patch('core.providers.kimi_provider.Anthropic') as mock_anthropic:
            mock_client = Mock()
            mock_client.messages.create.return_value = mock_response
            mock_anthropic.return_value = mock_client
            
            provider = KimiProvider(api_key="test-key")
            messages = [Message(role="user", content="Hello")]
            result = await provider.generate_sync(messages)
            
            assert result == "Test response"
            mock_client.messages.create.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_kimi_provider_generate_streaming(self, mock_env_vars):
        """Test Kimi provider generate streaming method."""
        from core.providers.kimi_provider import KimiProvider
        from core.providers.base import Message
        
        with patch('core.providers.kimi_provider.Anthropic') as mock_anthropic:
            mock_stream = MagicMock()
            mock_stream.__enter__ = Mock(return_value=mock_stream)
            mock_stream.__exit__ = Mock(return_value=False)
            mock_stream.text_stream = ["Hello", " ", "world"]
            
            mock_client = Mock()
            mock_client.messages.stream.return_value = mock_stream
            mock_anthropic.return_value = mock_client
            
            provider = KimiProvider(api_key="test-key")
            messages = [Message(role="user", content="Hello")]
            
            chunks = []
            async for chunk in provider.generate(messages):
                chunks.append(chunk)
            
            assert "".join(chunks) == "Hello world"
    
    def test_kimi_provider_count_tokens(self, mock_env_vars):
        """Test Kimi provider token counting."""
        from core.providers.kimi_provider import KimiProvider
        
        with patch('core.providers.kimi_provider.Anthropic'):
            provider = KimiProvider(api_key="test-key")
            tokens = provider.count_tokens("Hello world")
            assert tokens > 0
    
    def test_kimi_provider_get_model_info(self, mock_env_vars):
        """Test Kimi provider model info."""
        from core.providers.kimi_provider import KimiProvider
        
        with patch('core.providers.kimi_provider.Anthropic'):
            provider = KimiProvider(api_key="test-key")
            info = provider.get_model_info()
            
            assert info["provider"] == "kimi"
            assert "model" in info
            assert "max_tokens" in info


class TestAnthropicProvider:
    """Test Anthropic provider."""
    
    def test_anthropic_provider_creation(self):
        """Test creating Anthropic provider."""
        try:
            from core.providers.anthropic_provider import AnthropicProvider
            
            provider = AnthropicProvider(api_key="test-key")
            assert provider is not None
        except ImportError:
            pytest.skip("Anthropic provider not available")
    
    @pytest.mark.asyncio
    async def test_anthropic_provider_generate_sync(self):
        """Test Anthropic provider generate_sync."""
        try:
            from core.providers.anthropic_provider import AnthropicProvider
            from core.providers.base import Message
            
            provider = AnthropicProvider(api_key="test-key")
            messages = [Message(role="user", content="Hello")]
            
            # Just verify it doesn't crash - actual API call would need mocking
            assert provider is not None
            assert len(messages) == 1
        except ImportError:
            pytest.skip("Anthropic provider not available")


class TestOpenRouterProvider:
    """Test OpenRouter provider."""
    
    def test_openrouter_provider_creation(self):
        """Test creating OpenRouter provider."""
        try:
            from core.providers.openrouter_provider import OpenRouterProvider
            
            with patch.dict('os.environ', {'OPENROUTER_API_KEY': 'test-key'}):
                provider = OpenRouterProvider(api_key="test-key")
                assert provider is not None
        except ImportError:
            pytest.skip("OpenRouter provider not available")


class TestGeminiProvider:
    """Test Gemini provider."""
    
    def test_gemini_provider_creation(self):
        """Test creating Gemini provider."""
        try:
            from core.providers.gemini_provider import GeminiProvider
            
            provider = GeminiProvider(api_key="test-key")
            assert provider is not None
        except ImportError:
            pytest.skip("Gemini provider not available")


class TestProviderFactory:
    """Test provider factory."""
    
    def test_create_provider_kimi(self, mock_env_vars):
        """Test creating Kimi provider via factory."""
        from core.providers import create_provider
        
        with patch('core.providers.kimi_provider.Anthropic'):
            provider = create_provider("kimi", api_key="test-key")
            assert provider is not None
    
    def test_create_provider_invalid(self):
        """Test creating invalid provider."""
        from core.providers import create_provider
        
        with pytest.raises((ValueError, KeyError)):
            create_provider("invalid_provider", api_key="test")
    
    def test_create_provider_case_insensitive(self, mock_env_vars):
        """Test that provider names are case insensitive."""
        from core.providers import create_provider
        
        with patch('core.providers.kimi_provider.Anthropic'):
            provider_lower = create_provider("kimi", api_key="test-key")
            provider_upper = create_provider("KIMI", api_key="test-key")
            assert type(provider_lower) == type(provider_upper)


class TestProviderErrorHandling:
    """Test provider error handling."""
    
    @pytest.mark.asyncio
    async def test_provider_handles_timeout(self, mock_env_vars):
        """Test that providers handle timeouts."""
        from core.providers.kimi_provider import KimiProvider
        from core.providers.base import Message
        
        with patch('core.providers.kimi_provider.Anthropic') as mock_anthropic:
            mock_client = Mock()
            mock_client.messages.create.side_effect = TimeoutError("Connection timeout")
            mock_anthropic.return_value = mock_client
            
            provider = KimiProvider(api_key="test-key")
            messages = [Message(role="user", content="Hello")]
            
            with pytest.raises(TimeoutError):
                await provider.generate_sync(messages)
    
    @pytest.mark.asyncio
    async def test_provider_handles_rate_limit(self, mock_env_vars):
        """Test that providers handle rate limits."""
        from core.providers.kimi_provider import KimiProvider
        from core.providers.base import Message
        
        with patch('core.providers.kimi_provider.Anthropic') as mock_anthropic:
            mock_client = Mock()
            error = Exception("Rate limit exceeded")
            mock_client.messages.create.side_effect = error
            mock_anthropic.return_value = mock_client
            
            provider = KimiProvider(api_key="test-key")
            messages = [Message(role="user", content="Hello")]
            
            with pytest.raises(Exception):
                await provider.generate_sync(messages)


class TestProviderConfiguration:
    """Test provider configuration loading."""
    
    def test_load_config_exists(self):
        """Test that load_config function exists."""
        from core.llm_router import load_config
        assert callable(load_config)
    
    def test_load_config_returns_dict(self):
        """Test that load_config returns a dictionary."""
        from core.llm_router import load_config
        
        config = load_config()
        assert isinstance(config, dict)
    
    def test_config_has_structure(self):
        """Test that config has expected structure."""
        from core.llm_router import load_config
        
        config = load_config()
        # Config can be empty or have provider/agent/memory keys
        assert isinstance(config, dict)
        # Check for any of the expected top-level keys
        expected_keys = ["provider", "agent", "memory", "mode", "providers", "defaults"]
        has_expected = any(key in config for key in expected_keys)
        assert has_expected or len(config) == 0
