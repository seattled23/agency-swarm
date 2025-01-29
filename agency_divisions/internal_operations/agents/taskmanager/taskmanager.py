from agency_divisions.internal_operations.tools.async_agent_base import AsyncAgent
import asyncio
from typing import Dict, Any, List
from datetime import datetime

class TaskManager(AsyncAgent):
    """
    Task Manager Agent responsible for coordinating task delegation and execution
    across all agents in the agency.
    """
    
    def __init__(self):
        super().__init__(
            name="TaskManager",
            description="Expert in task delegation, coordination, and execution monitoring",
            instructions="./instructions.md",
            tools_folder="./tools",
            temperature=0.5,
            max_prompt_tokens=25000
        )
        
        # Register message handlers
        self.register_handler("task_creation_request", self._handle_task_creation)
        self.register_handler("task_assignment_request", self._handle_task_assignment)
        self.register_handler("task_update", self._handle_task_update)
        self.register_handler("task_query", self._handle_task_query)
        self.register_handler("agent_status_update", self._handle_agent_status)
        
        # Initialize task management state
        self._agent_states = {}
        self._task_priorities = {
            "critical": 1,
            "high": 2,
            "medium": 3,
            "low": 4
        }

    async def _handle_task_creation(self, message: Dict[str, Any]):
        """Handles requests to create new tasks"""
        try:
            # Extract task details
            task_data = message.get("content", {})
            
            # Create task using delegation tool
            delegation_tool = self.get_tool("TaskDelegationTool")
            delegation_tool.operation = "create_task"
            delegation_tool.data = {"task": task_data}
            
            result = await delegation_tool.run_async()
            
            # Send confirmation back
            await self.send_message(
                receiver=message["sender"],
                content=result,
                message_type="task_creation_response"
            )
            
            # If task is ready for assignment, try to assign it
            if not task_data.get("dependencies"):
                await self._try_assign_task(result["task_id"])
            
        except Exception as e:
            self.logger.error(f"Error creating task: {str(e)}")
            await self.send_message(
                receiver=message["sender"],
                content={"error": str(e)},
                message_type="error_response"
            )

    async def _handle_task_assignment(self, message: Dict[str, Any]):
        """Handles requests to assign tasks to agents"""
        try:
            # Extract assignment details
            assignment_data = message.get("content", {})
            task_id = assignment_data.get("task_id")
            agent_id = assignment_data.get("agent_id")
            
            # Assign task using delegation tool
            delegation_tool = self.get_tool("TaskDelegationTool")
            delegation_tool.operation = "assign_task"
            delegation_tool.data = {
                "task_id": task_id,
                "agent_id": agent_id
            }
            
            result = await delegation_tool.run_async()
            
            # Send confirmation back
            await self.send_message(
                receiver=message["sender"],
                content=result,
                message_type="task_assignment_response"
            )
            
            # If assignment successful, notify the assigned agent
            if result["status"] == "success":
                await self.send_message(
                    receiver=agent_id,
                    content=result["task"],
                    message_type="task_assigned"
                )
            
        except Exception as e:
            self.logger.error(f"Error assigning task: {str(e)}")
            await self.send_message(
                receiver=message["sender"],
                content={"error": str(e)},
                message_type="error_response"
            )

    async def _handle_task_update(self, message: Dict[str, Any]):
        """Handles task status and progress updates"""
        try:
            # Extract update details
            update_data = message.get("content", {})
            task_id = update_data.get("task_id")
            updates = update_data.get("updates", {})
            
            # Update task using delegation tool
            delegation_tool = self.get_tool("TaskDelegationTool")
            delegation_tool.operation = "update_task"
            delegation_tool.data = {
                "task_id": task_id,
                "updates": updates
            }
            
            result = await delegation_tool.run_async()
            
            # If task completed, check for dependent tasks
            if updates.get("status") == "completed":
                await self._process_task_completion(task_id)
            
            # Send confirmation back
            await self.send_message(
                receiver=message["sender"],
                content=result,
                message_type="task_update_response"
            )
            
        except Exception as e:
            self.logger.error(f"Error updating task: {str(e)}")
            await self.send_message(
                receiver=message["sender"],
                content={"error": str(e)},
                message_type="error_response"
            )

    async def _handle_task_query(self, message: Dict[str, Any]):
        """Handles requests to query task status and details"""
        try:
            # Extract query filters
            filters = message.get("content", {}).get("filters", {})
            
            # Query tasks using delegation tool
            delegation_tool = self.get_tool("TaskDelegationTool")
            delegation_tool.operation = "get_tasks"
            delegation_tool.data = {"filters": filters}
            
            result = await delegation_tool.run_async()
            
            # Send results back
            await self.send_message(
                receiver=message["sender"],
                content=result,
                message_type="task_query_response"
            )
            
        except Exception as e:
            self.logger.error(f"Error querying tasks: {str(e)}")
            await self.send_message(
                receiver=message["sender"],
                content={"error": str(e)},
                message_type="error_response"
            )

    async def _handle_agent_status(self, message: Dict[str, Any]):
        """Handles agent status updates"""
        try:
            # Update agent state
            agent_id = message["sender"]
            status_data = message.get("content", {})
            
            self._agent_states[agent_id] = {
                "status": status_data.get("status"),
                "current_task": status_data.get("current_task"),
                "capacity": status_data.get("capacity", 1.0),
                "last_update": datetime.now().isoformat()
            }
            
            # If agent is ready for new tasks, try to assign one
            if status_data.get("status") == "ready":
                await self._assign_next_task(agent_id)
            
        except Exception as e:
            self.logger.error(f"Error handling agent status: {str(e)}")

    async def _try_assign_task(self, task_id: str):
        """Attempts to assign a task to an available agent"""
        try:
            # Get task details
            delegation_tool = self.get_tool("TaskDelegationTool")
            delegation_tool.operation = "get_tasks"
            delegation_tool.data = {"filters": {"task_id": task_id}}
            
            result = await delegation_tool.run_async()
            if not result["tasks"]:
                return
            
            task = result["tasks"][0]
            
            # Find available agent
            available_agent = await self._find_available_agent(task)
            if available_agent:
                # Assign task
                delegation_tool.operation = "assign_task"
                delegation_tool.data = {
                    "task_id": task_id,
                    "agent_id": available_agent
                }
                
                await delegation_tool.run_async()
            
        except Exception as e:
            self.logger.error(f"Error trying to assign task: {str(e)}")

    async def _process_task_completion(self, completed_task_id: str):
        """Processes task completion and manages dependent tasks"""
        try:
            # Get dependent tasks
            delegation_tool = self.get_tool("TaskDelegationTool")
            delegation_tool.operation = "get_tasks"
            delegation_tool.data = {
                "filters": {
                    "status": "pending",
                    "has_dependency": completed_task_id
                }
            }
            
            result = await delegation_tool.run_async()
            
            # Check each dependent task
            for task in result["tasks"]:
                await self._try_assign_task(task["id"])
            
        except Exception as e:
            self.logger.error(f"Error processing task completion: {str(e)}")

    async def _find_available_agent(self, task: Dict[str, Any]) -> str:
        """Finds an available agent suitable for the task"""
        try:
            available_agents = [
                agent_id for agent_id, state in self._agent_states.items()
                if state["status"] == "ready" and state["capacity"] >= 0.5
            ]
            
            if available_agents:
                # For now, just return the first available agent
                # TODO: Implement more sophisticated agent selection
                return available_agents[0]
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error finding available agent: {str(e)}")
            return None

    async def _assign_next_task(self, agent_id: str):
        """Assigns the next highest priority task to an agent"""
        try:
            # Get pending tasks
            delegation_tool = self.get_tool("TaskDelegationTool")
            delegation_tool.operation = "get_tasks"
            delegation_tool.data = {
                "filters": {
                    "status": "pending",
                    "has_dependencies": False
                }
            }
            
            result = await delegation_tool.run_async()
            
            if not result["tasks"]:
                return
            
            # Sort tasks by priority
            tasks = sorted(
                result["tasks"],
                key=lambda t: self._task_priorities.get(t["priority"], 999)
            )
            
            # Assign highest priority task
            if tasks:
                delegation_tool.operation = "assign_task"
                delegation_tool.data = {
                    "task_id": tasks[0]["id"],
                    "agent_id": agent_id
                }
                
                await delegation_tool.run_async()
            
        except Exception as e:
            self.logger.error(f"Error assigning next task: {str(e)}")

    async def _perform_tasks(self):
        """Performs periodic task management operations"""
        try:
            # Check for stalled tasks
            current_time = datetime.now()
            
            delegation_tool = self.get_tool("TaskDelegationTool")
            delegation_tool.operation = "get_tasks"
            delegation_tool.data = {
                "filters": {
                    "status": "in_progress"
                }
            }
            
            result = await delegation_tool.run_async()
            
            for task in result["tasks"]:
                # Check if task has been in progress too long
                if task.get("status") == "in_progress":
                    started_time = datetime.fromisoformat(task["updated_at"])
                    if (current_time - started_time).total_seconds() > 3600:  # 1 hour
                        # Log potential issue
                        self.logger.warning(f"Task {task['id']} may be stalled")
                        
                        # Notify assigned agent
                        if task.get("assigned_agent"):
                            await self.send_message(
                                receiver=task["assigned_agent"],
                                content={
                                    "task_id": task["id"],
                                    "message": "Task may be stalled"
                                },
                                message_type="task_warning"
                            )
            
        except Exception as e:
            self.logger.error(f"Error in periodic tasks: {str(e)}")

if __name__ == "__main__":
    # Test the Task Manager
    async def test_task_manager():
        manager = TaskManager()
        
        # Start the agent
        await manager.start()
        
        # Simulate task creation request
        await manager.send_message(
            "self",
            {
                "name": "Test Task",
                "description": "A test task",
                "priority": "high",
                "dependencies": []
            },
            "task_creation_request"
        )
        
        # Run for a few minutes
        await asyncio.sleep(360)
        
        # Stop the agent
        await manager.stop()
    
    asyncio.run(test_task_manager()) 