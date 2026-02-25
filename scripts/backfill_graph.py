"""
Graph Backfill Migration
========================
Re-indexes all existing SQLite memories into the Kuzu graph
with the new rich topic/entity extraction and semantic embeddings.

Usage:
    python3 scripts/backfill_graph.py [--db PATH] [--dry-run]
"""

import sys
import os
import sqlite3
import argparse
import json
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.hybrid_memory import HybridMemoryStore

# ── Config ────────────────────────────────────────────────────────────────────
DEFAULT_DB  = "workspace/memory/agent_memory.db"
GRAPH_PATH  = "workspace/memory/agent_memory_graph"


def get_all_memories(db_path: str) -> list:
    """Read all memories directly from SQLite."""
    conn = sqlite3.connect(db_path)
    # PRAGMA table_info returns: (cid, name, type, notnull, dflt_value, pk)
    cols = [d[1] for d in conn.execute("PRAGMA table_info(memories)").fetchall()]
    rows = conn.execute("SELECT * FROM memories ORDER BY id").fetchall()
    conn.close()
    return [dict(zip(cols, row)) for row in rows]


def backfill(db_path: str, graph_path: str, dry_run: bool = False):
    """Backfill all memories from SQLite into Kuzu graph."""
    memories = get_all_memories(db_path)
    total    = len(memories)

    print(f"\n🔍 Found {total} memories in {db_path}")
    if dry_run:
        print("🟡 Dry-run mode — no writes to graph\n")

    if total == 0:
        print("Nothing to backfill.")
        return

    if dry_run:
        # Just show what topics/entities would be extracted
        store = HybridMemoryStore.__new__(HybridMemoryStore)
        # Minimal init for extraction methods only
        from core.memory import MemoryStore
        store.sqlite         = MemoryStore(db_path)
        store.graph          = None
        store.graph_available = False
        store._stop_sync     = True
        store._embed_model   = None
        import threading
        store._embed_lock    = threading.Lock()

        for m in memories:
            content = m.get("content", "")
            topics  = store._extract_topics(content)
            entities = store._extract_entities(content)
            print(f"  [{m.get('id')}] {content[:70]}...")
            print(f"        Topics  : {topics}")
            print(f"        Entities: {[e['name'] for e in entities[:4]]}")
            print()
        return

    # Real run
    print(f"📦 Initialising graph at: {graph_path}")
    store = HybridMemoryStore(db_path=db_path, graph_path=graph_path)

    if not store.graph_available:
        print("❌ Kuzu graph not available. Install kuzu: pip install kuzu")
        sys.exit(1)

    print(f"✅ Graph ready. Starting backfill of {total} memories...\n")

    # Check which memory IDs are already in the graph to avoid duplicates
    try:
        result  = store._graph_conn.execute("MATCH (m:Memory) RETURN m.id")
        already = set()
        while result.has_next():
            already.add(result.get_next()[0])
        print(f"   Already in graph: {len(already)} nodes")
    except Exception:
        already = set()

    skipped   = 0
    processed = 0
    errors    = 0

    for i, mem in enumerate(memories, 1):
        mem_id  = mem.get("id") or mem.get("rowid")
        content = mem.get("content", "")
        cat     = mem.get("category", "general")
        imp     = mem.get("importance", "medium")
        created = mem.get("created_at") or mem.get("timestamp") or datetime.now().isoformat()

        if mem_id in already:
            skipped += 1
            print(f"  [{i}/{total}] SKIP  id={mem_id} (already in graph)")
            continue

        print(f"  [{i}/{total}] SYNC  id={mem_id}  {content[:55]}...")

        topics   = store._extract_topics(content)
        entities = store._extract_entities(content)
        print(f"           Topics:    {topics[:5]}")
        print(f"           Entities:  {[e['name'] for e in entities[:4]]}")

        item = {
            "id":         mem_id,
            "content":    content,
            "category":   cat,
            "importance": imp,
            "metadata":   {},
            "created_at": str(created),
        }

        try:
            store._sync_to_graph(item)
            processed += 1
        except Exception as e:
            print(f"           ❌ Error: {e}")
            errors += 1

    # Final stats
    print(f"\n{'='*50}")
    print(f"✅ Backfill complete")
    print(f"   Processed : {processed}")
    print(f"   Already existed: {skipped}")
    print(f"   Errors    : {errors}")

    stats = store.get_stats()
    print(f"\n📊 Graph stats after backfill:")
    print(f"   Memory nodes  : {stats['graph']['nodes']}")
    print(f"   Relationships : {stats['graph']['relationships']}")
    print(f"   Embedding model: {stats.get('embedding_model', 'None (no sentence-transformers)')}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Backfill memories into Kuzu graph")
    parser.add_argument("--db",      default=DEFAULT_DB,   help="SQLite DB path")
    parser.add_argument("--graph",   default=GRAPH_PATH,   help="Kuzu graph directory path")
    parser.add_argument("--dry-run", action="store_true",  help="Preview only, no writes")
    args = parser.parse_args()

    backfill(args.db, args.graph, args.dry_run)
