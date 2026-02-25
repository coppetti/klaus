"""
Pytest Configuration and Shared Fixtures
========================================
"""
import pytest
import asyncio
import tempfile
import shutil
from pathlib import Path
from typing import Generator
import sys

# Add core to path
sys.path.insert(0, str(Path(__file__).parent.parent / "core"))


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def temp_workspace() -> Generator[Path, None, None]:
    """Create a temporary workspace for tests."""
    temp_dir = Path(tempfile.mkdtemp(prefix="klaus_test_"))
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def mock_env_vars(monkeypatch):
    """Set mock environment variables for testing."""
    monkeypatch.setenv("KIMI_API_KEY", "test-key-123")
    monkeypatch.setenv("WEB_UI_PORT", "8082")
    monkeypatch.setenv("KIMI_AGENT_URL", "http://localhost:7070")


@pytest.fixture
def sample_soul_content():
    """Return sample SOUL.md content for testing."""
    return """# SOUL - TestAgent

## Identity
**Name:** TestAgent  
**Role:** Test Specialist

## Core Philosophy
> "Test everything, trust nothing."

## Capabilities
- Unit Testing
- Integration Testing
- E2E Testing
"""
