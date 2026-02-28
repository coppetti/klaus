"""
Memory Store
============
Simple SQLite-based memory storage.
"""

import sqlite3
import json
import os
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

class MemoryStore:
    """SQLite-based memory store with keyword search."""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._ensure_db()
    
    def _ensure_db(self):
        """Ensure database exists."""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create memories table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                category TEXT DEFAULT 'general',
                importance TEXT DEFAULT 'medium',
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                access_count INTEGER DEFAULT 0,
                last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create index for faster search
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_memories_category ON memories(category)
        """)
        
        conn.commit()
        conn.close()
    
    def store(self, content: str, category: str = "general", 
              importance: str = "medium", metadata: Optional[Dict] = None) -> int:
        """Store a memory."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        meta_json = json.dumps(metadata) if metadata else None
        
        cursor.execute(
            """INSERT INTO memories (content, category, importance, metadata)
               VALUES (?, ?, ?, ?)""",
            (content, category, importance, meta_json)
        )
        
        memory_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return memory_id
    
    def get_all_memories(self, limit: int = 100, offset: int = 0) -> List[Dict]:
        """Get all memories with pagination."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            """SELECT id, content, category, importance, metadata, created_at, access_count 
               FROM memories 
               ORDER BY created_at DESC 
               LIMIT ? OFFSET ?""",
            (limit, offset)
        )
        
        rows = cursor.fetchall()
        conn.close()
        
        return [{
            "id": row[0],
            "content": row[1],
            "category": row[2],
            "importance": row[3],
            "metadata": json.loads(row[4]) if row[4] else {},
            "created_at": row[5],
            "access_count": row[6]
        } for row in rows]
    
    def delete_memory(self, memory_id: int) -> bool:
        """Delete a specific memory."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
        deleted = cursor.rowcount > 0
        
        conn.commit()
        conn.close()
        
        return deleted
    
    def recall(self, query: str, limit: int = 5) -> List[Dict]:
        """Recall memories matching query."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get recent memories
        cursor.execute(
            "SELECT * FROM memories ORDER BY created_at DESC LIMIT ?",
            (limit * 3,)
        )
        
        rows = cursor.fetchall()
        
        # Simple keyword matching
        keywords = query.lower().split()
        scored = []
        
        for row in rows:
            content = row[1].lower()
            score = sum(1 for kw in keywords if kw in content)
            if score > 0 or not keywords:
                scored.append({
                    "id": row[0],
                    "content": row[1],
                    "category": row[2],
                    "importance": row[3],
                    "created_at": row[5],
                    "score": score
                })
        
        # Sort by score and recency
        scored.sort(key=lambda x: (x["score"], x["created_at"]), reverse=True)
        
        # Update access count for returned memories
        for mem in scored[:limit]:
            cursor.execute(
                """UPDATE memories 
                   SET access_count = access_count + 1, last_accessed = ?
                   WHERE id = ?""",
                (datetime.now().isoformat(), mem["id"])
            )
        
        conn.commit()
        conn.close()
        
        return scored[:limit]
    
    def get_stats(self) -> Dict:
        """Get memory statistics."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*), category FROM memories GROUP BY category")
        categories = {row[1]: row[0] for row in cursor.fetchall()}
        
        cursor.execute("SELECT COUNT(*) FROM memories")
        total = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            "total": total,
            "categories": categories
        }
    
    def clear(self):
        """Clear all memories."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM memories")
        conn.commit()
        conn.close()
