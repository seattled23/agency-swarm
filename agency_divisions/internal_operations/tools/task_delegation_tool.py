from agency_swarm.tools import BaseTool
from pydantic import Field
import asyncio
from typing import Dict, List, Any, Optional
import uuid
from datetime import datetime
import logging
import os
import json
from dataclasses import dataclass, asdict

@dataclass
class TaskDefinition:
    """Data class for task definitions"""
    id: str
    name: str
    description: str
    priority: str
    dependencies: List[str]
    assigned_agent: Optional[str]
    status: str = "pending"
    created_at: str = None
    updated_at: str = None
    completion_percentage: float = 0.0
    subtasks: List[Dict] = None
    metadata: Dict = None

class TaskDelegationTool(BaseTool):
    """
    Tool for managing asynchronous task delegation between agents.
    Handles task creation, assignment, monitoring, and completion tracking.
    """
    
    operation: str = Field(
        ..., description="Operation to perform ('create_task', 'assign_task', 'update_task', 'get_tasks')"
    )
    
    agent_id: str = Field(
        ..., description="ID of the agent performing the operation"
    )
    
    data: Dict = Field(
        {}, description="Data for the operation (task details, updates, etc.)"
    )

    def __init__(self, **data):
        super().__init__(**data)
        self.tasks: Dict[str, TaskDefinition] = {}
        self.agent_tasks: Dict[str, List[str]] = {}  # Maps agents to their task IDs
        self.task_dependencies: Dict[str, List[str]] = {}  # Maps tasks to their dependency IDs
        self.setup_logging()
        self._load_state()

    def setup_logging(self):
        """Sets up logging for task delegation"""
        log_dir = "agency_divisions/internal_operations/logs/task_delegation"
        os.makedirs(log_dir, exist_ok=True)
        
        logging.basicConfig(
            filename=f"{log_dir}/task_delegation.log",
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger('TaskDelegation')

    async def run_async(self) -> Dict[str, Any]:
        """
        Asynchronously executes task delegation operations
        """
        try:
            if self.operation == "create_task":
                return await self._create_task()
            elif self.operation == "assign_task":
                return await self._assign_task()
            elif self.operation == "update_task":
                return await self._update_task()
            elif self.operation == "get_tasks":
                return await self._get_tasks()
            else:
                raise ValueError(f"Unknown operation: {self.operation}")
            
        except Exception as e:
            self.logger.error(f"Error in task delegation: {str(e)}")
            raise
        
        finally:
            await self._save_state()

    def run(self) -> Dict[str, Any]:
        """
        Synchronous wrapper for task delegation operations
        """
        return asyncio.run(self.run_async())

    async def _create_task(self) -> Dict[str, Any]:
        """Creates a new task"""
        try:
            task_data = self.data.get("task", {})
            task_id = str(uuid.uuid4())
            current_time = datetime.now().isoformat()
            
            task = TaskDefinition(
                id=task_id,
                name=task_data.get("name", ""),
                description=task_data.get("description", ""),
                priority=task_data.get("priority", "medium"),
                dependencies=task_data.get("dependencies", []),
                assigned_agent=None,
                status="pending",
                created_at=current_time,
                updated_at=current_time,
                subtasks=task_data.get("subtasks", []),
                metadata=task_data.get("metadata", {})
            )
            
            self.tasks[task_id] = task
            self.task_dependencies[task_id] = task.dependencies
            
            self.logger.info(f"Created task: {task_id}")
            
            return {
                "status": "success",
                "task_id": task_id,
                "task": asdict(task)
            }
            
        except Exception as e:
            self.logger.error(f"Error creating task: {str(e)}")
            raise

    async def _assign_task(self) -> Dict[str, Any]:
        """Assigns a task to an agent"""
        try:
            task_id = self.data.get("task_id")
            agent_id = self.data.get("agent_id")
            
            if task_id not in self.tasks:
                raise ValueError(f"Task not found: {task_id}")
            
            task = self.tasks[task_id]
            
            # Check if all dependencies are completed
            if not await self._check_dependencies(task_id):
                return {
                    "status": "error",
                    "message": "Task dependencies not met",
                    "pending_dependencies": [
                        dep_id for dep_id in task.dependencies
                        if self.tasks[dep_id].status != "completed"
                    ]
                }
            
            # Update task assignment
            task.assigned_agent = agent_id
            task.status = "assigned"
            task.updated_at = datetime.now().isoformat()
            
            # Update agent task mapping
            if agent_id not in self.agent_tasks:
                self.agent_tasks[agent_id] = []
            self.agent_tasks[agent_id].append(task_id)
            
            self.logger.info(f"Assigned task {task_id} to agent {agent_id}")
            
            return {
                "status": "success",
                "task_id": task_id,
                "agent_id": agent_id,
                "task": asdict(task)
            }
            
        except Exception as e:
            self.logger.error(f"Error assigning task: {str(e)}")
            raise

    async def _update_task(self) -> Dict[str, Any]:
        """Updates task status and progress"""
        try:
            task_id = self.data.get("task_id")
            updates = self.data.get("updates", {})
            
            if task_id not in self.tasks:
                raise ValueError(f"Task not found: {task_id}")
            
            task = self.tasks[task_id]
            
            # Update task fields
            for field, value in updates.items():
                if hasattr(task, field):
                    setattr(task, field, value)
            
            task.updated_at = datetime.now().isoformat()
            
            # If task is completed, check dependent tasks
            if task.status == "completed":
                await self._process_dependent_tasks(task_id)
            
            self.logger.info(f"Updated task {task_id}: {updates}")
            
            return {
                "status": "success",
                "task_id": task_id,
                "task": asdict(task)
            }
            
        except Exception as e:
            self.logger.error(f"Error updating task: {str(e)}")
            raise

    async def _get_tasks(self) -> Dict[str, Any]:
        """Retrieves tasks based on filters"""
        try:
            filters = self.data.get("filters", {})
            agent_id = filters.get("agent_id")
            status = filters.get("status")
            priority = filters.get("priority")
            
            tasks = self.tasks.values()
            
            # Apply filters
            if agent_id:
                tasks = [t for t in tasks if t.assigned_agent == agent_id]
            if status:
                tasks = [t for t in tasks if t.status == status]
            if priority:
                tasks = [t for t in tasks if t.priority == priority]
            
            return {
                "status": "success",
                "tasks": [asdict(t) for t in tasks]
            }
            
        except Exception as e:
            self.logger.error(f"Error retrieving tasks: {str(e)}")
            raise

    async def _check_dependencies(self, task_id: str) -> bool:
        """Checks if all task dependencies are completed"""
        task = self.tasks[task_id]
        
        for dep_id in task.dependencies:
            if dep_id not in self.tasks:
                return False
            if self.tasks[dep_id].status != "completed":
                return False
        
        return True

    async def _process_dependent_tasks(self, completed_task_id: str):
        """Processes tasks that depend on the completed task"""
        for task_id, dependencies in self.task_dependencies.items():
            if completed_task_id in dependencies:
                # Check if all dependencies are now completed
                if await self._check_dependencies(task_id):
                    task = self.tasks[task_id]
                    task.status = "ready"
                    task.updated_at = datetime.now().isoformat()
                    
                    self.logger.info(f"Task {task_id} is now ready for assignment")

    async def _save_state(self):
        """Saves current state to disk"""
        try:
            state_dir = "agency_divisions/internal_operations/data/task_delegation"
            os.makedirs(state_dir, exist_ok=True)
            
            state = {
                "tasks": {k: asdict(v) for k, v in self.tasks.items()},
                "agent_tasks": self.agent_tasks,
                "task_dependencies": self.task_dependencies,
                "last_updated": datetime.now().isoformat()
            }
            
            state_file = f"{state_dir}/state.json"
            with open(state_file, 'w') as f:
                json.dump(state, f, indent=2)
                
        except Exception as e:
            self.logger.error(f"Error saving state: {str(e)}")
            raise

    def _load_state(self):
        """Loads state from disk"""
        try:
            state_file = "agency_divisions/internal_operations/data/task_delegation/state.json"
            if os.path.exists(state_file):
                with open(state_file, 'r') as f:
                    state = json.load(f)
                    
                    # Reconstruct TaskDefinition objects
                    self.tasks = {
                        k: TaskDefinition(**v)
                        for k, v in state.get("tasks", {}).items()
                    }
                    self.agent_tasks = state.get("agent_tasks", {})
                    self.task_dependencies = state.get("task_dependencies", {})
                    
        except Exception as e:
            self.logger.error(f"Error loading state: {str(e)}")
            self.tasks = {}
            self.agent_tasks = {}
            self.task_dependencies = {}

if __name__ == "__main__":
    # Test the task delegation tool
    async def test_task_delegation():
        tool = TaskDelegationTool(
            operation="create_task",
            agent_id="test_agent",
            data={
                "task": {
                    "name": "Test Task",
                    "description": "A test task",
                    "priority": "high",
                    "dependencies": [],
                    "subtasks": [
                        {
                            "name": "Subtask 1",
                            "description": "First subtask",
                            "status": "pending"
                        }
                    ],
                    "metadata": {
                        "category": "test",
                        "estimated_duration": "1h"
                    }
                }
            }
        )
        
        try:
            # Create task
            result = await tool.run_async()
            task_id = result["task_id"]
            print("Created task:", json.dumps(result, indent=2))
            
            # Assign task
            tool.operation = "assign_task"
            tool.data = {
                "task_id": task_id,
                "agent_id": "worker_agent_1"
            }
            result = await tool.run_async()
            print("Assigned task:", json.dumps(result, indent=2))
            
            # Update task
            tool.operation = "update_task"
            tool.data = {
                "task_id": task_id,
                "updates": {
                    "status": "in_progress",
                    "completion_percentage": 50.0
                }
            }
            result = await tool.run_async()
            print("Updated task:", json.dumps(result, indent=2))
            
            # Get tasks
            tool.operation = "get_tasks"
            tool.data = {
                "filters": {
                    "status": "in_progress",
                    "priority": "high"
                }
            }
            result = await tool.run_async()
            print("Retrieved tasks:", json.dumps(result, indent=2))
            
        except Exception as e:
            print(f"Error in task delegation test: {str(e)}")
    
    asyncio.run(test_task_delegation()) 