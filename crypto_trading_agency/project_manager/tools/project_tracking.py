from agency_swarm.tools import BaseTool
from pydantic import Field
import os
from dotenv import load_dotenv
import json
from datetime import datetime
import sqlite3
from pathlib import Path

load_dotenv()

class ProjectTrackingTool(BaseTool):
    """
    A tool for tracking project progress, managing phases, and monitoring development status.
    Maintains a database of project milestones, tasks, and their completion status.
    """
    
    action: str = Field(
        ..., description="Action to perform ('update_status', 'get_status', 'add_task', 'get_phase_progress')"
    )
    phase: str = Field(
        None, description="Project phase name (optional)"
    )
    task: str = Field(
        None, description="Task name (optional)"
    )
    status: str = Field(
        None, description="Status update (optional: 'not_started', 'in_progress', 'completed', 'blocked')"
    )
    notes: str = Field(
        None, description="Additional notes or comments (optional)"
    )

    def initialize_database(self):
        """
        Initialize the SQLite database for project tracking.
        """
        db_path = Path('project_data/project_tracking.db')
        db_path.parent.mkdir(parents=True, exist_ok=True)
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Create tables if they don't exist
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS project_phases (
                id INTEGER PRIMARY KEY,
                name TEXT UNIQUE,
                status TEXT,
                start_date TEXT,
                completion_date TEXT,
                notes TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY,
                phase_id INTEGER,
                name TEXT,
                status TEXT,
                start_date TEXT,
                completion_date TEXT,
                notes TEXT,
                FOREIGN KEY (phase_id) REFERENCES project_phases (id)
            )
        ''')
        
        # Initialize project phases if not already present
        phases = [
            "Infrastructure Setup",
            "Data Collection & Processing",
            "Model Development",
            "Strategy Development",
            "Paper Trading",
            "System Integration",
            "Testing & Validation",
            "Documentation & Maintenance"
        ]
        
        for phase in phases:
            cursor.execute('''
                INSERT OR IGNORE INTO project_phases (name, status, start_date)
                VALUES (?, 'not_started', ?)
            ''', (phase, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        
        conn.commit()
        conn.close()

    def update_status(self, phase, task=None, status=None, notes=None):
        """
        Update the status of a phase or task.
        """
        conn = sqlite3.connect('project_data/project_tracking.db')
        cursor = conn.cursor()
        
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        if task:
            # Update task status
            cursor.execute('''
                UPDATE tasks
                SET status = ?, notes = ?, completion_date = CASE WHEN ? = 'completed' THEN ? ELSE completion_date END
                WHERE name = ? AND phase_id = (SELECT id FROM project_phases WHERE name = ?)
            ''', (status, notes, status, current_time, task, phase))
        else:
            # Update phase status
            cursor.execute('''
                UPDATE project_phases
                SET status = ?, notes = ?, completion_date = CASE WHEN ? = 'completed' THEN ? ELSE completion_date END
                WHERE name = ?
            ''', (status, notes, status, current_time, phase))
        
        conn.commit()
        conn.close()
        
        return f"Updated status for {'task' if task else 'phase'} in {phase}"

    def get_status(self, phase=None):
        """
        Get the current status of a phase or the entire project.
        """
        conn = sqlite3.connect('project_data/project_tracking.db')
        cursor = conn.cursor()
        
        if phase:
            # Get specific phase status
            cursor.execute('''
                SELECT p.*, GROUP_CONCAT(json_object(
                    'task', t.name,
                    'status', t.status,
                    'start_date', t.start_date,
                    'completion_date', t.completion_date,
                    'notes', t.notes
                )) as tasks
                FROM project_phases p
                LEFT JOIN tasks t ON t.phase_id = p.id
                WHERE p.name = ?
                GROUP BY p.id
            ''', (phase,))
        else:
            # Get all phases status
            cursor.execute('''
                SELECT p.*, GROUP_CONCAT(json_object(
                    'task', t.name,
                    'status', t.status,
                    'start_date', t.start_date,
                    'completion_date', t.completion_date,
                    'notes', t.notes
                )) as tasks
                FROM project_phases p
                LEFT JOIN tasks t ON t.phase_id = p.id
                GROUP BY p.id
            ''')
        
        results = cursor.fetchall()
        conn.close()
        
        # Format results
        status_report = []
        for row in results:
            phase_info = {
                'phase': row[1],
                'status': row[2],
                'start_date': row[3],
                'completion_date': row[4],
                'notes': row[5],
                'tasks': json.loads('[' + (row[6] or '{}') + ']') if row[6] else []
            }
            status_report.append(phase_info)
        
        return status_report

    def add_task(self, phase, task, status='not_started', notes=None):
        """
        Add a new task to a phase.
        """
        conn = sqlite3.connect('project_data/project_tracking.db')
        cursor = conn.cursor()
        
        # Get phase ID
        cursor.execute('SELECT id FROM project_phases WHERE name = ?', (phase,))
        phase_id = cursor.fetchone()[0]
        
        # Add task
        cursor.execute('''
            INSERT INTO tasks (phase_id, name, status, start_date, notes)
            VALUES (?, ?, ?, ?, ?)
        ''', (phase_id, task, status, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), notes))
        
        conn.commit()
        conn.close()
        
        return f"Added task '{task}' to phase '{phase}'"

    def get_phase_progress(self, phase=None):
        """
        Calculate progress percentage for a phase or the entire project.
        """
        conn = sqlite3.connect('project_data/project_tracking.db')
        cursor = conn.cursor()
        
        if phase:
            # Get specific phase progress
            cursor.execute('''
                SELECT 
                    COUNT(CASE WHEN status = 'completed' THEN 1 END) * 100.0 / COUNT(*) as progress
                FROM tasks
                WHERE phase_id = (SELECT id FROM project_phases WHERE name = ?)
            ''', (phase,))
        else:
            # Get overall project progress
            cursor.execute('''
                SELECT 
                    COUNT(CASE WHEN status = 'completed' THEN 1 END) * 100.0 / COUNT(*) as progress
                FROM tasks
            ''')
        
        progress = cursor.fetchone()[0] or 0
        conn.close()
        
        return {
            'phase': phase if phase else 'overall',
            'progress': round(progress, 2)
        }

    def run(self):
        """
        Execute the project tracking action.
        """
        try:
            # Initialize database if needed
            self.initialize_database()
            
            # Execute requested action
            if self.action == 'update_status':
                return str(self.update_status(self.phase, self.task, self.status, self.notes))
            elif self.action == 'get_status':
                return str(self.get_status(self.phase))
            elif self.action == 'add_task':
                return str(self.add_task(self.phase, self.task, self.status, self.notes))
            elif self.action == 'get_phase_progress':
                return str(self.get_phase_progress(self.phase))
            else:
                return f"Unknown action: {self.action}"
            
        except Exception as e:
            return f"Error in project tracking: {str(e)}"

if __name__ == "__main__":
    # Test the tool
    tool = ProjectTrackingTool(
        action="get_status",
        phase="Model Development"
    )
    print(tool.run()) 