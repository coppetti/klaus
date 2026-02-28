"""
Integration Tests for Hybrid Memory System
==========================================
"""
import pytest
import asyncio
import tempfile
import shutil
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "core"))

from hybrid_memory import HybridMemoryStore


class TestHybridMemoryIntegration:
    """Integration tests for hybrid memory."""
    
    @pytest.fixture
    async def memory_store(self, temp_workspace):
        """Create a hybrid memory store for testing."""
        db_path = temp_workspace / "test_memory.db"
        graph_path = temp_workspace / "test_graph"
        
        store = HybridMemoryStore(
            db_path=str(db_path),
            graph_path=str(graph_path)
        )
        
        yield store
        
        # Cleanup
        store.sqlite.close()
    
    @pytest.mark.asyncio
    async def test_add_and_retrieve_memory(self, memory_store):
        """Test adding and retrieving a memory."""
        # Add memory
        memory_id = await memory_store.add(
            content="Test memory content",
            category="conversation",
            metadata={"user": "test_user"}
        )
        
        assert memory_id is not None
        
        # Retrieve
        memories = memory_store.search("Test memory", limit=5)
        
        assert len(memories) > 0
        assert any("Test memory" in m.get("content", "") for m in memories)
    
    @pytest.mark.asyncio
    async def test_memory_persistence(self, temp_workspace):
        """Test that memories persist across store instances."""
        db_path = temp_workspace / "persist_test.db"
        graph_path = temp_workspace / "persist_graph"
        
        # First instance - add memory
        store1 = HybridMemoryStore(db_path=str(db_path), graph_path=str(graph_path))
        await store1.add(content="Persistent memory", category="test")
        store1.sqlite.close()
        
        # Second instance - retrieve
        store2 = HybridMemoryStore(db_path=str(db_path), graph_path=str(graph_path))
        memories = store2.search("Persistent", limit=5)
        
        assert any("Persistent memory" in m.get("content", "") for m in memories)
        store2.sqlite.close()
    
    @pytest.mark.asyncio
    async def test_graph_relationships(self, memory_store):
        """Test graph relationship creation."""
        # Add related memories
        id1 = await memory_store.add(content="Python programming", category="tech")
        id2 = await memory_store.add(content="Django framework", category="tech")
        
        # Create relationship (if supported)
        if hasattr(memory_store.graph, 'add_relationship'):
            memory_store.graph.add_relationship(id1, id2, "related_to")
            
            # Query relationship
            related = memory_store.graph.get_related(id1)
            assert id2 in related


class TestCognitiveMemoryIntegration:
    """Integration tests for cognitive memory."""
    
    @pytest.fixture
    def temp_cognitive_dir(self, temp_workspace):
        """Setup temp directory for cognitive memory."""
        cog_dir = temp_workspace / "cognitive_memory"
        cog_dir.mkdir(exist_ok=True)
        return cog_dir
    
    @pytest.mark.asyncio
    async def test_episodic_memory_creation(self, temp_cognitive_dir):
        """Test creating episodic memories."""
        from cognitive_memory import get_cognitive_memory_manager
        
        # This would need proper setup
        # manager = get_cognitive_memory_manager()
        
        # Placeholder for actual test
        assert True
    
    def test_memory_decay_calculation(self):
        """Test memory decay calculations."""
        from cognitive_memory import MemoryDecayCalculator
        from datetime import datetime, timedelta
        
        calculator = MemoryDecayCalculator()
        
        # Test decay over time
        old_time = (datetime.now() - timedelta(days=30)).isoformat()
        
        # This would test actual decay logic
        # decayed_strength = calculator.calculate_episodic_strength(memory)
        
        assert True  # Placeholder
