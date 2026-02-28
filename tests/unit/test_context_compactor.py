"""
Test Context Compactor - Aligned with Production Implementation
================================================================
Tests ContextCompactor and ContextAnalyzer as used in production.
"""
import pytest
from datetime import datetime


class TestContextCompactor:
    """Test ContextCompactor class."""
    
    def test_compactor_creation(self):
        """Test creating context compactor."""
        from core.context_compactor import ContextCompactor
        
        compactor = ContextCompactor(max_tokens=4000)
        assert compactor is not None
        assert compactor.max_tokens == 4000
    
    def test_compactor_default_tokens(self):
        """Test default token limit."""
        from core.context_compactor import ContextCompactor
        
        compactor = ContextCompactor()
        assert compactor.max_tokens > 0
    
    def test_estimate_tokens(self):
        """Test token estimation."""
        from core.context_compactor import ContextCompactor
        
        compactor = ContextCompactor()
        text = "Hello world test"
        tokens = compactor.estimate_tokens(text)
        assert tokens > 0
        assert tokens == len(text) // 3


class TestMessageCompaction:
    """Test message compaction strategies."""
    
    def test_compact_context_with_many_messages(self):
        """Test compact_context with many messages."""
        from core.context_compactor import ContextCompactor
        
        compactor = ContextCompactor(max_tokens=100)
        
        messages = [
            {"sender": "user", "text": "Very old message from long ago"},
            {"sender": "assistant", "text": "Old response"},
            {"sender": "user", "text": "Message 3"},
            {"sender": "assistant", "text": "Response 3"},
            {"sender": "user", "text": "Message 4"},
            {"sender": "assistant", "text": "Response 4"},
            {"sender": "user", "text": "Message 5"},
            {"sender": "assistant", "text": "Response 5"},
            {"sender": "user", "text": "Recent message"},
            {"sender": "assistant", "text": "Recent response"},
        ]
        
        new_messages, sub_context = compactor.compact_context(messages, preserve_recent=5)
        
        assert len(new_messages) <= len(messages)
        assert sub_context is not None
        # Recent messages should be preserved
        assert len(new_messages) >= 5  # Summary + 5 recent
    
    def test_compact_context_preserves_recent(self):
        """Test that compact_context preserves recent messages."""
        from core.context_compactor import ContextCompactor
        
        compactor = ContextCompactor(max_tokens=100)
        
        messages = [
            {"sender": "user", "text": "Old message 1"},
            {"sender": "assistant", "text": "Old response 1"},
            {"sender": "user", "text": "Recent message"},
            {"sender": "assistant", "text": "Recent response"},
            {"sender": "user", "text": "Most recent"},
        ]
        
        new_messages, sub_context = compactor.compact_context(messages, preserve_recent=3)
        
        # Check recent messages are preserved
        assert any("Most recent" in str(m.get("text", "")) for m in new_messages)
    
    def test_should_compact_true_when_large(self):
        """Test should_compact returns True for large context."""
        from core.context_compactor import ContextCompactor
        
        compactor = ContextCompactor(max_tokens=100, compression_threshold=0.5)
        
        # Create messages that exceed threshold
        messages = [{"sender": "user", "text": "A" * 200} for _ in range(10)]
        
        should_compact = compactor.should_compact(messages)
        assert should_compact is True
    
    def test_should_compact_false_when_small(self):
        """Test should_compact returns False for small context."""
        from core.context_compactor import ContextCompactor
        
        compactor = ContextCompactor(max_tokens=10000)
        
        messages = [{"sender": "user", "text": "Short"}]
        
        should_compact = compactor.should_compact(messages)
        assert should_compact is False
    
    def test_preserve_system_messages(self):
        """Test that system-like messages are handled properly."""
        from core.context_compactor import ContextCompactor
        
        compactor = ContextCompactor(max_tokens=50)
        
        messages = [
            {"sender": "system", "text": "Important system instruction"},
            {"sender": "user", "text": "A" * 1000},
        ]
        
        new_messages, sub_context = compactor.compact_context(messages, preserve_recent=1)
        
        # Should still have the system message or be compacted
        assert len(new_messages) >= 1


class TestTokenEstimation:
    """Test token estimation features."""
    
    def test_count_message_tokens(self):
        """Test estimating tokens for messages."""
        from core.context_compactor import ContextCompactor
        
        compactor = ContextCompactor()
        text = "This is a test message"
        tokens = compactor.estimate_tokens(text)
        
        assert tokens > 0
        assert isinstance(tokens, int)


class TestCompactionStrategies:
    """Test different compaction strategies."""
    
    def test_strategy_summarize_via_compact_context(self):
        """Test summarization via compact_context."""
        from core.context_compactor import ContextCompactor
        
        compactor = ContextCompactor(max_tokens=100)
        
        messages = [
            {"sender": "user", "text": "Question 1"},
            {"sender": "assistant", "text": "Answer 1" * 50},
            {"sender": "user", "text": "Question 2"},
            {"sender": "assistant", "text": "Answer 2" * 50},
        ]
        
        new_messages, sub_context = compactor.compact_context(messages, preserve_recent=2)
        
        # Should have summary + recent messages
        assert len(new_messages) <= len(messages)
        assert sub_context is not None
        assert len(sub_context.summary) > 0
    
    def test_compact_with_few_messages(self):
        """Test compact with too few messages returns unchanged."""
        from core.context_compactor import ContextCompactor
        
        compactor = ContextCompactor()
        
        messages = [
            {"sender": "user", "text": "Only message"},
        ]
        
        new_messages, sub_context = compactor.compact_context(messages, preserve_recent=5)
        
        assert new_messages == messages
        assert sub_context is None


class TestContextAnalyzer:
    """Test ContextAnalyzer class."""
    
    def test_analyze_importance_returns_score(self):
        """Test importance analysis returns valid score."""
        from core.context_compactor import ContextAnalyzer, MessageImportance
        
        message = {"id": 1, "sender": "user", "text": "I decided to use Python"}
        history = [message]
        
        importance = ContextAnalyzer.analyze_importance(message, history)
        
        assert isinstance(importance, MessageImportance)
        assert 0.0 <= importance.importance_score <= 1.0
        assert importance.message_id == 1
    
    def test_analyze_importance_with_code(self):
        """Test importance is higher for code-containing messages."""
        from core.context_compactor import ContextAnalyzer
        
        code_msg = {"id": 1, "sender": "user", "text": "```python\ndef hello():\n    pass\n```"}
        simple_msg = {"id": 2, "sender": "user", "text": "ok thanks"}
        history = [code_msg, simple_msg]
        
        code_importance = ContextAnalyzer.analyze_importance(code_msg, history)
        simple_importance = ContextAnalyzer.analyze_importance(simple_msg, history)
        
        assert code_importance.importance_score > simple_importance.importance_score
    
    def test_analyze_importance_with_keywords(self):
        """Test importance with important keywords."""
        from core.context_compactor import ContextAnalyzer
        
        important_msg = {"id": 1, "sender": "user", "text": "I decided to implement this solution"}
        history = [important_msg]
        
        importance = ContextAnalyzer.analyze_importance(important_msg, history)
        
        assert importance.importance_score > 0
        assert importance.factors["keywords"] > 0
    
    def test_cluster_messages(self):
        """Test message clustering."""
        from core.context_compactor import ContextAnalyzer
        
        messages = [
            {"sender": "user", "text": "Tell me about Python"},
            {"sender": "assistant", "text": "Python is a programming language"},
            {"sender": "user", "text": "What about JavaScript?"},
            {"sender": "assistant", "text": "JavaScript is also a language"},
        ]
        
        clusters = ContextAnalyzer.cluster_messages(messages)
        
        assert isinstance(clusters, list)
        assert len(clusters) > 0
    
    def test_cluster_messages_few_messages(self):
        """Test clustering with few messages."""
        from core.context_compactor import ContextAnalyzer
        
        messages = [
            {"sender": "user", "text": "Hello"},
        ]
        
        clusters = ContextAnalyzer.cluster_messages(messages)
        
        assert len(clusters) == 1
        assert clusters[0] == [0]


class TestSubContext:
    """Test SubContext dataclass."""
    
    def test_sub_context_creation(self):
        """Test creating SubContext."""
        from core.context_compactor import SubContext
        
        sub = SubContext(
            id="sub_1",
            title="Test SubContext",
            summary="Test summary",
            key_points=["point 1", "point 2"],
            original_message_count=10,
            compressed_token_estimate=100,
            created_at="2024-01-01T00:00:00",
            message_range=(0, 9)
        )
        
        assert sub.id == "sub_1"
        assert sub.title == "Test SubContext"
        assert len(sub.key_points) == 2
    
    def test_sub_context_to_dict(self):
        """Test SubContext serialization."""
        from core.context_compactor import SubContext
        
        sub = SubContext(
            id="sub_1",
            title="Test",
            summary="Summary",
            key_points=["point"],
            original_message_count=5,
            compressed_token_estimate=50,
            created_at="2024-01-01T00:00:00",
            message_range=(0, 4)
        )
        
        data = sub.to_dict()
        assert data["id"] == "sub_1"
        assert data["title"] == "Test"


class TestSmartCompaction:
    """Test intelligent compaction features."""
    
    def test_compact_creates_sub_context(self):
        """Test that compaction creates proper sub-context."""
        from core.context_compactor import ContextCompactor
        
        compactor = ContextCompactor()
        
        messages = [
            {"sender": "user", "text": "Question about Python"},
            {"sender": "assistant", "text": "Python is great for this"},
            {"sender": "user", "text": "What about JavaScript?"},
            {"sender": "assistant", "text": "JS is good too"},
            {"sender": "user", "text": "I decided to use Python"},
            {"sender": "assistant", "text": "Good choice"},
        ]
        
        new_messages, sub_context = compactor.compact_context(messages, preserve_recent=2)
        
        assert sub_context is not None
        assert sub_context.summary is not None
        assert len(sub_context.summary) > 0
        assert sub_context.original_message_count == 4  # 6 total - 2 preserved


class TestCompactionEdgeCases:
    """Test edge cases in compaction."""
    
    def test_empty_messages(self):
        """Test compaction with empty messages."""
        from core.context_compactor import ContextCompactor
        
        compactor = ContextCompactor()
        
        messages = []
        new_messages, sub_context = compactor.compact_context(messages)
        
        assert new_messages == []
        assert sub_context is None
    
    def test_single_message(self):
        """Test compaction with single message."""
        from core.context_compactor import ContextCompactor
        
        compactor = ContextCompactor()
        
        messages = [{"sender": "user", "text": "Hello"}]
        new_messages, sub_context = compactor.compact_context(messages)
        
        assert new_messages == messages
        assert sub_context is None
    
    def test_all_system_messages(self):
        """Test compaction with system-like messages."""
        from core.context_compactor import ContextCompactor
        
        compactor = ContextCompactor()
        
        messages = [
            {"sender": "system", "text": "Instruction 1"},
            {"sender": "system", "text": "Instruction 2"},
        ]
        new_messages, sub_context = compactor.compact_context(messages)
        
        # Should not compact very short message list
        assert sub_context is None
    
    def test_very_long_single_message(self):
        """Test compaction with one very long message."""
        from core.context_compactor import ContextCompactor
        
        compactor = ContextCompactor()
        
        messages = [{"sender": "user", "text": "A" * 10000}]
        new_messages, sub_context = compactor.compact_context(messages)
        
        assert sub_context is None  # Too few messages to compact
    
    def test_unicode_handling(self):
        """Test compaction handles unicode properly."""
        from core.context_compactor import ContextCompactor
        
        compactor = ContextCompactor()
        
        messages = [
            {"sender": "user", "text": "Olá! Como está você? 🎉"},
            {"sender": "assistant", "text": "Bem, obrigado! 👍"},
            {"sender": "user", "text": "Recente: café?"},
        ]
        new_messages, sub_context = compactor.compact_context(messages, preserve_recent=1)
        
        # Just verify it doesn't crash with unicode - may or may not compact
        assert isinstance(new_messages, list)
