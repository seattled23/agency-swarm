from agency_swarm.tools import BaseTool
from pydantic import Field
from pathlib import Path
import json

class TaskQuery(BaseTool):
    """
    A tool for querying and retrieving task information from the task database.
    Supports filtering by various criteria and generating task reports.
    """
    
    query_type: str = Field(
        ..., description="Type of query (all, division, status, priority, deadline)"
    )
    
    filter_value: str = Field(
        default="", description="Value to filter by (division name, status, priority level, or date)"
    )

    def __init__(self, **data):
        super().__init__(**data)
        self.tasks_file = Path("agency_divisions/planning/data/tasks.json")

    def run(self):
        """
        Queries tasks based on specified criteria and returns formatted results.
        """
        if not self.tasks_file.exists():
            return "No tasks found. Task database has not been initialized."

        tasks_data = self._load_tasks()
        filtered_tasks = self._filter_tasks(tasks_data["tasks"])
        
        if not filtered_tasks:
            return f"No tasks found matching criteria: {self.query_type} = {self.filter_value}"
        
        return self._format_results(filtered_tasks)

    def _load_tasks(self):
        """Load tasks from JSON file."""
        return json.loads(self.tasks_file.read_text())

    def _filter_tasks(self, tasks):
        """Filter tasks based on query criteria."""
        if self.query_type == "all":
            return tasks
            
        return [task for task in tasks if self._matches_criteria(task)]

    def _matches_criteria(self, task):
        """Check if task matches the query criteria."""
        if self.query_type == "division":
            return task["division"].lower() == self.filter_value.lower()
        elif self.query_type == "status":
            return task["status"].lower() == self.filter_value.lower()
        elif self.query_type == "priority":
            return task["priority"].lower() == self.filter_value.lower()
        elif self.query_type == "deadline":
            return task["deadline"] == self.filter_value
        return False

    def _format_results(self, tasks):
        """Format task results into a readable string."""
        result = []
        for task in tasks:
            result.append(f"\nTask ID: {task['id']}")
            result.append(f"Title: {task['title']}")
            result.append(f"Description: {task['description']}")
            result.append(f"Division: {task['division']}")
            result.append(f"Priority: {task['priority']}")
            result.append(f"Status: {task['status']}")
            result.append(f"Deadline: {task['deadline']}")
            if task['dependencies']:
                result.append(f"Dependencies: {', '.join(task['dependencies'])}")
            result.append("-" * 50)
        
        return "\n".join(result)

if __name__ == "__main__":
    # Test querying all tasks
    query = TaskQuery(query_type="all")
    print(query.run())
    
    # Test querying by division
    query = TaskQuery(query_type="division", filter_value="Planning")
    print(query.run()) 