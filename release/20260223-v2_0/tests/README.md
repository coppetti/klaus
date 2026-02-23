# IDE Agent Wizard - Test Suite

Automated tests for IDE Agent Wizard v2.0.0

## Quick Start

```bash
# Run all tests
./tests/run.sh

# Or using Python directly
python3 tests/run_tests.py
```

## Test Types

### 1. File Structure Tests
- Verifies all required files exist
- Checks no sensitive files are included

### 2. Syntax Tests
- Python syntax validation
- Docker Compose syntax validation

### 3. Port Availability Tests
- Ensures test ports are free (8083, 8084)
- Avoids conflicts with production

### 4. Unit Tests
- Memory Store functionality
- IDE Connector functionality
- Located in `tests/unit/`

### 5. Integration Tests (Optional)
- Docker container startup
- Health check endpoints
- Use `--docker` flag to include

## Test Ports

Tests use different ports to avoid conflicts:

| Service | Production | Test |
|---------|-----------|------|
| Kimi Agent | 8081 | 8083 |
| Web UI | 8082 | 8084 |

## Usage

```bash
# Quick tests (no Docker)
python3 tests/run_tests.py

# Include Docker tests
python3 tests/run_tests.py --docker

# Run specific test file
python3 -m pytest tests/unit/test_memory.py -v

# Run with coverage (if pytest-cov installed)
python3 -m pytest tests/ --cov=core
```

## Docker Test Environment

Start test containers manually:

```bash
cd tests
docker compose -f docker-compose.test.yml --profile test up -d

# Test Kimi Agent (port 8083)
curl http://localhost:8083/health

# Test Web UI (port 8084)
open http://localhost:8084

# Cleanup
docker compose -f docker-compose.test.yml --profile test down
```

## Adding Tests

### Unit Tests

Create a new file in `tests/unit/`:

```python
# tests/unit/test_new_feature.py
import pytest
from core.new_feature import NewFeature

class TestNewFeature:
    def test_something(self):
        feature = NewFeature()
        assert feature.do_something() == expected_result
```

### Integration Tests

Add to `tests/run_tests.py`:

```python
def test_new_integration():
    """Test new integration."""
    log("\n🆕 Testing new integration...")
    # Test code here
    return True
```

## CI/CD Integration

Example GitHub Actions workflow:

```yaml
name: Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Run tests
        run: python3 tests/run_tests.py
```

## Troubleshooting

### Port Conflicts

If test ports are in use:

```bash
# Check what's using port 8083
lsof -i :8083

# Kill process or use different ports
# Edit tests/docker-compose.test.yml
```

### Docker Tests Failing

Make sure Docker is running:

```bash
docker ps
```

And you have permission to use Docker.

### Import Errors

Make sure you're running from the project root:

```bash
cd /path/to/ide-agent-wizard
python3 tests/run_tests.py
```

## Test Checklist

Before releasing:

- [ ] All file structure tests pass
- [ ] Python syntax tests pass
- [ ] No sensitive files in release
- [ ] Unit tests pass (core modules)
- [ ] Docker tests pass (if using --docker)
- [ ] Port availability confirmed
