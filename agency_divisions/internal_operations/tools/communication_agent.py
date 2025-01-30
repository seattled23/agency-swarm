from agency_swarm.tools import BaseTool
from pydantic import Field, PrivateAttr
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging
import os
import json
from dataclasses import dataclass
import aiofiles
from queue import Queue

@dataclass
class Message:
    """Data class for messages"""
    sender: str
    recipient: str
    content: str
    timestamp: str
    message_type: str  # 'user_to_agent', 'agent_to_user', 'agent_to_agent'
    status: str  # 'sent', 'delivered', 'read', 'processing', 'responded'

class CommunicationAgent(BaseTool):
    """
    Tool for handling communication between user and agents.
    Manages message routing, history, and real-time updates.
    """

    operation: str = Field(
        ..., description="Operation to perform ('send_message', 'get_messages', 'update_status')"
    )

    data: Dict = Field(
        {}, description="Data for the operation (message content, status updates, etc.)"
    )

    # Private attributes
    _logger: logging.Logger = PrivateAttr()
    _message_history: List[Message] = PrivateAttr(default_factory=list)
    _message_queue: Queue = PrivateAttr()
    _active_conversations: Dict[str, List[Message]] = PrivateAttr(default_factory=dict)
    _is_running: bool = PrivateAttr(default=False)

    class ToolConfig:
        """Tool configuration"""
        strict: bool = True
        one_call_at_a_time: bool = False
        output_as_result: bool = True
        async_mode: str = "async"

    def __init__(self, **data):
        super().__init__(**data)
        self.setup_logging()
        self._message_queue = Queue()
        self._message_history = []
        self._active_conversations = {}
        self._is_running = False

    def setup_logging(self):
        """Sets up logging for the communication agent"""
        log_dir = "agency_divisions/internal_operations/logs/communication"
        os.makedirs(log_dir, exist_ok=True)

        logging.basicConfig(
            filename=f"{log_dir}/communication.log",
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self._logger = logging.getLogger('CommunicationAgent')

    async def run_async(self) -> Dict[str, Any]:
        """Async version of the run method"""
        try:
            if self.operation == "send_message":
                return await self._send_message()
            elif self.operation == "get_messages":
                return await self._get_messages()
            elif self.operation == "update_status":
                return await self._update_message_status()
            else:
                raise ValueError(f"Unknown operation: {self.operation}")
        except Exception as e:
            self._logger.error(f"Error in communication operation: {str(e)}")
            raise

    async def _send_message(self) -> Dict[str, Any]:
        """Sends a message and manages its routing"""
        message_data = self.data.get("message", {})

        message = Message(
            sender=message_data.get("sender"),
            recipient=message_data.get("recipient"),
            content=message_data.get("content"),
            timestamp=datetime.now().strftime("%H:%M:%S"),
            message_type=message_data.get("type", "user_to_agent"),
            status="sent"
        )

        # Add to history and queue
        self._message_history.append(message)
        self._message_queue.put(message)

        # Update active conversations
        conv_key = f"{message.sender}-{message.recipient}"
        if conv_key not in self._active_conversations:
            self._active_conversations[conv_key] = []
        self._active_conversations[conv_key].append(message)

        return {
            "status": "success",
            "message_id": len(self._message_history) - 1,
            "timestamp": message.timestamp
        }

    async def _get_messages(self) -> Dict[str, Any]:
        """Retrieves messages based on filters"""
        filters = self.data.get("filters", {})
        messages = []

        for msg in self._message_history:
            if self._matches_filters(msg, filters):
                messages.append({
                    "sender": msg.sender,
                    "recipient": msg.recipient,
                    "content": msg.content,
                    "timestamp": msg.timestamp,
                    "type": msg.message_type,
                    "status": msg.status
                })

        return {
            "status": "success",
            "messages": messages
        }

    async def _update_message_status(self) -> Dict[str, Any]:
        """Updates the status of a message"""
        update_data = self.data.get("update", {})
        message_id = update_data.get("message_id")
        new_status = update_data.get("status")

        if 0 <= message_id < len(self._message_history):
            self._message_history[message_id].status = new_status
            return {"status": "success", "message_id": message_id}
        else:
            raise ValueError("Invalid message ID")

    def _matches_filters(self, message: Message, filters: Dict) -> bool:
        """Checks if a message matches the given filters"""
        for key, value in filters.items():
            if hasattr(message, key) and getattr(message, key) != value:
                return False
        return True

if __name__ == "__main__":
    # Test the communication agent
    async def test():
        agent = CommunicationAgent(operation="send_message", data={
            "message": {
                "sender": "user",
                "recipient": "TestAgent",
                "content": "Hello, agent!",
                "type": "user_to_agent"
            }
        })

        result = await agent.run_async()
        print(f"Send message result: {result}")

        agent.operation = "get_messages"
        agent.data = {"filters": {"sender": "user"}}
        messages = await agent.run_async()
        print(f"Retrieved messages: {messages}")

    asyncio.run(test())