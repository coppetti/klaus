# Testing Guide

Complete guide for testing Klaus.

## Quick Test

```bash
# Run all tests
python tests/run_tests.py

# Run specific test types
python tests/run_tests.py unit
python tests/run_tests.py integration
python tests/run_tests.py e2e

# Run with coverage
python tests/run_tests.py coverage
```

## Test Structure

```
tests/
├── conftest.py              # Pytest configuration
├── run_tests.py             # Test runner script
├── unit/                    # Unit tests
│   ├── test_agent_spawner.py
│   ├── test_llm_router.py
│   └── test_memory.py
├── integration/             # Integration tests
│   ├── test_hybrid_memory.py
│   └── test_providers.py
└── e2e/                     # End-to-end tests
    └── test_api_flows.py
```

## Running Tests Manually

### Unit Tests

```bash
# Run all unit tests
pytest tests/unit -v

# Run specific test file
pytest tests/unit/test_agent_spawner.py -v

# Run specific test
pytest tests/unit/test_agent_spawner.py::TestAgentSpawner::test_spawn_agent_creates_task -v
```

### Integration Tests

```bash
# Run integration tests
pytest tests/integration -v

# These require Docker services to be running
docker compose up -d
pytest tests/integration -v
```

### E2E Tests

```bash
# Run E2E tests (requires full stack running)
docker compose up -d
pytest tests/e2e -v

# Run with browser automation (if implemented)
pytest tests/e2e --headed
```

## Writing Tests

### Unit Test Example

```python
# tests/unit/test_example.py
import pytest
from core.example import MyClass

class TestMyClass:
    """Test suite for MyClass."""
    
    def test_initialization(self):
        """Test that class initializes correctly."""
        obj = MyClass()
        assert obj is not None
    
    def test_method(self):
        """Test specific method."""
        obj = MyClass()
        result = obj.my_method("input")
        assert result == "expected"
    
    @pytest.mark.parametrize("input,expected", [
        ("a", "A"),
        ("b", "B"),
        ("hello", "HELLO"),
    ])
    def test_with_params(self, input, expected):
        """Test with multiple inputs."""
        obj = MyClass()
        assert obj.uppercase(input) == expected
```

### Integration Test Example

```python
# tests/integration/test_example.py
import pytest
from core.hybrid_memory import HybridMemoryStore

class TestHybridMemoryIntegration:
    """Integration tests for hybrid memory."""
    
    @pytest.fixture
    async def memory_store(self, tmp_path):
        """Create test memory store."""
        store = HybridMemoryStore(
            db_path=str(tmp_path / "test.db"),
            graph_path=str(tmp_path / "graph")
        )
        yield store
        store.close()
    
    @pytest.mark.asyncio
    async def test_add_and_retrieve(self, memory_store):
        """Test adding and retrieving memory."""
        memory_id = await memory_store.add(
            content="Test content",
            category="test"
        )
        
        memories = memory_store.search("Test")
        assert len(memories) > 0
```

### E2E Test Example

```python
# tests/e2e/test_example.py
import pytest
import httpx

BASE_URL = "http://localhost:7072"

class TestAPI:
    """E2E tests for API."""
    
    @pytest.mark.asyncio
    async def test_chat_endpoint(self):
        """Test chat endpoint."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{BASE_URL}/api/chat",
                json={"message": "Hello"},
                timeout=30.0
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "response" in data
```

## Fixtures

Common fixtures available in `conftest.py`:

| Fixture | Description |
|---------|-------------|
| `temp_workspace` | Temporary directory for tests |
| `mock_env_vars` | Mock environment variables |
| `sample_soul_content` | Sample SOUL.md content |
| `event_loop` | Async event loop |

## Markers

Use markers to categorize tests:

```python
@pytest.mark.slow          # Slow tests
@pytest.mark.requires_docker  # Requires Docker
@pytest.mark.requires_api     # Requires API keys

# Run specific markers
pytest -m slow
pytest -m "not slow"
```

## Coverage

```bash
# Generate coverage report
pytest --cov=core --cov-report=html

# View report
open coverage_html/index.html  # macOS
xdg-open coverage_html/index.html  # Linux
start coverage_html/index.html  # Windows
```

## Continuous Integration

Example GitHub Actions workflow:

```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install pytest pytest-asyncio pytest-cov
    
    - name: Run tests
      run: pytest tests/unit -v
    
    - name: Coverage
      run: pytest --cov=core --cov-report=xml
```

## Debugging Tests

```bash
# Run with PDB on failure
pytest --pdb

# Run with verbose output
pytest -vv

# Run specific test with logging
pytest tests/unit/test_example.py -v --log-cli-level=DEBUG
```

## Best Practices

1. **Use descriptive test names**: `test_user_can_login` not `test_login`
2. **One assertion per test** (generally)
3. **Use fixtures** for setup/teardown
4. **Mock external services** in unit tests
5. **Clean up** after tests (use tmp_path, temp_workspace)
6. **Parametrize** when testing multiple inputs

## Common Issues

### Tests Failing Due to Missing Services

```bash
# Start required services first
docker compose up -d

# Or skip integration/e2e tests
pytest tests/unit
```

### Async Test Issues

```bash
# Ensure pytest-asyncio is installed
pip install pytest-asyncio

# Mark async tests
@pytest.mark.asyncio
async def test_async_function():
    ...
```

### Import Errors

```bash
# Make sure core is in Python path
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

---

For more information, see:
- [Pytest Documentation](https://docs.pytest.org/)
- [Testing Best Practices](https://testing.googleblog.com/)
