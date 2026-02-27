# 🗺️ Roadmap - IDE Agent Wizard v2.x

> Strategic plan for improvements and new features
> Created: 2026-02-23
> Status: ACTIVE

---

## 🚨 Phase 1: Critical Fixes (Week 1)

### Task 1.1: Fix IDEConnector API Mismatch ✅
**Priority:** P0 🔴  
**Assignee:** Klaus  
**Estimated:** 2 hours  
**Status:** ✅ COMPLETED (2026-02-23)

**Problem:** `IDEConnector.recall()` incompatible with `HybridMemoryStore`

**Implementation:**
```python
# File: core/connectors/ide_connector.py

def recall(self, query: str, limit: int = 5) -> List[Dict]:
    """Recall memories matching query."""
    if not self.memory:
        return []
    
    # Handle both APIs
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
```

**Acceptance Criteria:**
- [ ] `IDEConnector.recall()` works with HybridMemoryStore
- [ ] `IDEConnector.recall()` works with MemoryStore (fallback)
- [ ] Unit test added

---

### Task 1.2: Fix Background Sync Thread ✅
**Priority:** P0 🔴  
**Assignee:** Klaus  
**Estimated:** 1 hour  
**Status:** ✅ COMPLETED (2026-02-23)

**Problem:** Using `asyncio.sleep()` in synchronous thread

**Implementation:**
```python
# File: core/hybrid_memory.py

import time  # Add to imports

def _start_background_sync(self):
    """Start background thread for syncing SQLite → Graph."""
    def sync_worker():
        while True:
            try:
                if self._sync_queue:
                    item = self._sync_queue.pop(0)
                    self._sync_to_graph(item)
                time.sleep(0.1)  # Changed from asyncio.sleep
            except Exception as e:
                print(f"Sync error: {e}")
    
    self._sync_thread = threading.Thread(target=sync_worker, daemon=True)
    self._sync_thread.start()
```

**Acceptance Criteria:**
- [ ] Background thread starts without error
- [ ] Memories sync to Graph automatically
- [ ] Test: Store memory → Check graph after 1 second

---

### Task 1.3: Fix Web UI Stats API ✅
**Priority:** P1 🟡  
**Assignee:** Klaus  
**Estimated:** 2 hours  
**Status:** ✅ COMPLETED (2026-02-23)

**Problem:** Web UI expects `stats.sqlite.total` but API returns different format

**Implementation:**
```python
# Option 1: Update HybridMemoryStore.get_stats()
def get_stats(self) -> Dict:
    """Get statistics from both stores."""
    sqlite_stats = self.sqlite.get_stats()
    
    # Wrap in 'sqlite' key for consistency
    return {
        "sqlite": sqlite_stats,  # Already has "total" and "categories"
        "graph": {...},
        "graph_available": self.graph_available,
        "sync_queue_size": len(self._sync_queue)
    }
```

**Acceptance Criteria:**
- [ ] Web UI memory stats display correctly
- [ ] Both SQLite-only and Hybrid modes work

---

### Task 1.4: Add Web Search Tool
**Priority:** P0 🔴  
**Assignee:** Klaus  
**Estimated:** 4 hours  
**Status:** ✅ IMPLEMENTED

**Problem:** Agent in Web UI and Telegram cannot access real-time information (weather, news, etc.)

**Implementation:**
```python
# core/tools/web_search.py - NEW FILE
class WebSearchTool:
    def search(self, query: str, num_results: int = 5) -> List[Dict]:
        # Try Serper.dev, fallback to DuckDuckGo
        pass
    
    def get_current_weather(self, location: str) -> Dict:
        # Try OpenWeatherMap API, fallback to web search
        pass
```

**Integration Points:**
- [x] Web UI chat endpoint (`docker/web-ui/app.py`)
- [x] Telegram bot (`bot/telegram_bot.py`)
- [x] Auto-detection for weather queries
- [x] Auto-detection for news/current events

**Files Created:**
- `core/tools/__init__.py`
- `core/tools/web_search.py`

**Files Modified:**
- `docker/web-ui/app.py` - Added web search integration
- `bot/telegram_bot.py` - Added web search integration
- `requirements.txt` - Added `duckduckgo-search`

**Acceptance Criteria:**
- [x] User can ask "What's the weather in Amsterdam?" and get real-time answer
- [x] User can ask "Latest news about AI" and get current information
- [x] Works in both Web UI and Telegram
- [x] Graceful fallback if search fails

---

## 🔧 Phase 2: Stabilization (Week 2-3)

### Task 2.1: Create Tests Directory
**Priority:** P1 🟡  
**Assignee:** TBD  
**Estimated:** 4 hours

**Structure:**
```
tests/
├── __init__.py
├── conftest.py
├── run_tests.py
├── unit/
│   ├── __init__.py
│   ├── test_memory.py
│   ├── test_hybrid_memory.py
│   └── test_ide_connector.py
└── integration/
    ├── __init__.py
    └── test_docker_services.py
```

**Acceptance Criteria:**
- [ ] `python tests/run_tests.py` works
- [ ] All P0 fixes have unit tests
- [ ] CI/CD can run tests

---

### Task 2.2: Update CHECKLIST.md
**Priority:** P1 🟡  
**Assignee:** TBD  
**Estimated:** 1 hour

**Changes:**
- Update version to v2.0.0
- Add Web UI checks
- Add Hybrid Memory checks
- Update Docker service list

---

### Task 2.3: Improve Error Handling
**Priority:** P2 🟢  
**Assignee:** TBD  
**Estimated:** 3 hours

**Areas:**
1. Web UI provider fallbacks
2. Graph sync error recovery
3. Memory database corruption detection

---

## ✨ Phase 3: New Features (Month 2)

### Feature 3.1: MCP Server Support
**Priority:** HIGH  
**Assignee:** TBD  
**Estimated:** 16 hours  
**Status:** 🆕 PROPOSED

**Description:** Add Model Context Protocol server to expose Klaus memory to other tools

**Implementation:**
```python
# mcp_server.py
from mcp.server import Server
from core.connectors.ide_connector import get_connector

app = Server("klaus-mcp")

@app.tool()
def search_memories(query: str, limit: int = 5) -> List[Dict]:
    """Search agent memories."""
    connector = get_connector()
    return connector.recall(query, limit)

@app.tool()
def store_fact(fact: str, category: str = "general"):
    """Store a fact in agent memory."""
    connector = get_connector()
    connector.store_fact(fact, category)
```

**Benefits:**
- Other AI tools can access Klaus memory
- Standardized interface
- Growing ecosystem support

---

### Feature 3.2: Memory Insights Dashboard
**Priority:** MEDIUM  
**Assignee:** TBD  
**Estimated:** 12 hours  
**Status:** 🆕 PROPOSED

**Description:** New Web UI page with analytics

**Features:**
- Memory growth chart (time series)
- Category distribution pie chart
- Top entities word cloud
- Relationship graph statistics
- Memory access patterns

**Tech:** Chart.js or D3.js

---

### Feature 3.3: Smart Memory Compaction
**Priority:** MEDIUM  
**Assignee:** TBD  
**Estimated:** 20 hours  
**Status:** 🆕 PROPOSED

**Description:** Use LLM to intelligently manage memories

**Capabilities:**
1. **Summarize Old Conversations**
   - Convert long conversations to key facts
   - Preserve important details

2. **Deduplication**
   - Detect similar facts
   - Merge or keep most recent

3. **Cold Storage**
   - Archive old memories to separate table
   - Keep hot memory fast

**Trigger:**
- Manual: "Compact Memory" button in Web UI
- Automatic: When memory exceeds threshold

---

## 🔮 Phase 4: Advanced Features (Month 3+)

### Feature 4.1: Multi-User Support
**Priority:** MEDIUM  
**Assignee:** TBD  
**Estimated:** 32 hours  
**Status:** 🆕 PROPOSED

**Description:** Support multiple users with isolated or shared memory

**Components:**
- User authentication (Web UI)
- User isolation in memory
- Optional shared knowledge base
- User-specific SOUL.md templates

---

### Feature 4.2: Vector Database Integration
**Priority:** LOW  
**Assignee:** TBD  
**Estimated:** 40 hours  
**Status:** 🆕 PROPOSED

**Description:** Optional vector DB for semantic search

**Options:**
- Chroma (local, easy)
- Pinecone (cloud, scalable)
- Milvus (self-hosted, powerful)

**Use Cases:**
- Better semantic search
- Clustering similar memories
- Finding "related" content beyond keywords

---

### Feature 4.3: Plugin System
**Priority:** LOW  
**Assignee:** TBD  
**Estimated:** 48 hours  
**Status:** 🆕 PROPOSED

**Description:** Allow custom plugins to extend Klaus

**API Design:**
```python
# plugins/example_plugin.py
from klaus import plugin, hook

@plugin
class MyPlugin:
    @hook("on_memory_stored")
    def process_memory(self, memory):
        # Custom processing
        pass
    
    @hook("on_query")
    def modify_query(self, query):
        # Query preprocessing
        return query
```

---

## 📊 Progress Tracking

### Phase 1 (Critical Fixes)
| Task | Status | Owner | Due |
|------|--------|-------|-----|
| 1.1 IDEConnector.recall() fix | ⏳ Pending | | Week 1 |
| 1.2 Background sync fix | ⏳ Pending | | Week 1 |
| 1.3 Web UI stats fix | ⏳ Pending | | Week 1 |

### Phase 2 (Stabilization)
| Task | Status | Owner | Due |
|------|--------|-------|-----|
| 2.1 Tests directory | ⏳ Pending | | Week 2 |
| 2.2 CHECKLIST.md update | ⏳ Pending | | Week 2 |
| 2.3 Error handling | ⏳ Pending | | Week 3 |

### Phase 3 (New Features)
| Feature | Priority | Status | Owner | Due |
|---------|----------|--------|-------|-----|
| 3.1 MCP Server | HIGH | ⏳ Proposed | | Month 2 |
| 3.2 Insights Dashboard | MEDIUM | ⏳ Proposed | | Month 2 |
| 3.3 Smart Compaction | MEDIUM | ⏳ Proposed | | Month 2 |

---

## 🎯 Success Metrics

### Phase 1 Success
- [ ] No API mismatch errors in logs
- [ ] Graph sync queue processes items
- [ ] Web UI displays stats correctly

### Phase 2 Success
- [ ] Test coverage > 60%
- [ ] All CI checks pass
- [ ] Documentation matches code

### Phase 3 Success
- [ ] MCP server usable by external tools
- [ ] Users can visualize memory analytics
- [ ] Memory size stays bounded with compaction

---

## 📝 Notes

### Technical Debt
- Cypher query escaping needs improvement
- Web UI needs input validation
- Docker health checks need proper implementation

### Dependencies to Add
```
# For MCP
mcp>=1.0.0

# For Tests
pytest>=7.4.0
pytest-asyncio>=0.21.0

# For Insights (optional)
matplotlib>=3.7.0
```

### Breaking Changes
None planned for v2.x - all changes are backward compatible

---

**Last Updated:** 2026-02-23  
**Next Review:** After Phase 1 completion
