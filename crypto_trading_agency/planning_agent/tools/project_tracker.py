from agency_swarm.tools import BaseTool
from pydantic import Field
import os
import json
import logging
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Union
import uuid

class ProjectTracker(BaseTool):
    """
    Tool for managing project milestones, tracking progress, and coordinating dependencies
    across multiple agents and divisions. Supports async tracking and real-time updates.
    """
    
    project_spec: Dict = Field(
        ...,
        description="Project specification including milestones, dependencies, and timeline"
    )
    
    tracking_mode: str = Field(
        default="async",
        description="Project tracking mode: 'async' or 'sync'"
    )
    
    update_interval: int = Field(
        default=300,
        description="Interval in seconds for status updates in async mode"
    )

    results_dir: Path = Field(
        default=Path("project_tracking"),
        description="Directory to store project tracking results"
    )

    project_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique identifier for this project tracking session"
    )

    project_state: Dict = Field(
        default_factory=dict,
        description="Current state of the project including milestones, tasks, and progress"
    )

    state_file: Path = Field(
        default=None,
        description="Path to the state file for this project"
    )

    def __init__(self, **data):
        super().__init__(**data)
        # Create results directory
        self.results_dir.mkdir(exist_ok=True)
        
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] %(message)s',
            handlers=[
                logging.FileHandler(self.results_dir / 'project_tracking.log'),
                logging.StreamHandler()
            ]
        )
        
        # Set state file path
        if self.state_file is None:
            self.state_file = self.results_dir / f"project_{self.project_id}_state.json"
        
        # Initialize project state
        self.initialize_project_state()

    def initialize_project_state(self):
        """Initialize or load project state."""
        if self.state_file.exists():
            with open(self.state_file, 'r') as f:
                self.project_state = json.load(f)
        else:
            self.project_state = {
                "project_id": self.project_id,
                "status": "initialized",
                "start_time": datetime.now().isoformat(),
                "last_update": datetime.now().isoformat(),
                "milestones": {},
                "dependencies": {},
                "progress": 0.0,
                "active_tasks": [],
                "completed_tasks": [],
                "issues": []
            }
            self._save_state()

    def _save_state(self):
        """Save current project state to file."""
        with open(self.state_file, 'w') as f:
            json.dump(self.project_state, f, indent=4)

    def analyze_project_structure(self) -> Dict:
        """Analyze project structure and dependencies."""
        logging.info("Analyzing project structure")
        
        structure = {
            "milestones": self._analyze_milestones(),
            "dependencies": self._analyze_dependencies(),
            "timeline": self._generate_timeline(),
            "critical_path": self._identify_critical_path()
        }
        
        return structure

    def _analyze_milestones(self) -> Dict:
        """Analyze project milestones and their relationships."""
        milestones = {}
        
        for milestone in self.project_spec.get("milestones", []):
            milestone_id = milestone.get("id", str(uuid.uuid4()))
            milestones[milestone_id] = {
                "name": milestone.get("name"),
                "description": milestone.get("description"),
                "deadline": milestone.get("deadline"),
                "dependencies": milestone.get("dependencies", []),
                "deliverables": milestone.get("deliverables", []),
                "status": "pending",
                "progress": 0.0,
                "assigned_agents": milestone.get("assigned_agents", [])
            }
        
        return milestones

    def _analyze_dependencies(self) -> Dict:
        """Analyze project dependencies and their status."""
        dependencies = {}
        
        for dep in self.project_spec.get("dependencies", []):
            dep_id = dep.get("id", str(uuid.uuid4()))
            dependencies[dep_id] = {
                "type": dep.get("type"),
                "source": dep.get("source"),
                "target": dep.get("target"),
                "status": "pending",
                "constraints": dep.get("constraints", []),
                "risk_level": self._assess_dependency_risk(dep)
            }
        
        return dependencies

    def _assess_dependency_risk(self, dependency: Dict) -> str:
        """Assess risk level of a dependency."""
        risk_factors = {
            "complexity": dependency.get("complexity", "low"),
            "impact": dependency.get("impact", "low"),
            "uncertainty": dependency.get("uncertainty", "low")
        }
        
        risk_scores = {"low": 1, "medium": 2, "high": 3}
        total_score = sum(risk_scores[factor] for factor in risk_factors.values())
        
        if total_score <= 4:
            return "low"
        elif total_score <= 7:
            return "medium"
        return "high"

    def _generate_timeline(self) -> Dict:
        """Generate project timeline with key events and deadlines."""
        timeline = {
            "start_date": self.project_spec.get("start_date", datetime.now().isoformat()),
            "end_date": self.project_spec.get("end_date"),
            "duration": self.project_spec.get("duration"),
            "key_events": []
        }
        
        # Add milestones to timeline
        for milestone in self.project_spec.get("milestones", []):
            timeline["key_events"].append({
                "type": "milestone",
                "name": milestone.get("name"),
                "date": milestone.get("deadline"),
                "duration": milestone.get("duration", "1d")
            })
        
        # Add dependency events
        for dep in self.project_spec.get("dependencies", []):
            if "deadline" in dep:
                timeline["key_events"].append({
                    "type": "dependency",
                    "name": f"Resolve {dep.get('type')} dependency",
                    "date": dep.get("deadline"),
                    "duration": dep.get("duration", "1d")
                })
        
        return timeline

    def _identify_critical_path(self) -> List[str]:
        """Identify critical path through project milestones."""
        # Simplified critical path analysis
        critical_path = []
        milestones = self.project_spec.get("milestones", [])
        
        # Sort milestones by dependencies
        dependency_graph = {m["id"]: m["dependencies"] for m in milestones if "id" in m}
        visited = set()
        
        def visit(milestone_id):
            if milestone_id in visited:
                return
            visited.add(milestone_id)
            for dep in dependency_graph.get(milestone_id, []):
                visit(dep)
            critical_path.append(milestone_id)
        
        for milestone in milestones:
            if "id" in milestone:
                visit(milestone["id"])
        
        return critical_path

    def update_project_status(self, status_update: Dict) -> Dict:
        """Update project status with new information."""
        timestamp = datetime.now().isoformat()
        
        # Update milestone status
        if "milestone_updates" in status_update:
            for milestone_id, update in status_update["milestone_updates"].items():
                if milestone_id in self.project_state["milestones"]:
                    self.project_state["milestones"][milestone_id].update(update)
        
        # Update dependencies
        if "dependency_updates" in status_update:
            for dep_id, update in status_update["dependency_updates"].items():
                if dep_id in self.project_state["dependencies"]:
                    self.project_state["dependencies"][dep_id].update(update)
        
        # Update active tasks
        if "task_updates" in status_update:
            self._update_tasks(status_update["task_updates"])
        
        # Update overall progress
        self._calculate_overall_progress()
        
        # Update project state
        self.project_state["last_update"] = timestamp
        self._save_state()
        
        return self.project_state

    def _update_tasks(self, task_updates: List[Dict]):
        """Update task status and manage task transitions."""
        for update in task_updates:
            task_id = update.get("id")
            status = update.get("status")
            
            if status == "completed":
                if task_id in self.project_state["active_tasks"]:
                    self.project_state["active_tasks"].remove(task_id)
                    self.project_state["completed_tasks"].append(task_id)
            elif status == "active":
                if task_id not in self.project_state["active_tasks"]:
                    self.project_state["active_tasks"].append(task_id)

    def _calculate_overall_progress(self):
        """Calculate overall project progress."""
        if not self.project_state["milestones"]:
            return
        
        total_progress = sum(
            milestone["progress"] 
            for milestone in self.project_state["milestones"].values()
        )
        self.project_state["progress"] = total_progress / len(self.project_state["milestones"])

    def generate_status_report(self) -> Dict:
        """Generate comprehensive status report."""
        return {
            "project_id": self.project_id,
            "timestamp": datetime.now().isoformat(),
            "overall_status": {
                "status": self.project_state["status"],
                "progress": self.project_state["progress"],
                "active_tasks": len(self.project_state["active_tasks"]),
                "completed_tasks": len(self.project_state["completed_tasks"])
            },
            "milestones": self.project_state["milestones"],
            "dependencies": self.project_state["dependencies"],
            "issues": self.project_state["issues"],
            "timeline_status": self._analyze_timeline_status()
        }

    def _analyze_timeline_status(self) -> Dict:
        """Analyze timeline status and detect delays."""
        timeline_status = {
            "on_track": True,
            "delayed_milestones": [],
            "at_risk_milestones": [],
            "upcoming_deadlines": []
        }
        
        current_date = datetime.now()
        
        for milestone_id, milestone in self.project_state["milestones"].items():
            deadline = datetime.fromisoformat(milestone["deadline"]) if "deadline" in milestone else None
            
            if deadline:
                if deadline < current_date and milestone["status"] != "completed":
                    timeline_status["delayed_milestones"].append(milestone_id)
                    timeline_status["on_track"] = False
                elif deadline < current_date + timedelta(days=7) and milestone["status"] != "completed":
                    timeline_status["at_risk_milestones"].append(milestone_id)
                elif deadline > current_date and milestone["status"] != "completed":
                    timeline_status["upcoming_deadlines"].append({
                        "milestone_id": milestone_id,
                        "deadline": deadline.isoformat(),
                        "days_remaining": (deadline - current_date).days
                    })
        
        return timeline_status

    def run(self) -> str:
        """
        Execute project tracking process and generate report.
        """
        try:
            # Analyze project structure
            project_structure = self.analyze_project_structure()
            
            # Update project state with structure
            self.project_state["milestones"] = project_structure["milestones"]
            self.project_state["dependencies"] = project_structure["dependencies"]
            
            # Generate initial status report
            status_report = self.generate_status_report()
            
            # Export report
            report_path = self.results_dir / f"project_{self.project_id}_report.json"
            with open(report_path, 'w') as f:
                json.dump(status_report, f, indent=4)
            
            logging.info(f"Project tracking initialized. Report saved to {report_path}")
            
            # Return summary
            return self._generate_summary(status_report)
            
        except Exception as e:
            logging.error(f"Error during project tracking: {str(e)}")
            raise

    def _generate_summary(self, report: Dict) -> str:
        """Generate a human-readable summary of the project status."""
        summary = []
        summary.append("Project Status Summary")
        summary.append("=" * 50)
        
        # Overall Status
        overall = report["overall_status"]
        summary.append(f"\nOverall Status: {overall['status']}")
        summary.append(f"Progress: {overall['progress']:.1f}%")
        summary.append(f"Active Tasks: {overall['active_tasks']}")
        summary.append(f"Completed Tasks: {overall['completed_tasks']}")
        
        # Timeline Status
        timeline = report["timeline_status"]
        summary.append(f"\nTimeline Status: {'On Track' if timeline['on_track'] else 'Delayed'}")
        
        if timeline["delayed_milestones"]:
            summary.append("\nDelayed Milestones:")
            for milestone_id in timeline["delayed_milestones"]:
                milestone = report["milestones"][milestone_id]
                summary.append(f"- {milestone['name']}")
        
        if timeline["at_risk_milestones"]:
            summary.append("\nAt Risk Milestones:")
            for milestone_id in timeline["at_risk_milestones"]:
                milestone = report["milestones"][milestone_id]
                summary.append(f"- {milestone['name']}")
        
        if timeline["upcoming_deadlines"]:
            summary.append("\nUpcoming Deadlines:")
            for deadline in timeline["upcoming_deadlines"]:
                milestone = report["milestones"][deadline["milestone_id"]]
                summary.append(f"- {milestone['name']}: {deadline['days_remaining']} days remaining")
        
        # Issues
        if report["issues"]:
            summary.append("\nActive Issues:")
            for issue in report["issues"]:
                summary.append(f"- {issue['description']} (Priority: {issue['priority']})")
        
        return "\n".join(summary)

if __name__ == "__main__":
    # Test the ProjectTracker tool
    project_spec = {
        "name": "Agency Restructuring",
        "description": "Transform crypto trading agency into a general-purpose intelligent automation agency",
        "start_date": datetime.now().isoformat(),
        "end_date": (datetime.now() + timedelta(days=90)).isoformat(),
        "milestones": [
            {
                "id": "rename_agency",
                "name": "Agency Renaming",
                "description": "Rename and rebrand the agency",
                "deadline": (datetime.now() + timedelta(days=7)).isoformat(),
                "dependencies": []
            },
            {
                "id": "create_divisions",
                "name": "Division Creation",
                "description": "Create specialized divisions",
                "deadline": (datetime.now() + timedelta(days=30)).isoformat(),
                "dependencies": ["rename_agency"]
            },
            {
                "id": "implement_tracking",
                "name": "Project Tracking Implementation",
                "description": "Implement async project tracking system",
                "deadline": (datetime.now() + timedelta(days=45)).isoformat(),
                "dependencies": ["create_divisions"]
            }
        ],
        "dependencies": [
            {
                "id": "dep_1",
                "type": "structural",
                "source": "rename_agency",
                "target": "create_divisions",
                "deadline": (datetime.now() + timedelta(days=15)).isoformat()
            }
        ]
    }
    
    tracker = ProjectTracker(
        project_spec=project_spec,
        tracking_mode="async",
        update_interval=300
    )
    print(tracker.run()) 