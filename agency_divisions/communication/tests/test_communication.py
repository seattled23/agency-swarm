import pytest
import asyncio
from datetime import datetime
from pathlib import Path
import uuid

from ..models.message_model import Message, MessageType, MessagePriority
from ..broker.message_broker import MessageBroker
from ..services.communication_service import CommunicationService
from ...task_management.models.task_model import TaskDefinition, TaskStatus, TaskPriority
from ...task_management.services.task_service import TaskService

# Test data directory setup
TEST_DATA_DIR = Path(__file__).resolve().parent / "test_data"
TEST_DB_PATH = TEST_DATA_DIR / "test_tasks.db"
TEST_JSON_PATH = TEST_DATA_DIR / "test_tasks.json"
TEST_LOG_PATH = TEST_DATA_DIR / "logs"

@pytest.fixture(autouse=True)
async def setup_test_env():
    """Set up test environment"""
    TEST_DATA_DIR.mkdir(parents=True, exist_ok=True)
    TEST_LOG_PATH.mkdir(parents=True, exist_ok=True)
    yield
    # Cleanup
    for path in [TEST_DB_PATH, TEST_JSON_PATH]:
        if path.exists():
            path.unlink()
    for path in [TEST_LOG_PATH, TEST_DATA_DIR]:
        if path.exists():
            path.rmdir()

@pytest.fixture
async def broker():
    """Create a message broker instance"""
    return MessageBroker(storage_path=TEST_LOG_PATH)

@pytest.fixture
async def task_service():
    """Create a task service instance"""
    return TaskService(db_path=TEST_DB_PATH, json_path=TEST_JSON_PATH)

@pytest.fixture
async def comm_service(broker, task_service):
    """Create a communication service instance"""
    return CommunicationService(
        broker=broker,
        task_service=task_service,
        log_path=TEST_LOG_PATH
    )

@pytest.mark.asyncio
async def test_message_creation():
    """Test message model creation and validation"""
    message = Message(
        id=f"msg_{uuid.uuid4().hex[:8]}",
        type=MessageType.NOTIFICATION,
        sender_id="test_sender",
        receiver_id="test_receiver",
        subject="Test Message",
        content={"data": "test"}
    )

    assert message.id.startswith("msg_")
    assert message.type == MessageType.NOTIFICATION
    assert message.priority == MessagePriority.NORMAL
    assert not message.is_expired()

@pytest.mark.asyncio
async def test_broker_pubsub(broker):
    """Test publish-subscribe functionality"""
    # Register agents
    await broker.register_agent("agent1")
    await broker.register_agent("agent2")

    # Subscribe to topic
    await broker.subscribe("agent1", "test_topic")

    # Create and publish message
    message = Message(
        id="test_msg_1",
        type=MessageType.NOTIFICATION,
        sender_id="system",
        receiver_id="broadcast",
        subject="Test Broadcast",
        content={"data": "test"}
    )

    await broker.publish("test_topic", message)

    # Check message received
    received = await broker.receive("agent1", timeout=1.0)
    assert received is not None
    assert received.id == "test_msg_1"

    # Check non-subscribed agent
    received = await broker.receive("agent2", timeout=1.0)
    assert received is None

@pytest.mark.asyncio
async def test_direct_messaging(broker):
    """Test direct messaging between agents"""
    # Register agents
    await broker.register_agent("sender")
    await broker.register_agent("receiver")

    # Send direct message
    message = Message(
        id="direct_msg_1",
        type=MessageType.QUERY,
        sender_id="sender",
        receiver_id="receiver",
        subject="Direct Query",
        content={"query": "status"}
    )

    await broker.send_direct(message)

    # Check message received
    received = await broker.receive("receiver", timeout=1.0)
    assert received is not None
    assert received.id == "direct_msg_1"
    assert received.type == MessageType.QUERY

@pytest.mark.asyncio
async def test_task_assignment_integration(comm_service):
    """Test task assignment through communication service"""
    # Register agents
    await comm_service.register_agent("manager", ["tasks"])
    await comm_service.register_agent("worker", ["tasks"])

    # Create task
    task = TaskDefinition(
        title="Integration Test Task",
        description="Testing task assignment through communication",
        priority=TaskPriority.HIGH
    )

    # Send task assignment
    await comm_service.send_task_assignment(
        task=task,
        sender_id="manager",
        receiver_id="worker"
    )

    # Check task assignment received
    received = await comm_service.broker.receive("worker", timeout=1.0)
    assert received is not None
    assert received.type == MessageType.TASK_ASSIGNMENT
    assert received.content["task_data"]["title"] == task.title

@pytest.mark.asyncio
async def test_status_updates(comm_service):
    """Test task status updates through communication service"""
    # Register agents
    await comm_service.register_agent("worker", ["tasks"])
    await comm_service.register_agent("manager", ["tasks"])

    # Create and assign task
    task = TaskDefinition(
        title="Status Update Test",
        description="Testing status updates",
        priority=TaskPriority.HIGH
    )

    if comm_service.task_service:
        task_id = await comm_service.task_service.storage.create_task(task)

        # Send status update
        await comm_service.send_status_update(
            task_id=task_id,
            status=TaskStatus.IN_PROGRESS,
            sender_id="worker",
            receiver_id="manager",
            message="Started working on task"
        )

        # Check status update received
        received = await comm_service.broker.receive("manager", timeout=1.0)
        assert received is not None
        assert received.type == MessageType.STATUS_UPDATE
        assert received.content["status"] == TaskStatus.IN_PROGRESS

        # Verify task status updated
        updated_task = await comm_service.task_service.storage.get_task(task_id)
        assert updated_task is not None
        assert updated_task.status == TaskStatus.IN_PROGRESS

@pytest.mark.asyncio
async def test_query_response(comm_service):
    """Test query and response mechanism"""
    # Register agents
    await comm_service.register_agent("requester", ["queries"])
    await comm_service.register_agent("responder", ["queries"])

    # Set up response handler
    async def handle_query(message: Message):
        if message.type == MessageType.QUERY:
            response = Message(
                id=f"resp_{uuid.uuid4().hex[:8]}",
                type=MessageType.RESPONSE,
                sender_id="responder",
                receiver_id=message.sender_id,
                subject="Query Response",
                content={"status": "ok"},
                references=[message.id]
            )
            await comm_service.broker.send_direct(response)

    # Register handler
    await comm_service.broker.register_handler(MessageType.QUERY, handle_query)

    # Send query and wait for response
    response = await comm_service.query_agent(
        receiver_id="responder",
        query_type="status",
        query_data={"request": "status_check"},
        sender_id="requester",
        timeout=2.0
    )

    assert response is not None
    assert response.type == MessageType.RESPONSE
    assert response.content["status"] == "ok"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])