"""
Unit Tests for Memory Store
===========================
"""

import unittest
import tempfile
import os
import sys

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.memory import MemoryStore


class TestMemoryStore(unittest.TestCase):
    """Test cases for MemoryStore."""
    
    def setUp(self):
        """Set up test database."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_memory.db")
        self.memory = MemoryStore(self.db_path)
    
    def tearDown(self):
        """Clean up test database."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_store_memory(self):
        """Test storing a memory."""
        memory_id = self.memory.store(
            content="Test memory content",
            category="test",
            importance="high"
        )
        
        self.assertIsInstance(memory_id, int)
        self.assertGreater(memory_id, 0)
    
    def test_recall_memory(self):
        """Test recalling memories."""
        # Store some memories
        self.memory.store("Python programming is fun", category="programming")
        self.memory.store("JavaScript is also nice", category="programming")
        self.memory.store("Weather is sunny today", category="weather")
        
        # Recall with keyword
        results = self.memory.recall("Python", limit=5)
        
        self.assertIsInstance(results, list)
        self.assertGreater(len(results), 0)
        
        # Check that relevant memory is found
        found_python = any("Python" in r["content"] for r in results)
        self.assertTrue(found_python)
    
    def test_get_stats(self):
        """Test getting memory statistics."""
        # Store memories in different categories
        self.memory.store("Memory 1", category="category_a")
        self.memory.store("Memory 2", category="category_a")
        self.memory.store("Memory 3", category="category_b")
        
        stats = self.memory.get_stats()
        
        self.assertIn("total", stats)
        self.assertIn("categories", stats)
        self.assertEqual(stats["total"], 3)
        self.assertEqual(stats["categories"]["category_a"], 2)
        self.assertEqual(stats["categories"]["category_b"], 1)
    
    def test_get_all_memories(self):
        """Test getting all memories with pagination."""
        # Store multiple memories
        for i in range(10):
            self.memory.store(f"Memory {i}", category="test")
        
        # Get first 5
        memories = self.memory.get_all_memories(limit=5, offset=0)
        self.assertEqual(len(memories), 5)
        
        # Get next 5
        memories = self.memory.get_all_memories(limit=5, offset=5)
        self.assertEqual(len(memories), 5)
    
    def test_delete_memory(self):
        """Test deleting a memory."""
        # Store and delete
        memory_id = self.memory.store("To be deleted", category="test")
        
        # Verify it exists
        memories = self.memory.get_all_memories(limit=100)
        self.assertEqual(len(memories), 1)
        
        # Delete
        deleted = self.memory.delete_memory(memory_id)
        self.assertTrue(deleted)
        
        # Verify it's gone
        memories = self.memory.get_all_memories(limit=100)
        self.assertEqual(len(memories), 0)
        
        # Delete non-existent
        deleted = self.memory.delete_memory(99999)
        self.assertFalse(deleted)


if __name__ == "__main__":
    unittest.main()
