from agency_swarm.tools import BaseTool
from pydantic import Field
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import logging
import os
import json
from dataclasses import dataclass
import aiofiles
from rich.console import Console
from rich.table import Table
from rich.live import Live
from rich.panel import Panel
from rich.layout import Layout
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn
import psutil
import time

@dataclass
class AgentStatus:
    """Data class for agent status information"""
    name: str
    status: str
    current_task: Optional[str]
    last_message: Optional[str]
    message_queue_size: int
    cpu_usage: float
    memory_usage: float
    uptime: float
    last_updated: str

class AgentDashboard(BaseTool):
    """
    Tool for displaying a real-time dashboard of agent activity and system metrics.
    Provides visual monitoring of agent status, tasks, and performance metrics.
    """
    
    operation: str = Field(
        ..., description="Operation to perform ('start_dashboard', 'update_agent_status', 'stop_dashboard')"
    )
    
    data: Dict = Field(
        {}, description="Data for the operation (agent status, metrics, etc.)"
    )

    def __init__(self, **data):
        super().__init__(**data)
        self.setup_logging()
        self.console = Console()
        self.agent_statuses: Dict[str, AgentStatus] = {}
        self.start_time = time.time()
        self.is_running = False
        self.layout = self._create_layout()

    def setup_logging(self):
        """Sets up logging for the dashboard"""
        log_dir = "agency_divisions/internal_operations/logs/dashboard"
        os.makedirs(log_dir, exist_ok=True)
        
        logging.basicConfig(
            filename=f"{log_dir}/dashboard.log",
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger('AgentDashboard')

    def _create_layout(self) -> Layout:
        """Creates the dashboard layout"""
        layout = Layout()
        
        layout.split(
            Layout(name="header", size=3),
            Layout(name="main"),
            Layout(name="footer", size=3)
        )
        
        layout["main"].split_row(
            Layout(name="agents", ratio=2),
            Layout(name="metrics", ratio=1)
        )
        
        return layout

    def _generate_header(self) -> Panel:
        """Generates the dashboard header"""
        grid = Table.grid(expand=True)
        grid.add_column(justify="center", ratio=1)
        
        title = Text("Agent Swarm Dashboard", style="bold blue")
        subtitle = Text(f"System Uptime: {self._format_uptime(time.time() - self.start_time)}")
        
        grid.add_row(title)
        grid.add_row(subtitle)
        
        return Panel(grid, style="white on blue")

    def _generate_agent_table(self) -> Table:
        """Generates the agent status table"""
        table = Table(title="Agent Status", expand=True)
        
        table.add_column("Agent", style="cyan", no_wrap=True)
        table.add_column("Status", style="magenta")
        table.add_column("Current Task", style="green")
        table.add_column("Queue Size", justify="right", style="yellow")
        table.add_column("CPU %", justify="right", style="red")
        table.add_column("Memory %", justify="right", style="blue")
        table.add_column("Last Updated", style="dim")
        
        for agent_name, status in sorted(self.agent_statuses.items()):
            table.add_row(
                agent_name,
                self._get_status_style(status.status),
                str(status.current_task or ""),
                str(status.message_queue_size),
                f"{status.cpu_usage:.1f}%",
                f"{status.memory_usage:.1f}%",
                status.last_updated
            )
        
        return table

    def _generate_metrics_panel(self) -> Panel:
        """Generates the system metrics panel"""
        table = Table.grid(expand=True)
        table.add_column("Metric", style="bold")
        table.add_column("Value", justify="right")
        
        # System metrics
        cpu_percent = psutil.cpu_percent()
        memory = psutil.virtual_memory()
        
        table.add_row("System CPU Usage", f"{cpu_percent}%")
        table.add_row("System Memory Usage", f"{memory.percent}%")
        table.add_row("Active Agents", str(len(self.agent_statuses)))
        
        # Calculate total message queue size
        total_queue_size = sum(status.message_queue_size for status in self.agent_statuses.values())
        table.add_row("Total Queue Size", str(total_queue_size))
        
        return Panel(table, title="System Metrics", border_style="green")

    def _generate_footer(self) -> Panel:
        """Generates the dashboard footer"""
        return Panel(
            Text("Press Ctrl+C to stop the dashboard", justify="center"),
            style="white on blue"
        )

    def _get_status_style(self, status: str) -> Text:
        """Returns styled status text"""
        style_map = {
            "online": "green",
            "busy": "yellow",
            "error": "red",
            "offline": "red dim",
            "initializing": "blue"
        }
        return Text(status, style=style_map.get(status.lower(), "white"))

    def _format_uptime(self, seconds: float) -> str:
        """Formats uptime duration"""
        return str(timedelta(seconds=int(seconds)))

    async def run_async(self) -> Dict[str, Any]:
        """
        Asynchronously executes dashboard operations
        """
        try:
            if self.operation == "start_dashboard":
                return await self._start_dashboard()
            elif self.operation == "update_agent_status":
                return await self._update_agent_status()
            elif self.operation == "stop_dashboard":
                return await self._stop_dashboard()
            else:
                raise ValueError(f"Unknown operation: {self.operation}")
            
        except Exception as e:
            self.logger.error(f"Error in dashboard operation: {str(e)}")
            raise

    def run(self) -> Dict[str, Any]:
        """
        Synchronous wrapper for dashboard operations
        """
        return asyncio.run(self.run_async())

    async def _start_dashboard(self) -> Dict[str, Any]:
        """Starts the dashboard display"""
        try:
            self.is_running = True
            
            with Live(self.layout, refresh_per_second=2) as live:
                while self.is_running:
                    self.layout["header"].update(self._generate_header())
                    self.layout["agents"].update(self._generate_agent_table())
                    self.layout["metrics"].update(self._generate_metrics_panel())
                    self.layout["footer"].update(self._generate_footer())
                    
                    await asyncio.sleep(0.5)
            
            return {"status": "success", "message": "Dashboard stopped"}
            
        except Exception as e:
            self.logger.error(f"Error starting dashboard: {str(e)}")
            raise

    async def _update_agent_status(self) -> Dict[str, Any]:
        """Updates the status of an agent"""
        try:
            agent_data = self.data.get("agent_status", {})
            agent_name = agent_data.get("name")
            
            if not agent_name:
                raise ValueError("Agent name is required")
            
            self.agent_statuses[agent_name] = AgentStatus(
                name=agent_name,
                status=agent_data.get("status", "unknown"),
                current_task=agent_data.get("current_task"),
                last_message=agent_data.get("last_message"),
                message_queue_size=agent_data.get("message_queue_size", 0),
                cpu_usage=agent_data.get("cpu_usage", 0.0),
                memory_usage=agent_data.get("memory_usage", 0.0),
                uptime=agent_data.get("uptime", 0.0),
                last_updated=datetime.now().strftime("%H:%M:%S")
            )
            
            return {
                "status": "success",
                "agent": agent_name
            }
            
        except Exception as e:
            self.logger.error(f"Error updating agent status: {str(e)}")
            raise

    async def _stop_dashboard(self) -> Dict[str, Any]:
        """Stops the dashboard display"""
        try:
            self.is_running = False
            return {"status": "success", "message": "Dashboard stopped"}
            
        except Exception as e:
            self.logger.error(f"Error stopping dashboard: {str(e)}")
            raise

if __name__ == "__main__":
    # Test the dashboard
    async def test():
        dashboard = AgentDashboard(operation="start_dashboard", data={})
        dashboard_task = asyncio.create_task(dashboard.run_async())
        
        # Simulate agent updates
        for i in range(3):
            dashboard.operation = "update_agent_status"
            dashboard.data = {
                "agent_status": {
                    "name": "TestAgent",
                    "status": "online",
                    "current_task": f"Task {i}",
                    "message_queue_size": i,
                    "cpu_usage": 0.5,
                    "memory_usage": 2.0,
                    "uptime": i * 10
                }
            }
            await dashboard.run_async()
            await asyncio.sleep(2)
        
        dashboard.operation = "stop_dashboard"
        await dashboard.run_async()
        await dashboard_task
    
    asyncio.run(test()) 