from agency_swarm.tools import BaseTool
from pydantic import Field
import os
from dotenv import load_dotenv
import asyncio
import json
from typing import Dict, List, Any
import uuid
from datetime import datetime
from dataclasses import dataclass, asdict
import logging

load_dotenv()

@dataclass
class AgentMessage:
    """Data class for agent messages"""
    id: str
    sender: str
    receiver: str
    content: Any
    timestamp: str
    message_type: str
    status: str = "pending"

class AsyncManagerTool(BaseTool):
    """
    Tool for managing asynchronous operations between agents.
    Handles message queuing, state management, and async communication.
    """
    operation: str = Field(
        ..., description="Operation to perform ('send_message', 'get_messages', 'update_state')"
    )
    agent_id: str = Field(
        ..., description="ID of the agent performing the operation"
    )
    data: Dict = Field(
        {}, description="Data for the operation (message content, state updates, etc.)"
    )

    def __init__(self, **data):
        super().__init__(**data)
        self.message_queue: Dict[str, List[AgentMessage]] = {}
        self.agent_states: Dict[str, Dict] = {}
        self.setup_logging()

    def setup_logging(self):
        """Sets up logging for async operations"""
        log_dir = "agency_divisions/internal_operations/logs"
        os.makedirs(log_dir, exist_ok=True)
        
        logging.basicConfig(
            filename=f"{log_dir}/async_operations.log",
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger('AsyncManager')

    async def run_async(self):
        """
        Asynchronous execution of operations.
        """
        try:
            if self.operation == "send_message":
                return await self._send_message()
            elif self.operation == "get_messages":
                return await self._get_messages()
            elif self.operation == "update_state":
                return await self._update_state()
            else:
                raise ValueError(f"Unknown operation: {self.operation}")
        
        except Exception as e:
            self.logger.error(f"Error in async operation: {str(e)}")
            raise

    def run(self):
        """
        Synchronous wrapper for async operations.
        """
        try:
            return asyncio.run(self.run_async())
        except Exception as e:
            self.logger.error(f"Error running async operation: {str(e)}")
            return {"status": "error", "message": str(e)}

    async def _send_message(self) -> Dict:
        """Sends a message to another agent"""
        try:
            message = AgentMessage(
                id=str(uuid.uuid4()),
                sender=self.agent_id,
                receiver=self.data.get("receiver"),
                content=self.data.get("content"),
                timestamp=datetime.now().isoformat(),
                message_type=self.data.get("message_type", "standard")
            )
            
            # Initialize queue for receiver if not exists
            if message.receiver not in self.message_queue:
                self.message_queue[message.receiver] = []
            
            # Add message to queue
            self.message_queue[message.receiver].append(message)
            
            self.logger.info(f"Message sent: {message.id} from {message.sender} to {message.receiver}")
            
            return {
                "status": "success",
                "message_id": message.id,
                "timestamp": message.timestamp
            }
            
        except Exception as e:
            self.logger.error(f"Error sending message: {str(e)}")
            raise

    async def _get_messages(self) -> Dict:
        """Retrieves messages for an agent"""
        try:
            if self.agent_id not in self.message_queue:
                return {"status": "success", "messages": []}
            
            messages = self.message_queue[self.agent_id]
            # Convert messages to dict for JSON serialization
            message_dicts = [asdict(msg) for msg in messages]
            
            # Clear processed messages
            self.message_queue[self.agent_id] = []
            
            self.logger.info(f"Retrieved {len(messages)} messages for agent {self.agent_id}")
            
            return {
                "status": "success",
                "messages": message_dicts
            }
            
        except Exception as e:
            self.logger.error(f"Error retrieving messages: {str(e)}")
            raise

    async def _update_state(self) -> Dict:
        """Updates agent state"""
        try:
            state_update = self.data.get("state", {})
            
            if self.agent_id not in self.agent_states:
                self.agent_states[self.agent_id] = {}
            
            # Update state
            self.agent_states[self.agent_id].update(state_update)
            
            self.logger.info(f"Updated state for agent {self.agent_id}")
            
            return {
                "status": "success",
                "current_state": self.agent_states[self.agent_id]
            }
            
        except Exception as e:
            self.logger.error(f"Error updating state: {str(e)}")
            raise

    def _save_state(self):
        """Saves current state to disk"""
        try:
            state_dir = "agency_divisions/internal_operations/data/agent_states"
            os.makedirs(state_dir, exist_ok=True)
            
            state_file = f"{state_dir}/states.json"
            with open(state_file, 'w') as f:
                json.dump({
                    "agent_states": self.agent_states,
                    "last_updated": datetime.now().isoformat()
                }, f, indent=2)
                
        except Exception as e:
            self.logger.error(f"Error saving state: {str(e)}")
            raise

    def _load_state(self):
        """Loads state from disk"""
        try:
            state_file = "agency_divisions/internal_operations/data/agent_states/states.json"
            if os.path.exists(state_file):
                with open(state_file, 'r') as f:
                    data = json.load(f)
                    self.agent_states = data.get("agent_states", {})
                    
        except Exception as e:
            self.logger.error(f"Error loading state: {str(e)}")
            self.agent_states = {}

if __name__ == "__main__":
    # Test the async manager
    async def test_async_operations():
        manager = AsyncManagerTool(
            operation="send_message",
            agent_id="test_agent_1",
            data={
                "receiver": "test_agent_2",
                "content": "Test message",
                "message_type": "test"
            }
        )
        
        # Test sending a message
        result = await manager.run_async()
        print("Send message result:", result)
        
        # Test retrieving messages
        manager.operation = "get_messages"
        manager.agent_id = "test_agent_2"
        result = await manager.run_async()
        print("Get messages result:", result)
        
        # Test updating state
        manager.operation = "update_state"
        manager.data = {"state": {"status": "active", "last_action": "test"}}
        result = await manager.run_async()
        print("Update state result:", result)
    
    asyncio.run(test_async_operations()) 