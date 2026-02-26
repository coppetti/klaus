# Claude Agent Guidelines - Klaus Project
# =========================================

> **NEW:** For a consolidated view of all guidelines, see `skills/AGENT_GUIDELINES.md`
> This file contains the critical rules that must never be broken.

## 🚨 CRITICAL RULES - NEVER BREAK

### 1. GIT DISCIPLINE
- **ALWAYS** use branches for any changes
- **NEVER** commit directly to main without explicit permission
- **ALWAYS** create backup branches before experiments: `git branch backup-<desc>`
- **ALWAYS** check status: `git status && git log --oneline -3`
- **NEVER** force push
- **TAG** working states: `git tag -a <name> -m "desc"`

### 2. TESTING PROTOCOL
- **NEVER** ask user to test before I test first
- Unit tests must be **75%+** before considering done
- **ALWAYS** test locally: `docker compose up -d && curl/test`
- **ALWAYS** verify health endpoints
- **Document** test results in comments

### 3. USER CONFIRMATION
- **NEVER** execute code changes unless explicitly told:
  - "Vai e faz"
  - "Execute agora"
  - "Implementa isso"
  - Similar direct commands
- **ALWAYS** propose first, wait for "ok/faz/sim"
- When in doubt: "Quer que eu execute isso?"

### 4. CHECKPOINTS
- **ALWAYS** create git tags before major changes
- **Current working checkpoint:** `checkpoint-pre-release` (d997590)
- **Backup branch:** `backup-pre-teste` (974ebf3 - has MEMORY_MODE fix)

---

## 📋 PROJECT ARCHITECTURE

### Memory System
```
web-ui (:2049)      → HybridMemoryStore (SQLite + Cognitive Memory) - HAS LOCK
kimi-agent (:2019)  → Stateless API, no direct memory access
telegram-bot        → MemoryStore (SQLite-only) - NO GRAPH ACCESS
```

**Kuzu Lock Issue:**
- Kuzu graph does NOT support multi-process access
- Only ONE container can hold the graph lock
- Currently: web-ui gets it first
- Result: telegram-bot falls back to SQLite-only mode

### Ports
- Local Dev: 2019 (kimi), 2049 (web-ui)
- Release: 2013 (kimi), 2077 (web-ui) - Easter eggs

### Docker Services
```yaml
kimi-agent   : CPU intensive, handles LLM calls
web-ui       : FastAPI + UI, owns memory graph lock
telegram-bot : Polling, SQLite-only memory mode
```

---

## 🔄 WORKFLOW

### Before ANY Change:
1. `git status` - check current state
2. `git log --oneline -5` - know where we are
3. Create backup branch if not exists
4. State current checkpoint clearly

### During Development:
1. Work on feature branch: `git checkout -b feature/x`
2. Make small, testable commits
3. Test locally BEFORE asking user
4. Document what was tested

### Before Asking User to Test:
1. Verify containers are healthy
2. Check logs for errors
3. Test key endpoints
4. State what is expected to work

---

## ⚠️ KNOWN ISSUES

1. **Kuzu Graph Lock**
   - Both web-ui and telegram-bot try to lock same file
   - Current workaround: telegram-bot uses MEMORY_MODE=sqlite
   - Proper fix: Memory service API or read-only mode

2. **Release Zip**
   - May be broken due to my premature changes
   - Need to rebuild from checkpoint-pre-release

3. **anthropic dependency**
   - Was missing from requirements.txt (commented out)
   - Fixed in 974ebf3, NOT in checkpoint-pre-release

---

## 🎯 NEXT STEPS (Pending User Approval)

- [ ] Decide on final architecture for memory sharing
- [ ] Rebuild release zip from checkpoint-pre-release
- [ ] Fix telegram-bot dependencies in release
- [ ] Full end-to-end testing

---

## 📝 LESSONS LEARNED

1. **Never assume** - always test first
2. **Never skip** backup branches
3. **Never commit** without verifying it works
4. **Always document** working states with tags

Created: 2026-02-25
Author: Claude (after fucking up and learning)
