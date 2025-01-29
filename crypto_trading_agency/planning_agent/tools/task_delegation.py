from agency_swarm.tools import BaseTool
from pydantic import Field
import os
from dotenv import load_dotenv
import json
from datetime import datetime
import sqlite3
from pathlib import Path
from typing import List, Dict, Optional
import asyncio
from dataclasses import dataclass
from enum import Enum
import uuid

load_dotenv()

class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"

class TaskPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class TaskMetrics:
    execution_time: float
    resource_usage: dict
    dependencies_met: bool
    blocking_tasks: List[str]
    completion_rate: float

class TaskDelegationTool(BaseTool):
    """
    Advanced tool for managing task delegation, asynchronous execution,
    and resource allocation across agents.
    """
    
    task_id: Optional[str] = Field(
        None, description="Unique identifier for the task"
    )
    task_name: str = Field(
        ..., description="Name of the task to delegate"
    )
    task_description: str = Field(
        ..., description="Detailed description of the task"
    )
    priority: TaskPriority = Field(
        ..., description="Priority level of the task"
    )
    dependencies: Optional[List[str]] = Field(
        None, description="List of dependent task IDs"
    )
    assigned_agent: Optional[str] = Field(
        None, description="ID of the agent assigned to the task"
    )
    deadline: Optional[str] = Field(
        None, description="Deadline for task completion (ISO format)"
    )
    db_path: Path = Field(
        default=Path('project_data/task_delegation.db'),
        description="Path to the SQLite database for task delegation"
    )

    def __init__(self, **data):
        super().__init__(**data)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize_database()
        if not self.task_id:
            self.task_id = str(uuid.uuid4())

    def initialize_database(self):
        """Initialize the SQLite database for task delegation."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                name TEXT,
                description TEXT,
                priority TEXT,
                status TEXT,
                assigned_agent TEXT,
                created_at TEXT,
                deadline TEXT,
                completed_at TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS task_dependencies (
                task_id TEXT,
                dependency_id TEXT,
                FOREIGN KEY (task_id) REFERENCES tasks (id),
                FOREIGN KEY (dependency_id) REFERENCES tasks (id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS task_metrics (
                task_id TEXT,
                metric_type TEXT,
                metric_value REAL,
                timestamp TEXT,
                FOREIGN KEY (task_id) REFERENCES tasks (id)
            )
        ''')
        
        conn.commit()
        conn.close()

    async def create_task(self) -> dict:
        """Create a new task and store it in the database."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Insert task
            cursor.execute('''
                INSERT INTO tasks
                (id, name, description, priority, status, assigned_agent, created_at, deadline)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                self.task_id,
                self.task_name,
                self.task_description,
                self.priority.value,
                TaskStatus.PENDING.value,
                self.assigned_agent,
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                self.deadline
            ))
            
            # Insert dependencies if any
            if self.dependencies:
                cursor.executemany('''
                    INSERT INTO task_dependencies (task_id, dependency_id)
                    VALUES (?, ?)
                ''', [(self.task_id, dep) for dep in self.dependencies])
            
            conn.commit()
            conn.close()
            
            return {
                'task_id': self.task_id,
                'status': 'created',
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
        except Exception as e:
            return f"Error creating task: {str(e)}"

    async def assign_task(self, agent_id: str) -> dict:
        """Assign a task to a specific agent."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check if task exists and is assignable
            cursor.execute('''
                SELECT status FROM tasks WHERE id = ?
            ''', (self.task_id,))
            
            result = cursor.fetchone()
            if not result:
                raise ValueError(f"Task {self.task_id} not found")
            
            current_status = result[0]
            if current_status not in [TaskStatus.PENDING.value, TaskStatus.BLOCKED.value]:
                raise ValueError(f"Task {self.task_id} cannot be assigned (status: {current_status})")
            
            # Update task assignment
            cursor.execute('''
                UPDATE tasks
                SET assigned_agent = ?, status = ?
                WHERE id = ?
            ''', (
                agent_id,
                TaskStatus.IN_PROGRESS.value,
                self.task_id
            ))
            
            conn.commit()
            conn.close()
            
            return {
                'task_id': self.task_id,
                'agent_id': agent_id,
                'status': 'assigned',
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
        except Exception as e:
            return f"Error assigning task: {str(e)}"

    async def update_task_status(self, status: TaskStatus) -> dict:
        """Update the status of a task."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Update task status
            cursor.execute('''
                UPDATE tasks
                SET status = ?, completed_at = ?
                WHERE id = ?
            ''', (
                status.value,
                datetime.now().strftime('%Y-%m-%d %H:%M:%S') if status == TaskStatus.COMPLETED else None,
                self.task_id
            ))
            
            # If completed, check and update dependent tasks
            if status == TaskStatus.COMPLETED:
                await self.update_dependent_tasks()
            
            conn.commit()
            conn.close()
            
            return {
                'task_id': self.task_id,
                'status': status.value,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
        except Exception as e:
            return f"Error updating task status: {str(e)}"

    async def update_dependent_tasks(self):
        """Update the status of dependent tasks."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Find tasks that depend on this task
            cursor.execute('''
                SELECT task_id FROM task_dependencies
                WHERE dependency_id = ?
            ''', (self.task_id,))
            
            dependent_tasks = cursor.fetchall()
            
            for task in dependent_tasks:
                # Check if all dependencies are completed
                cursor.execute('''
                    SELECT COUNT(*) FROM task_dependencies td
                    JOIN tasks t ON td.dependency_id = t.id
                    WHERE td.task_id = ? AND t.status != ?
                ''', (task[0], TaskStatus.COMPLETED.value))
                
                pending_dependencies = cursor.fetchone()[0]
                
                if pending_dependencies == 0:
                    # All dependencies completed, update task status
                    cursor.execute('''
                        UPDATE tasks
                        SET status = ?
                        WHERE id = ? AND status = ?
                    ''', (
                        TaskStatus.PENDING.value,
                        task[0],
                        TaskStatus.BLOCKED.value
                    ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            return f"Error updating dependent tasks: {str(e)}"

    async def get_task_metrics(self) -> TaskMetrics:
        """Get metrics for a specific task."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get task metrics
            cursor.execute('''
                SELECT metric_type, metric_value
                FROM task_metrics
                WHERE task_id = ?
                ORDER BY timestamp DESC
            ''', (self.task_id,))
            
            metrics = cursor.fetchall()
            
            # Get blocking tasks
            cursor.execute('''
                SELECT dependency_id FROM task_dependencies td
                JOIN tasks t ON td.dependency_id = t.id
                WHERE td.task_id = ? AND t.status != ?
            ''', (self.task_id, TaskStatus.COMPLETED.value))
            
            blocking_tasks = [row[0] for row in cursor.fetchall()]
            
            conn.close()
            
            return TaskMetrics(
                execution_time=0.0,  # Would be calculated from actual metrics
                resource_usage={},   # Would be populated from actual metrics
                dependencies_met=len(blocking_tasks) == 0,
                blocking_tasks=blocking_tasks,
                completion_rate=0.0  # Would be calculated from actual metrics
            )
            
        except Exception as e:
            return f"Error getting task metrics: {str(e)}"

    def record_task_metric(self, metric_type: str, value: float):
        """Record a metric for the task."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO task_metrics
                (task_id, metric_type, metric_value, timestamp)
                VALUES (?, ?, ?, ?)
            ''', (
                self.task_id,
                metric_type,
                value,
                datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            return f"Error recording task metric: {str(e)}"

    async def run(self):
        """Execute the task delegation action."""
        try:
            # Create new task if it doesn't exist
            if not self.task_id:
                result = await self.create_task()
                if isinstance(result, str) and result.startswith("Error"):
                    return result
            
            # Assign task if agent is specified
            if self.assigned_agent:
                result = await self.assign_task(self.assigned_agent)
                if isinstance(result, str) and result.startswith("Error"):
                    return result
            
            # Get task metrics
            metrics = await self.get_task_metrics()
            
            return {
                'task_id': self.task_id,
                'name': self.task_name,
                'status': 'initialized',
                'metrics': metrics,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
        except Exception as e:
            return f"Error in task delegation: {str(e)}"

if __name__ == "__main__":
    # Test the tool
    tool = TaskDelegationTool(
        task_name="test_task",
        task_description="A test task",
        priority=TaskPriority.MEDIUM
    )
    asyncio.run(tool.run()) 