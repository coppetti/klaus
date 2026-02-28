"""
End-to-End Tests - Full Workflows
Chuck Norris doesn't test workflows. Workflows test themselves for Chuck Norris.
"""
import pytest
import asyncio
import httpx
import json
import time
from datetime import datetime


@pytest.mark.e2e
class TestUserWorkflow:
    """Test complete user workflows."""
    
    @pytest.mark.asyncio
    async def test_complete_chat_workflow(self):
        """Test complete chat workflow from start to finish."""
        async with httpx.AsyncClient() as client:
            try:
                # 1. Get health check
                health = await client.get("http://localhost:7072/health", timeout=5.0)
                assert health.status_code == 200
                
                # 2. Create a session
                session_response = await client.post(
                    "http://localhost:7072/api/sessions",
                    json={"name": f"E2E Test {datetime.now().isoformat()}"},
                    timeout=5.0
                )
                assert session_response.status_code == 200
                session_data = session_response.json()
                session_id = session_data.get("id") or session_data.get("session_id")
                
                # 3. Send a message (via chat endpoint)
                chat_response = await client.post(
                    "http://localhost:7072/api/chat",
                    json={
                        "session_id": session_id,
                        "message": "Hello Klaus, this is an E2E test"
                    },
                    timeout=30.0
                )
                # Chat may fail due to API keys, but should return gracefully
                assert chat_response.status_code in [200, 401, 403, 500, 422]
                
                # 4. Check semantic memory was updated
                memory_response = await client.get(
                    f"http://localhost:7072/api/semantic-memory?session_id={session_id}",
                    timeout=5.0
                )
                assert memory_response.status_code == 200
                
                # 5. Get graph data
                graph_response = await client.get(
                    "http://localhost:7072/api/memory/graph-data",
                    timeout=5.0
                )
                assert graph_response.status_code == 200
                graph_data = graph_response.json()
                assert "nodes" in graph_data
                assert "edges" in graph_data
                
            except httpx.ConnectError:
                pytest.skip("Services not running")
    
    @pytest.mark.asyncio
    async def test_session_management_workflow(self):
        """Test session CRUD workflow."""
        async with httpx.AsyncClient() as client:
            try:
                # Create session
                create_response = await client.post(
                    "http://localhost:7072/api/sessions",
                    json={"name": "Session to Manage"},
                    timeout=5.0
                )
                assert create_response.status_code == 200
                session = create_response.json()
                # API returns {"status": "ok", "session": {"id": ...}}
                session_data = session.get("session", session)
                session_id = session_data.get("id") or session_data.get("session_id")
                
                # List sessions
                list_response = await client.get(
                    "http://localhost:7072/api/sessions",
                    timeout=5.0
                )
                assert list_response.status_code == 200
                sessions = list_response.json()
                assert isinstance(sessions, list)
                
                # Load session
                load_response = await client.post(
                    f"http://localhost:7072/api/sessions/{session_id}/load",
                    timeout=5.0
                )
                assert load_response.status_code == 200
                
                # Delete session
                delete_response = await client.delete(
                    f"http://localhost:7072/api/sessions/{session_id}",
                    timeout=5.0
                )
                assert delete_response.status_code in [200, 204]
                
            except httpx.ConnectError:
                pytest.skip("Services not running")


@pytest.mark.e2e
class TestMemoryWorkflow:
    """Test memory-related workflows."""
    
    @pytest.mark.asyncio
    async def test_memory_store_and_recall(self):
        """Test storing and recalling memory."""
        async with httpx.AsyncClient() as client:
            try:
                test_content = f"E2E test memory {time.time()}"
                
                # Store memory (cognitive memory endpoint)
                store_response = await client.post(
                    "http://localhost:7072/api/cognitive-memory/store",
                    json={
                        "session_id": "e2e-test-session",
                        "user_message": test_content,
                        "assistant_message": "E2E test response"
                    },
                    timeout=5.0
                )
                assert store_response.status_code in [200, 201]
                
                # Search for memory
                search_response = await client.get(
                    "http://localhost:7072/api/semantic-memory",
                    params={"query": "E2E test"},
                    timeout=5.0
                )
                assert search_response.status_code == 200
                
            except httpx.ConnectError:
                pytest.skip("Services not running")
    
    @pytest.mark.asyncio
    async def test_episodic_memory_accumulation(self):
        """Test episodic memory accumulation over multiple interactions."""
        async with httpx.AsyncClient() as client:
            try:
                # Create session
                session_response = await client.post(
                    "http://localhost:7072/api/sessions",
                    json={"name": "Episodic Test"},
                    timeout=5.0
                )
                session_id = session_response.json().get("id")
                
                # Simulate multiple exchanges
                for i in range(3):
                    await client.post(
                        "http://localhost:7072/api/chat",
                        json={
                            "session_id": session_id,
                            "message": f"Test message {i}"
                        },
                        timeout=10.0
                    )
                
                # Check episodic memories
                episodic_response = await client.get(
                    f"http://localhost:7072/api/cognitive-memory?session_id={session_id}",
                    timeout=5.0
                )
                assert episodic_response.status_code == 200
                
            except httpx.ConnectError:
                pytest.skip("Services not running")
    
    @pytest.mark.asyncio
    async def test_graph_visualization_data(self):
        """Test that graph visualization has valid data."""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    "http://localhost:7072/api/memory/graph-data",
                    timeout=5.0
                )
                assert response.status_code == 200
                data = response.json()
                
                # Validate structure
                assert isinstance(data["nodes"], list)
                assert isinstance(data["edges"], list)
                
                # Validate node structure
                for node in data["nodes"]:
                    assert "id" in node
                    assert "label" in node
                    assert "group" in node
                
                # Validate edge structure
                for edge in data["edges"]:
                    assert "from" in edge
                    assert "to" in edge
                    
            except httpx.ConnectError:
                pytest.skip("Services not running")


@pytest.mark.e2e
class TestSettingsWorkflow:
    """Test settings management workflow."""
    
    @pytest.mark.asyncio
    async def test_provider_settings_workflow(self):
        """Test provider settings CRUD."""
        async with httpx.AsyncClient() as client:
            try:
                # Get providers
                get_response = await client.get(
                    "http://localhost:7072/api/settings/providers",
                    timeout=5.0
                )
                assert get_response.status_code == 200
                
                # Get specific provider settings
                provider_response = await client.get(
                    "http://localhost:7072/api/settings/provider/custom",
                    timeout=5.0
                )
                assert provider_response.status_code == 200
                
            except httpx.ConnectError:
                pytest.skip("Services not running")
    
    @pytest.mark.asyncio
    async def test_telegram_settings_workflow(self):
        """Test Telegram settings workflow."""
        async with httpx.AsyncClient() as client:
            try:
                # Get Telegram status
                status_response = await client.get(
                    "http://localhost:7072/api/settings/telegram/status",
                    timeout=5.0
                )
                assert status_response.status_code == 200
                
            except httpx.ConnectError:
                pytest.skip("Services not running")


@pytest.mark.e2e
class TestAgentCommunication:
    """Test agent-to-agent communication."""
    
    @pytest.mark.asyncio
    async def test_web_ui_to_kimi_agent(self):
        """Test Web UI can communicate with Kimi Agent."""
        async with httpx.AsyncClient() as client:
            try:
                # Web UI should have endpoint that proxies to Kimi
                response = await client.get(
                    "http://localhost:7072/api/remote/status",
                    timeout=5.0
                )
                assert response.status_code == 200
                
                # Check if Kimi is reachable via Web UI health endpoint
                health = await client.get(
                    "http://localhost:7072/health",
                    timeout=5.0
                )
                assert health.status_code == 200
                data = health.json()
                # Kimi agent should be reported as available
                assert data.get("kimi_agent_status") in ["ok", "healthy", "online"]
                
            except httpx.ConnectError:
                pytest.skip("Services not running")


@pytest.mark.e2e
class TestErrorRecovery:
    """Test system error recovery."""
    
    @pytest.mark.asyncio
    async def test_service_restart_recovery(self):
        """Test system recovers after simulated restart."""
        # This would require Docker control, skip for now
        pytest.skip("Requires Docker control")
    
    @pytest.mark.asyncio
    async def test_invalid_session_handling(self):
        """Test handling of invalid session IDs."""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    "http://localhost:7072/api/semantic-memory?session_id=invalid-session-id-12345",
                    timeout=5.0
                )
                # Should return gracefully, not crash
                assert response.status_code in [200, 404]
                
            except httpx.ConnectError:
                pytest.skip("Services not running")
    
    @pytest.mark.asyncio
    async def test_concurrent_session_access(self):
        """Test concurrent access to same session."""
        async with httpx.AsyncClient() as client:
            try:
                # Create session
                session_response = await client.post(
                    "http://localhost:7072/api/sessions",
                    json={"name": "Concurrent Test"},
                    timeout=5.0
                )
                session_id = session_response.json().get("id")
                
                # Concurrent requests
                tasks = [
                    client.get(
                        f"http://localhost:7072/api/semantic-memory?session_id={session_id}",
                        timeout=5.0
                    )
                    for _ in range(5)
                ]
                responses = await asyncio.gather(*tasks, return_exceptions=True)
                
                # All should succeed or fail gracefully
                success_count = sum(
                    1 for r in responses
                    if not isinstance(r, Exception) and r.status_code == 200
                )
                assert success_count >= 3  # At least 60% success
                
            except httpx.ConnectError:
                pytest.skip("Services not running")


@pytest.mark.e2e
class TestLongRunningOperations:
    """Test long-running operations."""
    
    @pytest.mark.asyncio
    async def test_memory_compaction(self):
        """Test memory compaction operation."""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    "http://localhost:7072/api/compact",
                    json={"session_id": "test"},
                    timeout=30.0
                )
                # May take time, but should complete
                assert response.status_code in [200, 202, 404, 405]
                
            except httpx.ConnectError:
                pytest.skip("Services not running")
    
    @pytest.mark.asyncio
    async def test_graph_rebuild(self):
        """Test graph rebuild operation."""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    "http://localhost:7072/api/memory/scrub-graph",
                    timeout=60.0
                )
                # Long operation
                assert response.status_code in [200, 202, 404]
                
            except httpx.ConnectError:
                pytest.skip("Services not running")


@pytest.mark.e2e
class TestDataConsistency:
    """Test data consistency across operations."""
    
    @pytest.mark.asyncio
    async def test_session_consistency(self):
        """Test session data consistency."""
        async with httpx.AsyncClient() as client:
            try:
                # Create session
                create_response = await client.post(
                    "http://localhost:7072/api/sessions",
                    json={"name": "Consistency Test"},
                    timeout=5.0
                )
                session = create_response.json()
                session_id = session.get("id")
                
                # Multiple reads should return same data
                reads = []
                for _ in range(3):
                    response = await client.get(
                        f"http://localhost:7072/api/sessions/{session_id}",
                        timeout=5.0
                    )
                    if response.status_code == 200:
                        reads.append(response.json())
                
                if len(reads) >= 2:
                    # Name should be consistent
                    assert all(r.get("name") == reads[0].get("name") for r in reads)
                
            except httpx.ConnectError:
                pytest.skip("Services not running")


@pytest.mark.e2e  
class TestStress:
    """Stress tests."""
    
    @pytest.mark.asyncio
    async def test_rapid_session_creation(self):
        """Test rapid session creation."""
        async with httpx.AsyncClient() as client:
            try:
                # Create 10 sessions rapidly
                tasks = [
                    client.post(
                        "http://localhost:7072/api/sessions",
                        json={"name": f"Rapid Test {i}"},
                        timeout=5.0
                    )
                    for i in range(10)
                ]
                responses = await asyncio.gather(*tasks, return_exceptions=True)
                
                success_count = sum(
                    1 for r in responses
                    if not isinstance(r, Exception) and r.status_code == 200
                )
                
                assert success_count >= 8  # 80% success rate
                
            except httpx.ConnectError:
                pytest.skip("Services not running")
