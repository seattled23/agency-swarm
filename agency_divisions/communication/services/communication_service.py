from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid
import asyncio
import logging
from pathlib import Path

from ..models.message_model import Message, MessageType, MessagePriority
from ..broker.message_broker import MessageBroker
from ...task_management.models.task_model import TaskDefinition, TaskStatus
from ...task_management.services.task_service import TaskService

class CommunicationService:
    """
    Manages communication between agents and integrates with task management.
    """
    def __init__(
        self,
        broker: Optional[MessageBroker] = None,
        task_service: Optional[TaskService] = None,
        log_path: Optional[Path] = None
    ):
        self.broker = broker or MessageBroker()
        self.task_service = task_service
        self._setup_logging(log_path)
        self._setup_handlers()

    def _setup_logging(self, log_path: Optional[Path] = None):
        """Set up service logging"""
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger("CommunicationService")
        if log_path:
            file_handler = logging.FileHandler(log_path / "communication_service.log")
            file_handler.setFormatter(logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            ))
            self.logger.addHandler(file_handler)

    async def _setup_handlers(self):
        """Set up message type handlers"""
        await self.broker.register_handler(
            MessageType.TASK_ASSIGNMENT,
            self._handle_task_assignment
        )
        await self.broker.register_handler(
            MessageType.STATUS_UPDATE,
            self._handle_status_update
        )

    async def register_agent(self, agent_id: str, topics: Optional[List[str]] = None) -> None:
        """Register an agent with the communication service"""
        await self.broker.register_agent(agent_id)
        if topics:
            for topic in topics:
                await self.broker.subscribe(agent_id, topic)
        self.logger.info(f"Agent registered with topics: {agent_id}")

    async def send_task_assignment(
        self,
        task: TaskDefinition,
        sender_id: str,
        receiver_id: str,
        priority: MessagePriority = MessagePriority.NORMAL
    ) -> None:
        """Send a task assignment message"""
        message = Message(
            id=f"msg_{uuid.uuid4().hex[:8]}",
            type=MessageType.TASK_ASSIGNMENT,
            sender_id=sender_id,
            receiver_id=receiver_id,
            subject=f"Task Assignment: {task.title}",
            content={
                "task_id": task.id,
                "task_data": task.model_dump()
            },
            priority=priority
        )
        await self.broker.send_direct(message)

    async def send_status_update(
        self,
        task_id: str,
        status: TaskStatus,
        sender_id: str,
        receiver_id: str,
        message: str = ""
    ) -> None:
        """Send a task status update message"""
        status_message = Message(
            id=f"msg_{uuid.uuid4().hex[:8]}",
            type=MessageType.STATUS_UPDATE,
            sender_id=sender_id,
            receiver_id=receiver_id,
            subject=f"Status Update: Task {task_id}",
            content={
                "task_id": task_id,
                "status": status,
                "message": message,
                "timestamp": datetime.now().isoformat()
            }
        )
        await self.broker.send_direct(status_message)

    async def broadcast_notification(
        self,
        topic: str,
        subject: str,
        content: Dict[str, Any],
        sender_id: str,
        priority: MessagePriority = MessagePriority.NORMAL
    ) -> None:
        """Broadcast a notification to all subscribers of a topic"""
        message = Message(
            id=f"msg_{uuid.uuid4().hex[:8]}",
            type=MessageType.NOTIFICATION,
            sender_id=sender_id,
            receiver_id="broadcast",
            subject=subject,
            content=content,
            priority=priority
        )
        await self.broker.publish(topic, message)

    async def query_agent(
        self,
        receiver_id: str,
        query_type: str,
        query_data: Dict[str, Any],
        sender_id: str,
        timeout: float = 30.0
    ) -> Optional[Message]:
        """Send a query to an agent and wait for response"""
        query_id = f"query_{uuid.uuid4().hex[:8]}"
        query_message = Message(
            id=query_id,
            type=MessageType.QUERY,
            sender_id=sender_id,
            receiver_id=receiver_id,
            subject=f"Query: {query_type}",
            content={
                "query_type": query_type,
                "query_data": query_data
            }
        )

        # Send query
        await self.broker.send_direct(query_message)

        # Wait for response
        start_time = datetime.now()
        while (datetime.now() - start_time).total_seconds() < timeout:
            message = await self.broker.receive(sender_id, timeout=1.0)
            if message and message.type == MessageType.RESPONSE and query_id in message.references:
                return message
        return None

    async def _handle_task_assignment(self, message: Message) -> None:
        """Handle task assignment messages"""
        if self.task_service:
            try:
                task_data = message.content["task_data"]
                task = TaskDefinition(**task_data)
                await self.task_service.storage.create_task(task)
                self.logger.info(f"Task assigned: {task.id}")
            except Exception as e:
                self.logger.error(f"Error handling task assignment: {str(e)}")

    async def _handle_status_update(self, message: Message) -> None:
        """Handle status update messages"""
        if self.task_service:
            try:
                task_id = message.content["task_id"]
                status = message.content["status"]
                update_message = message.content.get("message", "")

                task = await self.task_service.storage.get_task(task_id)
                if task:
                    task.update_status(status, update_message)
                    await self.task_service.storage.update_task(task)
                    self.logger.info(f"Task status updated: {task_id} -> {status}")
            except Exception as e:
                self.logger.error(f"Error handling status update: {str(e)}")

if __name__ == "__main__":
    async def test_communication():
        # Create service instances
        broker = MessageBroker()
        comm_service = CommunicationService(broker=broker)

        # Register test agents
        await comm_service.register_agent("agent1", ["tasks", "notifications"])
        await comm_service.register_agent("agent2", ["tasks"])

        # Test notification broadcast
        await comm_service.broadcast_notification(
            topic="notifications",
            subject="System Update",
            content={"message": "System maintenance scheduled"},
            sender_id="system"
        )

        # Test query
        response = await comm_service.query_agent(
            receiver_id="agent2",
            query_type="status_check",
            query_data={"check_type": "health"},
            sender_id="agent1",
            timeout=5.0
        )

        if response:
            print(f"Query response received: {response.model_dump()}")
        else:
            print("No response received")

    # Run test
    asyncio.run(test_communication())
