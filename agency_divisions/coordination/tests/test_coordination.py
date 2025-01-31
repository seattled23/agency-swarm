import pytest
import asyncio
from datetime import datetime
from pathlib import Path
import uuid

from ..models.coordination_model import (
    Workflow,
    WorkflowStep,
    WorkflowState,
    WorkflowStepType
)
from ..executor.workflow_executor import WorkflowExecutor
from ...communication.services.communication_service import CommunicationService
from ...communication.models.message_model import Message, MessageType, MessagePriority

# Test data directory setup
TEST_DATA_DIR = Path(__file__).resolve().parent / "test_data"
TEST_LOG_PATH = TEST_DATA_DIR / "logs"

@pytest.fixture(autouse=True)
async def setup_test_env():
    """Set up test environment"""
    TEST_DATA_DIR.mkdir(parents=True, exist_ok=True)
    TEST_LOG_PATH.mkdir(parents=True, exist_ok=True)
    yield
    # Cleanup
    for path in [TEST_LOG_PATH, TEST_DATA_DIR]:
        if path.exists():
            path.rmdir()

@pytest.fixture
async def comm_service():
    """Create a communication service instance"""
    return CommunicationService(log_path=TEST_LOG_PATH)

@pytest.fixture
async def executor(comm_service):
    """Create a workflow executor instance"""
    return WorkflowExecutor(comm_service, log_path=TEST_LOG_PATH)

@pytest.mark.asyncio
async def test_workflow_creation():
    """Test workflow model creation and validation"""
    workflow = Workflow(
        name="Test Workflow",
        description="Testing workflow creation"
    )

    assert workflow.id.startswith("workflow_")
    assert workflow.state == WorkflowState.PENDING
    assert len(workflow.steps) == 0

    # Add steps
    step1 = WorkflowStep(
        type=WorkflowStepType.TASK,
        name="Step 1",
        description="First step"
    )
    workflow.add_step(step1)

    assert len(workflow.steps) == 1
    assert workflow.validate_workflow()

@pytest.mark.asyncio
async def test_workflow_dependencies():
    """Test workflow dependency validation"""
    workflow = Workflow(
        name="Dependency Test",
        description="Testing workflow dependencies"
    )

    # Create steps with dependencies
    step1 = WorkflowStep(
        type=WorkflowStepType.TASK,
        name="Step 1",
        description="First step"
    )

    step2 = WorkflowStep(
        type=WorkflowStepType.TASK,
        name="Step 2",
        description="Second step",
        requires=[step1.id]
    )

    workflow.add_step(step1)
    workflow.add_step(step2)

    assert workflow.validate_workflow()
    next_steps = workflow.get_next_steps()
    assert len(next_steps) == 1
    assert next_steps[0].id == step1.id

@pytest.mark.asyncio
async def test_circular_dependencies():
    """Test detection of circular dependencies"""
    workflow = Workflow(
        name="Circular Test",
        description="Testing circular dependencies"
    )

    # Create steps with circular dependency
    step1 = WorkflowStep(
        type=WorkflowStepType.TASK,
        name="Step 1",
        description="First step"
    )

    step2 = WorkflowStep(
        type=WorkflowStepType.TASK,
        name="Step 2",
        description="Second step",
        requires=[step1.id]
    )

    step1.requires.append(step2.id)  # Create circular dependency

    workflow.add_step(step1)
    workflow.add_step(step2)

    assert not workflow.validate_workflow()

@pytest.mark.asyncio
async def test_workflow_execution(executor):
    """Test basic workflow execution"""
    workflow = Workflow(
        name="Execution Test",
        description="Testing workflow execution"
    )

    # Create a simple task step
    step = WorkflowStep(
        type=WorkflowStepType.TASK,
        name="Test Task",
        description="Test task execution",
        agent_id="test_agent"
    )

    workflow.add_step(step)

    # Register test agent
    await executor.comm_service.register_agent("test_agent", ["tasks"])

    # Set up response handler
    async def handle_task(message: Message):
        if message.type == MessageType.TASK_ASSIGNMENT:
            # Simulate task completion
            await asyncio.sleep(0.1)
            await executor.comm_service.send_status_update(
                task_id=message.content["task_id"],
                status=WorkflowState.COMPLETED,
                sender_id="test_agent",
                receiver_id="workflow_executor",
                message="Task completed"
            )

    await executor.comm_service.broker.register_handler(
        MessageType.TASK_ASSIGNMENT,
        handle_task
    )

    # Start workflow
    await executor.start_workflow(workflow)

    # Wait for completion
    while workflow.state == WorkflowState.ACTIVE:
        await asyncio.sleep(0.1)

    assert workflow.state == WorkflowState.COMPLETED
    assert workflow.steps[step.id].state == WorkflowState.COMPLETED

@pytest.mark.asyncio
async def test_parallel_execution(executor):
    """Test parallel step execution"""
    workflow = Workflow(
        name="Parallel Test",
        description="Testing parallel execution"
    )

    # Create parallel step with substeps
    parallel_step = WorkflowStep(
        type=WorkflowStepType.PARALLEL,
        name="Parallel Tasks",
        description="Execute tasks in parallel",
        config={
            "steps": [
                {
                    "type": WorkflowStepType.TASK,
                    "name": "Task 1",
                    "description": "First parallel task",
                    "agent_id": "agent1"
                },
                {
                    "type": WorkflowStepType.TASK,
                    "name": "Task 2",
                    "description": "Second parallel task",
                    "agent_id": "agent2"
                }
            ]
        }
    )

    workflow.add_step(parallel_step)

    # Register test agents
    await executor.comm_service.register_agent("agent1", ["tasks"])
    await executor.comm_service.register_agent("agent2", ["tasks"])

    # Set up response handler
    async def handle_task(message: Message):
        if message.type == MessageType.TASK_ASSIGNMENT:
            # Simulate task completion with different delays
            delay = 0.1 if message.receiver_id == "agent1" else 0.2
            await asyncio.sleep(delay)
            await executor.comm_service.send_status_update(
                task_id=message.content["task_id"],
                status=WorkflowState.COMPLETED,
                sender_id=message.receiver_id,
                receiver_id="workflow_executor",
                message=f"Task completed by {message.receiver_id}"
            )

    await executor.comm_service.broker.register_handler(
        MessageType.TASK_ASSIGNMENT,
        handle_task
    )

    # Start workflow
    start_time = datetime.now()
    await executor.start_workflow(workflow)

    # Wait for completion
    while workflow.state == WorkflowState.ACTIVE:
        await asyncio.sleep(0.1)

    execution_time = (datetime.now() - start_time).total_seconds()

    assert workflow.state == WorkflowState.COMPLETED
    assert workflow.steps[parallel_step.id].state == WorkflowState.COMPLETED
    assert execution_time < 0.5  # Ensure parallel execution

@pytest.mark.asyncio
async def test_decision_step(executor):
    """Test decision step execution"""
    workflow = Workflow(
        name="Decision Test",
        description="Testing decision steps"
    )

    # Create decision step
    decision_step = WorkflowStep(
        type=WorkflowStepType.DECISION,
        name="Value Check",
        description="Check if value meets condition",
        config={
            "condition": "value > 10",
            "variables": {"value": 15}
        }
    )

    workflow.add_step(decision_step)

    # Start workflow
    await executor.start_workflow(workflow)

    # Wait for completion
    while workflow.state == WorkflowState.ACTIVE:
        await asyncio.sleep(0.1)

    assert workflow.state == WorkflowState.COMPLETED
    assert workflow.steps[decision_step.id].state == WorkflowState.COMPLETED
    assert workflow.steps[decision_step.id].result["decision"] == True

@pytest.mark.asyncio
async def test_workflow_control(executor):
    """Test workflow control operations"""
    workflow = Workflow(
        name="Control Test",
        description="Testing workflow control"
    )

    # Create a long-running task
    step = WorkflowStep(
        type=WorkflowStepType.TASK,
        name="Long Task",
        description="Long-running task",
        agent_id="test_agent"
    )

    workflow.add_step(step)
    await executor.comm_service.register_agent("test_agent", ["tasks"])

    # Start workflow
    await executor.start_workflow(workflow)
    assert workflow.state == WorkflowState.ACTIVE

    # Test pause
    await executor.pause_workflow(workflow.id)
    assert workflow.state == WorkflowState.PAUSED

    # Test resume
    await executor.resume_workflow(workflow.id)
    assert workflow.state == WorkflowState.ACTIVE

    # Test cancel
    await executor.cancel_workflow(workflow.id)
    assert workflow.state == WorkflowState.CANCELLED

if __name__ == "__main__":
    pytest.main([__file__, "-v"])