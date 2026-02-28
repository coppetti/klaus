"""
Context Manager for IDE Agent Wizard
=====================================
Manages conversation context intelligently:
- Short-term: Recent messages (sliding window)
- Long-term: Important facts extracted from conversation
- Auto-compaction: Summarizes old messages when limit reached

Similar to how IDE agents work with limited context window + memory.
"""

import json
import re
from typing import List, Dict, Optional
from datetime import datetime
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class ContextFact:
    """An important fact extracted from conversation."""
    content: str
    category: str  # "preference", "decision", "information", "task"
    timestamp: str
    message_id: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> "ContextFact":
        return cls(**data)


class ContextManager:
    """
    Manages conversation context with intelligent compaction.
    
    Strategy:
    1. Keep recent messages in full (short-term memory)
    2. Extract important facts automatically (long-term memory)
    3. When limit reached, summarize older messages
    4. Always maintain SOUL.md + facts + recent context
    """
    
    def __init__(self, max_messages: int = 0, max_tokens: int = 200000):
        self.max_messages = max_messages  # 0 = unlimited
        self.max_tokens = max_tokens  # Default 200k, 0 = unlimited
        self.facts: List[ContextFact] = []
        self.message_counter = 0
    
    def extract_facts(self, user_msg: str, assistant_msg: str = None) -> List[ContextFact]:
        """
        Extract important facts from user message.
        Lightweight extraction without LLM call.
        Only analyzes user_msg to avoid noise from assistant responses.
        """
        facts = []
        text = user_msg.lower()  # Only user message, not assistant
        
        # Preference patterns - expanded
        preference_patterns = [
            (r'(?:prefiro|gosto de|like|prefer)\s+(.+?)(?:\.|,|!|\?|$|\s+para|\s+pois|\s+porque)', 'preference'),
            (r'(?:não gosto de|don\'t like|hate|detesto)\s+(.+?)(?:\.|,|!|\?|$|\s+para|\s+pois|\s+porque)', 'preference'),
            (r'(?:sempre uso|always use)\s+(.+?)(?:\.|,|!|\?|$|\s+para|\s+pois|\s+porque)', 'preference'),
            (r'(?:nunca uso|never use)\s+(.+?)(?:\.|,|!|\?|$|\s+para|\s+pois|\s+porque)', 'preference'),
            # Padrões adicionais para preferências
            (r'(?:meu default|meu padrão|my default|my standard)\s+(?:é|eh|is|são|are)?\s*(?:o|a|os|as)?\s*(.+?)(?:\.|,|!|\?|$|\s+para|\s+pois|\s+porque)', 'preference'),
            (r'(?:eu uso|i use)\s+(.+?)(?:\.|,|!|\?|$|\s+para|\s+pois|\s+porque)', 'preference'),
            (r'(?:costumo usar|usually use|normalmente uso)\s+(.+?)(?:\.|,|!|\?|$|\s+para|\s+pois|\s+porque)', 'preference'),
        ]
        
        # Decision patterns
        decision_patterns = [
            (r'(?:decidi|decided|vamos usar|let\'s use)\s+(.+?)(?:\.|,|$)', 'decision'),
            (r'(?:escolhi|chose|vou usar|will use)\s+(.+?)(?:\.|,|$)', 'decision'),
            (r'(?:adotar|adopt|implementar|implement)\s+(.+?)(?:\.|,|$)', 'decision'),
        ]
        
        # Information patterns
        info_patterns = [
            (r'(?:meu nome é|my name is|eu sou|i am)\s+(.+?)(?:\.|,|$)', 'information'),
            (r'(?:trabalho com|work with|minha empresa|my company)\s+(.+?)(?:\.|,|$)', 'information'),
            (r'(?:projeto|project)\s+(.+?)(?:\.|,|$)', 'information'),
        ]
        
        # Task/Goal patterns - NOVO! Captura intenções e objetivos
        task_patterns = [
            (r'(?:preciso que você|need you to|quero que você|want you to)\s+(.+?)(?:\.|,|!|\?|$)', 'task'),
            (r'(?:me ajude|help me|me ajuda|ajuda-me)\s+(?:com|with)\s+(.+?)(?:\.|,|!|\?|$)', 'task'),
            (r'(?:estou trabalhando|i am working|trabalhando em|working on)\s+(?:em|on)?\s*(.+?)(?:\.|,|!|\?|$)', 'task'),
            (r'(?:meu objetivo|my goal|objetivo é|goal is)\s+(?:é|is)?\s*(.+?)(?:\.|,|!|\?|$)', 'task'),
            (r'(?:quero fazer|want to do|vou fazer|will do)\s+(.+?)(?:\.|,|!|\?|$)', 'task'),
            (r'(?:preciso fazer|need to do|tenho que|have to)\s+(.+?)(?:\.|,|!|\?|$)', 'task'),
            (r'(?:vamos|let\'s)\s+(.+?)(?:\.|,|!|\?|$)', 'task'),
            (r'(?:criar|create|build|desenvolver|develop)\s+(?:um|a|uma)?\s*(.+?)(?:\.|,|!|\?|$)', 'task'),
        ]
        
        all_patterns = preference_patterns + decision_patterns + info_patterns + task_patterns
        
        for pattern, category in all_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                match_clean = match.strip()
                # Allow short matches if they contain dots (file extensions) or are meaningful
                is_meaningful = len(match_clean) > 3 or '.' in match_clean or match_clean in ['.md', '.txt', '.py', '.js', '.ts']
                if is_meaningful:
                    fact = ContextFact(
                        content=match_clean.capitalize(),
                        category=category,
                        timestamp=datetime.now().isoformat(),
                        message_id=str(self.message_counter)
                    )
                    facts.append(fact)
        
        return facts
    
    def add_exchange(self, user_msg: str, assistant_msg: str) -> List[ContextFact]:
        """Process a conversation exchange and extract facts."""
        facts = self.extract_facts(user_msg, assistant_msg)
        self.facts.extend(facts)
        self.message_counter += 1
        return facts
    
    def estimate_tokens(self, text: str) -> int:
        """Estimate token count (rough approximation)."""
        # English: ~4 chars/token, Portuguese: ~3 chars/token
        # Conservative estimate
        return len(text) // 3
    
    def build_context(self, 
                      messages: List[Dict], 
                      soul_content: str,
                      web_search_results: Optional[str] = None) -> List[Dict]:
        """
        Build optimized context for LLM.
        
        Priority (highest to lowest):
        1. System message (SOUL + capabilities)
        2. Important facts (long-term memory)
        3. Web search results (if any)
        4. Recent messages (short-term memory)
        """
        context_messages = []
        total_tokens = 0
        
        # 1. System message with SOUL
        system_msg = f"{soul_content}\n\nYou are an AI assistant."
        
        # Add context management instructions
        if self.facts:
            system_msg += "\n\n[IMPORTANT FACTS FROM THIS CONVERSATION]:\n"
            for fact in self.facts[-10:]:  # Last 10 facts
                system_msg += f"• [{fact.category.upper()}] {fact.content}\n"
        
        context_messages.append({"role": "system", "content": system_msg})
        total_tokens += self.estimate_tokens(system_msg)
        
        # 2. Web search results (if present)
        if web_search_results:
            context_messages.append({"role": "system", "content": web_search_results})
            total_tokens += self.estimate_tokens(web_search_results)
        
        # 3. Add recent messages (respecting token budget)
        remaining_budget = self.max_tokens - total_tokens
        selected_messages = []
        
        # Start from most recent
        for msg in reversed(messages):
            msg_text = msg.get("text", "")
            msg_tokens = self.estimate_tokens(msg_text)
            
            if msg_tokens > remaining_budget:
                # If we can't fit this message, summarize older ones
                break
            
            role = "user" if msg.get("sender") == "user" else "assistant"
            selected_messages.insert(0, {  # Insert at beginning to maintain order
                "role": role,
                "content": msg_text
            })
            remaining_budget -= msg_tokens
        
        context_messages.extend(selected_messages)
        
        return context_messages
    
    def get_context_stats(self) -> Dict:
        """Get context statistics."""
        return {
            "facts_stored": len(self.facts),
            "facts_by_category": self._count_facts_by_category(),
            "max_messages": self.max_messages,
            "max_tokens": self.max_tokens
        }
    
    def _count_facts_by_category(self) -> Dict[str, int]:
        """Count facts by category."""
        counts = {}
        for fact in self.facts:
            counts[fact.category] = counts.get(fact.category, 0) + 1
        return counts
    
    def clear_facts(self):
        """Clear all extracted facts."""
        self.facts = []
    
    def export_facts(self) -> List[Dict]:
        """Export facts for storage."""
        return [f.to_dict() for f in self.facts]
    
    def import_facts(self, facts_data: List[Dict]):
        """Import facts from storage."""
        self.facts = [ContextFact.from_dict(f) for f in facts_data]


# Session-based context manager for Web UI
class SessionContextManager:
    """
    Manages context per session in Web UI.
    Stores facts in session storage.
    """
    
    def __init__(self, session_id: str, max_messages: int = 0):
        self.session_id = session_id
        self.max_messages = max_messages
        self.facts: List[ContextFact] = []
        self._load_facts()
    
    def _get_facts_file(self) -> Path:
        """Get path to facts file for this session."""
        from pathlib import Path
        data_dir = Path("/app/workspace/web_ui_data/context_facts")
        data_dir.mkdir(parents=True, exist_ok=True)
        return data_dir / f"{self.session_id}_facts.json"
    
    def _load_facts(self):
        """Load facts from disk."""
        facts_file = self._get_facts_file()
        if facts_file.exists():
            try:
                with open(facts_file) as f:
                    data = json.load(f)
                    self.facts = [ContextFact.from_dict(d) for d in data]
            except Exception as e:
                print(f"Warning: Could not load facts for session {self.session_id}: {e}")
    
    def _save_facts(self):
        """Save facts to disk."""
        facts_file = self._get_facts_file()
        try:
            with open(facts_file, 'w') as f:
                json.dump([f.to_dict() for f in self.facts], f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save facts for session {self.session_id}: {e}")
    
    def add_exchange(self, user_msg: str, assistant_msg: str):
        """Add exchange and extract facts."""
        manager = ContextManager(max_messages=self.max_messages)
        manager.facts = self.facts
        facts = manager.add_exchange(user_msg, assistant_msg)
        self.facts = manager.facts
        self._save_facts()
        return facts
    
    def build_context(self, messages: List[Dict], soul_content: str, 
                      web_search_results: Optional[str] = None) -> List[Dict]:
        """Build context for this session."""
        manager = ContextManager(max_messages=self.max_messages)
        manager.facts = self.facts
        return manager.build_context(messages, soul_content, web_search_results)
    
    def get_facts_summary(self) -> str:
        """Get summary of facts for display."""
        if not self.facts:
            return "No facts extracted yet"
        
        lines = []
        for fact in self.facts[-5:]:  # Last 5 facts
            lines.append(f"• [{fact.category}] {fact.content}")
        return "\n".join(lines)
    
    def export_facts(self) -> List[Dict]:
        """Export facts for storage."""
        return [f.to_dict() for f in self.facts]
    
    def clear_facts(self):
        """Clear all facts."""
        self.facts = []
        self._save_facts()
