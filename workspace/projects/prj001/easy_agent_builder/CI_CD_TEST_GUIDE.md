# CI/CD and Testing - Simple Guide

> Essential for quality projects. And we already have everything set up! 🎉

---

## 🤔 What is This? (Simple Explanation)

### 🧪 **Unit Tests** = "Verify that each piece works"

Imagine building a car:
- **Without tests**: Start the car and hope it works
- **With tests**: Test engine, brakes, wheels SEPARATELY first

It's the same with code:
```python
# Test: Does the Registry store agents correctly?
def test_registry():
    registry = AgentRegistry()
    registry.register("test", mock_agent)
    assert registry.get("test") == mock_agent  # Verify!
```

### 🔄 **CI/CD** = "Robot that tests and deploys automatically"

**CI** = Continuous Integration  
"Every time someone changes code, the robot tests if nothing broke"

**CD** = Continuous Deployment  
"If tests pass, the robot deploys to production automatically"

```
You do:           The robot does:
push code   →     Test → Build → Deploy
(1 minute)        (5 minutes automatic)
```

---

## ✅ What We ALREADY Have in the Project

### 1. Unit Tests (`tests/`)

```bash
easy_agent_builder/
└── tests/
    ├── unit/
    │   ├── test_circuit_breaker.py
    │   └── test_ultra_lowcode.py
    ├── integration/
    │   └── test_bibha_adapter.py
    └── load/
        └── test_adapter_load.py
```

**How to run:**
```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run all tests
./run_tests.sh all

# Run specific test
pytest tests/unit/test_circuit_breaker.py -v

# With coverage (what % of code is tested)
./run_tests.sh coverage
```

**What we test:**
- ✅ Circuit breaker state transitions
- ✅ YAML configuration validation
- ✅ Registry agent storage
- ✅ Bibha adapter endpoints
- ✅ Load handling capacity

---

### 2. CI/CD (`deployment/cloudbuild.yaml`)

**What it does automatically:**

```yaml
Pipeline (every time you "git push"):
│
├── 1. Lint (checks if code is well formatted)
│   └── black, ruff (formatters)
│
├── 2. Type Check (verifies types)
│   └── mypy
│
├── 3. Unit Tests
│   └── pytest tests/
│
├── 4. Docker Build
│   └── Creates container image
│
├── 5. Push to Registry
│   └── Stores image in Google Container Registry
│
├── 6. Deploy to Cloud Run
│   └── Publishes new version!
│
└── 7. Integration Tests
    └── Verifies it's responding
```

**Total time:** ~5-10 minutes automatic

---

## 🚀 How to Use

### Option A: Test Local (Before committing)

```bash
# 1. Auto formatter (makes code pretty)
black src/ tests/

# 2. Linter (finds problems)
ruff check src/ tests/

# 3. Type checker
mypy src/

# 4. Tests
./run_tests.sh unit

# If everything passes → can git push!
```

### Option B: Let CI/CD do it (Cloud Build)

```bash
# Just push
 git add .
git commit -m "New feature X"
git push origin main

# The robot does the rest!
# You get email if it errors
# Or check in GCP console
```

---

## 📊 Example Test Output

```bash
$ pytest tests/unit -v

tests/unit/test_circuit_breaker.py::TestCircuitBreaker::test_initial_state PASSED [ 20%]
tests/unit/test_circuit_breaker.py::TestCircuitBreaker::test_success_increments_count PASSED [ 40%]
tests/unit/test_circuit_breaker.py::TestCircuitBreaker::test_opens_after_threshold PASSED [ 60%]
tests/unit/test_ultra_lowcode.py::TestAgentConfig::test_valid_config PASSED [ 80%]
tests/unit/test_ultra_lowcode.py::TestAgentConfig::test_name_validation PASSED [100%]

======================== 5 passed in 0.82s =========================
```

**Green = Success** ✅  
**Red = Failure** ❌ (code broke something)

---

## 🔧 Testing Real Agents

### Simple Test (YAML)

```python
# tests/test_agent_yaml.py
def test_agent_yaml_valid():
    """Tests if agent YAML is valid"""
    from agent_builder.ultra_lowcode import ConfigLoader
    
    loader = ConfigLoader()
    config = loader.load_agent_yaml("agents/my_assistant.yaml")
    
    assert config.name == "my_assistant"
    assert config.type == "llm"
    assert len(config.tools) > 0
```

### Integration Test (API)

```python
# tests/test_api_integration.py
import pytest
from fastapi.testclient import TestClient
from bibha_adapter_real import create_app

client = TestClient(create_app())

def test_health_check():
    """Tests if API is alive"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_prediction_endpoint():
    """Tests prediction endpoint"""
    response = client.post(
        "/api/v1/prediction/test-flow",
        json={"question": "Hello", "sessionId": "test-123"}
    )
    assert response.status_code == 200
    assert "text" in response.json()
```

---

## 🎯 Why This Matters

### Without CI/CD:
```
You: "Deployed new code"
Customer: "System is down!"
You: "Oops, forgot to test integration with X"
→ Manual rollback, stress, 2h to resolve
```

### With CI/CD:
```
You: "Made push"
Robot: "Tests failed on integration X"
You: "Fix before deploying"
→ Production never breaks ✅
```

---

## 💰 Cost on GCP

| Service | Cost |
|---------|------|
| Cloud Build (CI) | ~$0.10 per build (2 min) |
| Container Registry | ~$0.10 per GB/month |
| **Total** | **~$5-10/month** for moderate use |

---

## 📝 Quality Checklist

Before each deploy, CI checks:

- [ ] Code formatted (black)
- [ ] No lint errors (ruff)
- [ ] Types correct (mypy)
- [ ] Unit tests pass (pytest)
- [ ] Docker build works
- [ ] Cloud Run deploy succeeds
- [ ] Health check responds

---

## 🚀 Want to Add More Tests?

```bash
# Create new test file
touch tests/test_my_feature.py

# Basic structure
def test_something_simple():
    # Arrange (prepare)
    data = {"name": "test"}
    
    # Act (execute)
    result = my_function(data)
    
    # Assert (verify)
    assert result == "expected"
```

---

## ❓ Summary

| Question | Answer |
|----------|--------|
| Do we have tests? | ✅ Yes, in `tests/` |
| Do we have CI/CD? | ✅ Yes, `cloudbuild.yaml` |
| Need to configure? | ⚠️ Just connect to GCP |
| Is it hard to use? | ❌ No, just `pytest` or `git push` |

**Next step:** Want me to configure GitHub Actions too (alternative to Cloud Build)? It's free for public repositories! 🚀
