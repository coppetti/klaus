"""
Integration Tests for Memory Flow
=================================
End-to-end tests for memory storage and retrieval.
"""

import unittest
import tempfile
import os
import sys
import shutil
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.connectors.ide_connector import IDEConnector
from core.hybrid_memory import HybridMemoryStore, MemoryQuery


class TestMemoryFlow(unittest.TestCase):
    """Integration tests for complete memory flow."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.workspace_dir = os.path.join(self.temp_dir, "workspace")
        self.memory_dir = os.path.join(self.workspace_dir, "memory")
        os.makedirs(self.memory_dir)
        
        # Create required files
        with open(os.path.join(self.workspace_dir, "SOUL.md"), "w") as f:
            f.write("# SOUL\n\nTest agent.")
        
        with open(os.path.join(self.workspace_dir, "USER.md"), "w") as f:
            f.write("# USER\n\nTest user.")
        
        self.config_path = os.path.join(self.temp_dir, "init.yaml")
        with open(self.config_path, "w") as f:
            f.write("""
agent:
  name: "IntegrationTestAgent"
user:
  name: "IntegrationTestUser"
memory:
  enabled: true
  sqlite:
    path: "./memory/integration.db"
""")
        
        self.orig_dir = os.getcwd()
        os.chdir(self.temp_dir)
    
    def tearDown(self):
        """Clean up."""
        os.chdir(self.orig_dir)
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_complete_flow(self):
        """Test complete memory flow: store → recall → stats."""
        # Initialize connector
        connector = IDEConnector(self.config_path)
        
        # Store some interactions
        connector.store_interaction(
            user_msg="What is Python?",
            assistant_msg="Python is a programming language.",
            category="conversation"
        )
        
        connector.store_fact(
            fact="User prefers Python over JavaScript",
            category="preference"
        )
        
        # Get context (includes memories)
        context = connector.get_context("Tell me about Python")
        self.assertIn("SOUL", context)
        
        # Recall memories
        results = connector.recall("Python", limit=5)
        self.assertIsInstance(results, list)
        
        # Get stats
        stats = connector.get_stats()
        # Stats format depends on memory type
        if "sqlite" in stats:
            self.assertIn("total", stats["sqlite"])
            self.assertGreaterEqual(stats["sqlite"]["total"], 2)
        else:
            self.assertIn("total", stats)
            self.assertGreaterEqual(stats["total"], 2)


class TestHybridMemoryIntegration(unittest.TestCase):
    """Integration tests for HybridMemoryStore."""
    
    def setUp(self):
        """Set up test database."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "hybrid_integration.db")
        self.memory = HybridMemoryStore(self.db_path)
    
    def tearDown(self):
        """Clean up."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_store_and_recall(self):
        """Test storing and recalling memories."""
        # Store memories
        for i in range(5):
            self.memory.store(
                content=f"Memory about topic {i}",
                category="test"
            )
        
        # Quick recall
        query = MemoryQuery(query_type="quick", text="topic", limit=5)
        results = self.memory.recall(query)
        
        self.assertEqual(len(results), 5)
    
    def test_stats_consistency(self):
        """Test that stats are consistent."""
        # Initial state
        stats1 = self.memory.get_stats()
        initial_total = stats1["sqlite"]["total"]
        
        # Add memories
        for i in range(3):
            self.memory.store(f"Memory {i}", category="consistency_test")
        
        # Check updated stats
        stats2 = self.memory.get_stats()
        new_total = stats2["sqlite"]["total"]
        
        self.assertEqual(new_total, initial_total + 3)


if __name__ == "__main__":
    unittest.main()
