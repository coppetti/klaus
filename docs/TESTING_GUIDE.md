# Testing Guide

How to test Klaus components.

---

## Test Structure

```
tests/
├── conftest.py           # Pytest fixtures
├── unit/                 # Unit tests
│   ├── test_kimi_provider.py
│   ├── test_agent_spawner.py
│   └── test_memory_store.py
├── integration/          # Integration tests
│   ├── test_chat_api.py
│   └── test_memory_graph.py
└── e2e/                  # End-to-end tests
    └── test_web_ui.py
```

---

## Running Tests

### All Tests

```bash
pytest
```

### Specific Categories

```bash
# Unit tests only
pytest tests/unit/

# Integration tests
pytest tests/integration/

# E2E tests
pytest tests/e2e/
```

### With Coverage

```bash
pytest --cov=core --cov-report=html
```

---

## Test Environment

### Setup Test Environment

```bash
# Create test virtual environment
python -m venv .venv-test
source .venv-test/bin/activate
pip install -r requirements.txt
pip install pytest pytest-asyncio pytest-cov
```

### Environment Variables

Tests use mock providers by default. For integration tests:

```bash
export KIMI_API_KEY=sk-test-key
export TEST_MODE=integration
```

---

## Writing Tests

### Unit Test Example

```python
def test_kimi_provider_format_messages():
    provider = KimiProvider(api_key="test")
    messages = [
        Message(role="user", content="Hello"),
        Message(role="assistant", content="Hi there!")
    ]
    formatted = provider.format_messages(messages)
    
    assert len(formatted) == 2
    assert formatted[0]["role"] == "user"
```

### Async Test Example

```python
@pytest.mark.asyncio
async def test_agent_spawner():
    spawner = AgentSpawner()
    task_id = await spawner.spawn_agent(
        template="developer",
        task="Review code"
    )
    
    assert task_id.startswith("sub_developer_")
```

---

## Mock Fixtures

Common mocks available in `conftest.py`:

| Fixture | Description |
|---------|-------------|
| `mock_provider` | Mock LLM provider |
| `temp_memory_dir` | Temporary memory directory |
| `test_db` | In-memory test database |
| `mock_session` | Mock chat session |

---

## CI/CD Testing

Run tests in CI:

```bash
#!/bin/bash
set -e

# Install dependencies
pip install -r requirements.txt
pip install pytest pytest-asyncio

# Run tests
pytest tests/unit/ -v

# Run integration tests if credentials available
if [ -n "$KIMI_API_KEY" ]; then
    pytest tests/integration/ -v
fi
```

---

## Performance Testing

### Memory Performance

```bash
python -m pytest tests/performance/test_memory_speed.py
```

### Load Testing

```bash
# Install locust
pip install locust

# Run load test
locust -f tests/performance/locustfile.py
```

---

## Debugging Tests

### Verbose Output

```bash
pytest -vvs tests/unit/test_kimi_provider.py
```

### PDB Debugging

```bash
pytest --pdb tests/unit/test_kimi_provider.py
```

---

## Test Checklist

Before releasing:

- [ ] All unit tests pass
- [ ] Integration tests pass
- [ ] E2E tests pass
- [ ] Coverage > 80%
- [ ] No deprecation warnings
- [ ] Documentation updated
