from agency_swarm.tools import BaseTool
from pydantic import Field
import os
from pathlib import Path
import json
from datetime import datetime

class TaskTracker(BaseTool):
    """
    A tool for tracking tasks, their status, and dependencies across all divisions.
    Maintains a centralized task database with priorities, deadlines, and assignments.
    """
    
    task_id: str = Field(
        default="", description="Unique identifier for the task. Leave empty for new tasks."
    )
    
    title: str = Field(
        ..., description="Title/name of the task"
    )
    
    description: str = Field(
        ..., description="Detailed description of the task"
    )
    
    division: str = Field(
        ..., description="Division responsible for the task"
    )
    
    priority: str = Field(
        ..., description="Task priority (High, Medium, Low)"
    )
    
    status: str = Field(
        default="New", description="Current status of the task (New, In Progress, Blocked, Completed)"
    )
    
    dependencies: list = Field(
        default=[], description="List of task IDs that this task depends on"
    )
    
    deadline: str = Field(
        default="", description="Task deadline in YYYY-MM-DD format"
    )

    def __init__(self, **data):
        super().__init__(**data)
        self.tasks_file = Path("agency_divisions/planning/data/tasks.json")
        self.tasks_file.parent.mkdir(parents=True, exist_ok=True)
        if not self.tasks_file.exists():
            self.tasks_file.write_text('{"tasks": []}')

    def run(self):
        """
        Manages task tracking operations including creating, updating, and retrieving tasks.
        """
        tasks_data = self._load_tasks()
        
        if not self.task_id:  # New task
            task_id = f"TASK-{len(tasks_data['tasks']) + 1}"
            task = {
                "id": task_id,
                "title": self.title,
                "description": self.description,
                "division": self.division,
                "priority": self.priority,
                "status": self.status,
                "dependencies": self.dependencies,
                "deadline": self.deadline,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            tasks_data["tasks"].append(task)
            result = f"Created new task: {task_id}"
        else:  # Update existing task
            for task in tasks_data["tasks"]:
                if task["id"] == self.task_id:
                    task.update({
                        "title": self.title,
                        "description": self.description,
                        "division": self.division,
                        "priority": self.priority,
                        "status": self.status,
                        "dependencies": self.dependencies,
                        "deadline": self.deadline,
                        "updated_at": datetime.now().isoformat()
                    })
                    result = f"Updated task: {self.task_id}"
                    break
            else:
                result = f"Task not found: {self.task_id}"
        
        self._save_tasks(tasks_data)
        return result

    def _load_tasks(self):
        """Load tasks from JSON file."""
        return json.loads(self.tasks_file.read_text())

    def _save_tasks(self, tasks_data):
        """Save tasks to JSON file."""
        self.tasks_file.write_text(json.dumps(tasks_data, indent=2))

if __name__ == "__main__":
    # Test creating a new task
    tracker = TaskTracker(
        title="Set up Planning Division",
        description="Initialize Planning Division with task tracking capabilities",
        division="Planning",
        priority="High",
        status="In Progress",
        deadline="2024-01-30"
    )
    print(tracker.run()) 