"""
Sanity Tests
============
Quick smoke tests to verify basic functionality.
"""

import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestImports(unittest.TestCase):
    """Test that all modules can be imported."""
    
    def test_core_imports(self):
        """Test core module imports."""
        try:
            from core.memory import MemoryStore
            from core.hybrid_memory import HybridMemoryStore, MemoryQuery
            from core.connectors.ide_connector import IDEConnector
            self.assertTrue(True)
        except ImportError as e:
            self.fail(f"Failed to import core modules: {e}")
    
    def test_tools_imports(self):
        """Test tools module imports."""
        try:
            from core.tools.web_search import WebSearchTool
            self.assertTrue(True)
        except ImportError as e:
            self.fail(f"Failed to import tools: {e}")


class TestBasicFunctionality(unittest.TestCase):
    """Test basic functionality."""
    
    def test_memory_store_creation(self):
        """Test creating a MemoryStore."""
        import tempfile
        from core.memory import MemoryStore
        
        with tempfile.TemporaryDirectory() as tmp:
            db_path = os.path.join(tmp, "test.db")
            memory = MemoryStore(db_path)
            self.assertIsNotNone(memory)
    
    def test_hybrid_memory_creation(self):
        """Test creating a HybridMemoryStore."""
        import tempfile
        from core.hybrid_memory import HybridMemoryStore
        
        with tempfile.TemporaryDirectory() as tmp:
            db_path = os.path.join(tmp, "test.db")
            memory = HybridMemoryStore(db_path)
            self.assertIsNotNone(memory)
            self.assertIsNotNone(memory.sqlite)


if __name__ == "__main__":
    unittest.main()
