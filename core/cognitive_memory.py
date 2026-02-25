"""
Cognitive Memory System for IDE Agent Wizard
============================================
Human-like memory architecture with:
- Episodic Memory: Events and experiences (with embeddings and VAD emotions)
- Semantic Memory: Knowledge graph with entities and relationships
- Procedural Memory: Successful patterns and skills

Based on cognitive science research and modern Knowledge Graph patterns.
Enhanced with features from ide-agent-builder (KimiMind):
- Semantic embeddings (384-dim) for similarity search
- VAD emotional model (Valence-Arousal-Dominance)
- Exponential decay with configurable half-life
- Automatic archival system
"""

import json
import re
import math
import hashlib
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
import pickle
import random
import string

# Try to import sentence-transformers for embeddings
try:
    from sentence_transformers import SentenceTransformer
    EMBEDDING_MODEL_AVAILABLE = True
except ImportError:
    EMBEDDING_MODEL_AVAILABLE = False
    print("⚠️ sentence-transformers not available. Using simple hash-based embeddings.")


# ============================================================================
# MEMORY TYPES (Cognitive Model)
# ============================================================================

class MemoryType(Enum):
    EPISODIC = "episodic"      # Events, experiences
    SEMANTIC = "semantic"      # Facts, concepts
    PROCEDURAL = "procedural"  # Skills, patterns


class EntityType(Enum):
    PERSON = "Person"
    COMPANY = "Company"
    TECHNOLOGY = "Technology"
    TOPIC = "Topic"
    PROJECT = "Project"
    CONVERSATION = "Conversation"
    PATTERN = "Pattern"


class RelationshipType(Enum):
    # Professional
    WORKS_AT = "WORKS_AT"
    WORKED_ON = "WORKED_ON"
    
    # Knowledge
    KNOWS = "KNOWS"
    LEARNING = "LEARNING"
    PREFERS = "PREFERS"
    DISLIKES = "DISLIKES"
    
    # Interest
    INTERESTED_IN = "INTERESTED_IN"
    RELATED_TO = "RELATED_TO"
    
    # Interaction
    PARTICIPATED_IN = "PARTICIPATED_IN"
    MENTIONS = "MENTIONS"
    ABOUT = "ABOUT"
    FOLLOWED_BY = "FOLLOWED_BY"
    
    # Procedural
    RESPONDS_WELL_TO = "RESPONDS_WELL_TO"
    SIMILAR_TO = "SIMILAR_TO"


# ============================================================================
# DATA MODELS
# ============================================================================

@dataclass
class Entity:
    """A node in the knowledge graph."""
    id: str
    type: str  # EntityType value
    name: str
    properties: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> "Entity":
        return cls(**data)


@dataclass
class Relationship:
    """An edge in the knowledge graph."""
    id: str
    type: str  # RelationshipType value
    source_id: str
    target_id: str
    properties: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    strength: float = 1.0  # 0-1, affects decay
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> "Relationship":
        return cls(**data)


@dataclass
class EpisodicMemory:
    """
    Specific event/interaction memory with embeddings and VAD emotions.
    (Who, What, When, Where, Emotional context, Semantic vector)
    """
    # === REQUIRED FIELDS (no defaults) ===
    memory_id: str
    timestamp: str
    session_id: str
    
    # Event details
    user_message: str
    assistant_message: str
    summary: str
    
    # Context
    entities_involved: List[str]  # IDs of entities
    topics: List[str]
    technologies: List[str]
    
    # Legacy emotional context
    sentiment: int  # 1-5
    user_state: str  # frustrated, learning, expert, etc.
    
    # Outcome (required)
    successful: bool
    outcome_description: str
    
    # === OPTIONAL FIELDS (with defaults) ===
    # VAD Emotional Model (3-dimensional emotion representation)
    emotion_valence: float = 0.0
    emotion_arousal: float = 0.5
    emotion_dominance: float = 0.5
    emotion_label: str = "neutral"
    
    # Semantic embedding (384-dim vector for similarity search)
    embedding: Optional[List[float]] = None
    embedding_model: str = ""
    
    # Metadata for decay
    importance: float = 0.5
    base_importance: float = 0.5
    decay_rate: float = 0.5
    access_count: int = 0
    last_accessed: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    # Archive status
    archived: bool = False
    archived_at: Optional[str] = None
    archive_reason: str = ""
    
    # Consolidation status
    consolidated: bool = False
    consolidated_at: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> "EpisodicMemory":
        # Handle legacy data migration
        if "consolidated" not in data:
            data["consolidated"] = False
        if "consolidated_at" not in data:
            data["consolidated_at"] = None
        # New VAD emotion fields
        if "emotion_valence" not in data:
            # Convert legacy sentiment (1-5) to valence (-1 to 1)
            sentiment = data.get("sentiment", 3)
            data["emotion_valence"] = (sentiment - 3) / 2.0  # 1->-1, 3->0, 5->1
            data["emotion_arousal"] = 0.5
            data["emotion_dominance"] = 0.5
            data["emotion_label"] = "neutral"
        # New embedding fields
        if "embedding" not in data:
            data["embedding"] = None
            data["embedding_model"] = ""
        # New decay fields
        if "base_importance" not in data:
            data["base_importance"] = data.get("importance", 0.5)
            data["decay_rate"] = 0.5
        # New archive fields
        if "archived" not in data:
            data["archived"] = False
            data["archived_at"] = None
            data["archive_reason"] = ""
        if "created_at" not in data:
            data["created_at"] = data.get("timestamp", datetime.now().isoformat())
        return cls(**data)


@dataclass
class ProceduralMemory:
    """
    "What works" memory - skills and patterns.
    Context → Action → Result
    """
    memory_id: str
    timestamp: str
    
    # Pattern definition
    context_pattern: str  # When this applies
    action_taken: str     # What was done
    result: str          # What happened
    
    # Success metrics
    success_rate: float  # 0-1
    usage_count: int
    
    # Metadata
    related_entities: List[str]
    examples: List[str]  # Episode IDs where this worked
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> "ProceduralMemory":
        return cls(**data)


# ============================================================================
# KNOWLEDGE GRAPH
# ============================================================================

class KnowledgeGraph:
    """
    In-memory knowledge graph for entities and relationships.
    Can be backed by Kuzu or Neo4j for persistence.
    """
    
    def __init__(self):
        self.entities: Dict[str, Entity] = {}
        self.relationships: Dict[str, Relationship] = {}
        self.entity_index_by_type: Dict[str, List[str]] = {}
        self.entity_index_by_name: Dict[str, str] = {}  # name -> id
    
    def add_entity(self, entity: Entity) -> Entity:
        """Add or update an entity."""
        # Check if entity with same name/type already exists
        existing_id = self.entity_index_by_name.get(f"{entity.type}:{entity.name.lower()}")
        
        if existing_id and existing_id in self.entities:
            # Merge properties
            existing = self.entities[existing_id]
            existing.properties.update(entity.properties)
            existing.updated_at = datetime.now().isoformat()
            return existing
        
        # New entity
        self.entities[entity.id] = entity
        
        # Update indexes
        if entity.type not in self.entity_index_by_type:
            self.entity_index_by_type[entity.type] = []
        self.entity_index_by_type[entity.type].append(entity.id)
        self.entity_index_by_name[f"{entity.type}:{entity.name.lower()}"] = entity.id
        
        return entity
    
    def get_entity(self, entity_id: str) -> Optional[Entity]:
        """Get entity by ID."""
        return self.entities.get(entity_id)
    
    def find_entity_by_name(self, entity_type: str, name: str) -> Optional[Entity]:
        """Find entity by type and name."""
        entity_id = self.entity_index_by_name.get(f"{entity_type}:{name.lower()}")
        if entity_id:
            return self.entities.get(entity_id)
        return None
    
    def add_relationship(self, rel: Relationship) -> Relationship:
        """Add a relationship between entities."""
        rel_id = f"{rel.source_id}-{rel.type}-{rel.target_id}"
        rel.id = rel_id
        self.relationships[rel_id] = rel
        return rel
    
    def get_relationships(self, entity_id: str, rel_type: str = None) -> List[Relationship]:
        """Get all relationships for an entity."""
        rels = []
        for rel in self.relationships.values():
            if rel.source_id == entity_id or rel.target_id == entity_id:
                if rel_type is None or rel.type == rel_type:
                    rels.append(rel)
        return rels
    
    def get_neighbors(self, entity_id: str, rel_type: str = None) -> List[Tuple[Entity, Relationship]]:
        """Get neighboring entities with their relationships."""
        neighbors = []
        for rel in self.relationships.values():
            if rel.source_id == entity_id:
                target = self.entities.get(rel.target_id)
                if target and (rel_type is None or rel.type == rel_type):
                    neighbors.append((target, rel))
            elif rel.target_id == entity_id:
                source = self.entities.get(rel.source_id)
                if source and (rel_type is None or rel.type == rel_type):
                    neighbors.append((source, rel))
        return neighbors
    
    def find_path(self, start_id: str, end_id: str, max_depth: int = 3) -> List[List[Relationship]]:
        """Find paths between two entities (multi-hop reasoning)."""
        paths = []
        visited = set()
        
        def dfs(current_id: str, target_id: str, path: List[Relationship], depth: int):
            if depth > max_depth:
                return
            if current_id == target_id:
                paths.append(path.copy())
                return
            if current_id in visited:
                return
            
            visited.add(current_id)
            
            for rel in self.relationships.values():
                if rel.source_id == current_id and rel.target_id not in visited:
                    path.append(rel)
                    dfs(rel.target_id, target_id, path, depth + 1)
                    path.pop()
                elif rel.target_id == current_id and rel.source_id not in visited:
                    path.append(rel)
                    dfs(rel.source_id, target_id, path, depth + 1)
                    path.pop()
            
            visited.remove(current_id)
        
        dfs(start_id, end_id, [], 0)
        return paths
    
    def get_related_entities(self, entity_id: str, max_depth: int = 2) -> List[Entity]:
        """Get all entities within N hops."""
        related = set()
        current_level = {entity_id}
        
        for _ in range(max_depth):
            next_level = set()
            for eid in current_level:
                for rel in self.relationships.values():
                    if rel.source_id == eid:
                        next_level.add(rel.target_id)
                    if rel.target_id == eid:
                        next_level.add(rel.source_id)
            related.update(next_level)
            current_level = next_level
        
        related.discard(entity_id)  # Remove self
        return [self.entities[eid] for eid in related if eid in self.entities]
    
    def to_dict(self) -> Dict:
        return {
            "entities": {k: v.to_dict() for k, v in self.entities.items()},
            "relationships": {k: v.to_dict() for k, v in self.relationships.items()}
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "KnowledgeGraph":
        kg = cls()
        for entity_data in data.get("entities", {}).values():
            kg.add_entity(Entity.from_dict(entity_data))
        for rel_data in data.get("relationships", {}).values():
            kg.add_relationship(Relationship.from_dict(rel_data))
        return kg


# ============================================================================
# EMBEDDING GENERATOR (Semantic Vectors)
# ============================================================================

class EmbeddingGenerator:
    """
    Generate semantic embeddings for memory similarity search.
    
    Uses sentence-transformers if available, otherwise falls back to
    simple TF-IDF-like hash-based embeddings.
    """
    
    EMBEDDING_DIM = 384  # Standard for all-MiniLM-L6-v2
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model = None
        self.model_name = model_name
        
        if EMBEDDING_MODEL_AVAILABLE:
            try:
                self.model = SentenceTransformer(model_name)
                print(f"✅ Loaded embedding model: {model_name}")
            except Exception as e:
                print(f"⚠️ Failed to load {model_name}: {e}. Using fallback.")
    
    def generate(self, text: str) -> List[float]:
        """Generate embedding vector for text."""
        if self.model is not None:
            # Use sentence-transformers
            embedding = self.model.encode(text, convert_to_tensor=False)
            return embedding.tolist()
        else:
            # Fallback: simple hash-based embedding
            return self._fallback_embedding(text)
    
    def _fallback_embedding(self, text: str) -> List[float]:
        """
        Simple hash-based embedding when model not available.
        Creates deterministic vectors based on character n-grams.
        """
        text = text.lower()
        embedding = [0.0] * self.EMBEDDING_DIM
        
        # Character trigrams
        for i in range(len(text) - 2):
            trigram = text[i:i+3]
            hash_val = hash(trigram) % self.EMBEDDING_DIM
            embedding[hash_val] += 1.0
        
        # Normalize
        norm = math.sqrt(sum(x**2 for x in embedding))
        if norm > 0:
            embedding = [x / norm for x in embedding]
        
        return embedding
    
    @staticmethod
    def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        if len(vec1) != len(vec2):
            return 0.0
        
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = math.sqrt(sum(a * a for a in vec1))
        norm2 = math.sqrt(sum(b * b for b in vec2))
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
    
    def find_similar(self, query: str, memories: List[Any], 
                     threshold: float = 0.6, top_k: int = 5) -> List[Tuple[Any, float]]:
        """
        Find memories similar to query text.
        
        Args:
            query: Search query
            memories: List of memory objects (must have 'embedding' attribute)
            threshold: Minimum similarity score (0-1)
            top_k: Maximum number of results
        
        Returns:
            List of (memory, similarity_score) tuples, sorted by similarity
        """
        query_embedding = self.generate(query)
        
        similarities = []
        for memory in memories:
            if hasattr(memory, 'embedding') and memory.embedding:
                sim = self.cosine_similarity(query_embedding, memory.embedding)
                if sim >= threshold:
                    similarities.append((memory, sim))
        
        # Sort by similarity (descending)
        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:top_k]


# ============================================================================
# EMOTION ANALYZER (VAD Model)
# ============================================================================

class EmotionAnalyzer:
    """
    Analyze emotional content using VAD (Valence-Arousal-Dominance) model.
    
    Based on Russell's circumplex model of affect.
    - Valence: negative (-1) to positive (+1)
    - Arousal: calm/sleepy (0) to excited/alert (1)
    - Dominance: submissive/controlled (0) to dominant/in-control (1)
    """
    
    # Simple keyword-based analysis (can be replaced with ML model)
    POSITIVE_WORDS = {'good', 'great', 'excellent', 'amazing', 'love', 'happy', 
                      'perfect', 'awesome', 'fantastic', 'wonderful', 'best',
                      'success', 'solved', 'working', 'done', 'ready', 'yes'}
    NEGATIVE_WORDS = {'bad', 'terrible', 'awful', 'hate', 'angry', 'sad',
                      'error', 'problem', 'issue', 'bug', 'fail', 'broken',
                      'wrong', 'not working', 'stuck', 'help', 'urgent'}
    HIGH_AROUSAL_WORDS = {'urgent', 'critical', 'emergency', 'excited', 'wow',
                          'amazing', 'shocked', 'surprised', 'panic', 'hurry'}
    LOW_AROUSAL_WORDS = {'calm', 'relaxed', 'sleepy', 'bored', 'tired', 'slow'}
    DOMINANCE_WORDS = {'need', 'want', 'must', 'should', 'decide', 'choose',
                       'control', 'manage', 'lead', 'create', 'build'}
    SUBMISSION_WORDS = {'help', 'please', 'can you', 'would you', 'maybe',
                        'not sure', 'confused', 'lost', 'don\'t know'}
    
    @classmethod
    def analyze(cls, text: str) -> Tuple[float, float, float, str]:
        """
        Analyze text and return VAD scores + emotion label.
        
        Returns:
            (valence, arousal, dominance, emotion_label)
        """
        text_lower = text.lower()
        words = set(text_lower.split())
        
        # Valence (positive/negative)
        pos_count = sum(1 for w in cls.POSITIVE_WORDS if w in text_lower)
        neg_count = sum(1 for w in cls.NEGATIVE_WORDS if w in text_lower)
        valence = (pos_count - neg_count) / max(pos_count + neg_count, 1)
        # Clamp to [-1, 1]
        valence = max(-1.0, min(1.0, valence))
        
        # Arousal (calm/excited)
        high_count = sum(1 for w in cls.HIGH_AROUSAL_WORDS if w in text_lower)
        low_count = sum(1 for w in cls.LOW_AROUSAL_WORDS if w in text_lower)
        arousal = 0.5 + (high_count - low_count) / max(high_count + low_count + 2, 1)
        arousal = max(0.0, min(1.0, arousal))
        
        # Dominance (submissive/dominant)
        dom_count = sum(1 for w in cls.DOMINANCE_WORDS if w in text_lower)
        sub_count = sum(1 for w in cls.SUBMISSION_WORDS if w in text_lower)
        dominance = 0.5 + (dom_count - sub_count) / max(dom_count + sub_count + 2, 1)
        dominance = max(0.0, min(1.0, dominance))
        
        # Label emotion
        emotion_label = cls._label_emotion(valence, arousal, dominance)
        
        return valence, arousal, dominance, emotion_label
    
    @staticmethod
    def _label_emotion(valence: float, arousal: float, dominance: float) -> str:
        """Map VAD to emotion label."""
        if arousal > 0.7:
            if valence > 0.3:
                return "excited"
            elif valence < -0.3:
                return "angry"
            else:
                return "alert"
        elif arousal < 0.3:
            if valence > 0.3:
                return "content"
            elif valence < -0.3:
                return "sad"
            else:
                return "calm"
        else:  # medium arousal
            if valence > 0.5:
                return "happy"
            elif valence < -0.5:
                return "unhappy"
            else:
                return "neutral"


# ============================================================================
# MEMORY DECAY SYSTEM
# ============================================================================

class MemoryDecayConfig:
    """Configuration for memory decay."""
    EPISODIC_HALF_LIFE_DAYS = 30
    SEMANTIC_HALF_LIFE_DAYS = 90
    PROCEDURAL_HALF_LIFE_DAYS = 365
    
    CONSOLIDATION_THRESHOLD = 0.8  # Importance + sentiment
    MIN_STRENGTH_TO_KEEP = 0.1
    ACCESS_BONUS = 0.05


class MemoryDecayCalculator:
    """
    Advanced decay calculator inspired by ide-agent-builder (KimiMind).
    
    Features:
    - Exponential decay with configurable half-life
    - Access boost factor (rehearsal strengthens memory)
    - Archive threshold for automatic archival
    - Emotion-based decay modulation (emotional memories last longer)
    """
    
    # From ide-agent-builder
    HALF_LIFE_BASE_DAYS = 180  # days for decay_rate=1.0 to reach 50%
    ARCHIVE_THRESHOLD = 0.1    # importance below this gets archived
    ACCESS_BOOST_FACTOR = 0.15  # 15% boost per access
    MAX_BOOST_ACCESSES = 10    # cap access boost at 10 accesses
    
    EMOTIONAL_MEMORY_BONUS = 0.2  # high arousal/emotion memories decay slower
    
    @staticmethod
    def calculate_lambda(decay_rate: float) -> float:
        """Calculate decay constant lambda from decay rate."""
        if decay_rate <= 0.0:
            return 0.0
        # Higher decay_rate = shorter half-life = faster decay
        half_life = MemoryDecayCalculator.HALF_LIFE_BASE_DAYS / (decay_rate * 2)
        return math.log(2) / half_life
    
    @classmethod
    def calculate_episodic_strength(cls, memory: EpisodicMemory, 
                                    apply_decay: bool = True) -> float:
        """
        Calculate current strength of episodic memory with full decay model.
        
        Args:
            memory: The episodic memory to evaluate
            apply_decay: If True, apply time-based decay; if False, use base importance
        
        Returns:
            Current strength (0.0 to 1.0+)
        """
        if not apply_decay:
            return memory.importance
        
        # Start with base importance
        base_strength = memory.base_importance
        
        # Calculate time decay
        last_access = datetime.fromisoformat(
            memory.last_accessed if memory.last_accessed else memory.created_at
        )
        now = datetime.now()
        days_delta = (now - last_access).total_seconds() / 86400
        
        # Exponential decay: S = S0 * e^(-lambda * t)
        lambda_val = cls.calculate_lambda(memory.decay_rate)
        decay_factor = math.exp(-lambda_val * days_delta)
        current_strength = base_strength * decay_factor
        
        # Apply access boost (rehearsal effect)
        # Each access adds ACCESS_BOOST_FACTOR, capped at MAX_BOOST_ACCESSES
        capped_accesses = min(memory.access_count, cls.MAX_BOOST_ACCESSES)
        access_boost = 1.0 + (capped_accesses * cls.ACCESS_BOOST_FACTOR)
        current_strength *= access_boost
        
        # Emotional memory bonus (high arousal = stronger encoding)
        # VAD model: high arousal memories are more salient
        if memory.emotion_arousal > 0.7 or abs(memory.emotion_valence) > 0.6:
            current_strength *= (1.0 + cls.EMOTIONAL_MEMORY_BONUS)
        
        # Consolidated memories resist decay
        if memory.consolidated:
            current_strength *= 1.3
        
        # Recency bonus (last 24 hours)
        if days_delta < 1:
            current_strength *= 1.2
        
        return min(current_strength, 2.0)  # Allow >1.0 for very strong memories
    
    @classmethod
    def should_archive(cls, memory: EpisodicMemory) -> Tuple[bool, str]:
        """
        Determine if memory should be archived.
        
        Returns:
            (should_archive, reason)
        """
        # Already archived
        if memory.archived:
            return False, "already_archived"
        
        # Calculate current strength
        strength = cls.calculate_episodic_strength(memory)
        
        # Archive if below threshold
        if strength < cls.ARCHIVE_THRESHOLD:
            return True, f"decay (strength={strength:.3f} < {cls.ARCHIVE_THRESHOLD})"
        
        # Archive very old unaccessed memories (1+ year, no accesses)
        created = datetime.fromisoformat(memory.created_at)
        days_old = (datetime.now() - created).days
        if days_old > 365 and memory.access_count == 0:
            return True, f"old_and_unused ({days_old} days, 0 accesses)"
        
        return False, ""
    
    @classmethod
    def access_memory(cls, memory: EpisodicMemory) -> float:
        """
        Record access to memory and return new strength.
        Updates access_count and last_accessed.
        """
        memory.access_count += 1
        memory.last_accessed = datetime.now().isoformat()
        return cls.calculate_episodic_strength(memory)
    
    @staticmethod
    def calculate_relationship_strength(rel: Relationship) -> float:
        """Calculate current strength of a relationship (slower decay)."""
        config = MemoryDecayConfig()
        
        strength = rel.strength
        
        # Time decay (slower than episodic - semantic memories last longer)
        rel_time = datetime.fromisoformat(rel.created_at)
        days_old = (datetime.now() - rel_time).days
        time_decay = 0.5 ** (days_old / config.SEMANTIC_HALF_LIFE_DAYS)
        strength *= time_decay
        
        return min(strength, 1.0)


# ============================================================================
# ENTITY EXTRACTION (NLP)
# ============================================================================

class EntityExtractor:
    """Extract entities from text using patterns and heuristics."""
    
    # Technology keywords
    TECH_PATTERNS = [
        r'\b(React|Vue|Angular|Svelte|Next\.js|Nuxt|Gatsby)\b',
        r'\b(Node\.js|Express|Fastify|NestJS|Django|Flask|Rails)\b',
        r'\b(Python|JavaScript|TypeScript|Rust|Go|Java|C\+\+|C#|Ruby)\b',
        r'\b(Docker|Kubernetes|AWS|GCP|Azure|Terraform|Ansible)\b',
        r'\b(PostgreSQL|MySQL|MongoDB|Redis|Elasticsearch|DynamoDB)\b',
        r'\b(GraphQL|REST|gRPC|WebSocket|WebRTC)\b',
        r'\b(TensorFlow|PyTorch|scikit-learn|OpenAI|LangChain)\b',
    ]
    
    # Company patterns
    COMPANY_INDICATORS = [
        r'(?:trabalho na|work at|work for)\s+([A-Z][\w\s]+?)(?:\.|,|$)',
        r'(?:minha empresa|my company)\s+(?:é|eh|is)?\s*([A-Z][\w\s]+?)(?:\.|,|$)',
        r'(?:trabalhamos na|we work at)\s+([A-Z][\w\s]+?)(?:\.|,|$)',
    ]
    
    # Role patterns
    ROLE_PATTERNS = [
        r'(?:sou|eu sou|I am|trabalho como|work as)\s+(?:um|uma|an|a)?\s*([\w\s]+?(?:engineer|developer|architect|manager|lead|designer|analyst))',
        r'(?:meu cargo|my role|minha função)\s+(?:é|eh|is)?\s*([\w\s]+)',
    ]
    
    @classmethod
    def extract_entities(cls, text: str) -> Dict[str, List[Dict]]:
        """Extract all types of entities from text (with deduplication)."""
        entities = {
            "technologies": [],
            "companies": [],
            "roles": [],
            "topics": []
        }
        
        # Sets to track already added entities (normalized names)
        seen_techs = set()
        seen_companies = set()
        seen_roles = set()
        seen_topics = set()
        
        text_lower = text.lower()
        
        # Extract technologies
        for pattern in cls.TECH_PATTERNS:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                tech_name = match.strip()
                tech_key = tech_name.lower()
                if tech_key not in seen_techs:
                    seen_techs.add(tech_key)
                    entities["technologies"].append({
                        "name": tech_name,
                        "type": "Technology",
                        "confidence": 0.9
                    })
        
        # Extract companies
        for pattern in cls.COMPANY_INDICATORS:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                company_name = match.strip()
                company_key = company_name.lower()
                if company_key not in seen_companies:
                    seen_companies.add(company_key)
                    entities["companies"].append({
                        "name": company_name,
                        "type": "Company",
                        "confidence": 0.8
                    })
        
        # Extract roles
        for pattern in cls.ROLE_PATTERNS:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                role_name = match.strip()
                role_key = role_name.lower()
                if role_key not in seen_roles:
                    seen_roles.add(role_key)
                    entities["roles"].append({
                        "name": role_name,
                        "type": "Role",
                        "confidence": 0.7
                    })
        
        # Extract topics (nouns that might be topics)
        topic_keywords = [
            "architecture", "microservices", "serverless", "cloud",
            "devops", "ci/cd", "testing", "security", "performance",
            "scalability", "database", "api", "frontend", "backend",
            "machine learning", "ai", "data science", "blockchain"
        ]
        
        for keyword in topic_keywords:
            if keyword in text_lower:
                topic_key = keyword.lower()
                if topic_key not in seen_topics:
                    seen_topics.add(topic_key)
                    entities["topics"].append({
                        "name": keyword,
                        "type": "Topic",
                        "confidence": 0.6
                    })
        
        return entities


# ============================================================================
# MAIN COGNITIVE MEMORY MANAGER
# ============================================================================

class CognitiveMemoryManager:
    """
    Main interface for the cognitive memory system.
    Manages episodic, semantic, and procedural memories.
    
    Enhanced with:
    - Semantic embeddings for similarity search
    - VAD emotional model
    - Automatic archival system
    """
    
    def __init__(self, data_dir: str = "/app/workspace/cognitive_memory"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Storage
        self.knowledge_graph = KnowledgeGraph()
        self.episodic_memories: List[EpisodicMemory] = []
        self.procedural_memories: List[ProceduralMemory] = []
        
        # Embedding generator for semantic search
        self.embedding_generator = EmbeddingGenerator()
        
        # Load existing data
        self._load()
        
        # Run maintenance on load (archive old memories)
        self._maintenance()
    
    def _maintenance(self):
        """Run periodic maintenance: archive old memories."""
        archived_count = 0
        for memory in self.episodic_memories:
            should_archive, reason = MemoryDecayCalculator.should_archive(memory)
            if should_archive and not memory.archived:
                memory.archived = True
                memory.archived_at = datetime.now().isoformat()
                memory.archive_reason = reason
                archived_count += 1
        
        if archived_count > 0:
            print(f"🗄️ Archived {archived_count} old memories")
            self._save()
    
    def _load(self):
        """Load all memory data from disk."""
        # Load knowledge graph
        kg_file = self.data_dir / "knowledge_graph.json"
        if kg_file.exists():
            try:
                with open(kg_file) as f:
                    self.knowledge_graph = KnowledgeGraph.from_dict(json.load(f))
            except Exception as e:
                print(f"Error loading knowledge graph: {e}")
        
        # Load episodic memories
        episodic_file = self.data_dir / "episodic_memories.json"
        if episodic_file.exists():
            try:
                with open(episodic_file) as f:
                    data = json.load(f)
                    self.episodic_memories = [EpisodicMemory.from_dict(m) for m in data]
            except Exception as e:
                print(f"Error loading episodic memories: {e}")
        
        # Load procedural memories
        procedural_file = self.data_dir / "procedural_memories.json"
        if procedural_file.exists():
            try:
                with open(procedural_file) as f:
                    data = json.load(f)
                    self.procedural_memories = [ProceduralMemory.from_dict(m) for m in data]
            except Exception as e:
                print(f"Error loading procedural memories: {e}")
        
        # Apply decay
        self._apply_decay()
        
        # Backfill missing embeddings
        self.backfill_embeddings()
    
    def _save(self):
        """Save all memory data to disk."""
        try:
            with open(self.data_dir / "knowledge_graph.json", 'w') as f:
                json.dump(self.knowledge_graph.to_dict(), f, indent=2)
            
            with open(self.data_dir / "episodic_memories.json", 'w') as f:
                json.dump([m.to_dict() for m in self.episodic_memories], f, indent=2)
            
            with open(self.data_dir / "procedural_memories.json", 'w') as f:
                json.dump([m.to_dict() for m in self.procedural_memories], f, indent=2)
        except Exception as e:
            print(f"Error saving memories: {e}")
    
    def _apply_decay(self):
        """Apply decay to all memories."""
        # Filter episodic memories
        strong_episodic = []
        for mem in self.episodic_memories:
            strength = MemoryDecayCalculator.calculate_episodic_strength(mem)
            if strength >= MemoryDecayConfig.MIN_STRENGTH_TO_KEEP:
                strong_episodic.append(mem)
        
        # Keep at least 10 most recent
        if len(strong_episodic) < 10:
            recent = sorted(self.episodic_memories, key=lambda m: m.timestamp, reverse=True)[:10]
            strong_episodic = list({m.memory_id: m for m in strong_episodic + recent}.values())
        
        if len(strong_episodic) < len(self.episodic_memories):
            print(f"🧠 Episodic memory decay: {len(self.episodic_memories)} → {len(strong_episodic)}")
            self.episodic_memories = strong_episodic
            self._save()

    def backfill_embeddings(self) -> int:
        """Backfill missing semantic embeddings for episodic memories."""
        count = 0
        for ep in self.episodic_memories:
            if ep.embedding is None:
                combined_text = ep.user_message + " " + ep.assistant_message
                ep.embedding = self.embedding_generator.generate(combined_text)
                ep.embedding_model = "sentence-transformers/all-MiniLM-L6-v2" if EMBEDDING_MODEL_AVAILABLE else "fallback-hash"
                count += 1
        
        if count > 0:
            print(f"✅ Backfilled {count} memories with semantic embeddings")
            self._save()
        return count
    
    def store_interaction(
        self,
        user_message: str,
        assistant_message: str,
        session_id: str,
        sentiment: int = 3,
        successful: bool = True
    ) -> EpisodicMemory:
        """
        Store a new interaction in memory.
        This is the main entry point for memory creation.
        
        Enhanced with:
        - VAD emotional analysis
        - Semantic embedding generation
        - Automatic importance and decay rate calculation
        """
        # Extract entities
        combined_text = user_message + " " + assistant_message
        entities = EntityExtractor.extract_entities(combined_text)
        
        # Analyze emotion using VAD model
        valence, arousal, dominance, emotion_label = EmotionAnalyzer.analyze(user_message)
        
        # Generate semantic embedding
        embedding = self.embedding_generator.generate(combined_text)
        
        # Calculate importance and decay rate
        importance, decay_rate = self._calculate_importance_and_decay(
            sentiment, entities, arousal, emotion_label
        )
        
        # Create episodic memory
        episode = EpisodicMemory(
            memory_id=f"ep_{datetime.now().strftime('%Y%m%d%H%M%S')}_{hash(user_message) % 10000}",
            timestamp=datetime.now().isoformat(),
            session_id=session_id,
            user_message=user_message,
            assistant_message=assistant_message,
            summary=self._generate_summary(user_message, assistant_message),
            entities_involved=[],
            topics=[t["name"] for t in entities.get("topics", [])],
            technologies=[t["name"] for t in entities.get("technologies", [])],
            sentiment=sentiment,
            user_state="neutral",
            # VAD emotions
            emotion_valence=valence,
            emotion_arousal=arousal,
            emotion_dominance=dominance,
            emotion_label=emotion_label,
            # Embedding
            embedding=embedding,
            embedding_model="sentence-transformers/all-MiniLM-L6-v2" if EMBEDDING_MODEL_AVAILABLE else "fallback-hash",
            # Outcome
            successful=successful,
            outcome_description="completed" if successful else "incomplete",
            # Decay metadata
            importance=importance,
            base_importance=importance,
            decay_rate=decay_rate,
            created_at=datetime.now().isoformat()
        )
        
        # Add to knowledge graph
        entity_ids = self._add_entities_to_graph(entities, episode.memory_id)
        episode.entities_involved = entity_ids
        
        # Learn procedural patterns if successful
        if successful and sentiment >= 4:
            self._learn_pattern(user_message, assistant_message, session_id, episode.memory_id)
        
        # Store episode
        self.episodic_memories.append(episode)
        self._save()
        
        return episode
    
    def _calculate_importance_and_decay(self, sentiment: int, entities: Dict, 
                                        arousal: float, emotion_label: str) -> Tuple[float, float]:
        """
        Calculate importance and decay rate for a memory.
        
        Returns:
            (importance, decay_rate)
        """
        # Base importance
        importance = 0.5
        
        # Sentiment contribution (-0.2 to +0.2)
        importance += (sentiment - 3) * 0.1
        
        # Entity richness (0 to +0.2)
        total_entities = sum(len(v) for v in entities.values())
        importance += min(total_entities * 0.05, 0.2)
        
        # Emotional arousal boost (high arousal = more important)
        if arousal > 0.7:
            importance += 0.1
        
        # Technical content boost
        tech_count = len(entities.get("technologies", []))
        if tech_count >= 2:
            importance += 0.05 * min(tech_count, 4)
        
        importance = min(max(importance, 0.1), 1.0)
        
        # Decay rate: inverse of importance (important memories decay slower)
        # Range: 0.1 (slow decay) to 1.0 (fast decay)
        decay_rate = 1.0 - importance
        
        # Emotional memories decay slower
        if arousal > 0.7 or abs(emotion_label) > 0.6:
            decay_rate *= 0.7  # 30% slower decay
        
        return importance, decay_rate
    
    def _generate_summary(self, user_msg: str, assistant_msg: str) -> str:
        """Generate a brief summary of the interaction."""
        # Simple heuristic: first sentence or first 100 chars
        combined = f"User: {user_msg[:50]}... Assistant: {assistant_msg[:50]}..."
        return combined
    
    def _calculate_importance(self, sentiment: int, entities: Dict) -> float:
        """Calculate importance score for an interaction."""
        importance = 0.5  # Base
        
        # Sentiment contribution
        importance += (sentiment - 3) * 0.1
        
        # Entity richness
        total_entities = sum(len(v) for v in entities.values())
        importance += min(total_entities * 0.05, 0.2)
        
        return min(max(importance, 0), 1.0)
    
    def _add_entities_to_graph(self, entities: Dict, episode_id: str) -> List[str]:
        """Add extracted entities to knowledge graph."""
        entity_ids = []
        
        # Helper to add entity
        def add_entity(entity_type: str, name: str, properties: Dict = None):
            entity_id = f"{entity_type.lower()}_{name.lower().replace(' ', '_')}"
            entity = Entity(
                id=entity_id,
                type=entity_type,
                name=name,
                properties=properties or {}
            )
            self.knowledge_graph.add_entity(entity)
            
            # Link to conversation
            self.knowledge_graph.add_relationship(Relationship(
                id="",
                type=RelationshipType.MENTIONS.value,
                source_id=episode_id,
                target_id=entity_id,
                properties={"timestamp": datetime.now().isoformat()}
            ))
            
            return entity_id
        
        # Add technologies
        for tech in entities.get("technologies", []):
            eid = add_entity("Technology", tech["name"], {"confidence": tech["confidence"]})
            entity_ids.append(eid)
        
        # Add companies
        for company in entities.get("companies", []):
            eid = add_entity("Company", company["name"], {"confidence": company["confidence"]})
            entity_ids.append(eid)
        
        # Add topics
        for topic in entities.get("topics", []):
            eid = add_entity("Topic", topic["name"], {"confidence": topic["confidence"]})
            entity_ids.append(eid)
        
        return entity_ids
    
    def _learn_pattern(self, user_msg: str, assistant_msg: str, session_id: str, episode_id: str):
        """Learn procedural patterns from successful interactions."""
        # Simple pattern: context + approach
        context = user_msg[:50]
        approach = "code_examples" if "```" in assistant_msg else "explanation"
        
        # Check if similar pattern exists
        for pattern in self.procedural_memories:
            if pattern.context_pattern == context and pattern.action_taken == approach:
                pattern.usage_count += 1
                pattern.examples.append(episode_id)
                pattern.success_rate = min(pattern.success_rate + 0.05, 1.0)
                return
        
        # New pattern
        new_pattern = ProceduralMemory(
            memory_id=f"proc_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            timestamp=datetime.now().isoformat(),
            context_pattern=context,
            action_taken=approach,
            result="successful",
            success_rate=1.0,
            usage_count=1,
            related_entities=[],
            examples=[episode_id]
        )
        
        self.procedural_memories.append(new_pattern)
    
    def retrieve_context(self, query: str, session_id: str = None, limit: int = 5) -> Dict:
        """
        Retrieve relevant context for a query.
        Combines episodic (semantic similarity), semantic (entity), and procedural memories.
        
        Enhanced with:
        - Semantic embedding similarity search
        - Combined keyword + vector scoring
        - Emotional context awareness
        """
        results = {
            "episodic": [],
            "semantic": {"entities": [], "relationships": []},
            "procedural": [],
            "related_topics": [],
            "search_method": "hybrid"  # hybrid = semantic + keyword
        }
        
        # Filter active (non-archived) memories
        active_memories = [m for m in self.episodic_memories if not m.archived]
        
        if session_id:
            active_memories = [m for m in active_memories if m.session_id == session_id]
        
        # 1. SEMANTIC SEARCH with embeddings
        scored_episodes = []
        query_lower = query.lower()
        query_embedding = self.embedding_generator.generate(query)
        
        for episode in active_memories:
            # A. Semantic similarity (embedding cosine similarity)
            semantic_score = 0.0
            if episode.embedding:
                semantic_score = EmbeddingGenerator.cosine_similarity(
                    query_embedding, episode.embedding
                )
            
            # B. Keyword matching (traditional)
            keyword_score = 0.0
            # Topic/technology overlap
            for tech in episode.technologies:
                if tech.lower() in query_lower:
                    keyword_score += 0.3
            for topic in episode.topics:
                if topic.lower() in query_lower:
                    keyword_score += 0.2
            # Content match
            if any(word in episode.user_message.lower() for word in query_lower.split()):
                keyword_score += 0.2
            
            # C. Recency and strength
            strength = MemoryDecayCalculator.calculate_episodic_strength(episode)
            recency_score = strength * 0.3
            
            # D. Emotional resonance (boost if query emotion matches memory emotion)
            emotion_boost = 0.0
            query_valence, query_arousal, _, _ = EmotionAnalyzer.analyze(query)
            if abs(query_valence - episode.emotion_valence) < 0.3:
                emotion_boost = 0.1  # Similar emotional tone
            
            # Combined score (weighted)
            # Give more weight to semantic similarity for longer queries
            if len(query.split()) > 5:
                score = (semantic_score * 0.5) + (keyword_score * 0.3) + recency_score + emotion_boost
            else:
                score = (semantic_score * 0.3) + (keyword_score * 0.5) + recency_score + emotion_boost
            
            if score > 0.15:  # Threshold
                scored_episodes.append((episode, score, {
                    "semantic": semantic_score,
                    "keyword": keyword_score,
                    "strength": strength,
                    "emotion_boost": emotion_boost
                }))
        
        # Sort by score
        scored_episodes.sort(key=lambda x: x[1], reverse=True)
        
        # Add to results with similarity info
        results["episodic"] = []
        for episode, score, breakdown in scored_episodes[:limit]:
            ep_dict = episode.to_dict()
            ep_dict["match_score"] = round(score, 3)
            ep_dict["match_breakdown"] = {k: round(v, 3) for k, v in breakdown.items()}
            results["episodic"].append(ep_dict)
        
        # 2. Knowledge graph lookup (entity-based)
        query_entities = EntityExtractor.extract_entities(query)
        for entity_list in query_entities.values():
            for entity_data in entity_list:
                entity = self.knowledge_graph.find_entity_by_name(
                    entity_data["type"], entity_data["name"]
                )
                if entity:
                    results["semantic"]["entities"].append(entity.to_dict())
                    
                    # Get related entities
                    related = self.knowledge_graph.get_related_entities(entity.id, max_depth=2)
                    results["semantic"]["entities"].extend([e.to_dict() for e in related])
        
        # 3. Procedural patterns
        for pattern in self.procedural_memories:
            if pattern.context_pattern.lower() in query_lower:
                results["procedural"].append(pattern.to_dict())
        
        # Deduplicate entities
        seen_entities = set()
        unique_entities = []
        for e in results["semantic"]["entities"]:
            if e["id"] not in seen_entities:
                seen_entities.add(e["id"])
                unique_entities.append(e)
        results["semantic"]["entities"] = unique_entities
        
        return results
    
    def semantic_search(self, query: str, threshold: float = 0.6, 
                        top_k: int = 5, session_id: str = None) -> List[Tuple[EpisodicMemory, float]]:
        """
        Pure semantic search using embeddings.
        
        Args:
            query: Search query
            threshold: Minimum cosine similarity (0-1)
            top_k: Maximum number of results
            session_id: Filter by session
        
        Returns:
            List of (memory, similarity_score) tuples
        """
        active_memories = [m for m in self.episodic_memories if not m.archived]
        if session_id:
            active_memories = [m for m in active_memories if m.session_id == session_id]
        
        return self.embedding_generator.find_similar(
            query, active_memories, threshold=threshold, top_k=top_k
        )
    
    def get_archived_memories(self, session_id: str = None) -> List[EpisodicMemory]:
        """Get archived memories (for review or restoration)."""
        archived = [m for m in self.episodic_memories if m.archived]
        if session_id:
            archived = [m for m in archived if m.session_id == session_id]
        return archived
    
    def unarchive_memory(self, memory_id: str) -> bool:
        """Restore an archived memory."""
        for m in self.episodic_memories:
            if m.memory_id == memory_id and m.archived:
                m.archived = False
                m.archived_at = None
                m.archive_reason = ""
                m.last_accessed = datetime.now().isoformat()
                self._save()
                return True
        return False
    
    def get_consolidation_preview(self, session_id: str = None, importance_threshold: float = 0.6) -> Dict:
        """
        Preview what would be consolidated without actually doing it.
        
        Args:
            session_id: If provided, only analyze memories from this session
            importance_threshold: Minimum importance score for consolidation
            
        Returns:
            Dict with preview information
        """
        candidates = []
        rejected = []
        all_entities = {"technologies": set(), "topics": set(), "companies": set()}
        
        # Filter memories by session if specified
        memories_to_check = [
            m for m in self.episodic_memories 
            if not session_id or m.session_id == session_id
        ]
        
        for memory in memories_to_check:
            # Check multiple relevance criteria (stricter)
            reasons = []
            
            # Criterion 1: Very high importance (primary criterion)
            if memory.importance >= importance_threshold:
                reasons.append(f"importance {memory.importance:.2f}")
            
            # Criterion 2: Successfully completed with substantial content
            substantial = len(memory.user_message) > 50 and len(memory.assistant_message) > 100
            if memory.successful and substantial:
                reasons.append("successful + substantial")
            
            # Criterion 3: Has REAL entities (technologies, companies, not just generic topics)
            has_real_tech = bool(memory.technologies and len(memory.technologies) > 0)
            has_companies = any('company_' in e for e in memory.entities_involved)
            if has_real_tech or has_companies:
                reasons.append("has tech/companies")
            
            # Criterion 4: Very positive sentiment
            if memory.sentiment >= 4:
                reasons.append("very positive")
            
            # Criterion 5: Has multiple topics (indicates richer conversation)
            rich_content = len(memory.topics or []) >= 2
            if rich_content:
                reasons.append("rich content")
            
            # Calculate score (need 3+ criteria OR very high importance)
            score = (
                (memory.importance >= importance_threshold) + 
                (memory.successful and substantial) + 
                (has_real_tech or has_companies) + 
                (memory.sentiment >= 4) +
                rich_content
            )
            
            # STRICT: Need at least 3 criteria OR importance >= 0.9
            if score >= 3 or memory.importance >= 0.9:
                candidates.append({
                    "memory_id": memory.memory_id,
                    "summary": memory.summary[:100] + "..." if len(memory.summary) > 100 else memory.summary,
                    "importance": memory.importance,
                    "successful": memory.successful,
                    "sentiment": memory.sentiment,
                    "reasons": reasons,
                    "entities_count": len(memory.entities_involved),
                    "technologies": memory.technologies[:3] if memory.technologies else [],
                    "topics": memory.topics[:3] if memory.topics else []
                })
                
                # Collect unique entities (normalized)
                for tech in memory.technologies or []:
                    all_entities["technologies"].add(tech.lower().strip())
                for topic in memory.topics or []:
                    all_entities["topics"].add(topic.lower().strip())
            else:
                rejected.append({
                    "memory_id": memory.memory_id,
                    "summary": memory.summary[:80] + "..." if len(memory.summary) > 80 else memory.summary,
                    "importance": memory.importance,
                    "reason": f"Score {score}/5, need 3+ criteria or importance ≥0.9"
                })
        
        return {
            "session_id": session_id,
            "total_memories": len(memories_to_check),
            "candidates_count": len(candidates),
            "rejected_count": len(rejected),
            "candidates": candidates[:10],  # Show top 10
            "rejected_sample": rejected[:5],  # Show sample of rejected
            "unique_entities": {
                "technologies": sorted(list(all_entities["technologies"]))[:10],
                "topics": sorted(list(all_entities["topics"]))[:10],
                "total_unique": len(all_entities["technologies"]) + len(all_entities["topics"])
            },
            "threshold": importance_threshold
        }
    
    def consolidate_memories(self, session_id: str = None, importance_threshold: float = 0.6) -> List[EpisodicMemory]:
        """
        Consolidate important episodic memories into knowledge graph.
        This is a manual consolidation triggered by the user.
        
        Args:
            session_id: If provided, only consolidate memories from this session
            importance_threshold: Minimum importance score for consolidation
            
        Returns:
            List of consolidated memories
        """
        consolidated = []
        entities_added = {"technologies": set(), "topics": set()}
        
        # Filter memories by session if specified
        memories_to_check = [
            m for m in self.episodic_memories 
            if not session_id or m.session_id == session_id
        ]
        
        for memory in memories_to_check:
            # Check multiple relevance criteria (stricter - same as preview)
            substantial = len(memory.user_message) > 50 and len(memory.assistant_message) > 100
            has_real_tech = bool(memory.technologies and len(memory.technologies) > 0)
            has_companies = any('company_' in e for e in memory.entities_involved)
            rich_content = len(memory.topics or []) >= 2
            
            score = (
                (memory.importance >= importance_threshold) + 
                (memory.successful and substantial) + 
                (has_real_tech or has_companies) + 
                (memory.sentiment >= 4) +
                rich_content
            )
            
            # STRICT: Need at least 3 criteria OR importance >= 0.9
            if score < 3 and memory.importance < 0.9:
                continue
            
            # Re-extract and add entities to knowledge graph
            combined_text = f"{memory.user_message} {memory.assistant_message}"
            entities = EntityExtractor.extract_entities(combined_text)
            
            # Add/update entities in knowledge graph (de-duplicated by normalized name)
            for tech in entities.get("technologies", []):
                # Normalize: lowercase, strip spaces
                tech_name = tech["name"].strip()
                tech_key = tech_name.lower()
                
                # Skip if already added in this run (de-duplication)
                if tech_key in entities_added["technologies"]:
                    continue
                entities_added["technologies"].add(tech_key)
                
                entity_id = f"technology_{tech_key.replace(' ', '_')}"
                entity = Entity(
                    id=entity_id,
                    type="Technology",
                    name=tech_name,  # Keep original casing for display
                    properties={"confidence": tech["confidence"], "consolidated": True, "normalized": tech_key}
                )
                self.knowledge_graph.add_entity(entity)
                
                # Add relationship if not exists
                rel_exists = any(
                    r.source_id == memory.memory_id and r.target_id == entity_id
                    for r in self.knowledge_graph.relationships.values()
                )
                if not rel_exists:
                    self.knowledge_graph.add_relationship(Relationship(
                        id=f"rel_{memory.memory_id}_{entity_id}",
                        type=RelationshipType.MENTIONS.value,
                        source_id=memory.memory_id,
                        target_id=entity_id,
                        properties={"timestamp": datetime.now().isoformat(), "consolidated": True}
                    ))
            
            for topic in entities.get("topics", []):
                # Normalize: lowercase, strip spaces
                topic_name = topic["name"].strip()
                topic_key = topic_name.lower()
                
                # Skip if already added in this run (de-duplication)
                if topic_key in entities_added["topics"]:
                    continue
                entities_added["topics"].add(topic_key)
                
                entity_id = f"topic_{topic_key.replace(' ', '_')}"
                entity = Entity(
                    id=entity_id,
                    type="Topic",
                    name=topic_name,  # Keep original casing for display
                    properties={"confidence": topic["confidence"], "consolidated": True, "normalized": topic_key}
                )
                self.knowledge_graph.add_entity(entity)
                
                rel_exists = any(
                    r.source_id == memory.memory_id and r.target_id == entity_id
                    for r in self.knowledge_graph.relationships.values()
                )
                if not rel_exists:
                    self.knowledge_graph.add_relationship(Relationship(
                        id=f"rel_{memory.memory_id}_{entity_id}",
                        type=RelationshipType.MENTIONS.value,
                        source_id=memory.memory_id,
                        target_id=entity_id,
                        properties={"timestamp": datetime.now().isoformat(), "consolidated": True}
                    ))
            
            # Mark memory as consolidated
            memory.consolidated = True
            memory.consolidated_at = datetime.now().isoformat()
            consolidated.append(memory)
        
        # Save changes
        if consolidated:
            self._save()
            print(f"🧠 Consolidated {len(consolidated)} memories into knowledge graph")
            print(f"   Added {len(entities_added['technologies'])} unique technologies, {len(entities_added['topics'])} unique topics")
        
        return consolidated
    
    def get_stats(self) -> Dict:
        """Get memory system statistics."""
        return {
            "episodic": {
                "total": len(self.episodic_memories),
                "strong": sum(1 for m in self.episodic_memories 
                           if MemoryDecayCalculator.calculate_episodic_strength(m) >= 0.7),
                "weak": sum(1 for m in self.episodic_memories 
                          if MemoryDecayCalculator.calculate_episodic_strength(m) <= 0.3)
            },
            "semantic": {
                "entities": len(self.knowledge_graph.entities),
                "relationships": len(self.knowledge_graph.relationships),
                "by_type": {
                    etype: len(ids) 
                    for etype, ids in self.knowledge_graph.entity_index_by_type.items()
                }
            },
            "procedural": {
                "total": len(self.procedural_memories),
                "high_success": sum(1 for p in self.procedural_memories if p.success_rate >= 0.8)
            }
        }


# Singleton instance
_cognitive_memory_manager: Optional[CognitiveMemoryManager] = None


def get_cognitive_memory_manager() -> CognitiveMemoryManager:
    """Get the singleton cognitive memory manager."""
    global _cognitive_memory_manager
    if _cognitive_memory_manager is None:
        _cognitive_memory_manager = CognitiveMemoryManager()
    return _cognitive_memory_manager
