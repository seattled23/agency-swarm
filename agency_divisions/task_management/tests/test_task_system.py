import pytest
import asyncio
from datetime import datetime
import os
from pathlib import Path
import sys

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from agency_divisions.task_management.models.task_model import TaskDefinition, TaskStatus, TaskPriority, TaskMetrics
from agency_divisions.task_management.storage.task_storage import TaskStorage
from agency_divisions.task_management.services.task_service import TaskService

# Test data directory setup
TEST_DATA_DIR = Path(__file__).parent / "test_data"
TEST_DB_PATH = TEST_DATA_DIR / "test_tasks.db"
TEST_JSON_PATH = TEST_DATA_DIR / "test_tasks.json"

@pytest.fixture(autouse=True)
def setup_test_env():
    """Set up test environment"""
    TEST_DATA_DIR.mkdir(parents=True, exist_ok=True)
    yield
    # Cleanup
    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()
    if TEST_JSON_PATH.exists():
        TEST_JSON_PATH.unlink()
    if TEST_DATA_DIR.exists():
        TEST_DATA_DIR.rmdir()

@pytest.mark.asyncio
async def test_task_model():
    """Test TaskDefinition model functionality"""
    # Create a basic task
    task = TaskDefinition(
        title="Test Task",
        description="Testing task model",
        priority=TaskPriority.HIGH,
        parent_id=None,
        assigned_agent=None,
        assigned_division=None,
        completion_percentage=0.0,
        started_at=None,
        completed_at=None,
        deadline=None,
        project_id=None,
        milestone=None,
        last_error=None
    )

    assert task.id.startswith("TASK-")
    assert task.status == TaskStatus.PENDING
    assert task.priority == TaskPriority.HIGH
    assert task.completion_percentage == 0.0

    # Test status update
    task.update_status(TaskStatus.IN_PROGRESS, "Starting work")
    assert task.status == TaskStatus.IN_PROGRESS
    assert task.started_at is not None
    assert len(task.notes) == 1

    # Test progress update
    task.update_progress(50.0, "Halfway there")
    assert task.completion_percentage == 50.0
    assert len(task.notes) == 2

    # Test completion
    task.update_status(TaskStatus.COMPLETED, "Work finished")
    assert task.status == TaskStatus.COMPLETED
    assert task.completed_at is not None
    assert task.completion_percentage == 100.0

@pytest.mark.asyncio
async def test_task_storage():
    """Test TaskStorage functionality"""
    storage = TaskStorage(
        db_path=TEST_DB_PATH,
        json_path=TEST_JSON_PATH
    )

    # Create test task
    task = TaskDefinition(
        title="Storage Test Task",
        description="Testing storage layer",
        priority=TaskPriority.MEDIUM,
        parent_id=None,
        assigned_agent=None,
        assigned_division=None,
        completion_percentage=0.0,
        started_at=None,
        completed_at=None,
        deadline=None,
        project_id=None,
        milestone=None,
        last_error=None
    )

    # Test create
    task_id = await storage.create_task(task)
    assert task_id == task.id

    # Test retrieve
    retrieved_task = await storage.get_task(task_id)
    assert retrieved_task is not None
    assert retrieved_task.title == task.title
    assert retrieved_task.priority == task.priority

    # Test update
    if retrieved_task:  # Type guard
        retrieved_task.update_status(TaskStatus.IN_PROGRESS)
        await storage.update_task(retrieved_task)
        updated_task = await storage.get_task(task_id)
        assert updated_task is not None  # Type guard
        assert updated_task.status == TaskStatus.IN_PROGRESS

    # Test query
    tasks = await storage.get_tasks(status=TaskStatus.IN_PROGRESS)
    assert len(tasks) == 1
    assert tasks[0].id == task_id

    # Test delete
    await storage.delete_task(task_id)
    deleted_task = await storage.get_task(task_id)
    assert deleted_task is None

@pytest.mark.asyncio
async def test_task_service():
    """Test TaskService functionality"""
    service = TaskService(TaskStorage(
        db_path=TEST_DB_PATH,
        json_path=TEST_JSON_PATH
    ))

    # Create parent task
    parent_task = await service.create_task(
        title="Parent Task",
        description="A parent task for testing",
        priority=TaskPriority.HIGH,
        assigned_division="TestDivision"
    )

    assert parent_task.id.startswith("TASK-")
    assert parent_task.assigned_division == "TestDivision"

    # Create dependent task
    dependent_task = await service.create_task(
        title="Dependent Task",
        description="A task that depends on the parent",
        priority=TaskPriority.MEDIUM,
        dependencies=[parent_task.id],
        assigned_agent="TestAgent"
    )

    assert dependent_task.dependencies == [parent_task.id]
    assert dependent_task.assigned_agent == "TestAgent"

    # Test status updates and dependency handling
    await service.update_task_status(
        parent_task.id,
        TaskStatus.COMPLETED,
        "Completed parent task",
        100.0
    )

    # Verify dependent task is unblocked
    updated_dependent = await service.storage.get_task(dependent_task.id)
    assert updated_dependent is not None  # Type guard
    assert updated_dependent.status != TaskStatus.BLOCKED

    # Test task queries
    division_tasks = await service.get_division_tasks("TestDivision")
    assert len(division_tasks) == 1
    assert division_tasks[0].id == parent_task.id

    agent_tasks = await service.get_agent_tasks("TestAgent")
    assert len(agent_tasks) == 1
    assert agent_tasks[0].id == dependent_task.id

@pytest.mark.asyncio
async def test_task_relationships():
    """Test task relationships and dependency management"""
    service = TaskService(TaskStorage(
        db_path=TEST_DB_PATH,
        json_path=TEST_JSON_PATH
    ))

    # Create a chain of dependent tasks
    task1 = await service.create_task(
        title="Task 1",
        description="First task",
        priority=TaskPriority.HIGH
    )

    task2 = await service.create_task(
        title="Task 2",
        description="Second task",
        priority=TaskPriority.HIGH,
        dependencies=[task1.id]
    )

    task3 = await service.create_task(
        title="Task 3",
        description="Third task",
        priority=TaskPriority.HIGH,
        dependencies=[task2.id]
    )

    # Complete tasks in sequence
    await service.update_task_status(task1.id, TaskStatus.COMPLETED, "Task 1 done")
    task2_updated = await service.storage.get_task(task2.id)
    assert task2_updated is not None  # Type guard
    assert task2_updated.status == TaskStatus.PENDING

    await service.update_task_status(task2.id, TaskStatus.COMPLETED, "Task 2 done")
    task3_updated = await service.storage.get_task(task3.id)
    assert task3_updated is not None  # Type guard
    assert task3_updated.status == TaskStatus.PENDING

    # Verify final state
    all_tasks = await service.storage.get_tasks()
    assert len(all_tasks) == 3

if __name__ == "__main__":
    pytest.main([__file__, "-v"])