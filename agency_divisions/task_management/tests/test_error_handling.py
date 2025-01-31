import pytest
import asyncio
from datetime import datetime
import os
from pathlib import Path
import sys

from agency_divisions.task_management.models.task_model import TaskDefinition, TaskStatus, TaskPriority
from agency_divisions.task_management.storage.task_storage import TaskStorage
from agency_divisions.task_management.services.task_service import TaskService

# Test data directory setup
TEST_DATA_DIR = Path(__file__).resolve().parent / "test_data"
TEST_DB_PATH = TEST_DATA_DIR / "test_tasks.db"
TEST_JSON_PATH = TEST_DATA_DIR / "test_tasks.json"

@pytest.fixture(autouse=True)
async def setup_test_env():
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
async def test_invalid_task_creation():
    """Test error handling for invalid task creation"""
    service = TaskService(TaskStorage(
        db_path=TEST_DB_PATH,
        json_path=TEST_JSON_PATH
    ))

    # Test missing required fields
    with pytest.raises(ValueError):
        await service.create_task(
            title="",  # Empty title
            description="Test task",
            priority=TaskPriority.HIGH
        )

    # Test invalid priority
    with pytest.raises(ValueError):
        await service.create_task(
            title="Test Task",
            description="Test task",
            priority="INVALID_PRIORITY"
        )

    # Test invalid dependency
    with pytest.raises(ValueError):
        await service.create_task(
            title="Test Task",
            description="Test task",
            priority=TaskPriority.HIGH,
            dependencies=["NON_EXISTENT_TASK"]
        )

@pytest.mark.asyncio
async def test_circular_dependencies():
    """Test handling of circular dependencies"""
    service = TaskService(TaskStorage(
        db_path=TEST_DB_PATH,
        json_path=TEST_JSON_PATH
    ))

    # Create first task
    task1 = await service.create_task(
        title="Task 1",
        description="First task",
        priority=TaskPriority.HIGH
    )

    # Create second task depending on first
    task2 = await service.create_task(
        title="Task 2",
        description="Second task",
        priority=TaskPriority.HIGH,
        dependencies=[task1.id]
    )

    # Attempt to update first task to depend on second (creating a circle)
    with pytest.raises(ValueError, match="Circular dependency detected"):
        task1.dependencies.append(task2.id)
        await service.storage.update_task(task1)

@pytest.mark.asyncio
async def test_concurrent_task_updates():
    """Test concurrent task updates"""
    service = TaskService(TaskStorage(
        db_path=TEST_DB_PATH,
        json_path=TEST_JSON_PATH
    ))

    # Create a test task
    task = await service.create_task(
        title="Concurrent Test Task",
        description="Testing concurrent updates",
        priority=TaskPriority.HIGH
    )

    # Simulate concurrent updates
    async def update_status(status: TaskStatus, message: str):
        await service.update_task_status(task.id, status, message)
        await asyncio.sleep(0.1)  # Simulate processing time

    # Run concurrent updates
    await asyncio.gather(
        update_status(TaskStatus.IN_PROGRESS, "Started"),
        update_status(TaskStatus.BLOCKED, "Blocked"),
        update_status(TaskStatus.IN_PROGRESS, "Resumed")
    )

    # Verify final state is consistent
    final_task = await service.storage.get_task(task.id)
    assert final_task is not None
    assert len(final_task.notes) == 3  # All updates should be recorded
    assert all(note.startswith("[") for note in final_task.notes)  # All notes should have timestamps

@pytest.mark.asyncio
async def test_edge_cases():
    """Test various edge cases"""
    service = TaskService(TaskStorage(
        db_path=TEST_DB_PATH,
        json_path=TEST_JSON_PATH
    ))

    # Test extremely long title/description
    long_task = await service.create_task(
        title="T" * 1000,  # Very long title
        description="D" * 5000,  # Very long description
        priority=TaskPriority.HIGH
    )
    assert len(long_task.title) == 1000
    assert len(long_task.description) == 5000

    # Test special characters in title/description
    special_task = await service.create_task(
        title="Test 🚀 Special 👍 Characters!@#$%^&*()",
        description="Testing\nMultiple\nLines\nand\tTabs",
        priority=TaskPriority.HIGH
    )
    retrieved_special = await service.storage.get_task(special_task.id)
    assert retrieved_special is not None
    assert retrieved_special.title == special_task.title
    assert retrieved_special.description == special_task.description

    # Test rapid status changes
    rapid_task = await service.create_task(
        title="Rapid Status Change",
        description="Testing rapid status changes",
        priority=TaskPriority.HIGH
    )

    statuses = [
        TaskStatus.IN_PROGRESS,
        TaskStatus.BLOCKED,
        TaskStatus.IN_PROGRESS,
        TaskStatus.ON_HOLD,
        TaskStatus.IN_PROGRESS,
        TaskStatus.COMPLETED
    ]

    for status in statuses:
        await service.update_task_status(rapid_task.id, status, f"Changed to {status}")
        await asyncio.sleep(0.01)  # Small delay to ensure order

    final_rapid = await service.storage.get_task(rapid_task.id)
    assert final_rapid is not None
    assert len(final_rapid.notes) == len(statuses)
    assert final_rapid.status == TaskStatus.COMPLETED

if __name__ == "__main__":
    pytest.main([__file__, "-v"])