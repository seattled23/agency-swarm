import asyncio
import random
from datetime import datetime
from typing import Dict, List, Optional
from agency_divisions.internal_operations.tools.agent_dashboard import AgentDashboard
from agency_divisions.internal_operations.tools.communication_agent import CommunicationAgent
from agency_divisions.task_management.task_manager import TaskManager
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class MockAgent:
    def __init__(self, name, initial_status="initializing"):
        self.name = name
        self.status = initial_status
        self.message_queue = []
        self.current_task = None
        self.start_time = datetime.now()
        self.message_history = []
        self._running = True

    async def simulate_work(self):
        statuses = ["running", "processing", "waiting", "analyzing"]
        tasks = [
            "Analyzing market data",
            "Processing signals",
            "Updating portfolio",
            "Checking risk metrics",
            "Optimizing strategy"
        ]

        while self._running:
            self.status = random.choice(statuses)
            self.current_task = random.choice(tasks)
            await asyncio.sleep(random.uniform(2, 5))

    async def stop(self):
        self._running = False
        self.status = "stopped"
        self.current_task = None

    async def handle_message(self, message: str) -> str:
        if not self._running:
            return "Agent is stopped"
        await asyncio.sleep(random.uniform(0.5, 2))  # Simulate processing time
        responses = [
            f"Processed request: {message}",
            f"Analyzing input: {message}",
            f"Executing command: {message}",
            f"Evaluating message: {message}"
        ]
        response = random.choice(responses)
        self.message_history.append({
            "timestamp": datetime.now().isoformat(),
            "received": message,
            "sent": response
        })
        return response

async def test_dashboard():
    # Create dashboard, communication agent, and task manager
    dashboard = AgentDashboard(
        name="DashboardAgent",
        operation="start_dashboard",
        data={
            "display_mode": "live",  # Enable live display mode
            "refresh_rate": 1  # Update every second
        }
    )

    # Start the dashboard display first
    dashboard_task = asyncio.create_task(dashboard.run_async())

    comm_agent = CommunicationAgent(
        name="CommunicationAgent",
        operation="send_message",
        data={}
    )
    task_manager = TaskManager()
    await task_manager.initialize()

    # Create multiple mock agents
    agents = {
        name: MockAgent(name)
        for name in ["MarketAnalyst", "RiskManager", "StrategyDeveloper", "ExecutionManager"]
    }

    # Start agent simulation tasks
    agent_tasks = [agent.simulate_work() for agent in agents.values()]

    async def update_dashboard():
        try:
            while True:
                # Update each agent's status
                for agent_name, agent in agents.items():
                    dashboard.data = {
                        "agent_status": {
                            "name": agent_name,
                            "status": agent.status,
                            "current_task": agent.current_task,
                            "message_queue_size": len(agent.message_queue),
                            "cpu_usage": random.uniform(0.1, 5.0),  # Simulated metrics
                            "memory_usage": random.uniform(100, 500),  # Simulated metrics in MB
                            "uptime": (datetime.now() - agent.start_time).total_seconds(),
                            "last_message": agent.message_history[-1]["sent"] if agent.message_history else None
                        }
                    }
                    dashboard.operation = "update_agent_status"
                    await dashboard.run_async()
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            # Update one last time with stopped status
            for agent_name, agent in agents.items():
                dashboard.data = {
                    "agent_status": {
                        "name": agent_name,
                        "status": "stopped",
                        "current_task": None,
                        "message_queue_size": 0,
                        "cpu_usage": 0,
                        "memory_usage": 0,
                        "uptime": (datetime.now() - agent.start_time).total_seconds(),
                        "last_message": None
                    }
                }
                dashboard.operation = "update_agent_status"
                await dashboard.run_async()
            raise

    async def handle_communication():
        try:
            while True:
                try:
                    # Simulate user input without aioconsole
                    message = f"Test message {datetime.now().strftime('%H:%M:%S')}"
                    target_agent = random.choice(list(agents.keys()))

                    # Process message
                    response = await agents[target_agent].handle_message(message)

                    # Update communication agent with the message
                    comm_agent.data = {
                        "message": {
                            "sender": "user",
                            "recipient": target_agent,
                            "content": message,
                            "type": "user_to_agent"
                        }
                    }
                    comm_agent.operation = "send_message"
                    await comm_agent.run_async()

                    # Update communication agent with the response
                    comm_agent.data = {
                        "message": {
                            "sender": target_agent,
                            "recipient": "user",
                            "content": response,
                            "type": "agent_to_user"
                        }
                    }
                    comm_agent.operation = "send_message"
                    await comm_agent.run_async()

                    await asyncio.sleep(3)  # Wait before next message
                except Exception as e:
                    print(f"Error in communication: {str(e)}")
                    await asyncio.sleep(1)
        except asyncio.CancelledError:
            # Send final shutdown message
            comm_agent.data = {
                "message": {
                    "sender": "system",
                    "recipient": "all",
                    "content": "System shutting down",
                    "type": "system"
                }
            }
            comm_agent.operation = "send_message"
            await comm_agent.run_async()
            raise

    async def shutdown():
        # Stop all agents
        await asyncio.gather(*[agent.stop() for agent in agents.values()])

        # Update dashboard one last time
        dashboard.operation = "stop_dashboard"
        await dashboard.run_async()

    try:
        # Run all tasks concurrently
        await asyncio.gather(
            dashboard_task,  # Make sure dashboard task is included
            update_dashboard(),
            handle_communication(),
            *agent_tasks
        )
    except (KeyboardInterrupt, asyncio.CancelledError):
        print("\nShutting down gracefully...")
        await shutdown()
        print("Shutdown complete.")

if __name__ == "__main__":
    try:
        asyncio.run(test_dashboard())
    except KeyboardInterrupt:
        print("\nDashboard test completed.")
    except Exception as e:
        print(f"\nError occurred: {str(e)}")
    finally:
        print("Exiting...")