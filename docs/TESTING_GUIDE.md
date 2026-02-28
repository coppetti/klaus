# Testing Guide

---

## Quick Start

```bash
# Unit tests (no Docker needed)
python3 -m pytest tests/unit --tb=short -q

# Full test suite (requires Docker)
python3 -m pytest tests/ -v
```

---

## Test Structure

```
tests/
├── conftest.py
├── run_tests.py
├── unit/
│   ├── test_agent_spawner.py
│   ├── test_llm_router.py
│   └── test_memory.py
├── integration/
│   ├── test_hybrid_memory.py
│   └── test_providers.py
└── e2e/
    └── test_api_flows.py
```

---

## Unit Tests

No Docker or API keys required. Tests core logic in isolation.

```bash
python3 -m pytest tests/unit -v
python3 -m pytest tests/unit/test_llm_router.py -v
```

Last known baseline: **152 passed, 1 skipped**.

---

## Integration Tests

Require Docker containers running.

```bash
bash scripts/start-services.sh
python3 -m pytest tests/integration -v
```

---

## E2E Tests

Full stack validation against running services.

```bash
# Verify services are up
docker ps | grep Klaus

# Run E2E
python3 -m pytest tests/e2e -v
```

Endpoints:
- Agent API: `http://localhost:12019`
- Web UI: `http://localhost:12049`

---

## Coverage

```bash
python3 -m pytest --cov=core --cov-report=html tests/unit
open coverage_html/index.html
```

---

## Debugging

```bash
pytest --pdb                          # Drop into debugger on failure
pytest -vv --log-cli-level=DEBUG      # Verbose with logs
pytest -k "test_llm_router"          # Run matching tests
```

---

## Known Issues

- `HybridMemoryStore.add()` may fail in integration tests (CHECK-01)
- Some async fixtures need `pytest-asyncio` configured
- Integration/E2E tests skip when Docker is not running (expected)
