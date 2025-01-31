from typing import Dict, List, Optional, Any
import asyncio
from datetime import datetime
import logging
from pathlib import Path

from ..models.task_model import TaskDefinition, TaskStatus, TaskPriority, TaskMetrics
from ..storage.task_storage import TaskStorage

class TaskService:
    """
    Task management service that coordinates task operations using the unified model.
    Provides high-level task management functionality and maintains system consistency.
    """

    def __init__(self, storage: Optional[TaskStorage] = None):
        self.storage = storage or TaskStorage()
        self.setup_logging()

        # Cache for task dependencies and states
        self._dependency_cache: Dict[str, List[str]] = {}  # task_id -> dependent_task_ids
        self._agent_tasks: Dict[str, List[str]] = {}      # agent_id -> task_ids
        self._division_tasks: Dict[str, List[str]] = {}   # division -> task_ids

    def setup_logging(self):
        """Set up logging for the task service"""
        log_dir = Path("logs/task_service")
        log_dir.mkdir(parents=True, exist_ok=True)

        logging.basicConfig(
            filename=log_dir / "task_service.log",
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger('TaskService')

    async def create_task(self,
                         title: str,
                         description: str,
                         priority: TaskPriority,
                         parent_id: Optional[str] = None,
                         dependencies: Optional[List[str]] = None,
                         assigned_agent: Optional[str] = None,
                         assigned_division: Optional[str] = None,
                         deadline: Optional[str] = None,
                         metadata: Optional[Dict[str, Any]] = None) -> TaskDefinition:
        """Create a new task with proper validation and relationship management"""
        try:
            # Validate dependencies if provided
            if dependencies:
                for dep_id in dependencies:
                    if not await self.storage.get_task(dep_id):
                        raise ValueError(f"Dependency task {dep_id} does not exist")

            # Validate parent if provided
            parent_task = None
            if parent_id:
                parent_task = await self.storage.get_task(parent_id)
                if not parent_task:
                    raise ValueError(f"Parent task {parent_id} does not exist")

            # Create task
            task = TaskDefinition(
                title=title,
                description=description,
                priority=priority,
                parent_id=parent_id,
                dependencies=dependencies or [],
                assigned_agent=assigned_agent,
                assigned_division=assigned_division,
                deadline=deadline,
                metadata=metadata or {},
                completion_percentage=0.0,
                started_at=None,
                completed_at=None,
                project_id=None,
                milestone=None,
                last_error=None
            )

            # Store task
            await self.storage.create_task(task)

            # Update parent if needed
            if parent_task:
                parent_task.add_subtask(task.id)
                await self.storage.update_task(parent_task)

            # Update caches
            if task.dependencies:
                for dep_id in task.dependencies:
                    if dep_id not in self._dependency_cache:
                        self._dependency_cache[dep_id] = []
                    self._dependency_cache[dep_id].append(task.id)

            if assigned_agent:
                if assigned_agent not in self._agent_tasks:
                    self._agent_tasks[assigned_agent] = []
                self._agent_tasks[assigned_agent].append(task.id)

            if assigned_division:
                if assigned_division not in self._division_tasks:
                    self._division_tasks[assigned_division] = []
                self._division_tasks[assigned_division].append(task.id)

            self.logger.info(f"Created task {task.id}: {title}")
            return task

        except Exception as e:
            self.logger.error(f"Error creating task: {str(e)}")
            raise

    async def update_task_status(self,
                                task_id: str,
                                new_status: TaskStatus,
                                message: Optional[str] = None,
                                completion_percentage: Optional[float] = None) -> TaskDefinition:
        """Update task status and manage dependent tasks"""
        try:
            task = await self.storage.get_task(task_id)
            if not task:
                raise ValueError(f"Task {task_id} not found")

            old_status = task.status
            task.update_status(new_status, message)

            if completion_percentage is not None:
                task.update_progress(completion_percentage)

            await self.storage.update_task(task)

            # Handle dependent tasks
            if new_status == TaskStatus.COMPLETED:
                await self._process_dependent_tasks(task_id)
            elif new_status == TaskStatus.BLOCKED:
                # Update dependent tasks to blocked status
                dependent_tasks = self._dependency_cache.get(task_id, [])
                for dep_task_id in dependent_tasks:
                    dep_task = await self.storage.get_task(dep_task_id)
                    if dep_task and dep_task.status != TaskStatus.COMPLETED:
                        dep_task.update_status(TaskStatus.BLOCKED,
                                            f"Blocked by task {task_id}")
                        await self.storage.update_task(dep_task)

            self.logger.info(f"Updated task {task_id} status from {old_status} to {new_status}")
            return task

        except Exception as e:
            self.logger.error(f"Error updating task status: {str(e)}")
            raise

    async def assign_task(self,
                         task_id: str,
                         agent_id: Optional[str] = None,
                         division: Optional[str] = None) -> TaskDefinition:
        """Assign a task to an agent and/or division"""
        try:
            task = await self.storage.get_task(task_id)
            if not task:
                raise ValueError(f"Task {task_id} not found")

            # Update assignment
            if agent_id:
                # Remove from old agent's tasks
                if task.assigned_agent:
                    self._agent_tasks[task.assigned_agent].remove(task_id)

                task.assigned_agent = agent_id
                if agent_id not in self._agent_tasks:
                    self._agent_tasks[agent_id] = []
                self._agent_tasks[agent_id].append(task_id)

            if division:
                # Remove from old division's tasks
                if task.assigned_division:
                    self._division_tasks[task.assigned_division].remove(task_id)

                task.assigned_division = division
                if division not in self._division_tasks:
                    self._division_tasks[division] = []
                self._division_tasks[division].append(task_id)

            await self.storage.update_task(task)

            self.logger.info(f"Assigned task {task_id} to agent={agent_id}, division={division}")
            return task

        except Exception as e:
            self.logger.error(f"Error assigning task: {str(e)}")
            raise

    async def get_agent_tasks(self,
                            agent_id: str,
                            status: Optional[TaskStatus] = None) -> List[TaskDefinition]:
        """Get all tasks assigned to an agent"""
        try:
            return await self.storage.get_tasks(
                assigned_agent=agent_id,
                status=status
            )
        except Exception as e:
            self.logger.error(f"Error getting agent tasks: {str(e)}")
            raise

    async def get_division_tasks(self,
                               division: str,
                               status: Optional[TaskStatus] = None) -> List[TaskDefinition]:
        """Get all tasks assigned to a division"""
        try:
            return await self.storage.get_tasks(
                assigned_division=division,
                status=status
            )
        except Exception as e:
            self.logger.error(f"Error getting division tasks: {str(e)}")
            raise

    async def get_critical_tasks(self) -> List[TaskDefinition]:
        """Get all critical priority tasks"""
        try:
            return await self.storage.get_tasks(priority=TaskPriority.CRITICAL)
        except Exception as e:
            self.logger.error(f"Error getting critical tasks: {str(e)}")
            raise

    async def get_blocked_tasks(self) -> List[TaskDefinition]:
        """Get all blocked tasks"""
        try:
            return await self.storage.get_tasks(status=TaskStatus.BLOCKED)
        except Exception as e:
            self.logger.error(f"Error getting blocked tasks: {str(e)}")
            raise

    async def _process_dependent_tasks(self, completed_task_id: str) -> None:
        """Process tasks that depend on a completed task"""
        try:
            dependent_tasks = self._dependency_cache.get(completed_task_id, [])
            for dep_task_id in dependent_tasks:
                dep_task = await self.storage.get_task(dep_task_id)
                if not dep_task:
                    continue

                # Check if all dependencies are completed
                all_completed = True
                for dep_id in dep_task.dependencies:
                    dep = await self.storage.get_task(dep_id)
                    if not dep or dep.status != TaskStatus.COMPLETED:
                        all_completed = False
                        break

                if all_completed and dep_task.status == TaskStatus.BLOCKED:
                    dep_task.update_status(TaskStatus.PENDING,
                                         "All dependencies completed")
                    await self.storage.update_task(dep_task)

        except Exception as e:
            self.logger.error(f"Error processing dependent tasks: {str(e)}")
            raise

    async def rebuild_caches(self) -> None:
        """Rebuild internal caches from storage"""
        try:
            self._dependency_cache.clear()
            self._agent_tasks.clear()
            self._division_tasks.clear()

            all_tasks = await self.storage.get_tasks()
            for task in all_tasks:
                # Build dependency cache
                for dep_id in task.dependencies:
                    if dep_id not in self._dependency_cache:
                        self._dependency_cache[dep_id] = []
                    self._dependency_cache[dep_id].append(task.id)

                # Build agent cache
                if task.assigned_agent:
                    if task.assigned_agent not in self._agent_tasks:
                        self._agent_tasks[task.assigned_agent] = []
                    self._agent_tasks[task.assigned_agent].append(task.id)

                # Build division cache
                if task.assigned_division:
                    if task.assigned_division not in self._division_tasks:
                        self._division_tasks[task.assigned_division] = []
                    self._division_tasks[task.assigned_division].append(task.id)

            self.logger.info("Rebuilt task service caches")

        except Exception as e:
            self.logger.error(f"Error rebuilding caches: {str(e)}")
            raise

if __name__ == "__main__":
    # Test the task service
    async def test_service():
        service = TaskService()

        try:
            # Create a parent task
            parent_task = await service.create_task(
                title="Parent Task",
                description="A parent task for testing",
                priority=TaskPriority.HIGH,
                assigned_division="TestDivision"
            )
            print(f"Created parent task: {parent_task.id}")

            # Create a dependent task
            dependent_task = await service.create_task(
                title="Dependent Task",
                description="A task that depends on the parent",
                priority=TaskPriority.MEDIUM,
                dependencies=[parent_task.id],
                assigned_agent="TestAgent"
            )
            print(f"Created dependent task: {dependent_task.id}")

            # Update parent task status
            updated_parent = await service.update_task_status(
                parent_task.id,
                TaskStatus.COMPLETED,
                "Completed parent task",
                100.0
            )
            print(f"Updated parent task status: {updated_parent.status}")

            # Get division tasks
            division_tasks = await service.get_division_tasks("TestDivision")
            print(f"Found {len(division_tasks)} tasks in TestDivision")

            # Get agent tasks
            agent_tasks = await service.get_agent_tasks("TestAgent")
            print(f"Found {len(agent_tasks)} tasks for TestAgent")

        except Exception as e:
            print(f"Error in test: {str(e)}")

    asyncio.run(test_service())
