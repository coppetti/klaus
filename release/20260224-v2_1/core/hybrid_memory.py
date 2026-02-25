"""
Hybrid Memory Store
===================
SQLite for fast access + Kuzu Graph for semantic/context queries

Strategy:
- Writes: SQLite (fast, reliable) + async sync to Graph
- Quick queries: SQLite
- Semantic/context queries: Graph
"""

import os
import json
import asyncio
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

from core.memory import MemoryStore

# Optional Kuzu import
try:
    import kuzu
    KUZU_AVAILABLE = True
except ImportError:
    KUZU_AVAILABLE = False


@dataclass
class MemoryQuery:
    """Query specification for hybrid memory."""
    query_type: str  # "quick", "semantic", "context", "related"
    text: str
    limit: int = 5
    context_depth: int = 2


class HybridMemoryStore:
    """
    Hybrid memory: SQLite + Kuzu Graph
    
    SQLite: Fast writes, simple queries, fallback
    Graph: Semantic relationships, context chains, topic clusters
    """
    
    def __init__(self, db_path: str, graph_path: Optional[str] = None):
        self.db_path = db_path
        self.graph_path = graph_path or db_path.replace(".db", "_graph")
        
        # Initialize SQLite (always available)
        self.sqlite = MemoryStore(db_path)
        
        # Initialize Graph (optional)
        self.graph = None
        self.graph_available = False
        if KUZU_AVAILABLE:
            try:
                self._init_graph()
                self.graph_available = True
            except Exception as e:
                print(f"⚠️  Graph initialization failed: {e}")
                print("   Falling back to SQLite-only mode")
        
        # Sync queue for background updates
        self._sync_queue = []
        self._sync_thread = None
        if self.graph_available:
            self._start_background_sync()
    
    def _init_graph(self):
        """Initialize Kuzu graph database."""
        Path(self.graph_path).parent.mkdir(parents=True, exist_ok=True)
        
        self._graph_db = kuzu.Database(self.graph_path)
        self._graph_conn = kuzu.Connection(self._graph_db)
        
        # Create schema if not exists
        self._ensure_graph_schema()
    
    def _ensure_graph_schema(self):
        """Create graph schema."""
        try:
            # Node: Memory
            self._graph_conn.execute("""
                CREATE NODE TABLE IF NOT EXISTS Memory(
                    id INT64,
                    content STRING,
                    category STRING,
                    importance STRING,
                    created_at TIMESTAMP,
                    PRIMARY KEY(id)
                )
            """)
            
            # Node: Topic
            self._graph_conn.execute("""
                CREATE NODE TABLE IF NOT EXISTS Topic(
                    name STRING,
                    category STRING,
                    PRIMARY KEY(name)
                )
            """)
            
            # Node: Entity
            self._graph_conn.execute("""
                CREATE NODE TABLE IF NOT EXISTS Entity(
                    name STRING,
                    type STRING,
                    PRIMARY KEY(name)
                )
            """)
            
            # Relationship: Related memories
            self._graph_conn.execute("""
                CREATE REL TABLE IF NOT EXISTS RELATED_TO(
                    FROM Memory TO Memory,
                    strength DOUBLE,
                    MANY_MANY
                )
            """)
            
            # Relationship: Has topic
            self._graph_conn.execute("""
                CREATE REL TABLE IF NOT EXISTS HAS_TOPIC(
                    FROM Memory TO Topic,
                    MANY_MANY
                )
            """)
            
            # Relationship: Mentions entity
            self._graph_conn.execute("""
                CREATE REL TABLE IF NOT EXISTS MENTIONS(
                    FROM Memory TO Entity,
                    MANY_MANY
                )
            """)
            
            # Relationship: Temporal sequence
            self._graph_conn.execute("""
                CREATE REL TABLE IF NOT EXISTS FOLLOWS(
                    FROM Memory TO Memory,
                    ONE_MANY
                )
            """)
            
        except Exception as e:
            print(f"Schema creation note: {e}")
    
    def _start_background_sync(self):
        """Start background thread for syncing SQLite → Graph."""
        def sync_worker():
            while True:
                try:
                    if self._sync_queue:
                        item = self._sync_queue.pop(0)
                        self._sync_to_graph(item)
                    time.sleep(0.1)
                except Exception as e:
                    print(f"Sync error: {e}")
        
        self._sync_thread = threading.Thread(target=sync_worker, daemon=True)
        self._sync_thread.start()
    
    def store(self, content: str, category: str = "general", 
              importance: str = "medium", metadata: Optional[Dict] = None) -> int:
        """
        Store memory: SQLite (fast, synchronous) + queue for Graph
        
        Returns SQLite ID immediately. Graph update is async.
        """
        # 1. Store in SQLite (fast, reliable)
        memory_id = self.sqlite.store(content, category, importance, metadata)
        
        # 2. Queue for Graph update (async)
        if self.graph_available:
            self._sync_queue.append({
                "id": memory_id,
                "content": content,
                "category": category,
                "importance": importance,
                "metadata": metadata or {},
                "created_at": datetime.now().isoformat()
            })
        
        return memory_id
    
    def _sync_to_graph(self, item: Dict):
        """Sync a memory item to the Graph (called asynchronously)."""
        try:
            # Create Memory node
            self._graph_conn.execute(f"""
                CREATE (m:Memory {{
                    id: {item['id']},
                    content: "{self._escape(item['content'])}",
                    category: "{item['category']}",
                    importance: "{item['importance']}",
                    created_at: timestamp("{item['created_at']}")
                }})
            """)
            
            # Extract and link topics
            topics = self._extract_topics(item['content'])
            for topic in topics:
                self._graph_conn.execute(f"""
                    MATCH (m:Memory) WHERE m.id = {item['id']}
                    MERGE (t:Topic {{name: "{topic}", category: "auto"}})
                    CREATE (m)-[:HAS_TOPIC]->(t)
                """)
            
            # Extract and link entities
            entities = self._extract_entities(item['content'])
            for entity in entities:
                self._graph_conn.execute(f"""
                    MATCH (m:Memory) WHERE m.id = {item['id']}
                    MERGE (e:Entity {{name: "{entity['name']}", type: "{entity['type']}"}})
                    CREATE (m)-[:MENTIONS]->(e)
                """)
            
            # Find and link related memories
            self._link_related_memories(item['id'], item['content'])
            
            # Link temporal sequence (follows previous memory)
            self._link_temporal_sequence(item['id'])
            
        except Exception as e:
            print(f"Graph sync failed for memory {item['id']}: {e}")
    
    def recall(self, query: MemoryQuery) -> List[Dict]:
        """
        Query memory with automatic routing:
        - "quick": SQLite (fast)
        - "semantic", "context", "related": Graph (relationships)
        """
        if query.query_type == "quick":
            return self._recall_sqlite(query)
        elif self.graph_available:
            return self._recall_graph(query)
        else:
            # Fallback to SQLite for all queries if graph unavailable
            return self._recall_sqlite(query)
    
    def _recall_sqlite(self, query: MemoryQuery) -> List[Dict]:
        """Fast recall from SQLite (keyword matching)."""
        return self.sqlite.recall(query.text, query.limit)
    
    def _recall_graph(self, query: MemoryQuery) -> List[Dict]:
        """Semantic recall from Graph (relationships, context)."""
        if query.query_type == "semantic":
            return self._semantic_search(query)
        elif query.query_type == "context":
            return self._context_chain(query)
        elif query.query_type == "related":
            return self._related_memories(query)
        else:
            return self._recall_sqlite(query)
    
    def _semantic_search(self, query: MemoryQuery) -> List[Dict]:
        """Find memories by topics and entities."""
        topics = self._extract_topics(query.text)
        
        if not topics:
            return self._recall_sqlite(query)
        
        # Build topic query
        topic_conditions = " OR ".join([f't.name = "{t}"' for t in topics[:3]])
        
        result = self._graph_conn.execute(f"""
            MATCH (m:Memory)-[:HAS_TOPIC]->(t:Topic)
            WHERE {topic_conditions}
            RETURN m.id, m.content, m.category, m.created_at
            ORDER BY m.created_at DESC
            LIMIT {query.limit}
        """)
        
        return self._parse_graph_results(result)
    
    def _context_chain(self, query: MemoryQuery) -> List[Dict]:
        """Get chain of related memories for context."""
        # Find most recent memory matching query
        recent = self._graph_conn.execute(f"""
            MATCH (m:Memory)
            WHERE m.content CONTAINS "{self._escape(query.text[:50])}"
            RETURN m.id
            ORDER BY m.created_at DESC
            LIMIT 1
        """)
        
        try:
            recent_id = recent.get_next()[0]
        except:
            return self._recall_sqlite(query)
        
        # Traverse relationships
        depth = min(query.context_depth, 5)
        result = self._graph_conn.execute(f"""
            MATCH (m:Memory)-[:RELATED_TO|FOLLOWS*1..{depth}]-(related:Memory)
            WHERE m.id = {recent_id}
            RETURN DISTINCT related.id, related.content, 
                   related.category, related.created_at
            ORDER BY related.created_at DESC
            LIMIT {query.limit}
        """)
        
        return self._parse_graph_results(result)
    
    def _related_memories(self, query: MemoryQuery) -> List[Dict]:
        """Find memories related to query topics/entities."""
        # Get entities from query
        entities = self._extract_entities(query.text)
        
        if not entities:
            return self._semantic_search(query)
        
        # Find memories mentioning same entities
        entity_names = [e['name'] for e in entities[:2]]
        entity_conditions = " OR ".join([f'e.name = "{n}"' for n in entity_names])
        
        result = self._graph_conn.execute(f"""
            MATCH (m:Memory)-[:MENTIONS]->(e:Entity)
            WHERE {entity_conditions}
            RETURN DISTINCT m.id, m.content, m.category, m.created_at
            ORDER BY m.created_at DESC
            LIMIT {query.limit}
        """)
        
        return self._parse_graph_results(result)
    
    def get_stats(self) -> Dict:
        """Get statistics from both stores."""
        sqlite_stats = self.sqlite.get_stats()
        
        # Ensure sqlite_stats has expected structure
        if "total" not in sqlite_stats:
            sqlite_stats = {"total": sqlite_stats.get("total", 0), "categories": sqlite_stats.get("categories", {})}
        
        graph_stats = {"nodes": 0, "relationships": 0}
        if self.graph_available:
            try:
                # Count memory nodes
                result = self._graph_conn.execute("MATCH (m:Memory) RETURN COUNT(m)")
                graph_stats["nodes"] = result.get_next()[0]
                
                # Count relationships
                result = self._graph_conn.execute(
                    "MATCH ()-[r]->() RETURN COUNT(r)"
                )
                graph_stats["relationships"] = result.get_next()[0]
            except:
                pass
        
        return {
            "sqlite": sqlite_stats,
            "graph": graph_stats,
            "graph_available": self.graph_available,
            "sync_queue_size": len(self._sync_queue)
        }
    
    def clear(self):
        """Clear both stores."""
        self.sqlite.clear()
        
        if self.graph_available:
            try:
                # Clear graph (drop and recreate tables)
                self._graph_conn.execute("MATCH (m:Memory) DELETE m")
                self._graph_conn.execute("MATCH (t:Topic) DELETE t")
                self._graph_conn.execute("MATCH (e:Entity) DELETE e")
            except:
                pass
    
    # ============ Helper Methods ============
    
    def _escape(self, text: str) -> str:
        """Escape special characters for Cypher."""
        return text.replace('"', '\\"').replace("'", "\\'")[:500]
    
    def _extract_topics(self, text: str) -> List[str]:
        """Extract topics from text (simplified)."""
        # In production, use NLP (spaCy, etc.)
        keywords = [
            "Docker", "Python", "JavaScript", "React", "API", "Database",
            "Architecture", "Testing", "Deploy", "Security", "Performance",
            "Kimi", "Claude", "OpenAI", "LLM", "AI", "Machine Learning"
        ]
        found = []
        text_lower = text.lower()
        for kw in keywords:
            if kw.lower() in text_lower:
                found.append(kw)
        return found[:5]
    
    def _extract_entities(self, text: str) -> List[Dict]:
        """Extract named entities (simplified)."""
        entities = []
        
        # Pattern: project names, person names (simplified)
        # In production, use NER model
        import re
        
        # Find potential project names (capitalized words)
        projects = re.findall(r'\b[A-Z][a-zA-Z]+(?:Project|App|System|Tool)\b', text)
        for p in projects:
            entities.append({"name": p, "type": "PROJECT"})
        
        # Find technologies (common patterns)
        tech_patterns = ["FastAPI", "Django", "Flask", "PostgreSQL", "MongoDB", "Redis"]
        for tech in tech_patterns:
            if tech in text:
                entities.append({"name": tech, "type": "TECHNOLOGY"})
        
        return entities[:5]
    
    def _link_related_memories(self, memory_id: int, content: str):
        """Create RELATED_TO links based on content similarity."""
        # Find recent memories with similar topics
        topics = self._extract_topics(content)
        if not topics:
            return
        
        topic_conditions = " OR ".join([f't.name = "{t}"' for t in topics[:2]])
        
        try:
            result = self._graph_conn.execute(f"""
                MATCH (m1:Memory)-[:HAS_TOPIC]->(t:Topic)<-[:HAS_TOPIC]-(m2:Memory)
                WHERE m1.id = {memory_id} AND m2.id <> {memory_id}
                  AND ({topic_conditions})
                RETURN DISTINCT m2.id
                LIMIT 3
            """)
            
            while result.has_next():
                related_id = result.get_next()[0]
                # Create relationship with strength
                self._graph_conn.execute(f"""
                    MATCH (m1:Memory) WHERE m1.id = {memory_id}
                    MATCH (m2:Memory) WHERE m2.id = {related_id}
                    MERGE (m1)-[:RELATED_TO {{strength: 0.8}}]->(m2)
                """)
        except:
            pass
    
    def _link_temporal_sequence(self, memory_id: int):
        """Link to previous memory in time sequence."""
        try:
            # Find most recent memory before this one
            result = self._graph_conn.execute(f"""
                MATCH (m:Memory)
                WHERE m.id < {memory_id}
                RETURN m.id
                ORDER BY m.id DESC
                LIMIT 1
            """)
            
            if result.has_next():
                prev_id = result.get_next()[0]
                self._graph_conn.execute(f"""
                    MATCH (prev:Memory) WHERE prev.id = {prev_id}
                    MATCH (curr:Memory) WHERE curr.id = {memory_id}
                    CREATE (prev)-[:FOLLOWS]->(curr)
                """)
        except:
            pass
    
    def _parse_graph_results(self, result) -> List[Dict]:
        """Parse Kuzu query results to dict format."""
        memories = []
        while result.has_next():
            row = result.get_next()
            memories.append({
                "id": row[0],
                "content": row[1],
                "category": row[2],
                "created_at": row[3]
            })
        return memories


# Factory function
def get_hybrid_memory(db_path: str, use_graph: bool = True) -> HybridMemoryStore:
    """Get hybrid memory store."""
    if use_graph and KUZU_AVAILABLE:
        return HybridMemoryStore(db_path)
    else:
        # Fallback to SQLite-only wrapper
        store = HybridMemoryStore.__new__(HybridMemoryStore)
        store.sqlite = MemoryStore(db_path)
        store.graph = None
        store.graph_available = False
        store._sync_queue = []
        return store
