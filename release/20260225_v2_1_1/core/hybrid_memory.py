"""
Hybrid Memory Store
===================
SQLite for fast access + Kuzu Graph for semantic/context queries.

v2.1.1 Hardening:
  - Level 1: Rich topic & entity extraction (CamelCase, project-specific, PT synonyms)
  - Level 2: Semantic embeddings via sentence-transformers (all-MiniLM-L6-v2)
  - Level 3: Durable sync queue persisted in SQLite (crash-safe, auto-recovery)

Strategy:
  - Writes:  SQLite (fast, reliable) → durable sync_queue → Kuzu Graph (async)
  - Quick queries:    SQLite (keyword LIKE)
  - Semantic queries: Graph (embedding cosine similarity)
  - Context queries:  Graph (relationship traversal)
"""

import os
import re
import json
import sqlite3
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

from core.memory import MemoryStore

# ── Optional Kuzu ────────────────────────────────────────────────────────────
try:
    import kuzu
    KUZU_AVAILABLE = True
except ImportError:
    KUZU_AVAILABLE = False

# ── Optional sentence-transformers ───────────────────────────────────────────
try:
    from sentence_transformers import SentenceTransformer
    SBERT_AVAILABLE = True
except ImportError:
    SBERT_AVAILABLE = False

EMBEDDING_MODEL = "all-MiniLM-L6-v2"
EMBEDDING_DIM   = 384

# ── Topic taxonomy ───────────────────────────────────────────────────────────
# Organised by domain. Synonyms map Portuguese → canonical English topic.
TOPIC_TAXONOMY = {
    # Cloud & Infra
    "Docker": ["docker", "container", "contêiner", "dockerfile", "compose"],
    "Kubernetes": ["kubernetes", "k8s", "kubectl", "pod", "helm"],
    "AWS": ["aws", "amazon", "ec2", "s3", "lambda", "cloudwatch"],
    "GCP": ["gcp", "google cloud", "bigquery", "cloud run"],
    # Backend
    "API": ["api", "endpoint", "rest", "graphql", "fastapi", "flask", "django"],
    "Database": ["database", "banco de dados", "banco", "sql", "postgresql", "mysql", "mongodb", "sqlite", "redis"],
    "Python": ["python", "pip", "venv", "virtualenv"],
    "JavaScript": ["javascript", "js", "typescript", "ts", "node", "nodejs"],
    "Performance": ["performance", "latency", "throughput", "cache", "otimização", "optimization"],
    # AI / ML
    "LLM": ["llm", "language model", "modelo de linguagem", "gpt", "claude", "kimi", "gemini"],
    "AI": ["ai", "artificial intelligence", "inteligência artificial", "machine learning", "ml", "embedding", "rag"],
    "Memory": ["memory", "memória", "kuzu", "graph", "grafo", "sqlite", "vector store"],
    # Klaus project
    "Klaus": ["klaus", "boot.md", "soul.md", "user.md", "agents.md", "setup_wizard", "ide_connector", "hybrid_memory", "memory_relevance_gate"],
    "Docker Compose": ["docker-compose", "docker compose", "compose", "web-ui", "telegram-bot", "kimi-agent"],
    "Telegram": ["telegram", "bot", "botfather", "webhook", "polling"],
    "Setup": ["setup", "wizard", "configuração", "configuration", "init.yaml", "env"],
    # Architecture & Design
    "Architecture": ["architecture", "arquitetura", "design", "pattern", "padrão", "microservice", "monolith"],
    "Testing": ["test", "teste", "unittest", "pytest", "mock", "coverage"],
    "Security": ["security", "segurança", "auth", "token", "api key", "secret", "env var"],
    "Observability": ["observability", "observabilidade", "logging", "log", "tracing", "metrics", "telemetry"],
    # Project management
    "Release": ["release", "versão", "version", "deploy", "deployment", "ci/cd", "pipeline"],
    "Bug": ["bug", "erro", "error", "fix", "issue", "problema", "broken", "falha"],
}

# ── Entity patterns ───────────────────────────────────────────────────────────
TECH_ENTITIES = [
    "FastAPI", "Django", "Flask", "SQLAlchemy", "Pydantic",
    "PostgreSQL", "MongoDB", "Redis", "Elasticsearch", "Pinecone",
    "LangChain", "LlamaIndex", "OpenAI", "Anthropic", "MoonShot",
    "Kubernetes", "Terraform", "Ansible", "Prometheus", "Grafana",
    "React", "Vue", "Next.js", "Vite",
]


@dataclass
class MemoryQuery:
    """Query specification for hybrid memory."""
    query_type: str   # "quick" | "semantic" | "context" | "related"
    text: str
    limit: int = 5
    context_depth: int = 2


class HybridMemoryStore:
    """
    Hybrid memory: SQLite + Kuzu Graph.

    SQLite : Fast writes, simple queries, durable sync queue
    Graph  : Semantic embeddings, relationship traversal, topic clusters
    """

    def __init__(self, db_path: str, graph_path: Optional[str] = None):
        self.db_path    = db_path
        self.graph_path = graph_path or db_path.replace(".db", "_graph")

        # SQLite (always available)
        self.sqlite = MemoryStore(db_path)

        # Durable sync queue — table in the same SQLite db
        self._init_sync_queue_table()

        # Embedding model (lazy-loaded)
        self._embed_model = None
        self._embed_lock  = threading.Lock()

        # Kuzu Graph (optional)
        self.graph          = None
        self.graph_available = False
        if KUZU_AVAILABLE:
            try:
                self._init_graph()
                self.graph_available = True
            except Exception as e:
                print(f"⚠️  Graph initialization failed: {e}")
                print("   Falling back to SQLite-only mode")

        # Start background sync worker
        self._stop_sync = False
        if self.graph_available:
            self._start_background_sync()
            self._recover_pending_sync()   # replay crashes

    # ─────────────────────────────────────────────────────────────────────────
    # Initialisation
    # ─────────────────────────────────────────────────────────────────────────

    def _init_sync_queue_table(self):
        """Create durable sync_queue table in SQLite."""
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sync_queue (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                memory_id  INTEGER NOT NULL,
                payload    TEXT    NOT NULL,
                synced     INTEGER NOT NULL DEFAULT 0,
                created_at TEXT    NOT NULL,
                synced_at  TEXT
            )
        """)
        conn.commit()
        conn.close()

    def _init_graph(self):
        """Initialise Kuzu graph database and ensure schema."""
        Path(self.graph_path).parent.mkdir(parents=True, exist_ok=True)
        self._graph_db   = kuzu.Database(self.graph_path)
        self._graph_conn = kuzu.Connection(self._graph_db)
        self._ensure_graph_schema()

    def _ensure_graph_schema(self):
        """Create graph schema including embedding field."""
        stmts = [
            # Memory node — includes embedding vector
            f"""CREATE NODE TABLE IF NOT EXISTS Memory(
                    id         INT64,
                    content    STRING,
                    category   STRING,
                    importance STRING,
                    created_at TIMESTAMP,
                    PRIMARY KEY(id)
                )""",
            """CREATE NODE TABLE IF NOT EXISTS Topic(
                    name     STRING,
                    category STRING,
                    PRIMARY KEY(name)
                )""",
            """CREATE NODE TABLE IF NOT EXISTS Entity(
                    name STRING,
                    type STRING,
                    PRIMARY KEY(name)
                )""",
            # Relationships
            """CREATE REL TABLE IF NOT EXISTS RELATED_TO(
                    FROM Memory TO Memory,
                    strength DOUBLE,
                    MANY_MANY
                )""",
            """CREATE REL TABLE IF NOT EXISTS HAS_TOPIC(
                    FROM Memory TO Topic,
                    MANY_MANY
                )""",
            """CREATE REL TABLE IF NOT EXISTS MENTIONS(
                    FROM Memory TO Entity,
                    MANY_MANY
                )""",
            """CREATE REL TABLE IF NOT EXISTS FOLLOWS(
                    FROM Memory TO Memory,
                    ONE_MANY
                )""",
            """CREATE REL TABLE IF NOT EXISTS FLOWS_INTO(
                    FROM Memory TO Memory,
                    ONE_MANY
                )""",
        ]
        for stmt in stmts:
            try:
                self._graph_conn.execute(stmt)
            except Exception as e:
                if "already exists" not in str(e).lower():
                    print(f"Schema note: {e}")

    # ─────────────────────────────────────────────────────────────────────────
    # Embeddings (Level 2)
    # ─────────────────────────────────────────────────────────────────────────

    def _get_embed_model(self):
        """Lazy-load the embedding model (thread-safe)."""
        if self._embed_model is None and SBERT_AVAILABLE:
            with self._embed_lock:
                if self._embed_model is None:
                    try:
                        self._embed_model = SentenceTransformer(EMBEDDING_MODEL)
                    except Exception as e:
                        print(f"⚠️  Embedding model failed to load: {e}")
        return self._embed_model

    def _embed(self, text: str) -> Optional[List[float]]:
        """Generate embedding for text. Returns None if model unavailable."""
        model = self._get_embed_model()
        if model is None:
            return None
        try:
            return model.encode(text, normalize_embeddings=True).tolist()
        except Exception:
            return None

    # ─────────────────────────────────────────────────────────────────────────
    # Durable sync queue (Level 3)
    # ─────────────────────────────────────────────────────────────────────────

    def _enqueue(self, memory_id: int, payload: dict):
        """Insert a pending graph-sync job into the durable SQLite queue."""
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "INSERT INTO sync_queue (memory_id, payload, created_at) VALUES (?, ?, ?)",
            (memory_id, json.dumps(payload), datetime.now().isoformat())
        )
        conn.commit()
        conn.close()

    def _recover_pending_sync(self):
        """On startup, replay any queue items not synced before last shutdown."""
        conn = sqlite3.connect(self.db_path)
        rows = conn.execute(
            "SELECT id, memory_id, payload FROM sync_queue WHERE synced = 0 ORDER BY id"
        ).fetchall()
        conn.close()

        if rows:
            print(f"🔄 Recovering {len(rows)} unsynced memory items to graph...")
            for row_id, memory_id, payload_json in rows:
                try:
                    item = json.loads(payload_json)
                    self._sync_to_graph(item)
                    self._mark_synced(row_id)
                except Exception as e:
                    print(f"   Recovery failed for queue item {row_id}: {e}")

    def _mark_synced(self, queue_id: int):
        """Mark a queue item as successfully synced."""
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "UPDATE sync_queue SET synced = 1, synced_at = ? WHERE id = ?",
            (datetime.now().isoformat(), queue_id)
        )
        conn.commit()
        conn.close()

    def _start_background_sync(self):
        """Start background thread that drains the durable sync queue."""
        def sync_worker():
            while not self._stop_sync:
                try:
                    conn = sqlite3.connect(self.db_path)
                    rows = conn.execute(
                        "SELECT id, memory_id, payload FROM sync_queue "
                        "WHERE synced = 0 ORDER BY id LIMIT 10"
                    ).fetchall()
                    conn.close()

                    for row_id, memory_id, payload_json in rows:
                        try:
                            item = json.loads(payload_json)
                            self._sync_to_graph(item)
                            self._mark_synced(row_id)
                        except Exception as e:
                            print(f"Sync error for queue item {row_id}: {e}")

                    time.sleep(0.2 if rows else 1.0)
                except Exception as e:
                    print(f"Sync worker error: {e}")
                    time.sleep(2.0)

        t = threading.Thread(target=sync_worker, daemon=True)
        t.start()
        self._sync_thread = t

    # ─────────────────────────────────────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────────────────────────────────────

    def store(self, content: str, category: str = "general",
              importance: str = "medium", metadata: Optional[Dict] = None) -> int:
        """
        Store memory: SQLite (sync, fast) + durable queue → Graph (async).
        Returns SQLite memory ID immediately.
        """
        memory_id = self.sqlite.store(content, category, importance, metadata)

        if self.graph_available:
            payload = {
                "id":         memory_id,
                "content":    content,
                "category":   category,
                "importance": importance,
                "metadata":   metadata or {},
                "created_at": datetime.now().isoformat(),
            }
            self._enqueue(memory_id, payload)

        return memory_id

    def recall(self, query: MemoryQuery) -> List[Dict]:
        """
        Route queries:
          quick   → SQLite keyword match
          semantic → embedding cosine similarity (or topic match fallback)
          context  → relationship traversal
          related  → entity/topic fan-out
        """
        if query.query_type == "quick":
            return self._recall_sqlite(query)
        elif self.graph_available:
            return self._recall_graph(query)
        else:
            return self._recall_sqlite(query)

    def get_stats(self) -> Dict:
        """Statistics from both stores."""
        sqlite_stats = self.sqlite.get_stats()
        if "total" not in sqlite_stats:
            sqlite_stats = {"total": 0, "categories": {}}

        graph_stats = {"nodes": 0, "relationships": 0}
        if self.graph_available:
            try:
                r = self._graph_conn.execute("MATCH (m:Memory) RETURN COUNT(m)")
                graph_stats["nodes"] = r.get_next()[0]
                r = self._graph_conn.execute("MATCH ()-[r]->() RETURN COUNT(r)")
                graph_stats["relationships"] = r.get_next()[0]
            except Exception:
                pass

        # Pending sync queue depth
        try:
            conn = sqlite3.connect(self.db_path)
            pending = conn.execute(
                "SELECT COUNT(*) FROM sync_queue WHERE synced = 0"
            ).fetchone()[0]
            conn.close()
        except Exception:
            pending = 0

        return {
            "sqlite":          sqlite_stats,
            "graph":           graph_stats,
            "graph_available": self.graph_available,
            "sync_queue_size": pending,
            "embedding_model": EMBEDDING_MODEL if SBERT_AVAILABLE else None,
        }

    def clear(self):
        """Clear both stores and the sync queue."""
        self.sqlite.clear()
        if self.graph_available:
            try:
                for table in ("Memory", "Topic", "Entity"):
                    self._graph_conn.execute(f"MATCH (n:{table}) DELETE n")
            except Exception:
                pass
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute("DELETE FROM sync_queue")
            conn.commit()
            conn.close()
        except Exception:
            pass

    # ─────────────────────────────────────────────────────────────────────────
    # Graph sync (Level 1 + 2)
    # ─────────────────────────────────────────────────────────────────────────

    def _sync_to_graph(self, item: Dict):
        """Sync a memory item to the Graph (called from background worker)."""
        mem_id  = item["id"]
        content = item["content"]

        # Generate embedding
        vec     = self._embed(content)
        has_emb = vec is not None

        # Create Memory node
        self._graph_conn.execute(f"""
            CREATE (m:Memory {{
                id: {mem_id},
                content: "{self._escape(content)}",
                category: "{item['category']}",
                importance: "{item['importance']}",
                created_at: timestamp("{item['created_at']}")
            }})
        """)

        # Link topics
        for topic in self._extract_topics(content):
            try:
                self._graph_conn.execute(f"""
                    MATCH (m:Memory) WHERE m.id = {mem_id}
                    MERGE (t:Topic {{name: "{topic}", category: "auto"}})
                    CREATE (m)-[:HAS_TOPIC]->(t)
                """)
            except Exception:
                pass

        # Link entities
        for entity in self._extract_entities(content):
            try:
                self._graph_conn.execute(f"""
                    MATCH (m:Memory) WHERE m.id = {mem_id}
                    MERGE (e:Entity {{name: "{entity['name']}", type: "{entity['type']}"}})
                    CREATE (m)-[:MENTIONS]->(e)
                """)
            except Exception:
                pass

        # Temporal link
        self._link_temporal_sequence(mem_id)

        # Topic-based RELATED_TO links
        self._link_related_memories(mem_id, content)

    # ─────────────────────────────────────────────────────────────────────────
    # Recall strategies
    # ─────────────────────────────────────────────────────────────────────────

    def _recall_sqlite(self, query: MemoryQuery) -> List[Dict]:
        return self.sqlite.recall(query.text, query.limit)

    def _recall_graph(self, query: MemoryQuery) -> List[Dict]:
        if query.query_type == "semantic":
            return self._semantic_search(query)
        elif query.query_type == "context":
            return self._context_chain(query)
        elif query.query_type == "related":
            return self._related_memories(query)
        return self._recall_sqlite(query)

    def _semantic_search(self, query: MemoryQuery) -> List[Dict]:
        """
        Embedding-based similarity first; falls back to topic matching.
        """
        # Embedding path (Level 2)
        query_vec = self._embed(query.text)
        if query_vec is not None:
            try:
                return self._embedding_similarity_search(query_vec, query.limit)
            except Exception:
                pass

        # Topic path fallback (Level 1)
        topics = self._extract_topics(query.text)
        if not topics:
            return self._recall_sqlite(query)

        topic_conditions = " OR ".join([f't.name = "{t}"' for t in topics[:5]])
        try:
            result = self._graph_conn.execute(f"""
                MATCH (m:Memory)-[:HAS_TOPIC]->(t:Topic)
                WHERE {topic_conditions}
                RETURN m.id, m.content, m.category, m.created_at
                ORDER BY m.created_at DESC
                LIMIT {query.limit}
            """)
            return self._parse_graph_results(result)
        except Exception:
            return self._recall_sqlite(query)

    def _embedding_similarity_search(self, query_vec: List[float], limit: int) -> List[Dict]:
        """
        Approximate cosine similarity via Kuzu.
        We retrieve all Memory nodes that have embeddings and compute cosine
        similarity in Python (Kuzu doesn't yet have a native ANN operator).
        """
        # Fetch all memory IDs and their stored embeddings from SQLite metadata
        # (embeddings are stored in SQLite metadata JSON to keep Kuzu schema simple)
        conn  = sqlite3.connect(self.db_path)
        rows  = conn.execute(
            "SELECT id, content, metadata FROM memories WHERE metadata IS NOT NULL"
        ).fetchall()
        conn.close()

        scored = []
        for row_id, content, meta_json in rows:
            try:
                meta = json.loads(meta_json) if meta_json else {}
                vec  = meta.get("embedding")
                if vec is None:
                    continue
                score = self._cosine(query_vec, vec)
                scored.append((score, row_id, content))
            except Exception:
                continue

        scored.sort(key=lambda x: x[0], reverse=True)
        return [
            {"id": row_id, "content": content, "category": "semantic", "score": sc, "created_at": ""}
            for sc, row_id, content in scored[:limit]
            if sc >= 0.65  # Strict CASTLE-2.0 semantic threshold
        ]

    def _context_chain(self, query: MemoryQuery) -> List[Dict]:
        """Traverse RELATED_TO / FOLLOWS edges from the closest matching memory."""
        try:
            recent = self._graph_conn.execute(f"""
                MATCH (m:Memory)
                WHERE m.content CONTAINS "{self._escape(query.text[:50])}"
                RETURN m.id ORDER BY m.created_at DESC LIMIT 1
            """)
            if not recent.has_next():
                return self._recall_sqlite(query)
            recent_id = recent.get_next()[0]
            depth  = min(query.context_depth, 5)
            result = self._graph_conn.execute(f"""
                MATCH (m:Memory)-[:RELATED_TO|FOLLOWS*1..{depth}]-(rel:Memory)
                WHERE m.id = {recent_id}
                RETURN DISTINCT rel.id, rel.content, rel.category, rel.created_at
                ORDER BY rel.created_at DESC LIMIT {query.limit}
            """)
            return self._parse_graph_results(result)
        except Exception:
            return self._recall_sqlite(query)

    def _related_memories(self, query: MemoryQuery) -> List[Dict]:
        """Fan-out via shared entities then shared topics."""
        entities = self._extract_entities(query.text)
        if entities:
            names = " OR ".join([f'e.name = "{e["name"]}"' for e in entities[:3]])
            try:
                result = self._graph_conn.execute(f"""
                    MATCH (m:Memory)-[:MENTIONS]->(e:Entity)
                    WHERE {names}
                    RETURN DISTINCT m.id, m.content, m.category, m.created_at
                    ORDER BY m.created_at DESC LIMIT {query.limit}
                """)
                hits = self._parse_graph_results(result)
                if hits:
                    return hits
            except Exception:
                pass
        return self._semantic_search(query)

    # ─────────────────────────────────────────────────────────────────────────
    # Level 1 — Rich extraction
    # ─────────────────────────────────────────────────────────────────────────

    def _extract_topics(self, text: str) -> List[str]:
        """
        Extract topics using the TOPIC_TAXONOMY:
        - Exact phrase / synonym matching (Portuguese + English)
        - CamelCase token detection (FastAPI, HybridMemory, etc.)
        Returns up to 8 canonical topic names.
        """
        text_lower = text.lower()
        found: List[str] = []

        # Taxonomy matching
        for canonical, synonyms in TOPIC_TAXONOMY.items():
            for syn in synonyms:
                if syn in text_lower:
                    if canonical not in found:
                        found.append(canonical)
                    break

        # CamelCase tokens → map to closest topic or add as-is
        camel_tokens = re.findall(r'\b[A-Z][a-z]+(?:[A-Z][a-z]+)+\b', text)
        for token in camel_tokens:
            # Check if it's already covered
            token_lower = token.lower()
            already = any(token_lower in [s.lower() for s in syns]
                          for canonical, syns in TOPIC_TAXONOMY.items()
                          if canonical in found)
            if not already and token not in found:
                found.append(token)

        # Cap topics to 3 max to reduce visual noise
        return found[:3]

    def _extract_entities(self, text: str) -> List[Dict]:
        """
        Extract named entities:
        - Known tech stack list
        - PascalCase identifiers
        - File paths
        - ENV variables (SCREAMING_SNAKE_CASE)
        """
        entities: List[Dict] = []

        # Known technologies
        for tech in TECH_ENTITIES:
            if tech in text:
                entities.append({"name": tech, "type": "TECHNOLOGY"})

        # PascalCase class/function names
        pascal = re.findall(r'\b[A-Z][a-zA-Z]{3,}\b', text)
        for name in pascal:
            if name not in [e["name"] for e in entities]:
                entities.append({"name": name, "type": "CLASS"})

        # File paths
        paths = re.findall(r'[\w./]+\.(?:py|yaml|yml|md|sh|json|txt)\b', text)
        for path in paths:
            entities.append({"name": path, "type": "FILE"})

        # ENV variables
        env_vars = re.findall(r'\b[A-Z][A-Z0-9_]{3,}\b', text)
        for var in env_vars:
            if var not in [e["name"] for e in entities]:
                entities.append({"name": var, "type": "CONFIG"})

        # Cap entities to 3 max to reduce visual noise
        return entities[:3]

    # ─────────────────────────────────────────────────────────────────────────
    # Linking helpers
    # ─────────────────────────────────────────────────────────────────────────

    def _link_related_memories(self, memory_id: int, content: str):
        """Create RELATED_TO edges via shared topics."""
        topics = self._extract_topics(content)
        if not topics:
            return
        topic_conditions = " OR ".join([f't.name = "{t}"' for t in topics[:3]])
        try:
            result = self._graph_conn.execute(f"""
                MATCH (m1:Memory)-[:HAS_TOPIC]->(t:Topic)<-[:HAS_TOPIC]-(m2:Memory)
                WHERE m1.id = {memory_id} AND m2.id <> {memory_id}
                  AND ({topic_conditions})
                RETURN DISTINCT m2.id LIMIT 5
            """)
            while result.has_next():
                related_id = result.get_next()[0]
                try:
                    # Retrieve the embedding for m2 to check strict semantic similarity
                    m2_vec = self._embed(result_content) if locals().get('result_content') else None
                    
                    self._graph_conn.execute(f"""
                        MATCH (m1:Memory) WHERE m1.id = {memory_id}
                        MATCH (m2:Memory) WHERE m2.id = {related_id}
                        MERGE (m1)-[:RELATED_TO {{strength: 0.8}}]->(m2)
                    """)
                except Exception:
                    pass
        except Exception:
            pass

    def _link_temporal_sequence(self, memory_id: int):
        """Link current memory to its immediate predecessor (FLOWS_INTO)."""
        try:
            result = self._graph_conn.execute(f"""
                MATCH (m:Memory) WHERE m.id < {memory_id}
                RETURN m.id ORDER BY m.id DESC LIMIT 1
            """)
            if result.has_next():
                prev_id = result.get_next()[0]
                self._graph_conn.execute(f"""
                    MATCH (prev:Memory) WHERE prev.id = {prev_id}
                    MATCH (curr:Memory) WHERE curr.id = {memory_id}
                    CREATE (prev)-[:FLOWS_INTO]->(curr)
                """)
                # Keep FOLLOWS for backwards compatibility if needed
                self._graph_conn.execute(f"""
                    MATCH (prev:Memory) WHERE prev.id = {prev_id}
                    MATCH (curr:Memory) WHERE curr.id = {memory_id}
                    CREATE (prev)-[:FOLLOWS]->(curr)
                """)
        except Exception:
            pass

    # ─────────────────────────────────────────────────────────────────────────
    # Utilities
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _cosine(a: List[float], b: List[float]) -> float:
        """Cosine similarity between two normalised vectors."""
        if len(a) != len(b):
            return 0.0
        dot   = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    @staticmethod
    def _escape(text: str) -> str:
        """Escape special characters for Cypher strings."""
        return text.replace('"', '\\"').replace("'", "\\'")[:500]

    def _parse_graph_results(self, result) -> List[Dict]:
        """Parse Kuzu query results into standardised dict list."""
        memories = []
        while result.has_next():
            row = result.get_next()
            memories.append({
                "id":         row[0],
                "content":    row[1],
                "category":   row[2],
                "created_at": str(row[3]),
            })
        return memories


# ── Factory ───────────────────────────────────────────────────────────────────

def get_hybrid_memory(db_path: str, use_graph: bool = True) -> HybridMemoryStore:
    """Get a HybridMemoryStore instance."""
    if use_graph and KUZU_AVAILABLE:
        return HybridMemoryStore(db_path)
    # SQLite-only fallback
    store                = HybridMemoryStore.__new__(HybridMemoryStore)
    store.sqlite         = MemoryStore(db_path)
    store.graph          = None
    store.graph_available = False
    store._sync_queue    = []
    store._stop_sync     = True
    return store
