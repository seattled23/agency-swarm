from agency_divisions.base_agent import BaseAgent
import asyncio
from typing import Dict, Any

class TaskManager(BaseAgent):
    def __init__(self):
        super().__init__()
        self.tasks: Dict[str, Any] = {}
        
    async def initialize(self):
        """Initialize the TaskManager agent"""
        await super().initialize()
        await self.set_current_task("Initializing task management system")
        # Simulate initialization work
        await asyncio.sleep(1)
        await self.set_current_task("Ready for task management")
        
    async def process_message(self, message: dict):
        """Process incoming task-related messages"""
        try:
            await self.set_status("busy")
            message_type = message.get("type")
            
            if message_type == "create_task":
                await self.create_task(message)
            elif message_type == "update_task":
                await self.update_task(message)
            elif message_type == "delete_task":
                await self.delete_task(message)
            
            await self.set_status("online")
            
        except Exception as e:
            await self.set_status("error")
            print(f"Error processing message: {str(e)}")
            
    async def create_task(self, message: dict):
        """Create a new task"""
        task_id = message.get("task_id")
        await self.set_current_task(f"Creating task: {task_id}")
        self.tasks[task_id] = message.get("task_data")
        await asyncio.sleep(0.5)  # Simulate work
        
    async def update_task(self, message: dict):
        """Update an existing task"""
        task_id = message.get("task_id")
        await self.set_current_task(f"Updating task: {task_id}")
        if task_id in self.tasks:
            self.tasks[task_id].update(message.get("task_data", {}))
        await asyncio.sleep(0.5)  # Simulate work
        
    async def delete_task(self, message: dict):
        """Delete a task"""
        task_id = message.get("task_id")
        await self.set_current_task(f"Deleting task: {task_id}")
        self.tasks.pop(task_id, None)
        await asyncio.sleep(0.5)  # Simulate work 