"""
Unit Tests for IDE Connector
============================
Tests for IDEConnector and memory integration.
"""

import unittest
import tempfile
import os
import sys
import shutil

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.connectors.ide_connector import IDEConnector
from core.hybrid_memory import HybridMemoryStore


class TestIDEConnector(unittest.TestCase):
    """Test cases for IDEConnector."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        
        # Create workspace structure
        self.workspace_dir = os.path.join(self.temp_dir, "workspace")
        self.memory_dir = os.path.join(self.workspace_dir, "memory")
        os.makedirs(self.memory_dir)
        
        # Create SOUL.md
        with open(os.path.join(self.workspace_dir, "SOUL.md"), "w") as f:
            f.write("# SOUL - Test Agent\n\nTest personality for testing.")
        
        # Create USER.md
        with open(os.path.join(self.workspace_dir, "USER.md"), "w") as f:
            f.write("# USER - Test User\n\nTest user profile.")
        
        # Create init.yaml
        self.config_path = os.path.join(self.temp_dir, "init.yaml")
        with open(self.config_path, "w") as f:
            f.write("""
agent:
  name: "TestAgent"
  template: "test"
user:
  name: "TestUser"
memory:
  enabled: true
  sqlite:
    path: "./memory/test.db"
""")
        
        # Change to temp directory
        self.orig_dir = os.getcwd()
        os.chdir(self.temp_dir)
        
        # Initialize connector
        self.connector = IDEConnector(self.config_path)
    
    def tearDown(self):
        """Clean up."""
        os.chdir(self.orig_dir)
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_initialization(self):
        """Test IDEConnector initialization."""
        self.assertEqual(self.connector.agent_name, "TestAgent")
        self.assertEqual(self.connector.user_name, "TestUser")
        self.assertIsNotNone(self.connector.memory)
    
    def test_get_context(self):
        """Test getting context."""
        context = self.connector.get_context("test message")
        
        # Should contain SOUL content
        self.assertIn("SOUL", context)
        
        # Should contain USER content
        self.assertIn("USER", context)
    
    def test_store_interaction(self):
        """Test storing interaction."""
        # Store an interaction
        self.connector.store_interaction(
            user_msg="Hello",
            assistant_msg="Hi there!",
            category="conversation"
        )
        
        # Should not raise error
        # Memory verification would require checking database
    
    def test_store_fact(self):
        """Test storing fact."""
        self.connector.store_fact(
            fact="Python is a programming language",
            category="knowledge"
        )
        
        # Should not raise error
    
    def test_recall(self):
        """Test recall functionality - THE CRITICAL FIX."""
        # Store some facts first
        self.connector.store_fact("Python programming language", category="tech")
        self.connector.store_fact("JavaScript web development", category="tech")
        
        # Recall - This tests the API compatibility fix
        results = self.connector.recall("Python", limit=5)
        
        # Should not raise TypeError
        self.assertIsInstance(results, list)
    
    def test_recall_with_hybrid_memory(self):
        """Test recall when using HybridMemoryStore."""
        # Verify memory is HybridMemoryStore
        if isinstance(self.connector.memory, HybridMemoryStore):
            # Store and recall
            self.connector.store_fact("Test for hybrid memory", category="test")
            results = self.connector.recall("hybrid", limit=3)
            
            # Should work without TypeError
            self.assertIsInstance(results, list)
    
    def test_get_stats(self):
        """Test getting memory stats."""
        stats = self.connector.get_stats()
        
        self.assertIsInstance(stats, dict)
        # Stats format depends on memory type (HybridMemoryStore has "sqlite" key)
        if "sqlite" in stats:
            self.assertIn("total", stats["sqlite"])
        else:
            self.assertIn("total", stats)


if __name__ == "__main__":
    unittest.main()
