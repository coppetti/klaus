"""
API de Sincronização de Memórias
Conecta o Agente Kimi (Docker) com o Clawd local
"""

import os
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

# Configuração do Clawd local
CLAWD_MEMORY_PATH = os.getenv("CLAWD_MEMORY_PATH", "/app/clawd/clawd/memory.db")


class MemoryEntry(BaseModel):
    """Entrada de memória para sincronização."""
    content: str
    memory_type: str = "fact"  # 'fact', 'preference', 'decision', 'code', 'conversation'
    importance: float = 0.5  # 0.0-1.0
    source: str = "telegram"  # De onde veio
    user_id: Optional[str] = None
    entities: List[str] = []


class MemorySyncRequest(BaseModel):
    """Request para sincronizar memórias."""
    memories: List[MemoryEntry]
    user_id: str


class MemoryRecallRequest(BaseModel):
    """Request para recuperar memórias relevantes."""
    user_id: str
    query: str
    top_k: int = 5


def _get_clawd_connection():
    """Obtém conexão com o banco do Clawd local."""
    # Se o arquivo não existe no host, criamos localmente
    db_path = Path(CLAWD_MEMORY_PATH)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    
    # Criar tabela se não existir
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT NOT NULL,
            memory_type TEXT DEFAULT 'fact',
            importance REAL DEFAULT 0.5,
            decay_rate REAL DEFAULT 0.5,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            access_count INTEGER DEFAULT 0,
            entities TEXT DEFAULT '[]',
            source TEXT DEFAULT 'telegram',
            user_id TEXT
        )
    """)
    conn.commit()
    
    return conn


@router.post("/sync/memories")
def sync_memories(request: MemorySyncRequest):
    """
    Sincroniza memórias do Agente Kimi para o Clawd local.
    Chamado quando o agente detecta algo importante na conversa.
    """
    try:
        conn = _get_clawd_connection()
        cursor = conn.cursor()
        
        saved_ids = []
        for mem in request.memories:
            cursor.execute("""
                INSERT INTO memories 
                (content, memory_type, importance, source, user_id, entities, decay_rate)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                mem.content,
                mem.memory_type,
                mem.importance,
                mem.source,
                request.user_id,
                json.dumps(mem.entities),
                0.3 if mem.memory_type == "preference" else 0.5
            ))
            saved_ids.append(cursor.lastrowid)
        
        conn.commit()
        conn.close()
        
        return {
            "status": "ok",
            "saved_count": len(saved_ids),
            "memory_ids": saved_ids
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync/recall")
def recall_memories(request: MemoryRecallRequest):
    """
    Recupera memórias relevantes do Clawd para o Agente Kimi usar como contexto.
    """
    try:
        conn = _get_clawd_connection()
        cursor = conn.cursor()
        
        # Buscar memórias do usuário (ou gerais se não tiver user_id)
        cursor.execute("""
            SELECT id, content, memory_type, importance, created_at, access_count
            FROM memories 
            WHERE user_id = ? OR user_id IS NULL
            ORDER BY created_at DESC
            LIMIT 50
        """, (request.user_id,))
        
        rows = cursor.fetchall()
        
        # Calcular relevance score simples (últimas + importância)
        memories = []
        for row in rows:
            mem_id, content, mem_type, importance, created_at, access_count = row
            
            # Score baseado em palavras-chave na query
            query_words = set(request.query.lower().split())
            content_words = set(content.lower().split())
            overlap = len(query_words & content_words)
            
            relevance = overlap + (importance * 2) + (access_count * 0.1)
            
            memories.append({
                "id": mem_id,
                "content": content,
                "type": mem_type,
                "importance": importance,
                "relevance": relevance,
                "created_at": created_at
            })
        
        # Ordenar por relevância e pegar top_k
        memories.sort(key=lambda x: x["relevance"], reverse=True)
        top_memories = memories[:request.top_k]
        
        # Incrementar access_count para memórias usadas
        for mem in top_memories:
            cursor.execute(
                "UPDATE memories SET access_count = access_count + 1, last_accessed = ? WHERE id = ?",
                (datetime.now().isoformat(), mem["id"])
            )
        
        conn.commit()
        conn.close()
        
        return {
            "status": "ok",
            "query": request.query,
            "memories": top_memories
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sync/stats")
def sync_stats():
    """Estatísticas de memória."""
    try:
        conn = _get_clawd_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM memories")
        total = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT memory_type, COUNT(*) 
            FROM memories 
            GROUP BY memory_type
        """)
        by_type = {row[0]: row[1] for row in cursor.fetchall()}
        
        cursor.execute("""
            SELECT COUNT(DISTINCT user_id) 
            FROM memories 
            WHERE user_id IS NOT NULL
        """)
        users = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            "total_memories": total,
            "by_type": by_type,
            "unique_users": users,
            "db_path": CLAWD_MEMORY_PATH
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
