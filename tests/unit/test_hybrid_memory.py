"""
Unit Tests for Hybrid Memory Store (v2.1.1 hardening)
======================================================
Tests for SQLite + Kuzu Graph hybrid memory with:
  - Level 1: Rich topic/entity extraction
  - Level 2: Embedding support
  - Level 3: Durable sync queue
"""

import unittest
import tempfile
import os
import sys
import json
import sqlite3

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.hybrid_memory import HybridMemoryStore, MemoryQuery, TOPIC_TAXONOMY


class TestHybridMemoryStore(unittest.TestCase):
    """Core store functionality."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path  = os.path.join(self.temp_dir, "test_hybrid.db")
        self.memory   = HybridMemoryStore(self.db_path)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_initialization(self):
        self.assertIsNotNone(self.memory.sqlite)
        self.assertIsInstance(self.memory.graph_available, bool)

    def test_store_memory(self):
        memory_id = self.memory.store("Test hybrid memory", category="test", importance="medium")
        self.assertIsInstance(memory_id, int)
        self.assertGreater(memory_id, 0)

    def test_recall_quick(self):
        self.memory.store("Python programming guide", category="programming")
        self.memory.store("JavaScript tutorial",      category="programming")
        self.memory.store("Weather forecast",         category="weather")
        query   = MemoryQuery(query_type="quick", text="Python", limit=5)
        results = self.memory.recall(query)
        self.assertIsInstance(results, list)
        found = any("Python" in str(r.get("content", "")) for r in results)
        self.assertTrue(found)

    def test_get_stats(self):
        self.memory.store("Memory 1", category="cat_a")
        self.memory.store("Memory 2", category="cat_b")
        stats = self.memory.get_stats()
        self.assertIn("sqlite",          stats)
        self.assertIn("graph",           stats)
        self.assertIn("graph_available", stats)
        self.assertIn("sync_queue_size", stats)
        self.assertEqual(stats["sqlite"]["total"], 2)

    def test_api_compatibility(self):
        query   = MemoryQuery(query_type="quick", text="test", limit=5)
        results = self.memory.recall(query)
        self.assertIsInstance(results, list)

    def test_memory_query_creation(self):
        query = MemoryQuery(query_type="context", text="test query", limit=10, context_depth=3)
        self.assertEqual(query.query_type,    "context")
        self.assertEqual(query.limit,         10)
        self.assertEqual(query.context_depth, 3)


class TestDurableSyncQueue(unittest.TestCase):
    """Level 3 — durable SQLite sync queue."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path  = os.path.join(self.temp_dir, "test_sync.db")
        self.memory   = HybridMemoryStore(self.db_path)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_sync_queue_table_exists(self):
        """sync_queue table must be created on init."""
        conn = sqlite3.connect(self.db_path)
        tables = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()]
        conn.close()
        self.assertIn("sync_queue", tables)

    def test_store_enqueues_when_graph_available(self):
        """Storing a memory should add a row to sync_queue if graph is up."""
        if not self.memory.graph_available:
            self.skipTest("Kuzu not available")
        self.memory.store("Architecture decision: using FastAPI", category="arch")
        conn    = sqlite3.connect(self.db_path)
        count   = conn.execute("SELECT COUNT(*) FROM sync_queue").fetchone()[0]
        conn.close()
        self.assertGreaterEqual(count, 1)

    def test_enqueue_and_mark_synced(self):
        """Enqueue then mark synced — verify flag flips."""
        self.memory._enqueue(99, {"id": 99, "content": "test", "category": "x",
                                   "importance": "medium", "metadata": {},
                                   "created_at": "2026-01-01T00:00:00"})
        conn = sqlite3.connect(self.db_path)
        row  = conn.execute(
            "SELECT id, synced FROM sync_queue WHERE memory_id = 99"
        ).fetchone()
        conn.close()

        self.assertIsNotNone(row)
        queue_id, synced = row
        self.assertEqual(synced, 0)

        self.memory._mark_synced(queue_id)
        conn   = sqlite3.connect(self.db_path)
        synced = conn.execute(
            "SELECT synced FROM sync_queue WHERE id = ?", (queue_id,)
        ).fetchone()[0]
        conn.close()
        self.assertEqual(synced, 1)

    def test_stats_includes_sync_queue_size(self):
        stats = self.memory.get_stats()
        self.assertIn("sync_queue_size", stats)
        self.assertIsInstance(stats["sync_queue_size"], int)


class TestTopicExtraction(unittest.TestCase):
    """Level 1 — rich topic extraction."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.memory   = HybridMemoryStore(os.path.join(self.temp_dir, "t.db"))

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_detects_docker(self):
        topics = self.memory._extract_topics("vamos usar docker-compose para o deploy")
        self.assertIn("Docker Compose", topics)

    def test_detects_portuguese_synonym(self):
        topics = self.memory._extract_topics("temos um bug no banco de dados")
        self.assertIn("Bug",      topics)
        self.assertIn("Database", topics)

    def test_detects_camelcase_token(self):
        topics = self.memory._extract_topics("HybridMemory e IDEConnector estão funcionando")
        # CamelCase tokens should appear in the result
        topic_names = " ".join(topics)
        self.assertTrue("HybridMemory" in topic_names or "Klaus" in topic_names)

    def test_detects_llm(self):
        topics = self.memory._extract_topics("precisamos usar um LLM para este caso de uso")
        self.assertIn("LLM", topics)

    def test_detects_Klaus_project_terms(self):
        topics = self.memory._extract_topics("o setup_wizard gerou o init.yaml corretamente")
        self.assertIn("Klaus", topics)
        self.assertIn("Setup", topics)

    def test_topic_limit(self):
        # Even a very rich text shouldn't return more than 3 to prevent graph noise
        rich = ("docker python api llm kimi telegram setup security testing "
                "release architecture database observability performance")
        topics = self.memory._extract_topics(rich)
        self.assertLessEqual(len(topics), 3)


class TestEntityExtraction(unittest.TestCase):
    """Level 1 — entity extraction (tech, class, file, env)."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.memory   = HybridMemoryStore(os.path.join(self.temp_dir, "e.db"))

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_detects_known_tech(self):
        entities = self.memory._extract_entities("we use FastAPI and PostgreSQL")
        names    = [e["name"] for e in entities]
        self.assertIn("FastAPI",    names)
        self.assertIn("PostgreSQL", names)

    def test_detects_file_path(self):
        entities = self.memory._extract_entities("see core/hybrid_memory.py for the implementation")
        names    = [e["name"] for e in entities]
        self.assertTrue(any("hybrid_memory.py" in n for n in names))

    def test_detects_env_variable(self):
        entities = self.memory._extract_entities("set KIMI_API_KEY in your .env file")
        names    = [e["name"] for e in entities]
        self.assertIn("KIMI_API_KEY", names)

    def test_entity_limit(self):
        # Even a very rich text shouldn't return more than 3 to prevent graph noise
        rich     = "FastAPI Django Flask PostgreSQL MongoDB Redis Elasticsearch FastAPI2 Something"
        entities = self.memory._extract_entities(rich)
        self.assertLessEqual(len(entities), 3)


class TestMemoryQuery(unittest.TestCase):
    """MemoryQuery dataclass defaults."""

    def test_default_values(self):
        q = MemoryQuery(query_type="quick", text="test")
        self.assertEqual(q.limit,         5)
        self.assertEqual(q.context_depth, 2)

    def test_custom_values(self):
        q = MemoryQuery(query_type="semantic", text="x", limit=20, context_depth=5)
        self.assertEqual(q.limit,         20)
        self.assertEqual(q.context_depth, 5)


if __name__ == "__main__":
    unittest.main()
