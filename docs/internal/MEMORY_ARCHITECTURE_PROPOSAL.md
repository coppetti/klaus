# Semantic Memory Architecture Proposal
## Human-like Memory System for AI Agents

Based on cognitive science research and modern Knowledge Graph patterns (GraphRAG, Neo4j).

---

## 1. Memory Types (Cognitive Model)

```
Long-term Memory
├── Explicit (Conscious)
│   ├── Episodic (Events/Experiences)     ← Conversations, interactions
│   └── Semantic (Knowledge/Facts)        ← Entities, concepts, relationships
│
└── Implicit (Unconscious)
    ├── Procedural (Skills/Patterns)      ← What works with this user
    └── Priming (Associations)            ← Related concepts activation
```

### Episodic Memory
- **What**: Specific interactions and events
- **Structure**: (Who, What, When, Where, Emotional context)
- **Decay**: Fast (30 days half-life)
- **Example**: "2024-02-23: User asked about React patterns, provided code examples, user was satisfied"

### Semantic Memory
- **What**: Facts, entities, concepts, relationships
- **Structure**: Knowledge Graph with typed nodes and relationships
- **Decay**: Slow (consolidated memories are stable)
- **Example**: "User knows React, works at Company X, prefers TypeScript"

### Procedural Memory
- **What**: Successful patterns, what works
- **Structure**: (Context → Action → Result)
- **Decay**: Very slow (skills persist)
- **Example**: "When user asks about architecture, provide diagrams + code"

---

## 2. Knowledge Graph Schema

### Node Types (Entities)

```cypher
(:Person {
  name: "User",
  role: "AI Solutions Architect",
  expertise_level: "expert",
  communication_style: "technical",
  first_seen: datetime(),
  last_interaction: datetime()
})

(:Company {
  name: "TechCorp",
  industry: "Software",
  size: "startup"
})

(:Technology {
  name: "React",
  category: "frontend",
  proficiency_level: "expert"
})

(:Topic {
  name: "microservices",
  domain: "architecture",
  related_topics: ["kubernetes", "docker"]
})

(:Project {
  name: "E-commerce Platform",
  status: "in_progress",
  tech_stack: ["React", "Node.js", "PostgreSQL"]
})

(:Conversation {
  id: "conv_001",
  timestamp: datetime(),
  summary: "Discussed React patterns",
  sentiment: 0.8,
  outcome: "successful"
})
```

### Relationship Types

```cypher
// Professional relationships
(:Person)-[:WORKS_AT {since: date(), role: "CTO"}]->(:Company)
(:Person)-[:WORKED_ON {from: date(), to: date()}]->(:Project)

// Knowledge relationships
(:Person)-[:KNOWS {level: "expert", since: date()}]->(:Technology)
(:Person)-[:LEARNING]->(:Technology)
(:Person)-[:PREFERS {strength: 0.9}]->(:Technology)
(:Person)-[:DISLIKES]->(:Technology)

// Interest relationships
(:Person)-[:INTERESTED_IN {level: "high"}]->(:Topic)
(:Topic)-[:RELATED_TO {weight: 0.8}]->(:Topic)

// Interaction relationships
(:Person)-[:PARTICIPATED_IN]->(:Conversation)
(:Conversation)-[:ABOUT]->(:Topic)
(:Conversation)-[:MENTIONS]->(:Technology)
(:Conversation)-[:MENTIONS]->(:Company)

// Temporal relationships
(:Conversation)-[:FOLLOWED_BY]->(:Conversation)
(:Conversation)-[:RELATED_TO]->(:Conversation)

// Procedural (what works)
(:Person)-[:RESPONDS_WELL_TO {
  context: "architecture_questions",
  approach: "diagrams_plus_code",
  success_rate: 0.9
}]->(:InteractionPattern)
```

---

## 3. Memory Decay & Consolidation

### Decay Rules

```python
# Episodic: Fast decay
episodic_decay = lambda days: 0.5 ** (days / 30)  # 30-day half-life

# Semantic: Slow decay (consolidated if important)
semantic_decay = lambda days, importance: (
    0.95 if importance > 0.8  # Consolidated
    else 0.5 ** (days / 90)   # 90-day half-life
)

# Procedural: Very slow decay
procedural_decay = lambda days: 0.5 ** (days / 365)  # 1-year half-life
```

### Consolidation Triggers
- High sentiment (≥4/5) + High importance (≥0.8)
- Repeated access (>3 times)
- Explicit user confirmation ("remember this")

### Forgetting Rules
- Strength < 0.1: Archive (not delete)
- Strength < 0.05: Delete
- Always keep minimum 10 most recent episodic memories

---

## 4. Retrieval Mechanisms

### 1. Graph Traversal (Explicit Context)
```cypher
// What technologies does the user know?
MATCH (u:Person {name: "User"})-[:KNOWS]->(t:Technology)
RETURN t.name, t.level

// What did we discuss about React?
MATCH (u:Person)-[:PARTICIPATED_IN]->(c:Conversation)-[:MENTIONS]->(t:Technology {name: "React"})
RETURN c.summary, c.sentiment
ORDER BY c.timestamp DESC
LIMIT 5
```

### 2. Vector Similarity (Semantic Search)
```python
# Find similar past interactions
query_embedding = embed("How to handle React state?")
similar_memories = vector_search(query_embedding, top_k=5)
```

### 3. Association Chains (Priming)
```cypher
// Activate related concepts
MATCH (t:Technology {name: "React"})-[:RELATED_TO]->(related)
RETURN related.name

// Multi-hop reasoning
MATCH (u:Person)-[:KNOWS]->(t:Technology)-[:RELATED_TO]->(t2:Technology)
WHERE NOT (u)-[:KNOWS]->(t2)
RETURN t2.name as might_be_interested
```

---

## 5. Implementation Architecture

### Storage Layer
```
┌─────────────────────────────────────────────────────┐
│                  STORAGE LAYER                      │
├─────────────────────────────────────────────────────┤
│  SQLite          │  Kuzu Graph      │  Vector DB   │
│  ─────────────   │  ─────────────   │  ──────────  │
│  • Fast queries  │  • Relationships │  • Semantic  │
│  • Metadata      │  • Path finding  │   similarity │
│  • Indexing      │  • Graph algos   │  • Embeddings│
└─────────────────────────────────────────────────────┘
```

### Memory Manager
```python
class CognitiveMemoryManager:
    def __init__(self):
        self.episodic = EpisodicMemoryStore()
        self.semantic = SemanticMemoryGraph()
        self.procedural = ProceduralMemoryStore()
        self.vector = VectorStore()
    
    def store_interaction(self, user_msg, assistant_msg, context):
        # 1. Extract entities and relationships (NLP)
        entities = self.extract_entities(user_msg + assistant_msg)
        
        # 2. Store episodic memory
        episode = self.episodic.create_episode(
            user_msg, assistant_msg, context, entities
        )
        
        # 3. Update semantic graph
        self.semantic.merge_entities(entities)
        self.semantic.create_relationships(entities, episode)
        
        # 4. Learn procedural patterns
        if self.is_successful_interaction(user_msg):
            self.procedural.learn_pattern(context, approach, outcome)
        
        # 5. Store embeddings
        self.vector.store(episode.embedding, episode.id)
    
    def retrieve_context(self, query, session_id):
        # 1. Semantic search
        similar = self.vector.search(query, top_k=5)
        
        # 2. Graph traversal from current context
        related = self.semantic.get_related_entities(session_id)
        
        # 3. Procedural suggestions
        patterns = self.procedural.get_patterns(query)
        
        return combine(similar, related, patterns)
```

---

## 6. Scalability Considerations

### Partitioning
- **By User**: Each user has their own memory graph
- **By Time**: Recent memories in hot storage, old in cold
- **By Type**: Episodic (high churn), Semantic (stable), Procedural (rare changes)

### Optimization
- **Lazy Loading**: Load graph nodes on demand
- **Caching**: Cache frequent queries
- **Pruning**: Archive weak/old memories periodically
- **Indexing**: Vector indexes for similarity, B-tree for time ranges

### Growth Estimates
- Episodic: ~100-1000 per user per month (with decay)
- Semantic: ~50-200 entities per user (stable)
- Procedural: ~10-50 patterns per user (very stable)

---

## 7. API Design

```python
# Store memory
POST /api/memory/episodic
{
  "session_id": "...",
  "user_message": "...",
  "assistant_message": "...",
  "sentiment": 5,
  "entities": [{"type": "Technology", "name": "React"}]
}

# Query memory
GET /api/memory/retrieve?query=React patterns&session_id=...
{
  "episodic": [...],  # Similar past conversations
  "semantic": {       # Related entities
    "technologies": ["React", "Redux"],
    "topics": ["state management"]
  },
  "procedural": [     # What works
    {"approach": "provide code examples", "success_rate": 0.9}
  ]
}

# Graph exploration
GET /api/memory/graph/entity/Technology/React
{
  "entity": {"name": "React", "level": "expert"},
  "relationships": {
    "known_by": ["User"],
    "related_to": ["Redux", "Next.js"],
    "mentioned_in": ["conv_001", "conv_003"]
  }
}
```

---

## Next Steps

1. **Phase 1**: Implement Episodic + basic Semantic
2. **Phase 2**: Add Knowledge Graph with Kuzu
3. **Phase 3**: Add Vector similarity search
4. **Phase 4**: Implement full Procedural memory
5. **Phase 5**: Advanced graph algorithms (centrality, community detection)

This architecture provides:
- ✅ Human-like memory types
- ✅ Rich relationship modeling
- ✅ Scalable storage
- ✅ Multi-modal retrieval
- ✅ Natural decay and consolidation
