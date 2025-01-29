from agency_swarm.tools import BaseTool
from pydantic import Field
from pathlib import Path
import json

class ProjectQuery(BaseTool):
    """
    A tool for querying and retrieving project information from the projects database.
    Supports filtering by various criteria and generating project reports.
    """
    
    query_type: str = Field(
        ..., description="Type of query (all, status, priority, division)"
    )
    
    filter_value: str = Field(
        default="", description="Value to filter by (status, priority level, or division name)"
    )

    def __init__(self, **data):
        super().__init__(**data)
        self.projects_file = Path("agency_divisions/projects/data/projects.json")

    def run(self):
        """
        Queries projects based on specified criteria and returns formatted results.
        """
        if not self.projects_file.exists():
            return "No projects found. Projects database has not been initialized."

        projects_data = self._load_projects()
        filtered_projects = self._filter_projects(projects_data["projects"])
        
        if not filtered_projects:
            return f"No projects found matching criteria: {self.query_type} = {self.filter_value}"
        
        return self._format_results(filtered_projects)

    def _load_projects(self):
        """Load projects from JSON file."""
        return json.loads(self.projects_file.read_text())

    def _filter_projects(self, projects):
        """Filter projects based on query criteria."""
        if self.query_type == "all":
            return projects
            
        return [project for project in projects if self._matches_criteria(project)]

    def _matches_criteria(self, project):
        """Check if project matches the query criteria."""
        if self.query_type == "status":
            return project["status"].lower() == self.filter_value.lower()
        elif self.query_type == "priority":
            return project["priority"].lower() == self.filter_value.lower()
        elif self.query_type == "division":
            return self.filter_value.lower() in [div.lower() for div in project["divisions_involved"]]
        return False

    def _format_results(self, projects):
        """Format project results into a readable string."""
        result = []
        for project in projects:
            result.append(f"\nProject ID: {project['id']}")
            result.append(f"Name: {project['name']}")
            result.append(f"Description: {project['description']}")
            result.append(f"Status: {project['status']}")
            result.append(f"Priority: {project['priority']}")
            result.append(f"Divisions Involved: {', '.join(project['divisions_involved'])}")
            result.append(f"Start Date: {project['start_date']}")
            result.append(f"End Date: {project['end_date']}")
            result.append("\nObjectives:")
            for obj in project['objectives']:
                result.append(f"- {obj}")
            result.append("-" * 50)
        
        return "\n".join(result)

if __name__ == "__main__":
    # Test querying all projects
    query = ProjectQuery(query_type="all")
    print(query.run())
    
    # Test querying by division
    query = ProjectQuery(query_type="division", filter_value="Planning")
    print(query.run()) 