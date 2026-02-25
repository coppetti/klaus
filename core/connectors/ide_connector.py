"""
IDE Connector - Kimi Code / Claude Code / etc.
===============================================
Connects IDE agents to memory and context system.
Mirrors Telegram bot behavior for IDE mode.
"""

import os
import sys
import yaml
from pathlib import Path
from typing import Optional, List, Dict
from datetime import datetime

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from memory import MemoryStore
from core.hybrid_memory import HybridMemoryStore, MemoryQuery
from core.memory_relevance_gate import MemoryRelevanceGate

class IDEConnector:
    """
    IDE Connector - Automatic memory for IDE conversations.
    
    Usage:
        connector = IDEConnector()
        
        # Before responding - get context
        context = connector.get_context(user_message)
        
        # After responding - store interaction
        connector.store_interaction(user_message, assistant_response)
    """
    
    def __init__(self, config_path: str = "init.yaml"):
        self.config = self._load_config(config_path)
        self.memory = None
        self._init_memory()
        
        # Load agent/user info
        self.agent_name = self.config.get('agent', {}).get('name', 'Agent')
        self.user_name = self.config.get('user', {}).get('name', 'User')
        
        # Relevance gate - filters low-value interactions before storing
        memory_cfg = self.config.get('memory', {})
        high_t = memory_cfg.get('relevance_threshold', {}).get('high', 0.6)
        low_t  = memory_cfg.get('relevance_threshold', {}).get('low',  0.3)
        self.relevance_gate = MemoryRelevanceGate(high_threshold=high_t, low_threshold=low_t)
        
    def _load_config(self, path: str) -> Dict:
        """Load init.yaml."""
        config_path = Path(path)
        if not config_path.exists():
            # Try workspace parent
            config_path = Path("workspace").parent / path
        
        if config_path.exists():
            with open(config_path) as f:
                return yaml.safe_load(f)
        return {}
    
    def _init_memory(self):
        """Initialize hybrid memory (SQLite + Graph)."""
        memory_config = self.config.get('memory', {})
        
        if not memory_config.get('enabled', True):
            return
        
        # Use hybrid memory (SQLite + Kuzu Graph)
        db_path = memory_config.get('sqlite', {}).get('path', './memory.db')
        # Adjust path if in workspace
        if not Path(db_path).exists() and Path('workspace').exists():
            db_path = f"workspace/{db_path}"
        
        # Initialize hybrid store (auto-fallback to SQLite if Graph fails)
        try:
            self.memory = HybridMemoryStore(db_path)
        except Exception as e:
            print(f"⚠️  Hybrid memory failed: {e}, using SQLite fallback")
            self.memory = MemoryStore(db_path)
    
    def get_context(self, message: str, include_memories: bool = True) -> str:
        """
        Get context for response - like Telegram bot does.
        Returns formatted context with relevant memories.
        """
        context_parts = []
        
        # Load SOUL.md
        soul_paths = [
            Path("workspace/SOUL.md"),
            Path("SOUL.md"),
        ]
        for path in soul_paths:
            if path.exists():
                context_parts.append(f"--- AGENT SOUL ---\n{path.read_text()}")
                break
        
        # Load USER.md
        user_paths = [
            Path("workspace/USER.md"),
            Path("USER.md"),
        ]
        for path in user_paths:
            if path.exists():
                context_parts.append(f"--- USER PROFILE ---\n{path.read_text()}")
                break
        
        # Add relevant memories (use hybrid memory for contextual recall)
        if include_memories and self.memory:
            # Use context-aware recall if hybrid, fallback to simple recall
            if hasattr(self.memory, 'recall') and callable(getattr(self.memory, 'recall')):
                try:
                    # Try hybrid/contextual recall first
                    if isinstance(self.memory, HybridMemoryStore):
                        query = MemoryQuery(
                            query_type="context",
                            text=message,
                            limit=5,
                            context_depth=2
                        )
                        memories = self.memory.recall(query)
                    else:
                        # Fallback to simple SQLite recall
                        memories = self.memory.recall(message, limit=5)
                except Exception:
                    memories = self.memory.recall(message, limit=5)
            else:
                memories = []
            
            if memories:
                mem_lines = ["--- RELEVANT MEMORIES ---"]
                for m in memories:
                    mem_lines.append(f"• [{m.get('category', 'general')}] {m['content']}")
                context_parts.append("\n".join(mem_lines))
        
        return "\n\n".join(context_parts)
    
    def store_interaction(self, user_msg: str, assistant_msg: str,
                          category: str = "conversation", importance: str = "medium"):
        """
        Store conversation after relevance filtering.
        Low-value turns (greetings, acks) are silently dropped.
        High-value turns get structured facts extracted.
        """
        if not self.memory:
            return

        # --- Relevance gate ---
        decision = self.relevance_gate.evaluate(user_msg, assistant_msg)

        if not decision.should_store:
            # Debug: uncomment to trace what's being dropped
            # print(f"[memory] SKIP — {decision.skip_reason}")
            return

        # Determine what to persist
        if decision.extracted_facts:
            # High-importance: store each fact separately for better recall
            for fact in decision.extracted_facts:
                self.memory.store(
                    content=fact,
                    category=category,
                    importance=decision.importance,
                    metadata={
                        'timestamp': datetime.now().isoformat(),
                        'user': self.user_name,
                        'agent': self.agent_name,
                        'source': 'ide_connector',
                        'relevance_score': decision.score,
                    }
                )
        else:
            # Medium-importance: store compact Q/A summary
            content = f"Q: {user_msg[:100]}\nA: {assistant_msg[:200]}"
            self.memory.store(
                content=content,
                category=category,
                importance=decision.importance,
                metadata={
                    'timestamp': datetime.now().isoformat(),
                    'user': self.user_name,
                    'agent': self.agent_name,
                    'source': 'ide_connector',
                    'relevance_score': decision.score,
                }
            )
    
    def store_fact(self, fact: str, category: str = "general", 
                   importance: str = "medium"):
        """Store a specific fact/memory."""
        if self.memory:
            self.memory.store(
                content=fact,
                category=category,
                importance=importance,
                metadata={'type': 'fact', 'source': 'ide_connector'}
            )
    
    def recall(self, query: str, limit: int = 5) -> List[Dict]:
        """Recall memories matching query."""
        if not self.memory:
            return []
        
        # Handle both HybridMemoryStore and MemoryStore APIs
        if isinstance(self.memory, HybridMemoryStore):
            from core.hybrid_memory import MemoryQuery
            mem_query = MemoryQuery(
                query_type="quick", 
                text=query, 
                limit=limit
            )
            return self.memory.recall(mem_query)
        else:
            # MemoryStore API
            return self.memory.recall(query, limit)
    
    def get_stats(self) -> Dict:
        """Get memory stats."""
        if self.memory:
            return self.memory.get_stats()
        return {'total': 0, 'categories': {}}


# Global instance for easy access
_connector = None

def get_connector() -> IDEConnector:
    """Get or create global connector instance."""
    global _connector
    if _connector is None:
        _connector = IDEConnector()
    return _connector


def with_memory(func):
    """
    Decorator to automatically handle memory.
    
    Usage:
        @with_memory
        def respond(message: str) -> str:
            # Get context automatically
            context = get_context(message)
            # Generate response...
            return response
        # Response is automatically stored
    """
    def wrapper(message: str, *args, **kwargs):
        connector = get_connector()
        
        # Get context before
        context = connector.get_context(message)
        
        # Call function
        response = func(message, context=context, *args, **kwargs)
        
        # Store after
        connector.store_interaction(message, response)
        
        return response
    
    return wrapper


if __name__ == "__main__":
    # Test
    connector = IDEConnector()
    print(f"Agent: {connector.agent_name}")
    print(f"User: {connector.user_name}")
    print(f"Memory: {'✅ Enabled' if connector.memory else '❌ Disabled'}")
    print(f"Stats: {connector.get_stats()}")
