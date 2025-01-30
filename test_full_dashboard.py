import asyncio
import random
from datetime import datetime
from agency_divisions.internal_operations.tools.agent_dashboard import AgentDashboard
from agency_divisions.internal_operations.tools.communication_agent import CommunicationAgent
from agency_divisions.task_management.task_manager import TaskManager
import signal
import sys
import os
from dotenv import load_dotenv
import aioconsole

# Load environment variables
load_dotenv()

class MockAgent:
    def __init__(self, name, initial_status="initializing"):
        self.name = name
        self.status = initial_status
        self.current_task = None
        self.queue_size = 0
        self.start_time = datetime.now().timestamp()

    async def simulate_work(self):
        """Simulate agent work and status changes"""
        statuses = ["online", "busy", "processing", "waiting"]
        tasks = [
            "Analyzing market data",
            "Processing user request",
            "Updating database",
            "Communicating with other agents",
            "Optimizing parameters",
            "Generating report"
        ]

        while True:
            # Randomly change status and task
            self.status = random.choice(statuses)
            self.current_task = random.choice(tasks)
            # Simulate message queue changes
            queue_change = random.randint(-1, 2)
            self.queue_size = max(0, self.queue_size + queue_change)
            await asyncio.sleep(random.uniform(1.5, 4.0))

    async def handle_message(self, message: str) -> str:
        """Handle incoming messages and generate responses"""
        responses = [
            f"Processing your request: {message}",
            f"Working on it: {message}",
            f"Analyzing input: {message}",
            f"Task received: {message}"
        ]
        await asyncio.sleep(random.uniform(0.5, 2.0))  # Simulate processing time
        return random.choice(responses)

async def test_dashboard():
    # Create dashboard, communication agent, and task manager
    dashboard = AgentDashboard(operation="start_dashboard", data={})
    comm_agent = CommunicationAgent(operation="send_message", data={})
    task_manager = TaskManager()

    # Create multiple mock agents
    agents = [
        MockAgent("MarketAnalyzer"),
        MockAgent("RiskManager"),
        MockAgent("DataProcessor"),
        MockAgent("CommunicationHandler"),
        MockAgent("TaskCoordinator")
    ]

    try:
        # Initialize task manager
        await task_manager.initialize()

        # Start the dashboard
        dashboard_task = asyncio.create_task(dashboard.run_async())

        # Start agent simulation tasks
        agent_tasks = []
        for agent in agents:
            agent_tasks.append(asyncio.create_task(agent.simulate_work()))

        # Create a task to update the dashboard with agent statuses
        async def update_dashboard():
            while True:
                for agent in agents:
                    status_data = {
                        "name": agent.name,
                        "status": agent.status,
                        "current_task": agent.current_task,
                        "message_queue_size": agent.queue_size,
                        "cpu_usage": random.uniform(0.1, 5.0),
                        "memory_usage": random.uniform(1.0, 8.0),
                        "uptime": datetime.now().timestamp() - agent.start_time
                    }

                    dashboard.operation = "update_agent_status"
                    dashboard.data = {"agent_status": status_data}
                    await dashboard.run_async()

                await asyncio.sleep(1)  # Update interval

        # Create a task to handle user input and agent responses
        async def handle_communication():
            while True:
                try:
                    # Get user input
                    user_input = await aioconsole.ainput("")
                    if user_input.lower() in ['quit', 'exit']:
                        break

                    # Select a random agent to handle the message
                    target_agent = random.choice(agents)

                    # Send user message
                    comm_agent.operation = "send_message"
                    comm_agent.data = {
                        "message": {
                            "sender": "user",
                            "recipient": target_agent.name,
                            "content": user_input,
                            "type": "user_to_agent"
                        }
                    }
                    await comm_agent.run_async()

                    # Get agent response
                    response = await target_agent.handle_message(user_input)

                    # Send agent response
                    comm_agent.data = {
                        "message": {
                            "sender": target_agent.name,
                            "recipient": "user",
                            "content": response,
                            "type": "agent_to_user"
                        }
                    }
                    await comm_agent.run_async()

                except Exception as e:
                    print(f"Error in communication: {str(e)}")
                    continue

        # Start the update and communication tasks
        update_task = asyncio.create_task(update_dashboard())
        comm_task = asyncio.create_task(handle_communication())

        # Wait for all tasks
        try:
            await asyncio.gather(
                dashboard_task,
                update_task,
                comm_task,
                *agent_tasks
            )
        except KeyboardInterrupt:
            # Cancel all tasks on Ctrl+C
            update_task.cancel()
            comm_task.cancel()
            for task in agent_tasks:
                task.cancel()
            dashboard.operation = "stop_dashboard"
            await dashboard.run_async()
            await dashboard_task

    except Exception as e:
        print(f"Error in test: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    try:
        print("Starting full dashboard test with multiple agents...")
        print("Type your messages in the input area. Type 'quit' or 'exit' to stop.")
        asyncio.run(test_dashboard())
    except KeyboardInterrupt:
        print("\nTest completed successfully.")