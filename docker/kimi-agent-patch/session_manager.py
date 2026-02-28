"""
Gerenciamento de sessões persistentes para o Agente Kimi.
SQLite + armazenamento de contexto.
"""

import json
import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class Message:
    role: str  # 'user' | 'assistant' | 'system'
    content: str
    timestamp: str
    metadata: Optional[Dict] = None


@dataclass
class Session:
    session_id: str
    user_id: str
    messages: List[Message]
    created_at: str
    last_activity: str
    context_data: Dict  # Dados extras (tópico atual, preferências, etc.)


class SessionManager:
    """Gerencia sessões persistentes em SQLite."""
    
    def __init__(self, db_path: str = "/app/data/sessions.db"):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Inicializa o banco de dados."""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    messages TEXT NOT NULL,  -- JSON
                    created_at TEXT NOT NULL,
                    last_activity TEXT NOT NULL,
                    context_data TEXT NOT NULL  -- JSON
                )
            """)
            
            # Índice para busca por usuário
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_user_id 
                ON sessions(user_id)
            """)
            
            conn.commit()
    
    def get_or_create_session(self, user_id: str, max_history: int = 10) -> Session:
        """Obtém sessão existente ou cria nova."""
        session_id = f"session_{user_id}"
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT * FROM sessions WHERE session_id = ?",
                (session_id,)
            )
            row = cursor.fetchone()
            
            if row:
                # Sessão existe - carregar
                session = Session(
                    session_id=row[0],
                    user_id=row[1],
                    messages=[Message(**m) for m in json.loads(row[2])],
                    created_at=row[3],
                    last_activity=row[4],
                    context_data=json.loads(row[5])
                )
                
                # Verificar se expirou (2 horas de inatividade)
                last = datetime.fromisoformat(session.last_activity)
                if datetime.now() - last > timedelta(hours=2):
                    # Resetar sessão expirada
                    return self._create_session(user_id, session_id)
                
                return session
            else:
                # Criar nova sessão
                return self._create_session(user_id, session_id)
    
    def _create_session(self, user_id: str, session_id: str) -> Session:
        """Cria nova sessão."""
        now = datetime.now().isoformat()
        session = Session(
            session_id=session_id,
            user_id=user_id,
            messages=[],
            created_at=now,
            last_activity=now,
            context_data={"topic": None, "preferences": {}}
        )
        self._save_session(session)
        return session
    
    def _save_session(self, session: Session):
        """Salva sessão no banco."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """INSERT OR REPLACE INTO sessions 
                   (session_id, user_id, messages, created_at, last_activity, context_data)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    session.session_id,
                    session.user_id,
                    json.dumps([{"role": m.role, "content": m.content, 
                                "timestamp": m.timestamp, "metadata": m.metadata} 
                               for m in session.messages]),
                    session.created_at,
                    session.last_activity,
                    json.dumps(session.context_data)
                )
            )
            conn.commit()
    
    def add_message(self, user_id: str, role: str, content: str, 
                   metadata: Optional[Dict] = None) -> Session:
        """Adiciona mensagem à sessão."""
        session = self.get_or_create_session(user_id)
        
        msg = Message(
            role=role,
            content=content,
            timestamp=datetime.now().isoformat(),
            metadata=metadata
        )
        session.messages.append(msg)
        
        # Manter apenas últimas N mensagens
        if len(session.messages) > 10:
            session.messages = session.messages[-10:]
        
        session.last_activity = datetime.now().isoformat()
        self._save_session(session)
        
        return session
    
    def get_messages_for_api(self, user_id: str, system_prompt: str = None) -> List[Dict]:
        """Retorna mensagens formatadas para API do Kimi."""
        session = self.get_or_create_session(user_id)
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        for msg in session.messages:
            messages.append({"role": msg.role, "content": msg.content})
        
        return messages
    
    def update_context(self, user_id: str, **kwargs):
        """Atualiza dados de contexto da sessão."""
        session = self.get_or_create_session(user_id)
        session.context_data.update(kwargs)
        session.last_activity = datetime.now().isoformat()
        self._save_session(session)
    
    def clear_session(self, user_id: str):
        """Limpa sessão do usuário."""
        session_id = f"session_{user_id}"
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
            conn.commit()
    
    def get_stats(self) -> Dict:
        """Estatísticas do sistema."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM sessions")
            total = cursor.fetchone()[0]
            
            cursor = conn.execute(
                "SELECT COUNT(*) FROM sessions WHERE last_activity > ?",
                ((datetime.now() - timedelta(hours=2)).isoformat(),)
            )
            active = cursor.fetchone()[0]
            
            return {"total_sessions": total, "active_sessions": active}
