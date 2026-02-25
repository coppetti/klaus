# 🆘 Emergency Recovery Guide

> Use this guide if Klaus (AI Agent) crashes, loses memory, or becomes unresponsive
> Last Updated: 2026-02-23

---

## ⚠️ Before You Start

1. **Don't Panic** - Your data is safe in `workspace/`
2. **Backup First** - Always backup before major operations
3. **Check Status** - Verify what's actually broken

---

## 🔍 Quick Diagnostics

### Step 1: Check Container Status
```bash
cd /Users/matheussilveira/Documents/CODE/klaus
docker compose -f docker/docker-compose.yml ps
```

**Expected Output:**
```
NAME                STATUS
ide-agent-kimi      Up X hours
ide-agent-telegram  Up X hours
ide-agent-web       Up X hours
```

### Step 2: Check Memory Files
```bash
ls -la workspace/memory/
```

**Expected:**
```
agent_memory.db          # SQLite database
agent_memory_graph       # Kuzu graph
agent_memory_graph.wal   # Write-ahead log
```

### Step 3: Check Identity Files
```bash
cat workspace/SOUL.md
cat workspace/USER.md
```

**Expected:** Both files should exist and have content

### Step 4: Test Core Imports
```bash
python3 -c "
from core.connectors.ide_connector import get_connector
c = get_connector()
print(f'✅ Agent: {c.agent_name}')
print(f'✅ Memory: {type(c.memory).__name__}')
"
```

---

## 🚨 Common Issues & Fixes

### Issue 1: "HybridMemoryStore.recall() takes 2 positional arguments but 3 were given"

**Symptom:** IDE Connector crashes when recalling memories

**Root Cause:** Bug in `IDEConnector.recall()` - API mismatch

**Quick Fix:**
```bash
# Apply the fix manually
cat > /tmp/fix_connector.py << 'EOF'
import re

with open('core/connectors/ide_connector.py', 'r') as f:
    content = f.read()

# Find and replace the recall method
old_method = '''    def recall(self, query: str, limit: int = 5) -> List[Dict]:
        """Recall memories matching query."""
        if self.memory:
            return self.memory.recall(query, limit)
        return []'''

new_method = '''    def recall(self, query: str, limit: int = 5) -> List[Dict]:
        """Recall memories matching query."""
        if not self.memory:
            return []
        
        # Handle both HybridMemoryStore and MemoryStore APIs
        if isinstance(self.memory, HybridMemoryStore):
            from core.hybrid_memory import MemoryQuery
            mem_query = MemoryQuery(query_type="quick", text=query, limit=limit)
            return self.memory.recall(mem_query)
        else:
            # MemoryStore API
            return self.memory.recall(query, limit)'''

content = content.replace(old_method, new_method)

with open('core/connectors/ide_connector.py', 'w') as f:
    f.write(content)

print("✅ Fix applied")
EOF

python3 /tmp/fix_connector.py
```

**Verify Fix:**
```bash
python3 -c "
from core.connectors.ide_connector import get_connector
c = get_connector()
results = c.recall('test query')
print(f'✅ Recall works! Found {len(results)} memories')
"
```

---

### Issue 2: Graph Not Syncing (Background Thread Failed)

**Symptom:** Memories stored but Graph is empty

**Root Cause:** `asyncio.sleep()` used in synchronous thread

**Quick Fix:**
```bash
# Apply the fix manually
cat > /tmp/fix_sync.py << 'EOF'
with open('core/hybrid_memory.py', 'r') as f:
    content = f.read()

# Add time import if missing
if 'import time' not in content:
    content = content.replace(
        'import threading',
        'import threading\nimport time'
    )

# Fix asyncio.sleep → time.sleep
content = content.replace('asyncio.sleep(0.1)', 'time.sleep(0.1)')

with open('core/hybrid_memory.py', 'w') as f:
    f.write(content)

print("✅ Fix applied - restart required")
EOF

python3 /tmp/fix_sync.py

# Restart Docker
docker compose -f docker/docker-compose.yml restart
```

---

### Issue 3: Web UI Shows "0 memories" but Memories Exist

**Symptom:** Web UI stats show 0 memories

**Root Cause:** Stats API format mismatch

**Quick Fix:**
```bash
# Check actual memory count
sqlite3 workspace/memory/agent_memory.db "SELECT COUNT(*) FROM memories;"

# If count > 0 but Web UI shows 0, the stats API is broken
# Fix is in docs/ROADMAP_V2.md Task 1.3
```

---

### Issue 4: Complete Memory Loss

**Symptom:** Agent doesn't remember anything

**Check:**
```bash
# Verify memory file exists and has data
sqlite3 workspace/memory/agent_memory.db ".tables"
sqlite3 workspace/memory/agent_memory.db "SELECT COUNT(*) FROM memories;"
```

**If Empty:**
```bash
# Check if backup exists
ls -la workspace/memory.backup.*

# Restore from backup
mv workspace/memory workspace/memory.corrupted.$(date +%s)
mkdir workspace/memory
# Copy backup files to workspace/memory/
```

**If No Backup:**
- Memories are lost but agent identity (SOUL.md) is preserved
- Rebuild knowledge through conversation

---

## 🔄 Recovery Procedures

### Procedure A: Soft Restart (Keeps Memory)

```bash
cd /Users/matheussilveira/Documents/CODE/klaus

# 1. Stop services
docker compose -f docker/docker-compose.yml stop

# 2. Verify memory files are intact
ls -la workspace/memory/

# 3. Start services
docker compose -f docker/docker-compose.yml up -d

# 4. Check status
docker compose -f docker/docker-compose.yml ps

# 5. Test
curl http://localhost:8082/health
```

---

### Procedure B: Hard Restart (Resets Runtime State)

```bash
cd /Users/matheussilveira/Documents/CODE/klaus

# 1. Stop and remove containers
docker compose -f docker/docker-compose.yml down

# 2. Remove Web UI data (keeps memory)
rm -rf workspace/web_ui_data

# 3. Start fresh
docker compose -f docker/docker-compose.yml up -d

# 4. Verify
docker compose -f docker/docker-compose.yml ps
curl http://localhost:8082/health
```

---

### Procedure C: Memory Reset (Nuclear Option)

⚠️ **WARNING: This deletes all memories!**

```bash
cd /Users/matheussilveira/Documents/CODE/klaus

# 1. Backup first
cp -r workspace/memory workspace/memory.emergency.$(date +%s)

# 2. Stop everything
docker compose -f docker/docker-compose.yml down

# 3. Clear memory
rm -f workspace/memory/agent_memory.db*

# 4. Restart
docker compose -f docker/docker-compose.yml up -d

# 5. Re-initialize
python3 scripts/initialize.py
```

---

### Procedure D: Factory Reset

⚠️ **WARNING: Deletes ALL configuration and memories!**

```bash
cd /Users/matheussilveira/Documents/CODE/klaus

# 1. Run factory reset
./reset.sh

# 2. Re-setup
./setup.sh

# 3. Configure again
# - Choose your template
# - Set your name
# - Configure interfaces
```

---

## 🧪 Validation After Recovery

Run these checks after any recovery procedure:

```bash
#!/bin/bash
# save as: validate_recovery.sh

echo "=== Recovery Validation ==="

# 1. Docker containers
echo -n "Docker containers: "
if docker compose -f docker/docker-compose.yml ps | grep -q "Up"; then
    echo "✅ Running"
else
    echo "❌ Not running"
fi

# 2. Web UI health
echo -n "Web UI (8082): "
if curl -s http://localhost:8082/health > /dev/null; then
    echo "✅ Responding"
else
    echo "❌ Not responding"
fi

# 3. Memory database
echo -n "Memory DB: "
if [ -f "workspace/memory/agent_memory.db" ]; then
    COUNT=$(sqlite3 workspace/memory/agent_memory.db "SELECT COUNT(*) FROM memories;" 2>/dev/null)
    echo "✅ $COUNT memories"
else
    echo "❌ Missing"
fi

# 4. Identity files
echo -n "SOUL.md: "
[ -f "workspace/SOUL.md" ] && echo "✅ Present" || echo "❌ Missing"

echo -n "USER.md: "
[ -f "workspace/USER.md" ] && echo "✅ Present" || echo "❌ Missing"

# 5. Core imports
echo -n "Core imports: "
if python3 -c "from core.connectors.ide_connector import get_connector" 2>/dev/null; then
    echo "✅ Working"
else
    echo "❌ Failed"
fi

echo "=== Validation Complete ==="
```

Run: `bash validate_recovery.sh`

---

## 📞 Emergency Contacts

If all else fails:

1. **Check Project Documentation:**
   - `docs/PROJECT_AUDIT_V2.md` - Known issues and fixes
   - `docs/ROADMAP_V2.md` - Feature status and plans
   - `docs/README.md` - Setup and usage guide

2. **Check User Profile:**
   ```bash
   cat workspace/USER.md
   ```

3. **File Locations:**
   - Agent Identity: `workspace/SOUL.md`
   - User Profile: `workspace/USER.md`
   - Memories: `workspace/memory/`
   - Config: `init.yaml`
   - Secrets: `.env`

---

## 💾 Backup Strategy

### Automated Daily Backup

```bash
# Add to crontab: crontab -e
# 0 2 * * * /Users/matheussilveira/Documents/CODE/klaus/backup.sh

# backup.sh
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="$HOME/klaus_backups/$DATE"
mkdir -p "$BACKUP_DIR"

cd /Users/matheussilveira/Documents/CODE/klaus

# Backup memory
cp -r workspace/memory "$BACKUP_DIR/"

# Backup identity
cp workspace/SOUL.md "$BACKUP_DIR/"
cp workspace/USER.md "$BACKUP_DIR/"

# Backup config
cp init.yaml "$BACKUP_DIR/"

echo "Backup completed: $BACKUP_DIR"
```

### Manual Backup Now

```bash
DATE=$(date +%Y%m%d_%H%M%S)
tar czf "klaus_backup_$DATE.tar.gz" workspace/memory workspace/SOUL.md workspace/USER.md init.yaml
```

---

## ✅ Post-Recovery Checklist

- [ ] All Docker containers running
- [ ] Web UI accessible at http://localhost:8082
- [ ] Agent responds to queries
- [ ] Memories are accessible
- [ ] File upload works (Web UI)
- [ ] Memory Graph Explorer loads
- [ ] Identity (SOUL.md) is correct
- [ ] User profile (USER.md) is correct

---

**Emergency Version:** v2.0.0  
**Compatible With:** IDE Agent Wizard v2.x  
**Last Tested:** 2026-02-23
