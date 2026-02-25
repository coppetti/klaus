"""
Agent Spawner - Multi-Agent System for Klaus
==============================================

Allows Klaus to spawn specialized sub-agents for specific tasks.
Each sub-agent runs in its own context/session and communicates back to parent.

Usage:
    from agent_spawner import AgentSpawner
    
    # Spawn a developer agent
    task_id = await spawner.spawn_agent(
        template="developer",
        task="Review this code for bugs",
        context={"code": "...", "language": "python"}
    )
    
    # Check status
    status = spawner.get_task_status(task_id)
    
    # Get result when done
    result = await spawner.get_result(task_id)
"""

import asyncio
import json
import uuid
import httpx
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import sys
from pathlib import Path

# Add core to path
sys.path.insert(0, str(Path(__file__).parent))


class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class SubAgentTask:
    """A task assigned to a sub-agent."""
    task_id: str
    parent_session_id: str
    template: str
    task_description: str
    context: Dict[str, Any]
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[str] = None
    error: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    agent_session_id: Optional[str] = None
    messages: List[Dict] = field(default_factory=list)


class AgentSpawner:
    """
    Spawns specialized sub-agents for parallel task execution.
    
    Supports two modes:
    - LOCAL: Spawns agents via local API calls (IDE mode)
    - API: Spawns agents via Kimi Agent API (Web/Telegram mode)
    """
    
    def __init__(self, mode: str = "local", base_url: str = "http://localhost:7070"):
        self.mode = mode
        self.base_url = base_url
        self.tasks: Dict[str, SubAgentTask] = {}
        self._callbacks: Dict[str, Callable] = {}
        
    async def spawn_agent(
        self,
        template: str,
        task: str,
        context: Dict[str, Any],
        parent_session_id: str,
        provider: str = "kimi",
        model: str = "kimi-k2-0711"
    ) -> str:
        """
        Spawn a new sub-agent with specific template and task.
        
        Args:
            template: Agent template (developer, architect, finance, etc.)
            task: Task description for the sub-agent
            context: Additional context (code, files, etc.)
            parent_session_id: Parent agent's session ID
            provider: LLM provider to use
            model: Model to use
            
        Returns:
            task_id: Unique ID to track this task
        """
        task_id = f"task_{uuid.uuid4().hex[:8]}"
        
        subtask = SubAgentTask(
            task_id=task_id,
            parent_session_id=parent_session_id,
            template=template,
            task_description=task,
            context=context,
            status=TaskStatus.PENDING
        )
        
        self.tasks[task_id] = subtask
        
        # Start the task asynchronously
        asyncio.create_task(self._execute_task(task_id, provider, model))
        
        return task_id
    
    async def _execute_task(self, task_id: str, provider: str, model: str):
        """Execute the sub-agent task."""
        task = self.tasks[task_id]
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now().isoformat()
        
        try:
            if self.mode == "local":
                result = await self._execute_local(task, provider, model)
            else:
                result = await self._execute_api(task, provider, model)
                
            task.result = result
            task.status = TaskStatus.COMPLETED
            
        except Exception as e:
            task.error = str(e)
            task.status = TaskStatus.FAILED
            
        task.completed_at = datetime.now().isoformat()
        
        # Trigger callback if registered
        if task_id in self._callbacks:
            try:
                await self._callbacks[task_id](task)
            except Exception as e:
                print(f"Callback error for {task_id}: {e}")
    
    async def _execute_local(self, task: SubAgentTask, provider: str, model: str) -> str:
        """Execute task via local API (IDE mode)."""
        
        # 1. Create a new session for the sub-agent
        async with httpx.AsyncClient() as client:
            # Create session
            session_res = await client.post(
                f"{self.base_url}/api/sessions",
                json={
                    "name": f"SubAgent-{task.template}-{task.task_id[:6]}",
                    "template": task.template
                }
            )
            session_data = session_res.json()
            task.agent_session_id = session_data.get("id")
            
            # 2. Send the task as first message with context
            system_context = self._build_system_prompt(task)
            
            messages = [
                {"role": "system", "content": system_context},
                {"role": "user", "content": task.task_description}
            ]
            
            # Call the LLM directly via router
            from llm_router import chat_with_provider
            
            response = await chat_with_provider(
                messages=messages,
                provider=provider,
                model=model,
                temperature=0.7,
                max_tokens=4096
            )
            
            # Store conversation
            task.messages = messages + [{"role": "assistant", "content": response}]
            
            return response
    
    async def _execute_api(self, task: SubAgentTask, provider: str, model: str) -> str:
        """Execute task via Kimi Agent API (Web mode)."""
        
        async with httpx.AsyncClient() as client:
            # Call the chat endpoint
            res = await client.post(
                f"{self.base_url}/api/chat",
                json={
                    "message": task.task_description,
                    "template": task.template,
                    "context": task.context,
                    "provider": provider,
                    "model": model,
                    "system_prompt": self._build_system_prompt(task)
                },
                timeout=120.0
            )
            
            data = res.json()
            return data.get("response", "No response")
    
    def _build_system_prompt(self, task: SubAgentTask) -> str:
        """Build system prompt for sub-agent."""
        
        base_prompt = f"""You are a specialized {task.template} agent spawned by Klaus (the main AI Solutions Architect).

YOUR ROLE:
- Focus exclusively on: {task.template.upper()} tasks
- You are working on a SUB-TASK assigned by Klaus
- Do not deviate from your specialization

TASK CONTEXT:
- Parent Session: {task.parent_session_id}
- Your Task ID: {task.task_id}
- Original Task: {task.task_description}

ADDITIONAL CONTEXT PROVIDED:
{json.dumps(task.context, indent=2)}

WORKFLOW:
1. Analyze the task carefully
2. Execute to the best of your ability
3. Return a CLEAR, CONCISE result
4. If you need clarification, ask specific questions

COMMUNICATION STYLE:
- Be direct and technical
- Provide actionable results
- Include code examples when relevant
- Note any assumptions you made

Remember: Klaus is waiting for your result to integrate into the main workflow.
"""
        
        # Load template SOUL if available
        try:
            template_path = Path(__file__).parent.parent / "templates" / task.template / "SOUL.md"
            if template_path.exists():
                soul_content = template_path.read_text()
                base_prompt += f"\n\n=== TEMPLATE PERSONALITY ===\n{soul_content[:2000]}\n"
        except Exception:
            pass
            
        return base_prompt
    
    def get_task_status(self, task_id: str) -> Optional[Dict]:
        """Get current status of a task."""
        task = self.tasks.get(task_id)
        if not task:
            return None
            
        return {
            "task_id": task.task_id,
            "status": task.status.value,
            "template": task.template,
            "created_at": task.created_at,
            "started_at": task.started_at,
            "completed_at": task.completed_at,
            "has_result": task.result is not None,
            "has_error": task.error is not None
        }
    
    async def get_result(self, task_id: str, timeout: float = 300.0) -> Optional[str]:
        """
        Wait for and retrieve task result.
        
        Args:
            task_id: Task to wait for
            timeout: Maximum time to wait (seconds)
            
        Returns:
            Result string or None if timeout/failed
        """
        start_time = asyncio.get_event_loop().time()
        
        while True:
            task = self.tasks.get(task_id)
            if not task:
                return None
                
            if task.status == TaskStatus.COMPLETED:
                return task.result
                
            if task.status == TaskStatus.FAILED:
                raise Exception(f"Task failed: {task.error}")
                
            if task.status == TaskStatus.CANCELLED:
                return None
                
            # Check timeout
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed > timeout:
                raise TimeoutError(f"Task {task_id} timed out after {timeout}s")
                
            await asyncio.sleep(0.5)
    
    def register_callback(self, task_id: str, callback: Callable):
        """Register a callback to be called when task completes."""
        self._callbacks[task_id] = callback
    
    def cancel_task(self, task_id: str) -> bool:
        """Cancel a running task."""
        task = self.tasks.get(task_id)
        if task and task.status in [TaskStatus.PENDING, TaskStatus.RUNNING]:
            task.status = TaskStatus.CANCELLED
            return True
        return False
    
    def get_active_tasks(self, parent_session_id: Optional[str] = None) -> List[Dict]:
        """Get list of active (pending/running) tasks."""
        active = []
        for task in self.tasks.values():
            if task.status in [TaskStatus.PENDING, TaskStatus.RUNNING]:
                if parent_session_id is None or task.parent_session_id == parent_session_id:
                    active.append({
                        "task_id": task.task_id,
                        "template": task.template,
                        "status": task.status.value,
                        "started_at": task.started_at
                    })
        return active
    
    def get_task_history(self, parent_session_id: Optional[str] = None) -> List[Dict]:
        """Get history of all tasks (completed/failed)."""
        history = []
        for task in self.tasks.values():
            if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
                if parent_session_id is None or task.parent_session_id == parent_session_id:
                    history.append({
                        "task_id": task.task_id,
                        "template": task.template,
                        "status": task.status.value,
                        "created_at": task.created_at,
                        "completed_at": task.completed_at,
                        "result_preview": task.result[:200] if task.result else None,
                        "error": task.error
                    })
        return history


# Singleton instance
_spawner_instance: Optional[AgentSpawner] = None


def get_spawner(mode: str = "local", base_url: str = "http://localhost:7070") -> AgentSpawner:
    """Get or create singleton spawner instance."""
    global _spawner_instance
    if _spawner_instance is None:
        _spawner_instance = AgentSpawner(mode=mode, base_url=base_url)
    return _spawner_instance
