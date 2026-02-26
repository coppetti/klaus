"""
Unit Tests for Agent Spawner
============================
"""
import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "core"))

from agent_spawner import AgentSpawner, SubAgentTask, TaskStatus, get_spawner


class TestAgentSpawner:
    """Test suite for AgentSpawner."""
    
    @pytest.fixture
    def spawner(self):
        """Create a fresh spawner instance."""
        return AgentSpawner(mode="local", base_url="http://localhost:8082")
    
    @pytest.mark.asyncio
    async def test_spawn_agent_creates_task(self, spawner):
        """Test that spawn_agent creates a task entry."""
        task_id = await spawner.spawn_agent(
            template="developer",
            task="Review this code",
            context={"code": "print('hello')"},
            parent_session_id="session_123"
        )
        
        assert task_id.startswith("task_")
        assert task_id in spawner.tasks
        
        task = spawner.tasks[task_id]
        assert task.template == "developer"
        assert task.task_description == "Review this code"
        assert task.status == TaskStatus.PENDING
        assert task.parent_session_id == "session_123"
    
    @pytest.mark.asyncio
    async def test_get_task_status_existing(self, spawner):
        """Test getting status of existing task."""
        task_id = await spawner.spawn_agent(
            template="developer",
            task="Test task",
            context={},
            parent_session_id="session_123"
        )
        
        status = spawner.get_task_status(task_id)
        
        assert status is not None
        assert status["task_id"] == task_id
        assert status["template"] == "developer"
        assert status["status"] == "pending"
    
    def test_get_task_status_nonexistent(self, spawner):
        """Test getting status of non-existent task."""
        status = spawner.get_task_status("nonexistent_task")
        assert status is None
    
    def test_cancel_task_pending(self, spawner):
        """Test canceling a pending task."""
        # Create a task manually
        task = SubAgentTask(
            task_id="test_cancel",
            parent_session_id="session_123",
            template="developer",
            task_description="Test",
            context={},
            status=TaskStatus.PENDING
        )
        spawner.tasks["test_cancel"] = task
        
        result = spawner.cancel_task("test_cancel")
        
        assert result is True
        assert task.status == TaskStatus.CANCELLED
    
    def test_cancel_task_completed(self, spawner):
        """Test canceling an already completed task."""
        task = SubAgentTask(
            task_id="test_completed",
            parent_session_id="session_123",
            template="developer",
            task_description="Test",
            context={},
            status=TaskStatus.COMPLETED
        )
        spawner.tasks["test_completed"] = task
        
        result = spawner.cancel_task("test_completed")
        
        assert result is False  # Can't cancel completed task
    
    def test_get_active_tasks(self, spawner):
        """Test getting list of active tasks."""
        # Create tasks with different statuses
        spawner.tasks["active1"] = SubAgentTask(
            task_id="active1", parent_session_id="s1", template="dev",
            task_description="Test", context={}, status=TaskStatus.RUNNING
        )
        spawner.tasks["active2"] = SubAgentTask(
            task_id="active2", parent_session_id="s1", template="arch",
            task_description="Test", context={}, status=TaskStatus.PENDING
        )
        spawner.tasks["completed"] = SubAgentTask(
            task_id="completed", parent_session_id="s1", template="fin",
            task_description="Test", context={}, status=TaskStatus.COMPLETED
        )
        
        active = spawner.get_active_tasks()
        
        assert len(active) == 2
        assert all(t["status"] in ["pending", "running"] for t in active)
    
    def test_get_active_tasks_filtered_by_session(self, spawner):
        """Test getting active tasks filtered by session."""
        spawner.tasks["s1_task"] = SubAgentTask(
            task_id="s1_task", parent_session_id="session_1", template="dev",
            task_description="Test", context={}, status=TaskStatus.RUNNING
        )
        spawner.tasks["s2_task"] = SubAgentTask(
            task_id="s2_task", parent_session_id="session_2", template="dev",
            task_description="Test", context={}, status=TaskStatus.RUNNING
        )
        
        active = spawner.get_active_tasks(parent_session_id="session_1")
        
        assert len(active) == 1
        assert active[0]["task_id"] == "s1_task"
    
    def test_build_system_prompt(self, spawner):
        """Test system prompt construction."""
        task = SubAgentTask(
            task_id="test_prompt",
            parent_session_id="session_123",
            template="developer",
            task_description="Review code",
            context={"language": "python", "code": "print('test')"}
        )
        
        prompt = spawner._build_system_prompt(task)
        
        assert "developer" in prompt.lower()
        assert "DEVELOPER" in prompt
        assert "session_123" in prompt
        assert "python" in prompt.lower()
        assert "Review code" in prompt


class TestSingleton:
    """Test singleton pattern."""
    
    def test_get_spawner_singleton(self):
        """Test that get_spawner returns same instance."""
        spawner1 = get_spawner()
        spawner2 = get_spawner()
        
        assert spawner1 is spawner2
    
    def test_get_spawner_creates_instance(self):
        """Test that get_spawner creates instance on first call."""
        # Reset singleton for test
        import agent_spawner
        agent_spawner._spawner_instance = None
        
        spawner = get_spawner(mode="api", base_url="http://test:8080")
        
        assert spawner.mode == "api"
        assert spawner.base_url == "http://test:8080"
