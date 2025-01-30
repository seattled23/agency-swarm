import asyncio
from agency_divisions.task_management.task_manager import TaskManager
from agency_divisions.internal_operations.tools.agent_dashboard import AgentDashboard
import signal
import sys
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def test_dashboard():
    # Create dashboard and task manager
    dashboard = AgentDashboard(operation="start_dashboard", data={})
    task_manager = TaskManager()
    
    try:
        # Initialize task manager
        await task_manager.initialize()
        
        # Create a task to update the dashboard
        async def update_dashboard():
            while True:
                try:
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
                    await asyncio.sleep(2)
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    print(f"Error updating dashboard: {str(e)}")
                    break

        # Start the dashboard and updater tasks
        dashboard_task = asyncio.create_task(dashboard.run_async())
        updater_task = asyncio.create_task(update_dashboard())
        
        # Wait for both tasks
        try:
            await asyncio.gather(dashboard_task, updater_task)
        except KeyboardInterrupt:
            # Cancel tasks on Ctrl+C
            updater_task.cancel()
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