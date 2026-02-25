"""
Semantic Memory System for Klaus
===========================================
Human-like memory that understands:
- Feedback (positive/negative)
- What worked and what didn't
- Context of successful interactions
- Emotional and relational context

Instead of just extracting "facts", this system understands the 
*meaning* of interactions and learns from them.
"""

import json
import re
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path


class InteractionType(Enum):
    """Types of human-AI interactions."""
    TASK_COMPLETION = "task_completion"      # User asked, AI delivered
    COLLABORATION = "collaboration"          # Working together on something
    EXPLORATION = "exploration"              # Brainstorming, discovering
    PROBLEM_SOLVING = "problem_solving"      # Debugging, fixing issues
    LEARNING = "learning"                    # Teaching/learning moment
    FEEDBACK = "feedback"                    # Explicit feedback given


class Sentiment(Enum):
    """Emotional sentiment of interaction."""
    VERY_POSITIVE = 5   # "Excelente!", "Perfeito!", "Incrível!"
    POSITIVE = 4        # "Bom", "Funcionou", "Obrigado"
    NEUTRAL = 3         # "OK", "Entendido"
    NEGATIVE = 2        # "Não funcionou", "Errado"
    VERY_NEGATIVE = 1   # "Péssimo", "Não ajudou"


@dataclass
class SemanticMemory:
    """
    A rich, human-like memory of an interaction.
    
    Not just WHAT was said, but:
    - What was the context?
    - Did it work?
    - What approach was used?
    - What should we remember for next time?
    """
    # Core identification
    memory_id: str
    timestamp: str
    session_id: str
    
    # What happened
    user_intent: str              # What the user wanted
    approach_taken: str           # How the AI responded
    outcome: str                  # What was the result
    
    # Semantic understanding
    interaction_type: str         # Task, collaboration, exploration...
    sentiment: int                # 1-5 scale
    
    # Learning
    what_worked: List[str]        # Specific things that worked
    what_to_avoid: List[str]      # Things that didn't work
    key_insights: List[str]       # Important learnings
    
    # Context
    user_state: str               # User's context (frustrated, learning, expert...)
    topics: List[str]             # Related topics
    related_memories: List[str]   # IDs of related memories
    
    # For retrieval
    importance_score: float       # 0-1, how important is this memory
    access_count: int = 0         # How many times recalled
    last_accessed: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> "SemanticMemory":
        return cls(**data)


class SemanticMemoryExtractor:
    """
    Extracts rich, semantic memories from conversations.
    Goes beyond regex to understand the meaning of interactions.
    """
    
    # Patterns for feedback detection
    FEEDBACK_PATTERNS = {
        Sentiment.VERY_POSITIVE: [
            r'(?:excelente|perfeito|incr[ií]vel|fant[aá]stico|muito bom|ótimo|adorei|amei)',
            r'(?:excellent|perfect|amazing|fantastic|great|awesome|love it)',
            r'(?:isso mesmo|exatamente|certinho|nossa senhora)',
        ],
        Sentiment.POSITIVE: [
            r'(?:bom|funcionou|obrigado|valeu|legal|ok|certo|show)',
            r'(?:good|thanks|works|nice|cool|alright)',
            r'(?:serve|atende|resolve|ajudou)',
        ],
        Sentiment.NEGATIVE: [
            r'(?:n[aã]o funcionou|errado|errada|pior|n[aã]o [eé] isso)',
            r'(?:not working|wrong|worse|that\'s not it)',
            r'(?:quase|faltou|incompleto)',
        ],
        Sentiment.VERY_NEGATIVE: [
            r'(?:p[eé]ssimo|horr[ií]vel|terr[ií]vel|n[aã]o ajudou|deu errado)',
            r'(?:terrible|horrible|awful|didn\'t help|went wrong)',
            r'(?:odiei|detestei|perda de tempo)',
        ]
    }
    
    # Patterns for understanding what worked
    SUCCESS_PATTERNS = [
        r'(?:isso|essa|esse)\s+(?:abordagem|approach|m[eé]todo|jeito|forma)\s+(?:funciona|funcionou|serve|boa)',
        r'(?:gostei|curti|gosto)\s+(?:desse|dessa|desse jeito|assim)',
        r'(?:assim|dessa forma|desse jeito)\s+(?:sim|ok|serve|funciona)',
        r'(?:vamos|vou)\s+(?:manter|continuar|usar)\s+(?:assim|desse jeito)',
    ]
    
    # Patterns for task completion
    TASK_PATTERNS = [
        r'(?:conseguiu?|conseguimos|deu certo|funcionou)',
        r'(?:resolvido|pronto|feito|completo|terminado)',
        r'(?:resolvido|done|ready|complete|finished|working)',
    ]
    
    @classmethod
    def analyze_conversation_exchange(
        cls,
        user_msg: str,
        assistant_msg: str,
        context: Dict = None
    ) -> Optional[SemanticMemory]:
        """
        Analyze a conversation exchange and create a semantic memory if meaningful.
        
        This is where the "magic" happens - understanding what just occurred.
        """
        user_lower = user_msg.lower()
        assistant_lower = assistant_msg.lower()
        
        # Detect sentiment
        sentiment = cls._detect_sentiment(user_lower)
        
        # Check if this is a meaningful interaction worth remembering
        is_task_completion = cls._detect_task_completion(user_lower, assistant_lower)
        has_feedback = sentiment != Sentiment.NEUTRAL
        is_collaboration = cls._detect_collaboration(user_lower, assistant_lower)
        
        # If nothing meaningful happened, don't create memory
        if not (is_task_completion or has_feedback or is_collaboration):
            return None
        
        # Extract what worked
        what_worked = cls._extract_what_worked(user_lower, assistant_lower)
        
        # Detect interaction type
        interaction_type = cls._detect_interaction_type(user_lower, assistant_lower)
        
        # Generate key insights
        insights = cls._generate_insights(user_msg, assistant_msg, sentiment)
        
        # Calculate importance
        importance = cls._calculate_importance(sentiment, what_worked, interaction_type)
        
        return SemanticMemory(
            memory_id=f"sm_{datetime.now().strftime('%Y%m%d%H%M%S')}_{hash(user_msg) % 10000}",
            timestamp=datetime.now().isoformat(),
            session_id=context.get('session_id', 'unknown') if context else 'unknown',
            
            user_intent=cls._extract_user_intent(user_msg),
            approach_taken=cls._summarize_approach(assistant_msg),
            outcome=cls._determine_outcome(sentiment, is_task_completion),
            
            interaction_type=interaction_type.value,
            sentiment=sentiment.value,
            
            what_worked=what_worked,
            what_to_avoid=cls._extract_what_to_avoid(user_lower, sentiment),
            key_insights=insights,
            
            user_state=cls._detect_user_state(user_lower, context),
            topics=cls._extract_topics(user_msg, assistant_msg),
            related_memories=[],
            
            importance_score=importance
        )
    
    @classmethod
    def _detect_sentiment(cls, text: str) -> Sentiment:
        """Detect the emotional sentiment of user's message."""
        for sentiment, patterns in cls.FEEDBACK_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    return sentiment
        return Sentiment.NEUTRAL
    
    @classmethod
    def _detect_task_completion(cls, user: str, assistant: str) -> bool:
        """Detect if a task was just completed."""
        combined = f"{user} {assistant}"
        for pattern in cls.TASK_PATTERNS:
            if re.search(pattern, combined, re.IGNORECASE):
                return True
        return False
    
    @classmethod
    def _detect_collaboration(cls, user: str, assistant: str) -> bool:
        """Detect if this was a collaborative interaction."""
        collab_patterns = [
            r'(?:vamos|let\'s)\s+(?:fazer|try|tentar)',
            r'(?:pode|could you)\s+(?:ajustar|adjust|mudar|change)',
            r'(?:melhorar|improve|refinar|refine)',
            r'(?:quase|almost|falta|missing)\s+(?:s[oó]|just)',
        ]
        for pattern in collab_patterns:
            if re.search(pattern, user, re.IGNORECASE):
                return True
        return False
    
    @classmethod
    def _extract_what_worked(cls, user: str, assistant: str) -> List[str]:
        """Extract specific approaches/methods that worked."""
        worked = []
        
        # Check for explicit praise of approaches
        if re.search(r'(?:abordagem|approach|jeito|forma|m[eé]todo)', user, re.IGNORECASE):
            # Extract the praised approach
            match = re.search(
                r'(?:gostei|curti|funcionou|serve)\s+(?:desse|dessa|do|da)\s+(.+?)(?:\.|,|$)',
                user, re.IGNORECASE
            )
            if match:
                worked.append(f"Approach: {match.group(1).strip()}")
        
        # Check for format preferences
        if re.search(r'(?:formato|format|estrutura|structure)', user, re.IGNORECASE):
            worked.append("Format/structure used")
        
        # Check for depth/detail level
        if re.search(r'(?:n[ií]vel|level|profundidade|depth)', user, re.IGNORECASE):
            worked.append("Level of detail provided")
        
        # Check for tone/style
        if re.search(r'(?:tom|tone|estilo|style|clareza|clear)', user, re.IGNORECASE):
            worked.append("Communication style/tone")
        
        return worked
    
    @classmethod
    def _detect_interaction_type(cls, user: str, assistant: str) -> InteractionType:
        """Classify the type of interaction."""
        combined = f"{user} {assistant}"
        
        if re.search(r'(?:debug|error|err|bug|fix|arrumar|consertar)', combined, re.IGNORECASE):
            return InteractionType.PROBLEM_SOLVING
        
        if re.search(r'(?:aprender|learn|explicar|explain|como funciona|how does)', combined, re.IGNORECASE):
            return InteractionType.LEARNING
        
        if re.search(r'(?:explorar|explore|opções|opções|alternativas)', combined, re.IGNORECASE):
            return InteractionType.EXPLORATION
        
        if re.search(r'(?:juntos|together|colaborar|collaborate|ajustar juntos)', combined, re.IGNORECASE):
            return InteractionType.COLLABORATION
        
        if cls._detect_task_completion(user, assistant):
            return InteractionType.TASK_COMPLETION
        
        return InteractionType.FEEDBACK
    
    @classmethod
    def _generate_insights(cls, user: str, assistant: str, sentiment: Sentiment) -> List[str]:
        """Generate key insights from the interaction."""
        insights = []
        
        if sentiment.value >= 4:
            insights.append("User responded positively - approach was effective")
        elif sentiment.value <= 2:
            insights.append("User responded negatively - needs different approach")
        
        # Detect if this was iterative refinement
        if re.search(r'(?:melhor|better|ajustar|adjust)', user, re.IGNORECASE):
            insights.append("Iterative refinement - user likes to polish solutions")
        
        # Detect preference for examples
        if re.search(r'(?:exemplo|example|código|code)', user, re.IGNORECASE):
            insights.append("User learns better with concrete examples")
        
        # Detect time pressure
        if re.search(r'(?:rápido|quick|urgente|urgent|tempo|time)', user, re.IGNORECASE):
            insights.append("User often has time constraints")
        
        return insights
    
    @classmethod
    def _extract_user_intent(cls, user_msg: str) -> str:
        """Extract what the user was trying to achieve."""
        # Remove filler words and extract core intent
        intent = user_msg[:100]  # First 100 chars as summary
        return intent
    
    @classmethod
    def _summarize_approach(cls, assistant_msg: str) -> str:
        """Summarize the approach taken by the assistant."""
        # Look for structure indicators
        if re.search(r'```', assistant_msg):
            return "Provided code example"
        if re.search(r'\d+\.', assistant_msg[:200]):
            return "Numbered step-by-step approach"
        if re.search(r'\*|-', assistant_msg[:200]):
            return "Bullet point explanation"
        if len(assistant_msg) > 500:
            return "Detailed comprehensive explanation"
        return "Direct concise response"
    
    @classmethod
    def _determine_outcome(cls, sentiment: Sentiment, task_completed: bool) -> str:
        """Determine the outcome of the interaction."""
        if task_completed and sentiment.value >= 4:
            return "Task completed successfully with high satisfaction"
        elif task_completed:
            return "Task completed, neutral satisfaction"
        elif sentiment.value >= 4:
            return "Positive reception, may need follow-up"
        elif sentiment.value <= 2:
            return "Needs revision or different approach"
        return "Ongoing interaction"
    
    @classmethod
    def _extract_what_to_avoid(cls, user: str, sentiment: Sentiment) -> List[str]:
        """Extract what didn't work or should be avoided."""
        avoid = []
        
        if sentiment.value <= 2:
            if re.search(r'(?:muito longo|too long|verbose)', user, re.IGNORECASE):
                avoid.append("Overly verbose responses")
            if re.search(r'(?:complicado|complicated|complexo)', user, re.IGNORECASE):
                avoid.append("Overly complex explanations")
            if re.search(r'(?:n[aã]o entendi|didn\'t understand)', user, re.IGNORECASE):
                avoid.append("Current explanation style")
        
        return avoid
    
    @classmethod
    def _detect_user_state(cls, user_msg: str, context: Dict) -> str:
        """Detect user's emotional/cognitive state."""
        user_lower = user_msg.lower()
        
        if re.search(r'(?:urgente|urgent|asap|agora|now)', user_lower):
            return "under_time_pressure"
        if re.search(r'(?:confuso|confused|n[aã]o entendi|lost)', user_lower):
            return "confused_needs_clarity"
        if re.search(r'(?:experiente|expert|avan[cç]ado|advanced)', user_lower):
            return "expert_user"
        if re.search(r'(?:iniciante|beginner|b[aá]sico|basic)', user_lower):
            return "beginner_learning"
        if re.search(r'(?:brigad|obrigad|valeu|thanks|grat)', user_lower):
            return "appreciative"
        
        return "neutral"
    
    @classmethod
    def _extract_topics(cls, user: str, assistant: str) -> List[str]:
        """Extract topics discussed."""
        combined = f"{user} {assistant}".lower()
        topics = []
        
        # Tech topics
        tech_keywords = {
            'react', 'vue', 'angular', 'svelte', 'javascript', 'typescript',
            'python', 'rust', 'go', 'node', 'docker', 'kubernetes', 'aws',
            'database', 'api', 'frontend', 'backend', 'devops'
        }
        
        for keyword in tech_keywords:
            if keyword in combined:
                topics.append(keyword)
        
        return topics[:5]  # Top 5 topics
    
    @classmethod
    def _calculate_importance(
        cls,
        sentiment: Sentiment,
        what_worked: List[str],
        interaction_type: InteractionType
    ) -> float:
        """Calculate how important this memory is to keep."""
        importance = 0.5  # Base
        
        # Strong sentiment = more important
        if sentiment == Sentiment.VERY_POSITIVE:
            importance += 0.3
        elif sentiment == Sentiment.VERY_NEGATIVE:
            importance += 0.25  # Also important to remember mistakes
        
        # What worked = important
        importance += len(what_worked) * 0.05
        
        # Task completion is important
        if interaction_type == InteractionType.TASK_COMPLETION:
            importance += 0.1
        
        return min(importance, 1.0)


class SemanticMemoryStore:
    """
    Store and retrieve semantic memories.
    
    Implements memory decay similar to human memory:
    - Time-based decay: Older memories fade
    - Access-based decay: Unused memories fade
    - Rehearsal: Accessing strengthens memory
    - Consolidation: Very important memories resist decay
    """
    
    # Decay constants (tune these based on desired behavior)
    DECAY_HALF_LIFE_DAYS = 30  # Memory loses half relevance in 30 days
    DECAY_ACCESS_BONUS = 0.1   # Each access adds 10% strength
    DECAY_MIN_STRENGTH = 0.1   # Minimum strength before forgetting
    CONSOLIDATION_THRESHOLD = 0.8  # Very positive + important = consolidated
    
    def __init__(self, data_dir: str = "/app/workspace/semantic_memory"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.memories_file = self.data_dir / "memories.json"
        self.memories: List[SemanticMemory] = []
        self._load_memories()
        self._apply_decay()  # Apply decay on load
    
    def _load_memories(self):
        """Load memories from disk."""
        if self.memories_file.exists():
            try:
                with open(self.memories_file) as f:
                    data = json.load(f)
                    self.memories = [SemanticMemory.from_dict(m) for m in data]
            except Exception as e:
                print(f"Error loading memories: {e}")
    
    def _save_memories(self):
        """Save memories to disk."""
        try:
            with open(self.memories_file, 'w') as f:
                json.dump([m.to_dict() for m in self.memories], f, indent=2)
        except Exception as e:
            print(f"Error saving memories: {e}")
    
    def add_memory(self, memory: SemanticMemory):
        """Add a new semantic memory."""
        self.memories.append(memory)
        self._save_memories()
    
    def _calculate_memory_strength(self, memory: SemanticMemory) -> float:
        """
        Calculate current strength of a memory based on:
        - Time decay (older = weaker)
        - Access history (rehearsal = stronger)
        - Consolidation (very good memories resist decay)
        """
        from datetime import datetime, timedelta
        
        # Base strength from importance
        strength = memory.importance_score
        
        # Time decay calculation
        memory_time = datetime.fromisoformat(memory.timestamp)
        now = datetime.now()
        days_old = (now - memory_time).days
        
        # Consolidated memories (very positive + important) resist decay
        is_consolidated = (
            memory.sentiment >= 4 and 
            memory.importance_score >= self.CONSOLIDATION_THRESHOLD
        )
        
        if is_consolidated:
            # Consolidated memories decay 10x slower
            effective_days = days_old / 10
        else:
            effective_days = days_old
        
        # Exponential decay: strength * (0.5 ^ (days / half_life))
        import math
        time_decay = math.pow(0.5, effective_days / self.DECAY_HALF_LIFE_DAYS)
        strength *= time_decay
        
        # Access bonus (rehearsal strengthens memory)
        access_bonus = memory.access_count * self.DECAY_ACCESS_BONUS
        strength += access_bonus
        
        # Recent memories get a boost
        if days_old < 1:  # Less than a day old
            strength *= 1.5  # 50% boost for very recent memories
        elif days_old < 7:  # Less than a week
            strength *= 1.2  # 20% boost for recent memories
        
        return min(strength, 1.0)  # Cap at 1.0
    
    def _apply_decay(self):
        """
        Apply memory decay - forget weak memories.
        Called periodically to clean up old/unused memories.
        """
        if not self.memories:
            return
        
        original_count = len(self.memories)
        
        # Calculate strength for each memory
        memory_strengths = []
        for memory in self.memories:
            strength = self._calculate_memory_strength(memory)
            memory_strengths.append((memory, strength))
        
        # Keep only memories above minimum strength
        # But always keep at least 10 most recent memories
        sorted_by_strength = sorted(
            memory_strengths,
            key=lambda x: (x[1], x[0].timestamp),
            reverse=True
        )
        
        # Keep top memories by strength
        strong_memories = []
        for memory, strength in sorted_by_strength:
            if strength >= self.DECAY_MIN_STRENGTH:
                strong_memories.append(memory)
        
        # Always keep at least 10 most recent (even if weak)
        recent_memories = sorted(
            self.memories,
            key=lambda m: m.timestamp,
            reverse=True
        )[:10]
        
        # Combine strong + recent (avoiding duplicates)
        memory_ids = {m.memory_id for m in strong_memories}
        for memory in recent_memories:
            if memory.memory_id not in memory_ids:
                strong_memories.append(memory)
        
        self.memories = strong_memories
        
        if len(self.memories) < original_count:
            print(f"🧠 Memory decay applied: {original_count} → {len(self.memories)} memories")
            self._save_memories()
    
    def access_memory(self, memory_id: str):
        """
        Access a memory - strengthens it (rehearsal effect).
        Called when a memory is retrieved/used.
        """
        for memory in self.memories:
            if memory.memory_id == memory_id:
                memory.access_count += 1
                memory.last_accessed = datetime.now().isoformat()
                # Accessing slightly boosts importance
                memory.importance_score = min(memory.importance_score + 0.02, 1.0)
                self._save_memories()
                return True
        return False
    
    def find_relevant_memories(
        self,
        query: str,
        session_id: str = None,
        limit: int = 5
    ) -> List[SemanticMemory]:
        """
        Find memories relevant to a query.
        Also strengthens accessed memories (rehearsal effect).
        """
        query_lower = query.lower()
        scored = []
        
        for memory in self.memories:
            score = 0
            
            # Topic overlap
            for topic in memory.topics:
                if topic.lower() in query_lower:
                    score += 0.3
            
            # Intent similarity
            if any(word in memory.user_intent.lower() for word in query_lower.split()):
                score += 0.2
            
            # Current memory strength (applies decay)
            current_strength = self._calculate_memory_strength(memory)
            score += current_strength * 0.4  # Strength is important!
            
            # Same session context
            if session_id and memory.session_id == session_id:
                score += 0.1
            
            # Recent access bonus (working memory effect)
            if memory.last_accessed:
                from datetime import datetime
                last_access = datetime.fromisoformat(memory.last_accessed)
                minutes_since = (datetime.now() - last_access).total_seconds() / 60
                if minutes_since < 30:  # Accessed in last 30 minutes
                    score += 0.2
            
            if score > 0.3:
                scored.append((memory, score))
        
        # Sort by score
        scored.sort(key=lambda x: x[1], reverse=True)
        
        # Get top memories
        top_memories = scored[:limit]
        
        # Strengthen accessed memories (rehearsal)
        for memory, _ in top_memories:
            self.access_memory(memory.memory_id)
        
        return [m for m, _ in top_memories]
    
    def get_successful_approaches(self, topic: str = None) -> List[Dict]:
        """Get approaches that have worked well in the past."""
        successful = [
            m for m in self.memories
            if m.sentiment >= 4 and m.what_worked
        ]
        
        if topic:
            successful = [
                m for m in successful
                if topic.lower() in [t.lower() for t in m.topics]
            ]
        
        # Sort by importance and recency
        successful.sort(key=lambda m: (m.importance_score, m.timestamp), reverse=True)
        
        return [
            {
                "approach": m.approach_taken,
                "what_worked": m.what_worked,
                "context": m.user_intent[:100],
                "sentiment": m.sentiment
            }
            for m in successful[:10]
        ]
    
    def get_user_preferences_summary(self) -> Dict:
        """Generate a summary of user preferences from memories."""
        preferences = {
            "preferred_approaches": [],
            "successful_formats": [],
            "topics_of_interest": [],
            "communication_style": ""
        }
        
        # Analyze what approaches worked
        approach_counts = {}
        for m in self.memories:
            if m.sentiment >= 4:
                approach = m.approach_taken
                approach_counts[approach] = approach_counts.get(approach, 0) + 1
                
                for worked in m.what_worked:
                    if worked not in preferences["preferred_approaches"]:
                        preferences["preferred_approaches"].append(worked)
        
        # Get top approaches
        sorted_approaches = sorted(
            approach_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )
        preferences["successful_formats"] = [a for a, _ in sorted_approaches[:3]]
        
        # Topics
        all_topics = []
        for m in self.memories:
            all_topics.extend(m.topics)
        preferences["topics_of_interest"] = list(set(all_topics))[:10]
        
        return preferences


# Singleton instance
_semantic_memory_store: Optional[SemanticMemoryStore] = None


def get_semantic_memory_store() -> SemanticMemoryStore:
    """Get the singleton semantic memory store."""
    global _semantic_memory_store
    if _semantic_memory_store is None:
        _semantic_memory_store = SemanticMemoryStore()
    return _semantic_memory_store
