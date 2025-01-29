import asyncio
from agency_divisions.internal_operations.tools.agent_dashboard import AgentDashboard
from agency_divisions.task_management.task_manager import TaskManager
from agency_divisions.market_analysis.market_analyst import MarketAnalyst
from agency_divisions.risk_management.risk_manager import RiskManager
import psutil
import os
import signal
import sys

class AgencyRunner:
    def __init__(self):
        self.dashboard = AgentDashboard(operation="start_dashboard", data={})
        self.task_manager = TaskManager()
        self.market_analyst = MarketAnalyst()
        self.risk_manager = RiskManager()
        self.agents = {
            "TaskManager": self.task_manager,
            "MarketAnalyst": self.market_analyst,
            "RiskManager": self.risk_manager
        }
        self.running = True

    async def start_agents(self):
        """Start all agents and initialize them"""
        for agent_name, agent in self.agents.items():
            try:
                # Start agent initialization
                await self._update_agent_status(agent_name, "initializing")
                await agent.initialize()
                await self._update_agent_status(agent_name, "online")
                
            except Exception as e:
                print(f"Error starting {agent_name}: {str(e)}")
                await self._update_agent_status(agent_name, "error")

    async def monitor_agents(self):
        """Monitor agent status and update dashboard"""
        while self.running:
            try:
                process = psutil.Process()
                
                for agent_name, agent in self.agents.items():
                    status_data = {
                        "name": agent_name,
                        "status": await agent.get_status(),
                        "current_task": await agent.get_current_task(),
                        "message_queue_size": await agent.get_queue_size(),
                        "cpu_usage": process.cpu_percent() / psutil.cpu_count(),
                        "memory_usage": process.memory_percent(),
                        "uptime": agent.uptime if hasattr(agent, 'uptime') else 0.0
                    }
                    
                    await self._update_agent_status(agent_name, status_data["status"], status_data)
                
                await asyncio.sleep(1)  # Update frequency
                
            except Exception as e:
                print(f"Error monitoring agents: {str(e)}")
                await asyncio.sleep(5)  # Longer delay on error

    async def _update_agent_status(self, agent_name: str, status: str, status_data: dict = None):
        """Update agent status in dashboard"""
        try:
            if status_data is None:
                status_data = {
                    "name": agent_name,
                    "status": status,
                    "current_task": None,
                    "message_queue_size": 0,
                    "cpu_usage": 0.0,
                    "memory_usage": 0.0,
                    "uptime": 0.0
                }
            
            self.dashboard.operation = "update_agent_status"
            self.dashboard.data = {"agent_status": status_data}
            await self.dashboard.run_async()
            
        except Exception as e:
            print(f"Error updating status for {agent_name}: {str(e)}")

    async def shutdown(self):
        """Gracefully shutdown all agents"""
        print("\nInitiating shutdown...")
        self.running = False
        
        for agent_name, agent in self.agents.items():
            try:
                await self._update_agent_status(agent_name, "shutting_down")
                await agent.shutdown()
                await self._update_agent_status(agent_name, "offline")
                
            except Exception as e:
                print(f"Error shutting down {agent_name}: {str(e)}")

        # Stop the dashboard
        try:
            self.dashboard.operation = "stop_dashboard"
            await self.dashboard.run_async()
        except Exception as e:
            print(f"Error stopping dashboard: {str(e)}")

    def signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        if self.running:
            print("\nShutdown signal received...")
            asyncio.create_task(self.shutdown())

async def main():
    try:
        # Create and start the agency runner
        agency = AgencyRunner()
        
        # Set up signal handlers
        signal.signal(signal.SIGINT, agency.signal_handler)
        signal.signal(signal.SIGTERM, agency.signal_handler)
        
        # Start the dashboard in the background
        dashboard_task = asyncio.create_task(agency.dashboard.run_async())
        
        # Start all agents
        await agency.start_agents()
        
        # Start monitoring
        monitor_task = asyncio.create_task(agency.monitor_agents())
        
        # Wait for shutdown signal
        while agency.running:
            await asyncio.sleep(1)
        
        # Wait for tasks to complete
        await asyncio.gather(monitor_task, dashboard_task)
        
    except Exception as e:
        print(f"Error in main: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutdown complete.") 