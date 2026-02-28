"""
Pytest Configuration and Shared Fixtures - KLAUS BULLETPROOF TESTING
=====================================================================
Chuck Norris doesn't need tests. But Klaus does. And they ALL pass.
"""
import pytest
import asyncio
import tempfile
import shutil
import os
import json
import sqlite3
from pathlib import Path
from typing import Generator, Dict, Any
from unittest.mock import Mock, MagicMock, AsyncMock
from datetime import datetime, timedelta
import sys

# Add paths
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "core"))
sys.path.insert(0, str(Path(__file__).parent.parent / "bot"))
sys.path.insert(0, str(Path(__file__).parent.parent / "docker" / "web-ui"))

# =============================================================================
# EVENT LOOP
# =============================================================================

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# =============================================================================
# TEMPORARY DIRECTORIES
# =============================================================================

@pytest.fixture
def temp_workspace() -> Generator[Path, None, None]:
    """Create a temporary workspace for tests."""
    temp_dir = Path(tempfile.mkdtemp(prefix="klaus_test_"))
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def temp_memory_dir(temp_workspace) -> Path:
    """Create temporary memory directory."""
    memory_dir = temp_workspace / "memory"
    memory_dir.mkdir(parents=True, exist_ok=True)
    return memory_dir


@pytest.fixture
def temp_projects_dir(temp_workspace) -> Path:
    """Create temporary projects directory."""
    projects_dir = temp_workspace / "projects"
    projects_dir.mkdir(parents=True, exist_ok=True)
    return projects_dir


@pytest.fixture
def temp_web_ui_dir(temp_workspace) -> Path:
    """Create temporary web-ui data directory."""
    web_ui_dir = temp_workspace / "web_ui_data"
    web_ui_dir.mkdir(parents=True, exist_ok=True)
    return web_ui_dir


# =============================================================================
# MOCK ENVIRONMENT
# =============================================================================

@pytest.fixture
def mock_env_vars(monkeypatch):
    """Set mock environment variables for testing."""
    monkeypatch.setenv("KIMI_API_KEY", "test-key-123")
    monkeypatch.setenv("WEB_UI_PORT", "8082")
    monkeypatch.setenv("KIMI_AGENT_URL", "http://localhost:7070")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token:123456")
    monkeypatch.setenv("MEMORY_PATH", "/tmp/test_memory")
    monkeypatch.setenv("CLAWD_WORKSPACE", "/tmp/test_workspace")


@pytest.fixture
def mock_env_clean(monkeypatch):
    """Clean environment - remove sensitive vars."""
    for var in ["KIMI_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY"]:
        monkeypatch.delenv(var, raising=False)


# =============================================================================
# SAMPLE DATA FIXTURES
# =============================================================================

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


@pytest.fixture
def sample_user_content():
    """Return sample USER.md content."""
    return """# USER - TestUser

**Name:** John Doe
**Role:** Developer
**Preferences:** Python, FastAPI, Clean Code
"""


@pytest.fixture
def sample_agents_content():
    """Return sample AGENTS.md content."""
    return """# AGENTS.md - Project Guidelines

## Rules
1. Always test before deploying
2. Never commit broken code
3. Document everything
"""


@pytest.fixture
def sample_memory_entries():
    """Return sample memory entries for testing."""
    return [
        {
            "id": 1,
            "content": "Test memory entry 1",
            "category": "test",
            "timestamp": datetime.now().isoformat(),
            "importance": 0.8,
            "metadata": {"test": True}
        },
        {
            "id": 2,
            "content": "Another test memory",
            "category": "conversation",
            "timestamp": datetime.now().isoformat(),
            "importance": 0.5,
            "metadata": {"test": True}
        },
        {
            "id": 3,
            "content": "Python is great for testing",
            "category": "knowledge",
            "timestamp": datetime.now().isoformat(),
            "importance": 0.9,
            "metadata": {"language": "python"}
        }
    ]


@pytest.fixture
def sample_chat_messages():
    """Return sample chat messages."""
    return [
        {"role": "user", "content": "Hello Klaus"},
        {"role": "assistant", "content": "Hello! How can I help?"},
        {"role": "user", "content": "Test my code"},
        {"role": "assistant", "content": "Sure, I'll test it thoroughly!"}
    ]


@pytest.fixture
def sample_session_data():
    """Return sample session data."""
    return {
        "session_id": "test-session-123",
        "user_id": "test-user",
        "messages": [
            {"role": "user", "content": "Hi", "timestamp": datetime.now().isoformat()},
            {"role": "assistant", "content": "Hello!", "timestamp": datetime.now().isoformat()}
        ],
        "created_at": datetime.now().isoformat(),
        "last_activity": datetime.now().isoformat()
    }


# =============================================================================
# MOCK OBJECTS
# =============================================================================

@pytest.fixture
def mock_llm_response():
    """Return mock LLM response."""
    return {
        "content": "This is a test response",
        "model": "test-model",
        "usage": {"input_tokens": 10, "output_tokens": 5}
    }


@pytest.fixture
def mock_anthropic_client():
    """Return mock Anthropic client."""
    client = Mock()
    response = Mock()
    message = Mock()
    message.text = "Test response from Claude"
    message.content = [message]
    response.content = [message]
    response.usage = Mock()
    response.usage.input_tokens = 10
    response.usage.output_tokens = 5
    client.messages.create.return_value = response
    return client


@pytest.fixture
def mock_http_client():
    """Return mock HTTP client."""
    client = AsyncMock()
    response = AsyncMock()
    response.status_code = 200
    response.json.return_value = {"status": "ok"}
    response.text = '{"status": "ok"}'
    client.get.return_value = response
    client.post.return_value = response
    return client


@pytest.fixture
def mock_telegram_bot():
    """Return mock Telegram bot."""
    bot = AsyncMock()
    bot.send_message = AsyncMock(return_value=Mock(message_id=123))
    bot.send_photo = AsyncMock(return_value=Mock(message_id=124))
    bot.get_me = AsyncMock(return_value=Mock(username="test_bot", first_name="Test Bot"))
    return bot


# =============================================================================
# DATABASE FIXTURES
# =============================================================================

@pytest.fixture
def sqlite_memory_db(temp_memory_dir):
    """Create SQLite memory database for testing."""
    db_path = temp_memory_dir / "test_memory.db"
    conn = sqlite3.connect(str(db_path))
    
    # Create tables
    conn.execute("""
        CREATE TABLE IF NOT EXISTS memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT NOT NULL,
            category TEXT,
            timestamp TEXT,
            importance REAL,
            metadata TEXT
        )
    """)
    conn.commit()
    
    yield conn
    conn.close()


@pytest.fixture
def populated_memory_db(sqlite_memory_db, sample_memory_entries):
    """Create populated memory database."""
    conn = sqlite_memory_db
    for entry in sample_memory_entries:
        conn.execute(
            """INSERT INTO memories (id, content, category, timestamp, importance, metadata)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                entry["id"],
                entry["content"],
                entry["category"],
                entry["timestamp"],
                entry["importance"],
                json.dumps(entry["metadata"])
            )
        )
    conn.commit()
    return conn


# =============================================================================
# FILE SYSTEM FIXTURES
# =============================================================================

@pytest.fixture
def sample_project_structure(temp_projects_dir):
    """Create sample project structure."""
    (temp_projects_dir / "prj001").mkdir()
    (temp_projects_dir / "prj001" / "README.md").write_text("# Project 1")
    (temp_projects_dir / "prj001" / "src").mkdir()
    (temp_projects_dir / "prj001" / "src" / "main.py").write_text("print('hello')")
    
    (temp_projects_dir / "prj002").mkdir()
    (temp_projects_dir / "prj002" / "README.md").write_text("# Project 2")
    
    return temp_projects_dir


@pytest.fixture
def sample_workspace_files(temp_workspace):
    """Create sample workspace files."""
    # SOUL.md
    (temp_workspace / "SOUL.md").write_text(sample_soul_content.__wrapped__())
    # USER.md
    (temp_workspace / "USER.md").write_text(sample_user_content.__wrapped__())
    # AGENTS.md
    (temp_workspace / "AGENTS.md").write_text(sample_agents_content.__wrapped__())
    
    return temp_workspace


# =============================================================================
# PERFORMANCE FIXTURES
# =============================================================================

@pytest.fixture
def performance_threshold():
    """Return performance thresholds."""
    return {
        "memory_store_init_ms": 100,
        "recall_query_ms": 50,
        "api_response_ms": 200,
        "db_write_ms": 20,
        "db_read_ms": 10
    }


@pytest.fixture
def load_test_params():
    """Return load testing parameters."""
    return {
        "concurrent_requests": 100,
        "total_requests": 1000,
        "ramp_up_seconds": 10,
        "max_response_time_ms": 500
    }


# =============================================================================
# ERROR SCENARIOS
# =============================================================================

@pytest.fixture
def error_scenarios():
    """Return common error scenarios."""
    return {
        "db_lock": Exception("database is locked"),
        "connection_error": ConnectionError("Failed to connect"),
        "timeout_error": TimeoutError("Request timed out"),
        "validation_error": ValueError("Invalid input"),
        "file_not_found": FileNotFoundError("File not found"),
        "permission_error": PermissionError("Permission denied")
    }


# =============================================================================
# ASSERTION HELPERS
# =============================================================================

def assert_valid_memory_entry(entry: Dict[str, Any]):
    """Assert that a memory entry is valid."""
    assert "id" in entry
    assert "content" in entry
    assert isinstance(entry["content"], str)
    assert len(entry["content"]) > 0


def assert_valid_session(session: Dict[str, Any]):
    """Assert that a session is valid."""
    assert "session_id" in session
    assert "user_id" in session
    assert "messages" in session
    assert isinstance(session["messages"], list)


def assert_valid_api_response(response: Dict[str, Any]):
    """Assert that an API response is valid."""
    assert "status" in response or "error" in response
    assert isinstance(response, dict)


# Make assertion helpers available globally
pytest.assert_valid_memory_entry = assert_valid_memory_entry
pytest.assert_valid_session = assert_valid_session
pytest.assert_valid_api_response = assert_valid_api_response
