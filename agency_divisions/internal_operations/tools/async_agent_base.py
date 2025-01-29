from agency_swarm import Agent
from typing import Dict, List, Any, Optional
import asyncio
import logging
from datetime import datetime
import os
from .async_manager import AsyncManagerTool

class AsyncAgent(Agent):
    """
    Base class for asynchronous agents.
    Extends the standard Agent class with async capabilities.
    """
    
    def __init__(self, name: str, description: str, instructions: str, tools_folder: str,
                 temperature: float = 0.5, max_prompt_tokens: int = 25000):
        super().__init__(
            name=name,
            description=description,
            instructions=instructions,
            tools_folder=tools_folder,
            temperature=temperature,
            max_prompt_tokens=max_prompt_tokens
        )
        
        self.async_manager = AsyncManagerTool(
            operation="update_state",
            agent_id=self.name,
            data={"state": {"status": "initialized"}}
        )
        
        self.setup_logging()
        self.message_handlers = {}
        self._running = False
        self._paused = False

    def setup_logging(self):
        """Sets up agent-specific logging"""
        log_dir = f"agency_divisions/internal_operations/logs/agents"
        os.makedirs(log_dir, exist_ok=True)
        
        logging.basicConfig(
            filename=f"{log_dir}/{self.name.lower()}.log",
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(self.name)

    async def start(self):
        """Starts the agent's async operations"""
        if self._running:
            return
        
        self._running = True
        self._paused = False
        
        try:
            await self._update_state({"status": "running"})
            self.logger.info(f"Agent {self.name} started")
            
            # Start main processing loop
            await self._process_loop()
            
        except Exception as e:
            self.logger.error(f"Error starting agent: {str(e)}")
            await self._update_state({"status": "error", "error": str(e)})
            raise

    async def stop(self):
        """Stops the agent's operations"""
        self._running = False
        await self._update_state({"status": "stopped"})
        self.logger.info(f"Agent {self.name} stopped")

    async def pause(self):
        """Pauses the agent's operations"""
        self._paused = True
        await self._update_state({"status": "paused"})
        self.logger.info(f"Agent {self.name} paused")

    async def resume(self):
        """Resumes the agent's operations"""
        self._paused = False
        await self._update_state({"status": "running"})
        self.logger.info(f"Agent {self.name} resumed")

    async def send_message(self, receiver: str, content: Any, message_type: str = "standard") -> Dict:
        """Sends a message to another agent"""
        try:
            self.async_manager.operation = "send_message"
            self.async_manager.data = {
                "receiver": receiver,
                "content": content,
                "message_type": message_type
            }
            
            result = await self.async_manager.run_async()
            self.logger.info(f"Message sent to {receiver}")
            return result
            
        except Exception as e:
            self.logger.error(f"Error sending message: {str(e)}")
            raise

    async def get_messages(self) -> List[Dict]:
        """Retrieves messages for this agent"""
        try:
            self.async_manager.operation = "get_messages"
            result = await self.async_manager.run_async()
            return result.get("messages", [])
            
        except Exception as e:
            self.logger.error(f"Error retrieving messages: {str(e)}")
            raise

    async def _update_state(self, state_update: Dict):
        """Updates the agent's state"""
        try:
            self.async_manager.operation = "update_state"
            self.async_manager.data = {"state": state_update}
            await self.async_manager.run_async()
            
        except Exception as e:
            self.logger.error(f"Error updating state: {str(e)}")
            raise

    def register_handler(self, message_type: str, handler):
        """Registers a message handler for a specific message type"""
        self.message_handlers[message_type] = handler

    async def _process_loop(self):
        """Main processing loop for the agent"""
        while self._running:
            try:
                if self._paused:
                    await asyncio.sleep(1)
                    continue
                
                # Get and process messages
                messages = await self.get_messages()
                for message in messages:
                    await self._handle_message(message)
                
                # Perform agent-specific tasks
                await self._perform_tasks()
                
                # Brief pause to prevent tight loop
                await asyncio.sleep(0.1)
                
            except Exception as e:
                self.logger.error(f"Error in processing loop: {str(e)}")
                await self._update_state({"status": "error", "error": str(e)})
                await asyncio.sleep(5)  # Pause before retrying

    async def _handle_message(self, message: Dict):
        """Handles incoming messages"""
        try:
            message_type = message.get("message_type", "standard")
            handler = self.message_handlers.get(message_type)
            
            if handler:
                await handler(message)
            else:
                self.logger.warning(f"No handler for message type: {message_type}")
                
        except Exception as e:
            self.logger.error(f"Error handling message: {str(e)}")
            raise

    async def _perform_tasks(self):
        """
        Override this method in derived classes to implement
        agent-specific periodic tasks
        """
        pass

if __name__ == "__main__":
    # Test the async agent
    async def test_async_agent():
        agent = AsyncAgent(
            name="TestAgent",
            description="Test async agent",
            instructions="./instructions.md",
            tools_folder="./tools"
        )
        
        # Register a test message handler
        async def test_handler(message):
            print(f"Received message: {message}")
        
        agent.register_handler("test", test_handler)
        
        # Start the agent
        await agent.start()
        
        # Send a test message
        await agent.send_message("TestAgent2", "Hello!", "test")
        
        # Run for a few seconds
        await asyncio.sleep(5)
        
        # Stop the agent
        await agent.stop()
    
    asyncio.run(test_async_agent()) 