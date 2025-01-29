from agency_swarm.tools import BaseTool
from pydantic import Field
import os
from dotenv import load_dotenv
import json
from datetime import datetime

load_dotenv()

class StatusTrackerTool(BaseTool):
    """
    Tool for tracking and managing the status of tasks and agents across the agency.
    Provides comprehensive status reports and identifies bottlenecks.
    """
    report_type: str = Field(
        ..., description="Type of report to generate ('tasks', 'agents', 'full')"
    )
    division_filter: str = Field(
        None, description="Optional division to filter results"
    )

    def run(self):
        """
        Generates a status report based on the specified parameters.
        """
        try:
            report = []
            
            if self.report_type in ['tasks', 'full']:
                report.extend(self._generate_task_status())
            
            if self.report_type in ['agents', 'full']:
                report.extend(self._generate_agent_status())
            
            if not report:
                return "No status information available"
            
            return "\n\n".join(report)
            
        except Exception as e:
            return f"Error generating status report: {str(e)}"

    def _generate_task_status(self):
        """Generates task status report"""
        report = ["# Task Status Report", ""]
        
        try:
            # Load tasks
            with open("agency_divisions/planning/data/tasks.json", 'r') as f:
                task_data = json.load(f)
            
            # Filter by division if specified
            tasks = task_data["tasks"]
            if self.division_filter:
                tasks = [t for t in tasks if t["division"] == self.division_filter]
            
            # Group tasks by status
            status_groups = {}
            for task in tasks:
                status = task["status"]
                if status not in status_groups:
                    status_groups[status] = []
                status_groups[status].append(task)
            
            # Generate status sections
            for status, tasks in status_groups.items():
                report.append(f"## {status.upper()} Tasks")
                for task in tasks:
                    report.append(f"- {task['id']}: {task['title']}")
                    report.append(f"  - Division: {task['division']}")
                    report.append(f"  - Priority: {task['priority']}")
                    report.append(f"  - Deadline: {task['deadline']}")
                    if task["dependencies"]:
                        report.append(f"  - Dependencies: {', '.join(task['dependencies'])}")
                report.append("")
            
            # Add summary
            report.append("## Task Summary")
            for status, tasks in status_groups.items():
                report.append(f"- {status.upper()}: {len(tasks)} tasks")
            
        except Exception as e:
            report.append(f"Error loading task data: {str(e)}")
        
        return report

    def _generate_agent_status(self):
        """Generates agent status report"""
        report = ["# Agent Status Report", ""]
        
        try:
            # Load agency configuration
            with open("agency_divisions/agency_config.json", 'r') as f:
                config = json.load(f)
            
            # Filter by division if specified
            agents = config["agents"]
            if self.division_filter:
                agents = {name: info for name, info in agents.items() 
                         if info["division"] == self.division_filter}
            
            # Group agents by status
            status_groups = {}
            for name, info in agents.items():
                status = info["status"]
                if status not in status_groups:
                    status_groups[status] = []
                status_groups[status].append((name, info))
            
            # Generate status sections
            for status, agent_list in status_groups.items():
                report.append(f"## {status.upper()} Agents")
                for name, info in agent_list:
                    report.append(f"- {name}")
                    report.append(f"  - Division: {info['division']}")
                    report.append(f"  - Description: {info['description']}")
                report.append("")
            
            # Add communication flows
            report.append("## Communication Flows")
            for flow in config["communication_flows"]:
                report.append(f"- {flow[0]} → {flow[1]}")
            report.append("")
            
            # Add summary
            report.append("## Agent Summary")
            for status, agent_list in status_groups.items():
                report.append(f"- {status.upper()}: {len(agent_list)} agents")
            
        except Exception as e:
            report.append(f"Error loading agent data: {str(e)}")
        
        return report

    def _get_bottlenecks(self):
        """Identifies potential bottlenecks in the system"""
        bottlenecks = []
        
        try:
            # Load task data
            with open("agency_divisions/planning/data/tasks.json", 'r') as f:
                task_data = json.load(f)
            
            # Check for blocked tasks
            for task in task_data["tasks"]:
                if task["status"] == "Blocked":
                    bottlenecks.append(f"Task {task['id']} is blocked")
                elif task["status"] == "In Progress" and datetime.strptime(task["deadline"], "%Y-%m-%d").date() < datetime.now().date():
                    bottlenecks.append(f"Task {task['id']} is past deadline")
            
            # Load agent data
            with open("agency_divisions/agency_config.json", 'r') as f:
                config = json.load(f)
            
            # Check for inactive critical agents
            for name, info in config["agents"].items():
                if name in config.get("agent_priorities", {}).get("critical", []) and info["status"] != "active":
                    bottlenecks.append(f"Critical agent {name} is not active")
            
        except Exception as e:
            bottlenecks.append(f"Error checking bottlenecks: {str(e)}")
        
        return bottlenecks

if __name__ == "__main__":
    # Test the tool
    tool = StatusTrackerTool(
        report_type="full",
        division_filter=None
    )
    print(tool.run()) 