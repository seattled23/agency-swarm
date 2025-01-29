from agency_swarm.tools import BaseTool
from pydantic import Field
from pathlib import Path
import json
from datetime import datetime

class ProjectManager(BaseTool):
    """
    A tool for managing projects, their components, and tracking their progress.
    Handles project creation, updates, and status tracking.
    """
    
    project_id: str = Field(
        default="", description="Unique identifier for the project. Leave empty for new projects."
    )
    
    name: str = Field(
        ..., description="Name of the project"
    )
    
    description: str = Field(
        ..., description="Detailed description of the project"
    )
    
    objectives: list = Field(
        ..., description="List of project objectives"
    )
    
    divisions_involved: list = Field(
        ..., description="List of divisions involved in the project"
    )
    
    status: str = Field(
        default="Planning", description="Current status of the project (Planning, In Progress, On Hold, Completed)"
    )
    
    priority: str = Field(
        ..., description="Project priority (High, Medium, Low)"
    )
    
    start_date: str = Field(
        default="", description="Project start date in YYYY-MM-DD format"
    )
    
    end_date: str = Field(
        default="", description="Project end date in YYYY-MM-DD format"
    )

    def __init__(self, **data):
        super().__init__(**data)
        self.projects_file = Path("agency_divisions/projects/data/projects.json")
        self.projects_file.parent.mkdir(parents=True, exist_ok=True)
        if not self.projects_file.exists():
            self.projects_file.write_text('{"projects": []}')

    def run(self):
        """
        Manages project operations including creating, updating, and retrieving project information.
        """
        projects_data = self._load_projects()
        
        if not self.project_id:  # New project
            project_id = f"PROJ-{len(projects_data['projects']) + 1}"
            project = {
                "id": project_id,
                "name": self.name,
                "description": self.description,
                "objectives": self.objectives,
                "divisions_involved": self.divisions_involved,
                "status": self.status,
                "priority": self.priority,
                "start_date": self.start_date,
                "end_date": self.end_date,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "tasks": []
            }
            projects_data["projects"].append(project)
            result = f"Created new project: {project_id}"
        else:  # Update existing project
            for project in projects_data["projects"]:
                if project["id"] == self.project_id:
                    project.update({
                        "name": self.name,
                        "description": self.description,
                        "objectives": self.objectives,
                        "divisions_involved": self.divisions_involved,
                        "status": self.status,
                        "priority": self.priority,
                        "start_date": self.start_date,
                        "end_date": self.end_date,
                        "updated_at": datetime.now().isoformat()
                    })
                    result = f"Updated project: {self.project_id}"
                    break
            else:
                result = f"Project not found: {self.project_id}"
        
        self._save_projects(projects_data)
        return result

    def _load_projects(self):
        """Load projects from JSON file."""
        return json.loads(self.projects_file.read_text())

    def _save_projects(self, projects_data):
        """Save projects to JSON file."""
        self.projects_file.write_text(json.dumps(projects_data, indent=2))

if __name__ == "__main__":
    # Test creating a new project
    manager = ProjectManager(
        name="Agency Restructuring",
        description="Reorganize the agency into specialized divisions",
        objectives=[
            "Create division structure",
            "Define roles and responsibilities",
            "Implement communication flows",
            "Set up tracking systems"
        ],
        divisions_involved=[
            "Planning",
            "Internal Operations",
            "Projects"
        ],
        priority="High",
        start_date="2024-01-29",
        end_date="2024-02-29"
    )
    print(manager.run()) 