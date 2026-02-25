# Klaus Development Discipline
## "Bulletproof Code - Chuck Norris Approved"

> **WARNING:** This document is MANDATORY reading before any code changes.
> Previous violations resulted in broken releases and angry users.
> Don't be that developer.

---

## 🚨 THE 5 COMMANDMENTS

### 1. TEST FIRST, CODE SECOND
```
❌ WRONG: Write code → "Works on my machine" → Commit → Ask user to test
✅ RIGHT: Write tests → Write code → Run tests → Verify coverage 75%+ → Commit
```

**Rule:** If you haven't run the tests, you haven't finished the task.

### 2. BRANCH OR DIE
```
❌ WRONG: git commit -m "quick fix"  # On main!
✅ RIGHT: 
  git checkout -b feature/my-feature
  git commit -m "feat: add new feature"
  git push origin feature/my-feature
  # Create PR, wait for CI
```

**Rule:** Direct commits to `main` are FORBIDDEN. Always use feature branches.

### 3. BACKUP BEFORE EXPERIMENTS
```bash
# Before ANY risky change:
git branch backup-before-refactor
git tag checkpoint-working-state

# If things go wrong:
git reset --hard checkpoint-working-state
```

**Rule:** If you can't revert in 30 seconds, you're doing it wrong.

### 4. NEVER ASK USER TO TEST YOUR SHIT
```
❌ WRONG: "Can you test this?"
✅ RIGHT: 
  pytest tests/ -v --cov=75%
  docker compose up -d
  curl http://localhost:7072/health
  "All tests pass. Ready for your review."
```

**Rule:** User testing is the LAST line of defense, not the first.

### 5. CONFIRMATION REQUIRED
```
❌ WRONG: (user mentions idea) → (you implement immediately)
✅ RIGHT:
  User: "Maybe we should add X?"
  You: "Good idea. I'll prepare a proposal."
  [Write proposal]
  You: "Here's the plan. Should I proceed?"
  User: "Yes, go ahead."
  [Only then implement]
```

**Rule:** Wait for explicit "DO IT" before executing.

---

## 📋 DEVELOPMENT WORKFLOW

### Phase 1: Planning (BEFORE any code)
- [ ] Understand the requirement fully
- [ ] Check existing code for similar patterns
- [ ] Identify affected modules
- [ ] Estimate test coverage needed
- [ ] Create feature branch: `git checkout -b feature/description`

### Phase 2: Testing (Write tests FIRST)
- [ ] Write unit tests for new functionality
- [ ] Write integration tests for API changes
- [ ] Write E2E tests for user workflows
- [ ] Run tests: `pytest tests/ -v` (expect failures - code doesn't exist yet!)

### Phase 3: Implementation
- [ ] Write minimal code to pass tests
- [ ] Run tests: `pytest tests/ -v` (should pass now)
- [ ] Check coverage: `pytest --cov=core --cov-fail-under=75`
- [ ] Refactor while keeping tests green

### Phase 4: Local Verification
- [ ] Build Docker images: `docker compose build`
- [ ] Start services: `docker compose up -d`
- [ ] Health check: `curl http://localhost:7070/health`
- [ ] Health check: `curl http://localhost:7072/health`
- [ ] Run full test suite: `pytest tests/`

### Phase 5: Commit & Push
- [ ] Stage changes: `git add -p`
- [ ] Commit with conventional format: `git commit -m "feat: description"`
- [ ] Push to origin: `git push origin feature/description`
- [ ] Create Pull Request
- [ ] Wait for CI to pass

### Phase 6: User Validation
- [ ] "All tests pass. CI green. Ready for your review."
- [ ] Wait for user approval
- [ ] Merge PR
- [ ] Tag release: `git tag -a v1.x.x -m "Release description"`

---

## 🧪 TESTING HIERARCHY

### Unit Tests (Fast, Isolated)
```python
# tests/unit/test_module.py
def test_function_does_x():
    """Test that function does X correctly."""
    result = module.function()
    assert result == expected
```
- Run: `pytest tests/unit/ -v`
- Coverage target: 75%+
- Speed: < 5 seconds

### Integration Tests (Services, APIs)
```python
# tests/integration/test_service.py
async def test_api_endpoint():
    """Test API endpoint returns correct data."""
    response = await client.get("/api/endpoint")
    assert response.status_code == 200
```
- Run: `pytest tests/integration/ -v`
- Requires: Docker services running
- Speed: < 30 seconds

### E2E Tests (Full Workflows)
```python
# tests/e2e/test_workflow.py
async def test_user_can_complete_task():
    """Test complete user workflow."""
    # Create session → Send message → Verify response
```
- Run: `pytest tests/e2e/ -v`
- Requires: Full stack running
- Speed: < 2 minutes

### Running All Tests
```bash
# Quick check (unit only)
pytest tests/unit/ -v

# Full check (all tests)
pytest tests/ -v --cov=core --cov-report=html

# With Docker services
make test-all  # If Makefile exists
```

---

## 🏷️ GIT CONVENTIONS

### Branch Naming
```
feature/description     - New features
fix/description         - Bug fixes
docs/description        - Documentation
refactor/description    - Code refactoring
test/description        - Test additions
chore/description       - Maintenance
hotfix/description      - Critical production fixes
```

### Commit Messages (Conventional Commits)
```
feat: add new memory search endpoint
fix: resolve Kuzu graph lock issue
docs: update API documentation
refactor: simplify context manager
test: add unit tests for providers
chore: update dependencies
```

### Commit Message Format
```
type(scope): subject

body (optional)

footer (optional)
```

Examples:
```
feat(memory): add semantic search endpoint

Implements vector-based semantic search using
cosine similarity on embeddings.

Closes #123
```

---

## 🐳 DOCKER WORKFLOW

### Local Development
```bash
# Build all images
docker compose -f docker/docker-compose.yml build

# Start services
docker compose -f docker/docker-compose.yml --profile web up -d

# View logs
docker compose logs -f

# Restart single service
docker compose restart web-ui

# Stop everything
docker compose down
```

### Health Checks
```bash
# Check all services
curl http://localhost:7070/health  # Kimi agent
curl http://localhost:7072/health  # Web UI
```

### Cleanup
```bash
# Remove all containers and volumes
docker compose down -v

# Remove unused images
docker system prune -af
```

---

## 📊 COVERAGE REQUIREMENTS

### Minimum Coverage: 75%
```bash
# Check coverage
pytest --cov=core --cov-report=html --cov-fail-under=75

# View report
open htmlcov/index.html
```

### Coverage by Module
```
core/memory.py          - 90%+ (Critical)
core/hybrid_memory.py   - 85%+ (Critical)
core/agent.py           - 80%+ (Important)
core/context_manager.py - 80%+ (Important)
core/llm_router.py      - 75%+ (Important)
bot/telegram_bot.py     - 70%+ (Medium)
docker/web-ui/app.py    - 70%+ (Medium)
```

---

## 🚨 EMERGENCY PROCEDURES

### "I Broke Everything!"
1. **DON'T PANIC**
2. Create backup: `git branch backup-emergency-$(date +%s)`
3. Check status: `git status && git log --oneline -5`
4. Revert to last known good state:
   ```bash
   git reset --hard checkpoint-pre-release
   ```
5. Verify: `docker compose up -d && curl localhost:7072/health`
6. Document what happened

### "Tests Are Failing!"
1. Run specific failing test: `pytest tests/unit/test_x.py::test_y -v`
2. Check if it's a real failure or flaky test
3. Fix test OR fix code (never skip tests!)
4. Re-run: `pytest tests/`

### "Production Is Down!"
1. **STOP** - Don't make hasty changes
2. Assess: What changed recently? `git log --oneline -10`
3. Rollback to stable version
4. Fix in dev environment
5. Test thoroughly
6. Deploy fix

---

## 📚 DOCUMENTATION

### Code Documentation
```python
def function_name(param: str) -> dict:
    """
    Short description of what function does.
    
    Args:
        param: Description of parameter
        
    Returns:
        Description of return value
        
    Raises:
        ValueError: When input is invalid
        
    Example:
        >>> function_name("test")
        {'result': 'success'}
    """
```

### Test Documentation
```python
def test_feature_under_condition():
    """
    GIVEN: Initial state
    WHEN: Action is performed
    THEN: Expected outcome occurs
    """
```

---

## ✅ PRE-COMMIT CHECKLIST

Before every commit:
- [ ] Code works (tested locally)
- [ ] Tests pass (`pytest tests/unit/`)
- [ ] Coverage ≥ 75%
- [ ] No secrets in code
- [ ] No debug print statements
- [ ] Documentation updated (if needed)
- [ ] Commit message follows convention
- [ ] Branch is up to date with main

---

## 🎯 SUCCESS METRICS

### For Every Task:
1. **Tests Written:** ≥ 3x test functions per feature
2. **Coverage Maintained:** ≥ 75%
3. **CI Green:** All checks pass
4. **User Confirmed:** Explicit approval obtained

### Quality Gates:
```
Unit Tests Pass      → ✓
Coverage ≥ 75%       → ✓
Integration Tests    → ✓
E2E Tests            → ✓
Security Scan        → ✓
User Approval        → ✓
                     → MERGE
```

---

## 💀 ANTI-PATTERNS (NEVER DO THIS)

```python
# ❌ Hardcoded credentials
API_KEY = "sk-1234567890abcdef"

# ❌ No error handling
data = fetch_data()  # May crash
process(data)

# ❌ Print debugging
print(f"DEBUG: value = {value}")

# ❌ Untested code
if some_condition:
    do_something()  # Never tested!

# ❌ Direct commits to main
git checkout main
git commit -m "quick fix"

# ❌ Asking user to test
"Can you test this for me?"
```

---

## 🔗 QUICK REFERENCE

### Essential Commands
```bash
# Test
pytest tests/unit/ -v
pytest tests/ --cov=core --cov-fail-under=75

# Docker
docker compose up -d --build
docker compose logs -f
docker compose down

# Git
git checkout -b feature/x
git commit -m "feat: description"
git push origin feature/x

# Coverage
pytest --cov=core --cov-report=html
open htmlcov/index.html
```

### Key Files
- `skills/CLAUDE.md` - Agent guidelines
- `tests/conftest.py` - Test configuration
- `.github/workflows/ci.yml` - CI/CD pipeline
- `DISCIPLINE.md` - This file

### Important Tags
- `checkpoint-pre-release` - Last known good state

---

## 🏆 THE BOTTOM LINE

**Good developers:**
- Write tests first
- Verify before asking
- Document their work
- Follow conventions
- Respect the process

**Bad developers:**
- Skip tests
- Break main
- Ask users to test
- Ignore conventions
- Cause incidents

---

*"Discipline equals freedom."* - Jocko Willink

*"Test everything. Trust nothing."* - Klaus Development Team

---

**Last Updated:** 2026-02-25
**Version:** 1.0
**Status:** MANDATORY
