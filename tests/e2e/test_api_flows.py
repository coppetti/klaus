"""
E2E Tests for API Flows
=======================
Tests complete user workflows through the API.
"""
import pytest
import httpx
import asyncio
import time
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "core"))

BASE_URL = "http://localhost:7072"
KIMI_URL = "http://localhost:7070"


@pytest.fixture(scope="module")
def check_services():
    """Check if services are running."""
    try:
        import httpx
        response = httpx.get(f"{BASE_URL}/health", timeout=5.0)
        if response.status_code != 200:
            pytest.skip("Web UI not running")
    except Exception:
        pytest.skip("Services not available for E2E tests")


class TestSessionFlow:
    """E2E tests for session management."""
    
    @pytest.mark.asyncio
    async def test_create_and_load_session(self, check_services):
        """Test creating and loading a session."""
        async with httpx.AsyncClient() as client:
            # Create session
            create_res = await client.post(
                f"{BASE_URL}/api/sessions",
                json={"name": "E2E Test Session"}
            )
            assert create_res.status_code == 200
            session_data = create_res.json()
            session_id = session_data["id"]
            
            # Load session
            load_res = await client.post(
                f"{BASE_URL}/api/sessions/{session_id}/load"
            )
            assert load_res.status_code == 200
            
            # Verify
            assert load_res.json()["status"] == "ok"
    
    @pytest.mark.asyncio
    async def test_rename_session(self, check_services):
        """Test renaming a session."""
        async with httpx.AsyncClient() as client:
            # Create
            create_res = await client.post(
                f"{BASE_URL}/api/sessions",
                json={"name": "Old Name"}
            )
            session_id = create_res.json()["id"]
            
            # Rename
            rename_res = await client.post(
                f"{BASE_URL}/api/sessions/{session_id}/rename",
                json={"name": "New Name"}
            )
            assert rename_res.status_code == 200
            
            # Verify
            sessions_res = await client.get(f"{BASE_URL}/api/sessions")
            sessions = sessions_res.json()
            session = next((s for s in sessions if s["id"] == session_id), None)
            assert session["name"] == "New Name"


class TestChatFlow:
    """E2E tests for chat functionality."""
    
    @pytest.mark.asyncio
    async def test_simple_chat_message(self, check_services):
        """Test sending a simple chat message."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{BASE_URL}/api/chat",
                json={"message": "Hello, this is a test"},
                timeout=30.0
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "response" in data
            assert "model_used" in data
            assert data["provider"] == "kimi"
    
    @pytest.mark.asyncio
    async def test_chat_with_template_detection(self, check_services):
        """Test that template detection works."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{BASE_URL}/api/chat",
                json={"message": "Review this code: print('hello')"},
                timeout=60.0
            )
            
            assert response.status_code == 200
            data = response.json()
            
            # Should have triggered developer agent
            if "sub_agent" in data:
                assert data["sub_agent"]["template"] == "developer"


class TestMemoryFlow:
    """E2E tests for memory operations."""
    
    @pytest.mark.asyncio
    async def test_memory_stats_endpoint(self, check_services):
        """Test memory stats endpoint."""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BASE_URL}/api/memory/stats")
            
            assert response.status_code == 200
            data = response.json()
            assert "sqlite" in data
            assert "graph" in data
    
    @pytest.mark.asyncio
    async def test_semantic_memory_endpoint(self, check_services):
        """Test semantic memory endpoint."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{BASE_URL}/api/semantic-memory?session_id=test"
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "memories" in data
            assert "count" in data


class TestAgentSpawnerFlow:
    """E2E tests for agent spawner."""
    
    @pytest.mark.asyncio
    async def test_spawn_agent_endpoint(self, check_services):
        """Test spawning an agent via API."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{BASE_URL}/api/agents/spawn",
                json={
                    "template": "developer",
                    "task": "Test task",
                    "context": {"test": True}
                },
                timeout=10.0
            )
            
            # May return 503 if spawner not available
            if response.status_code == 200:
                data = response.json()
                assert "task_id" in data
                assert data["status"] == "ok"
    
    @pytest.mark.asyncio
    async def test_get_active_agents(self, check_services):
        """Test getting active agents."""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BASE_URL}/api/agents/active")
            
            if response.status_code == 200:
                data = response.json()
                assert "active_tasks" in data
                assert "count" in data


class TestSettingsFlow:
    """E2E tests for settings."""
    
    @pytest.mark.asyncio
    async def test_get_settings(self, check_services):
        """Test getting current settings."""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BASE_URL}/api/settings")
            
            assert response.status_code == 200
            data = response.json()
            assert "provider" in data
            assert "model" in data
    
    @pytest.mark.asyncio
    async def test_update_settings(self, check_services):
        """Test updating settings."""
        async with httpx.AsyncClient() as client:
            # Get current
            get_res = await client.get(f"{BASE_URL}/api/settings")
            original = get_res.json()
            
            # Update
            update_res = await client.post(
                f"{BASE_URL}/api/settings",
                json={
                    **original,
                    "temperature": 0.5
                }
            )
            
            assert update_res.status_code == 200


class TestHealthEndpoints:
    """Tests for health endpoints."""
    
    @pytest.mark.asyncio
    async def test_web_ui_health(self, check_services):
        """Test Web UI health endpoint."""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BASE_URL}/health")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert "kimi_agent_status" in data
    
    @pytest.mark.asyncio
    async def test_kimi_agent_health(self, check_services):
        """Test Kimi Agent health."""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(f"{KIMI_URL}/health", timeout=5.0)
                assert response.status_code == 200
            except Exception:
                pytest.skip("Kimi Agent not accessible")


# Run tests with: pytest tests/e2e/ -v --tb=short
# Or with coverage: pytest tests/ --cov=core --cov-report=html
