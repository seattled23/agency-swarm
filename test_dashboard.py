import asyncio
from agency_divisions.task_management.task_manager import TaskManager
from agency_divisions.internal_operations.tools.agent_dashboard import AgentDashboard
import signal
import sys

async def test_dashboard():
    # Create dashboard and task manager
    dashboard = AgentDashboard(operation="start_dashboard", data={})
    task_manager = TaskManager()
    
    try:
        # Start the dashboard
        dashboard_task = asyncio.create_task(dashboard.run_async())
        
        # Initialize task manager
        await task_manager.initialize()
        
        # Update task manager status in dashboard
        for i in range(5):
            status_data = {
                "name": "TaskManager",
                "status": await task_manager.get_status(),
                "current_task": await task_manager.get_current_task(),
                "message_queue_size": await task_manager.get_queue_size(),
                "cpu_usage": 0.5,  # Example value
                "memory_usage": 2.0,  # Example value
                "uptime": task_manager.uptime
            }
            
            dashboard.operation = "update_agent_status"
            dashboard.data = {"agent_status": status_data}
            await dashboard.run_async()
            
            # Simulate some task manager work
            await task_manager.add_to_queue({
                "type": "create_task",
                "task_id": f"task_{i}",
                "task_data": {"description": f"Test task {i}"}
            })
            
            await asyncio.sleep(2)
        
        # Stop the dashboard
        dashboard.operation = "stop_dashboard"
        await dashboard.run_async()
        await dashboard_task
        
    except Exception as e:
        print(f"Error in test: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    try:
        asyncio.run(test_dashboard())
    except KeyboardInterrupt:
        print("\nTest completed.") 