import asyncio
from typing import Dict, List, Set, Optional, Callable, Awaitable, Any
from datetime import datetime
import json
import logging
from pathlib import Path
import aiofiles

from ..models.message_model import Message, MessageType, MessagePriority

class MessageBroker:
    """
    Handles message routing and delivery between agents in the agency.
    Implements a publish-subscribe pattern with message queuing.
    """
    def __init__(self, storage_path: Optional[Path] = None):
        self.subscribers: Dict[str, Set[str]] = {}  # topic -> set of agent_ids
        self.message_queues: Dict[str, asyncio.Queue] = {}  # agent_id -> message queue
        self.handlers: Dict[MessageType, List[Callable[[Message], Awaitable[None]]]] = {}
        self.storage_path = storage_path or Path("message_logs")
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self._setup_logging()

    def _setup_logging(self):
        """Set up message logging"""
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger("MessageBroker")
        file_handler = logging.FileHandler(self.storage_path / "message_broker.log")
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        self.logger.addHandler(file_handler)

    async def register_agent(self, agent_id: str) -> None:
        """Register a new agent with the broker"""
        if agent_id not in self.message_queues:
            self.message_queues[agent_id] = asyncio.Queue()
            self.logger.info(f"Agent registered: {agent_id}")

    async def unregister_agent(self, agent_id: str) -> None:
        """Unregister an agent from the broker"""
        if agent_id in self.message_queues:
            del self.message_queues[agent_id]
            # Remove agent from all subscriptions
            for subscribers in self.subscribers.values():
                subscribers.discard(agent_id)
            self.logger.info(f"Agent unregistered: {agent_id}")

    async def subscribe(self, agent_id: str, topic: str) -> None:
        """Subscribe an agent to a topic"""
        if topic not in self.subscribers:
            self.subscribers[topic] = set()
        self.subscribers[topic].add(agent_id)
        self.logger.info(f"Agent {agent_id} subscribed to topic: {topic}")

    async def unsubscribe(self, agent_id: str, topic: str) -> None:
        """Unsubscribe an agent from a topic"""
        if topic in self.subscribers:
            self.subscribers[topic].discard(agent_id)
            self.logger.info(f"Agent {agent_id} unsubscribed from topic: {topic}")

    async def publish(self, topic: str, message: Message) -> None:
        """Publish a message to a topic"""
        if topic in self.subscribers:
            message.metadata["topic"] = topic
            message.metadata["published_at"] = datetime.now().isoformat()

            for agent_id in self.subscribers[topic]:
                if agent_id in self.message_queues:
                    await self.message_queues[agent_id].put(message)

            await self._log_message(message)
            self.logger.info(f"Message published to topic {topic}: {message.id}")

    async def send_direct(self, message: Message) -> None:
        """Send a message directly to a specific agent"""
        if message.receiver_id in self.message_queues:
            message.metadata["sent_at"] = datetime.now().isoformat()
            await self.message_queues[message.receiver_id].put(message)
            await self._log_message(message)
            self.logger.info(f"Direct message sent: {message.id}")
        else:
            self.logger.warning(f"Recipient not found: {message.receiver_id}")

    async def receive(self, agent_id: str, timeout: Optional[float] = None) -> Optional[Message]:
        """Receive a message for an agent"""
        if agent_id not in self.message_queues:
            return None

        try:
            message = await asyncio.wait_for(
                self.message_queues[agent_id].get(),
                timeout=timeout
            )
            message.metadata["received_at"] = datetime.now().isoformat()
            await self._log_message(message)
            return message
        except asyncio.TimeoutError:
            return None

    async def register_handler(
        self,
        message_type: MessageType,
        handler: Callable[[Message], Awaitable[None]]
    ) -> None:
        """Register a handler for a specific message type"""
        if message_type not in self.handlers:
            self.handlers[message_type] = []
        self.handlers[message_type].append(handler)
        self.logger.info(f"Handler registered for message type: {message_type}")

    async def _log_message(self, message: Message) -> None:
        """Log message to storage"""
        try:
            log_file = self.storage_path / f"messages_{datetime.now().strftime('%Y%m%d')}.jsonl"
            async with aiofiles.open(log_file, mode='a') as f:
                await f.write(json.dumps(message.model_dump()) + '\n')
        except Exception as e:
            self.logger.error(f"Error logging message: {str(e)}")

    async def process_message(self, message: Message) -> None:
        """Process a message through registered handlers"""
        if message.type in self.handlers:
            for handler in self.handlers[message.type]:
                try:
                    await handler(message)
                except Exception as e:
                    self.logger.error(f"Error in message handler: {str(e)}")

if __name__ == "__main__":
    async def test_broker():
        # Create broker instance
        broker = MessageBroker()

        # Register test agents
        await broker.register_agent("agent1")
        await broker.register_agent("agent2")

        # Subscribe agent1 to a topic
        await broker.subscribe("agent1", "test_topic")

        # Create and publish a test message
        test_message = Message(
            id="test_msg_001",
            type=MessageType.NOTIFICATION,
            sender_id="system",
            receiver_id="agent1",
            subject="Test Message",
            content={"data": "Hello, Agent!"},
            expires_at=None  # Add expires_at parameter
        )

        # Publish to topic
        await broker.publish("test_topic", test_message)

        # Receive message
        received = await broker.receive("agent1", timeout=1.0)
        if received:
            print(f"Message received: {received.model_dump()}")

    # Run test
    asyncio.run(test_broker())
