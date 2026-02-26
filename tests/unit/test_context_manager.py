"""
Test Context Manager - Aligned with Production Implementation
==============================================================
Tests the actual SessionContextManager and ContextManager classes
as used in docker/web-ui/app.py
"""
import pytest
from unittest.mock import Mock, patch, MagicMock, mock_open
from datetime import datetime
import json
from pathlib import Path


class TestContextManagerInitialization:
    """Test ContextManager initialization."""
    
    def test_context_manager_creation(self):
        """Test creating ContextManager."""
        from core.context_manager import ContextManager
        
        cm = ContextManager(max_tokens=4000)
        assert cm is not None
        assert cm.max_tokens == 4000
    
    def test_context_manager_default_tokens(self):
        """Test ContextManager default token count."""
        from core.context_manager import ContextManager
        
        cm = ContextManager()
        assert cm.max_tokens > 0  # Default is 200000
    
    def test_context_manager_initial_state(self):
        """Test ContextManager initial state."""
        from core.context_manager import ContextManager
        
        cm = ContextManager()
        assert hasattr(cm, 'facts')
        assert isinstance(cm.facts, list)
        assert len(cm.facts) == 0
        assert cm.message_counter == 0


class TestContextManagerFactExtraction:
    """Test ContextManager fact extraction capabilities."""
    
    def test_extract_preference_facts(self):
        """Test extracting preference facts from user message."""
        from core.context_manager import ContextManager
        
        cm = ContextManager()
        facts = cm.extract_facts("I prefer Python over JavaScript")
        
        assert len(facts) > 0
        assert any(f.category == "preference" for f in facts)
    
    def test_extract_task_facts(self):
        """Test extracting task facts from user message."""
        from core.context_manager import ContextManager
        
        cm = ContextManager()
        facts = cm.extract_facts("I need you to create a REST API")
        
        assert len(facts) > 0
        assert any(f.category == "task" for f in facts)
    
    def test_extract_information_facts(self):
        """Test extracting information facts."""
        from core.context_manager import ContextManager
        
        cm = ContextManager()
        facts = cm.extract_facts("My name is John and I work with AI")
        
        assert len(facts) > 0
        assert any(f.category == "information" for f in facts)
    
    def test_add_exchange_extracts_facts(self):
        """Test that add_exchange extracts and stores facts."""
        from core.context_manager import ContextManager
        
        cm = ContextManager()
        facts = cm.add_exchange("I prefer using React", "I'll help you with React")
        
        assert len(facts) > 0
        assert len(cm.facts) > 0
        cm.message_counter == 1


class TestContextManagerTokenEstimation:
    """Test ContextManager token estimation."""
    
    def test_estimate_tokens(self):
        """Test token estimation for text."""
        from core.context_manager import ContextManager
        
        cm = ContextManager()
        # Portuguese ~3 chars/token
        text = "Hello world"  # 11 chars
        tokens = cm.estimate_tokens(text)
        assert tokens > 0
        assert tokens == len(text) // 3


class TestContextManagerContextBuilding:
    """Test ContextManager context building."""
    
    def test_build_context_with_soul(self):
        """Test building context with SOUL content."""
        from core.context_manager import ContextManager
        
        cm = ContextManager()
        messages = [{"sender": "user", "text": "Hello"}]
        soul = "You are a helpful assistant."
        
        context = cm.build_context(messages, soul)
        
        assert len(context) > 0
        assert context[0]["role"] == "system"
        assert soul in context[0]["content"]
    
    def test_build_context_includes_facts(self):
        """Test that facts are included in context."""
        from core.context_manager import ContextManager
        
        cm = ContextManager()
        cm.add_exchange("My name is Alice", "Hello Alice")
        
        messages = [{"sender": "user", "text": "Hello"}]
        soul = "You are helpful."
        
        context = cm.build_context(messages, soul)
        
        assert len(context) > 0
        assert any("Alice" in str(msg.get("content", "")) for msg in context)
    
    def test_build_context_with_web_search(self):
        """Test building context with web search results."""
        from core.context_manager import ContextManager
        
        cm = ContextManager()
        messages = [{"sender": "user", "text": "Search results"}]
        soul = "You are helpful."
        web_results = "Web: Python is popular"
        
        context = cm.build_context(messages, soul, web_results)
        
        assert len(context) > 0


class TestContextManagerStats:
    """Test ContextManager statistics."""
    
    def test_get_context_stats_empty(self):
        """Test stats with no facts."""
        from core.context_manager import ContextManager
        
        cm = ContextManager()
        stats = cm.get_context_stats()
        
        assert stats["facts_stored"] == 0
        assert isinstance(stats["facts_by_category"], dict)
    
    def test_get_context_stats_with_facts(self):
        """Test stats with facts."""
        from core.context_manager import ContextManager
        
        cm = ContextManager()
        cm.add_exchange("I prefer Python", "OK")
        
        stats = cm.get_context_stats()
        
        assert stats["facts_stored"] > 0
        assert "preference" in stats["facts_by_category"]


class TestContextFact:
    """Test ContextFact dataclass."""
    
    def test_context_fact_creation(self):
        """Test creating ContextFact."""
        from core.context_manager import ContextFact
        
        fact = ContextFact(
            content="Prefers Python",
            category="preference",
            timestamp="2024-01-01T00:00:00",
            message_id="1"
        )
        
        assert fact.content == "Prefers Python"
        assert fact.category == "preference"
    
    def test_context_fact_to_dict(self):
        """Test ContextFact serialization."""
        from core.context_manager import ContextFact
        
        fact = ContextFact(
            content="Prefers Python",
            category="preference",
            timestamp="2024-01-01T00:00:00",
            message_id="1"
        )
        
        data = fact.to_dict()
        assert data["content"] == "Prefers Python"
        assert data["category"] == "preference"
    
    def test_context_fact_from_dict(self):
        """Test ContextFact deserialization."""
        from core.context_manager import ContextFact
        
        data = {
            "content": "Prefers Python",
            "category": "preference",
            "timestamp": "2024-01-01T00:00:00",
            "message_id": "1"
        }
        
        fact = ContextFact.from_dict(data)
        assert fact.content == "Prefers Python"
        assert fact.category == "preference"


class TestSessionContextManager:
    """Test SessionContextManager - the production interface."""
    
    @patch('pathlib.Path.mkdir')
    @patch('pathlib.Path.exists')
    @patch('builtins.open', mock_open(read_data='[]'))
    def test_session_context_manager_creation(self, mock_exists, mock_mkdir):
        """Test creating SessionContextManager."""
        from core.context_manager import SessionContextManager
        
        mock_exists.return_value = False
        
        scm = SessionContextManager("session_123", max_messages=100)
        assert scm.session_id == "session_123"
        assert scm.max_messages == 100
    
    @patch('pathlib.Path.mkdir')
    @patch('pathlib.Path.exists')
    @patch('pathlib.Path.__truediv__')
    @patch('builtins.open')
    def test_session_add_exchange(self, mock_open, mock_truediv, mock_exists, mock_mkdir):
        """Test adding exchange to session."""
        from core.context_manager import SessionContextManager
        
        mock_exists.return_value = False
        mock_file = MagicMock()
        mock_open.return_value.__enter__ = MagicMock(return_value=mock_file)
        mock_open.return_value.__exit__ = MagicMock(return_value=None)
        
        scm = SessionContextManager("session_123")
        facts = scm.add_exchange("I prefer React", "I'll help with React")
        
        assert isinstance(facts, list)
    
    @patch('pathlib.Path.mkdir')
    @patch('pathlib.Path.exists')
    @patch('builtins.open', mock_open(read_data='[]'))
    def test_session_build_context(self, mock_exists, mock_mkdir):
        """Test building context for session."""
        from core.context_manager import SessionContextManager
        
        mock_exists.return_value = False
        
        scm = SessionContextManager("session_123")
        scm.add_exchange("My name is Bob", "Hello Bob")
        
        messages = [{"sender": "user", "text": "Hello"}]
        soul = "You are helpful."
        
        context = scm.build_context(messages, soul)
        
        assert isinstance(context, list)
        assert len(context) > 0
    
    @patch('pathlib.Path.mkdir')
    @patch('pathlib.Path.exists')
    @patch('builtins.open', mock_open(read_data='[]'))
    def test_session_export_facts(self, mock_exists, mock_mkdir):
        """Test exporting facts from session."""
        from core.context_manager import SessionContextManager
        
        mock_exists.return_value = False
        
        scm = SessionContextManager("session_123")
        scm.add_exchange("I prefer Python", "OK")
        
        facts = scm.export_facts()
        
        assert isinstance(facts, list)
        assert len(facts) > 0
    
    @patch('pathlib.Path.mkdir')
    @patch('pathlib.Path.exists')
    @patch('builtins.open', mock_open(read_data='[]'))
    def test_session_clear_facts(self, mock_exists, mock_mkdir):
        """Test clearing session facts."""
        from core.context_manager import SessionContextManager
        
        mock_exists.return_value = False
        
        scm = SessionContextManager("session_123")
        scm.add_exchange("I prefer Python", "OK")
        scm.clear_facts()
        
        assert len(scm.facts) == 0
    
    @patch('pathlib.Path.mkdir')
    @patch('pathlib.Path.exists')
    @patch('builtins.open', mock_open(read_data='[]'))
    def test_session_get_facts_summary_empty(self, mock_exists, mock_mkdir):
        """Test facts summary when empty."""
        from core.context_manager import SessionContextManager
        
        mock_exists.return_value = False
        
        scm = SessionContextManager("session_123")
        summary = scm.get_facts_summary()
        
        assert "No facts" in summary
    
    @patch('pathlib.Path.mkdir')
    @patch('pathlib.Path.exists')
    @patch('builtins.open', mock_open(read_data='[]'))
    def test_session_get_facts_summary_with_facts(self, mock_exists, mock_mkdir):
        """Test facts summary with facts."""
        from core.context_manager import SessionContextManager
        
        mock_exists.return_value = False
        
        scm = SessionContextManager("session_123")
        scm.add_exchange("I prefer Python", "OK")
        
        summary = scm.get_facts_summary()
        
        assert "preference" in summary
