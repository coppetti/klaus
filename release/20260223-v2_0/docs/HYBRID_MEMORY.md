# Hybrid Memory System

The IDE Agent Wizard v2.0 features a **Hybrid Memory** system that combines the speed and reliability of SQLite with the intelligence of a Graph database (Kuzu).

## Overview

```
┌─────────────────────────────────────────────────────────┐
│                  HybridMemoryStore                      │
├─────────────────────────────────────────────────────────┤
│                                                         │
│   WRITE OPERATIONS                                      │
│   ├─► SQLite (synchronous, fast, reliable)             │
│   └─► Graph (asynchronous, background sync)            │
│                                                         │
│   READ OPERATIONS                                       │
│   ├─► "quick" → SQLite (keyword search)                │
│   ├─► "semantic" → Graph (topic/entity search)         │
│   ├─► "context" → Graph (relationship traversal)       │
│   └─► "related" → Graph (entity relationships)         │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

## Why Hybrid?

| Feature | SQLite Only | Graph Only | Hybrid |
|---------|-------------|------------|--------|
| Write Speed | ⚡ Fast | 🐢 Slower | ⚡ Fast (SQLite) |
| Query Speed | ⚡ Fast | ⚡ Fast | ⚡ Fast (both) |
| Relationships | ❌ None | ✅ Rich | ✅ Rich |
| Context Chains | ❌ Manual | ✅ Automatic | ✅ Automatic |
| Fallback | ✅ Always | ❌ None | ✅ SQLite fallback |

## Architecture

### Storage Layer

**SQLite**: Traditional relational storage
- Table: `memories` (id, content, category, created_at)
- Fast writes and simple queries
- Always available, reliable

**Kuzu Graph**: Native graph storage
- Nodes: `Memory`, `Topic`, `Entity`
- Relationships: `RELATED_TO`, `HAS_TOPIC`, `MENTIONS`, `FOLLOWS`
- Relationship-aware queries
- Context chain traversal

### Automatic Sync

When you store a memory:
1. Immediately saved to SQLite (fast, synchronous)
2. Queued for Graph update (async, background)
3. Graph extracts topics and entities
4. Relationships created automatically

## Usage

### Basic Usage

```python
from core.hybrid_memory import HybridMemoryStore, MemoryQuery

# Initialize (auto-fallback to SQLite if Graph fails)
memory = HybridMemoryStore("workspace/memory/agent_memory.db")

# Store a memory
category = memory.store(
    content="I prefer Python for backend development",
    category="preference",
    importance="high"
)
```

### Query Types

#### Quick Query (SQLite)
Fast keyword search for immediate context:

```python
query = MemoryQuery(
    query_type="quick",
    text="Python",
    limit=5
)
results = memory.recall(query)
```

#### Semantic Query (Graph)
Find memories by topics and entities:

```python
query = MemoryQuery(
    query_type="semantic",
    text="backend development preferences",
    limit=5
)
results = memory.recall(query)
```

#### Context Query (Graph)
Traverse relationship chains for deep context:

```python
query = MemoryQuery(
    query_type="context",
    text="development preferences",
    limit=5,
    context_depth=3  # Traverse up to 3 relationships
)
results = memory.recall(query)
```

#### Related Query (Graph)
Find memories mentioning same entities:

```python
query = MemoryQuery(
    query_type="related",
    text="Python Django project",
    limit=5
)
results = memory.recall(query)
```

## Graph Schema

### Nodes

```cypher
// Memory node
CREATE NODE TABLE Memory(
    id INT64,
    content STRING,
    category STRING,
    importance STRING,
    created_at TIMESTAMP,
    PRIMARY KEY(id)
)

// Topic node (extracted from content)
CREATE NODE TABLE Topic(
    name STRING,
    category STRING,
    PRIMARY KEY(name)
)

// Entity node (people, projects, technologies)
CREATE NODE TABLE Entity(
    name STRING,
    type STRING,  // PERSON, PROJECT, TECHNOLOGY
    PRIMARY KEY(name)
)
```

### Relationships

```cypher
// Memories related by content similarity
CREATE REL TABLE RELATED_TO(
    FROM Memory TO Memory,
    strength DOUBLE,
    MANY_MANY
)

// Memory has topics
CREATE REL TABLE HAS_TOPIC(
    FROM Memory TO Topic,
    MANY_MANY
)

// Memory mentions entities
CREATE REL TABLE MENTIONS(
    FROM Memory TO Entity,
    MANY_MANY
)

// Temporal sequence
CREATE REL TABLE FOLLOWS(
    FROM Memory TO Memory,
    ONE_MANY
)
```

## Topic Extraction

The system automatically extracts topics from memory content:

```python
topics = [
    "Docker", "Python", "JavaScript", "React", "API", "Database",
    "Architecture", "Testing", "Deploy", "Security", "Performance",
    "Kimi", "Claude", "OpenAI", "LLM", "AI", "Machine Learning"
]
```

## Entity Extraction

Entities are extracted using pattern matching:

- **Projects**: Capitalized words ending in Project/App/System/Tool
- **Technologies**: Known tech names (FastAPI, Django, PostgreSQL, etc.)
- **People**: Names mentioned with context

## Fallback Behavior

If Kuzu Graph is not available:
- System automatically falls back to SQLite-only mode
- All queries route to SQLite
- No relationship features available
- Still fully functional

To check availability:

```python
if memory.graph_available:
    print("Graph features enabled")
else:
    print("Running in SQLite-only mode")
```

## Installation

### SQLite Only (Default)
```bash
# No additional installation needed
# SQLite is built into Python
```

### With Graph Support
```bash
pip install kuzu
```

## Configuration

The Hybrid Memory is automatically used by all interfaces (IDE, Web, Telegram). No configuration needed.

To force SQLite-only mode:

```python
from core.memory import MemoryStore
# Use MemoryStore directly instead of HybridMemoryStore
```

## Performance

### Write Performance
- SQLite: ~1-2ms per write
- Graph sync: ~50-100ms (async, background)

### Read Performance
- SQLite quick query: ~5-10ms
- Graph semantic query: ~20-50ms
- Graph context traversal: ~50-100ms

## Migration

If you have existing SQLite data and want to enable Graph:

1. Install Kuzu: `pip install kuzu`
2. Restart your application
3. New memories will be synced to Graph automatically
4. Existing memories remain in SQLite (accessible via "quick" queries)

## Troubleshooting

### Graph not available
```
⚠️ Graph initialization failed: [error]
   Falling back to SQLite-only mode
```

This is normal if Kuzu is not installed. The system works fine without it.

### Slow queries
- Check if Graph is being used for appropriate queries
- Use "quick" queries for simple keyword searches
- Reserve "context" queries for when you need relationship traversal

### Storage usage
- SQLite: ~1KB per memory
- Graph: ~2-3KB per memory (including relationships)
- Total: ~3-4KB per memory with full Hybrid

## Future Enhancements

Planned improvements:
- Semantic embeddings for vector similarity search
- Automatic memory consolidation
- Time-based decay for old memories
- Cross-session memory export/import

## API Reference

See `core/hybrid_memory.py` for full API documentation.

Key classes:
- `HybridMemoryStore`: Main storage class
- `MemoryQuery`: Query specification
- `get_hybrid_memory()`: Factory function
