import asyncio
from datetime import datetime
from typing import Optional
import time

class BaseAgent:
    def __init__(self):
        self.status = "offline"
        self.current_task = None
        self.message_queue = asyncio.Queue()
        self.start_time = time.time()
        self.running = False

    @property
    def uptime(self) -> float:
        """Get agent uptime in seconds"""
        return time.time() - self.start_time

    async def initialize(self):
        """Initialize the agent"""
        self.running = True
        self.status = "online"
        self.start_time = time.time()

    async def get_status(self) -> str:
        """Get current agent status"""
        return self.status

    async def get_current_task(self) -> Optional[str]:
        """Get the current task being executed"""
        return self.current_task

    async def get_queue_size(self) -> int:
        """Get the size of the message queue"""
        return self.message_queue.qsize()

    async def set_status(self, status: str):
        """Set agent status"""
        self.status = status

    async def set_current_task(self, task: Optional[str]):
        """Set current task"""
        self.current_task = task

    async def add_to_queue(self, message: dict):
        """Add message to queue"""
        await self.message_queue.put(message)

    async def process_queue(self):
        """Process messages in the queue"""
        while self.running:
            try:
                if not self.message_queue.empty():
                    message = await self.message_queue.get()
                    await self.process_message(message)
                    self.message_queue.task_done()
                await asyncio.sleep(0.1)
            except Exception as e:
                print(f"Error processing queue: {str(e)}")
                await asyncio.sleep(1)

    async def process_message(self, message: dict):
        """Process a single message - to be implemented by child classes"""
        raise NotImplementedError

    async def shutdown(self):
        """Shutdown the agent"""
        self.running = False
        self.status = "offline"
        # Wait for queue to be processed
        if self.message_queue.qsize() > 0:
            await self.message_queue.join() 