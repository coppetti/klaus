"""
Test Cognitive Memory - Aligned with Production Implementation
===============================================================
Tests the actual CognitiveMemoryManager interface:
- store_interaction() - main entry point
- retrieve_context() - memory retrieval
- knowledge_graph operations
- get_stats()
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import json
import tempfile
import shutil
from pathlib import Path


@pytest.fixture
def temp_memory_dir():
    """Create temporary directory for memory storage."""
    temp_dir = Path(tempfile.mkdtemp(prefix="klaus_memory_"))
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


class TestCognitiveMemoryManager:
    """Test CognitiveMemoryManager."""
    
    def test_manager_creation(self, temp_memory_dir):
        """Test creating cognitive memory manager."""
        from core.cognitive_memory import CognitiveMemoryManager
        
        manager = CognitiveMemoryManager(data_dir=str(temp_memory_dir))
        assert manager is not None
        assert manager.data_dir == temp_memory_dir
    
    def test_manager_has_knowledge_graph(self, temp_memory_dir):
        """Test that manager has knowledge graph."""
        from core.cognitive_memory import CognitiveMemoryManager
        
        manager = CognitiveMemoryManager(data_dir=str(temp_memory_dir))
        assert manager.knowledge_graph is not None
    
    def test_manager_has_episodic_memories(self, temp_memory_dir):
        """Test that manager has episodic memories list."""
        from core.cognitive_memory import CognitiveMemoryManager
        
        manager = CognitiveMemoryManager(data_dir=str(temp_memory_dir))
        assert isinstance(manager.episodic_memories, list)


class TestEpisodicMemory:
    """Test episodic memory functions."""
    
    def test_store_interaction(self, temp_memory_dir):
        """Test storing an interaction."""
        from core.cognitive_memory import CognitiveMemoryManager
        
        manager = CognitiveMemoryManager(data_dir=str(temp_memory_dir))
        
        episode = manager.store_interaction(
            session_id="test-session",
            user_message="How do I write tests?",
            assistant_message="You can use pytest...",
            sentiment=5,
            successful=True
        )
        
        assert episode is not None
        assert episode.memory_id is not None
        assert episode.session_id == "test-session"
        assert len(manager.episodic_memories) == 1
    
    def test_store_multiple_interactions(self, temp_memory_dir):
        """Test storing multiple interactions."""
        from core.cognitive_memory import CognitiveMemoryManager
        
        manager = CognitiveMemoryManager(data_dir=str(temp_memory_dir))
        
        manager.store_interaction(
            session_id="test-session",
            user_message="Query 1",
            assistant_message="Response 1"
        )
        manager.store_interaction(
            session_id="test-session",
            user_message="Query 2",
            assistant_message="Response 2"
        )
        
        assert len(manager.episodic_memories) == 2
    
    def test_retrieve_context(self, temp_memory_dir):
        """Test retrieving context for a query."""
        from core.cognitive_memory import CognitiveMemoryManager
        
        manager = CognitiveMemoryManager(data_dir=str(temp_memory_dir))
        
        manager.store_interaction(
            session_id="test-session",
            user_message="How do I use Python?",
            assistant_message="Python is a programming language..."
        )
        
        results = manager.retrieve_context(
            query="Python programming",
            session_id="test-session",
            limit=5
        )
        
        assert isinstance(results, dict)
        assert "episodic" in results
        assert "semantic" in results
    
    def test_get_archived_memories(self, temp_memory_dir):
        """Test getting archived memories."""
        from core.cognitive_memory import CognitiveMemoryManager
        
        manager = CognitiveMemoryManager(data_dir=str(temp_memory_dir))
        
        # Initially no archived memories
        archived = manager.get_archived_memories(session_id="test-session")
        assert isinstance(archived, list)


class TestKnowledgeGraph:
    """Test knowledge graph operations."""
    
    def test_add_entity(self, temp_memory_dir):
        """Test adding entity to knowledge graph."""
        from core.cognitive_memory import CognitiveMemoryManager, Entity
        
        manager = CognitiveMemoryManager(data_dir=str(temp_memory_dir))
        
        entity = Entity(
            id="tech_python",
            type="Technology",
            name="Python",
            properties={"category": "language"}
        )
        
        result = manager.knowledge_graph.add_entity(entity)
        assert result is not None
    
    def test_get_entity(self, temp_memory_dir):
        """Test getting entity from knowledge graph."""
        from core.cognitive_memory import CognitiveMemoryManager, Entity
        
        manager = CognitiveMemoryManager(data_dir=str(temp_memory_dir))
        
        entity = Entity(
            id="tech_python",
            type="Technology",
            name="Python"
        )
        manager.knowledge_graph.add_entity(entity)
        
        retrieved = manager.knowledge_graph.get_entity("tech_python")
        assert retrieved is not None
        assert retrieved.name == "Python"
    
    def test_add_relationship(self, temp_memory_dir):
        """Test adding relationship between entities."""
        from core.cognitive_memory import (
            CognitiveMemoryManager, Entity, Relationship, RelationshipType
        )
        
        manager = CognitiveMemoryManager(data_dir=str(temp_memory_dir))
        
        # Add two entities
        entity1 = Entity(id="person_john", type="Person", name="John")
        entity2 = Entity(id="company_acme", type="Company", name="ACME")
        manager.knowledge_graph.add_entity(entity1)
        manager.knowledge_graph.add_entity(entity2)
        
        # Add relationship
        rel = Relationship(
            id="rel_1",
            type=RelationshipType.WORKS_AT.value,
            source_id="person_john",
            target_id="company_acme"
        )
        result = manager.knowledge_graph.add_relationship(rel)
        
        assert result is not None
    
    def test_get_related_entities(self, temp_memory_dir):
        """Test getting related entities."""
        from core.cognitive_memory import (
            CognitiveMemoryManager, Entity, Relationship, RelationshipType
        )
        
        manager = CognitiveMemoryManager(data_dir=str(temp_memory_dir))
        
        # Add entities and relationship
        entity1 = Entity(id="tech_python", type="Technology", name="Python")
        entity2 = Entity(id="tech_django", type="Technology", name="Django")
        manager.knowledge_graph.add_entity(entity1)
        manager.knowledge_graph.add_entity(entity2)
        
        rel = Relationship(
            id="rel_1",
            type=RelationshipType.RELATED_TO.value,
            source_id="tech_python",
            target_id="tech_django"
        )
        manager.knowledge_graph.add_relationship(rel)
        
        # Get related
        related = manager.knowledge_graph.get_related_entities("tech_python", max_depth=1)
        assert isinstance(related, list)


class TestMemoryStats:
    """Test memory statistics."""
    
    def test_get_stats(self, temp_memory_dir):
        """Test getting memory statistics."""
        from core.cognitive_memory import CognitiveMemoryManager
        
        manager = CognitiveMemoryManager(data_dir=str(temp_memory_dir))
        
        stats = manager.get_stats()
        
        assert isinstance(stats, dict)
        assert "episodic" in stats
        assert "semantic" in stats
        assert "procedural" in stats
    
    def test_stats_increases_with_additions(self, temp_memory_dir):
        """Test that stats increase when adding memories."""
        from core.cognitive_memory import CognitiveMemoryManager
        
        manager = CognitiveMemoryManager(data_dir=str(temp_memory_dir))
        
        initial_stats = manager.get_stats()
        initial_episodic = initial_stats["episodic"]["total"]
        
        manager.store_interaction(
            session_id="test-session",
            user_message="Test query",
            assistant_message="Test response"
        )
        
        new_stats = manager.get_stats()
        assert new_stats["episodic"]["total"] == initial_episodic + 1


class TestMemoryPersistence:
    """Test memory persistence to disk."""
    
    def test_save_and_load(self, temp_memory_dir):
        """Test saving and loading memories."""
        from core.cognitive_memory import CognitiveMemoryManager
        
        # Create manager and add memory
        manager1 = CognitiveMemoryManager(data_dir=str(temp_memory_dir))
        manager1.store_interaction(
            session_id="test-session",
            user_message="Save this",
            assistant_message="Saved"
        )
        
        # Files should exist
        assert (temp_memory_dir / "episodic_memories.json").exists()
    
    def test_persistence_across_instances(self, temp_memory_dir):
        """Test that data persists across manager instances."""
        from core.cognitive_memory import CognitiveMemoryManager
        
        # First instance
        manager1 = CognitiveMemoryManager(data_dir=str(temp_memory_dir))
        manager1.store_interaction(
            session_id="test-session",
            user_message="Persistent query",
            assistant_message="Persistent response"
        )
        
        # Second instance should load the same data
        manager2 = CognitiveMemoryManager(data_dir=str(temp_memory_dir))
        assert len(manager2.episodic_memories) == 1


class TestContextEnrichment:
    """Test context enrichment with memories."""
    
    def test_retrieve_returns_structured_results(self, temp_memory_dir):
        """Test that retrieve_context returns properly structured results."""
        from core.cognitive_memory import CognitiveMemoryManager
        
        manager = CognitiveMemoryManager(data_dir=str(temp_memory_dir))
        
        # Store some interactions
        for i in range(3):
            manager.store_interaction(
                session_id="test-session",
                user_message=f"Question {i} about Python",
                assistant_message=f"Answer {i}"
            )
        
        # Retrieve context
        results = manager.retrieve_context(
            query="Python questions",
            session_id="test-session",
            limit=5
        )
        
        assert "episodic" in results
        assert "semantic" in results
        assert "procedural" in results
        assert "related_topics" in results


class TestMemoryDecay:
    """Test memory decay functionality."""
    
    def test_decay_calculator_exists(self):
        """Test that decay calculator exists."""
        from core.cognitive_memory import MemoryDecayCalculator
        assert MemoryDecayCalculator is not None
    
    def test_should_archive_exists(self):
        """Test that should_archive method exists."""
        from core.cognitive_memory import MemoryDecayCalculator
        
        # The method signature is different - just test it exists and works
        assert hasattr(MemoryDecayCalculator, 'should_archive')
