from typing import Dict, List, Optional, Any, Union
import sqlite3
import json
from datetime import datetime
from pathlib import Path
import asyncio
from ..models.task_model import TaskDefinition, TaskStatus, TaskPriority

class TaskStorage:
    """
    Unified storage interface for tasks with both SQLite and JSON support.
    Provides async operations and maintains consistency across storage types.
    """

    def __init__(self,
                 db_path: Union[str, Path] = "data/tasks.db",
                 json_path: Union[str, Path] = "data/tasks.json"):
        self.db_path = Path(db_path)
        self.json_path = Path(json_path)

        # Ensure directories exist
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.json_path.parent.mkdir(parents=True, exist_ok=True)

        self._initialize_storage()

    def _initialize_storage(self):
        """Initialize both storage backends"""
        self._initialize_sqlite()
        self._initialize_json()

    def _initialize_sqlite(self):
        """Initialize SQLite database with proper schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Create tasks table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                data TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                status TEXT NOT NULL,
                priority TEXT NOT NULL,
                completion_percentage REAL DEFAULT 0.0,
                assigned_agent TEXT,
                assigned_division TEXT
            )
        ''')

        # Create relationships tables
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS task_dependencies (
                task_id TEXT,
                dependency_id TEXT,
                PRIMARY KEY (task_id, dependency_id),
                FOREIGN KEY (task_id) REFERENCES tasks(id),
                FOREIGN KEY (dependency_id) REFERENCES tasks(id)
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS task_subtasks (
                parent_id TEXT,
                subtask_id TEXT,
                PRIMARY KEY (parent_id, subtask_id),
                FOREIGN KEY (parent_id) REFERENCES tasks(id),
                FOREIGN KEY (subtask_id) REFERENCES tasks(id)
            )
        ''')

        # Create indices
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_task_status ON tasks(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_task_priority ON tasks(priority)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_task_agent ON tasks(assigned_agent)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_task_division ON tasks(assigned_division)')

        conn.commit()
        conn.close()

    def _initialize_json(self):
        """Initialize JSON storage if it doesn't exist"""
        if not self.json_path.exists():
            initial_data = {
                "tasks": {},
                "task_states": {
                    "pending": [],
                    "in_progress": [],
                    "completed": [],
                    "blocked": [],
                    "failed": [],
                    "on_hold": []
                },
                "critical_tasks": [],
                "last_updated": datetime.now().isoformat()
            }
            with open(self.json_path, 'w') as f:
                json.dump(initial_data, f, indent=2)

    async def create_task(self, task: TaskDefinition) -> str:
        """Create a new task in both storage backends"""
        try:
            # Store in SQLite
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO tasks (
                    id, data, created_at, updated_at, status,
                    priority, completion_percentage, assigned_agent,
                    assigned_division
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                task.id,
                json.dumps(task.model_dump()),
                task.created_at,
                task.updated_at,
                task.status,
                task.priority,
                task.completion_percentage,
                task.assigned_agent,
                task.assigned_division
            ))

            # Store dependencies
            if task.dependencies:
                cursor.executemany('''
                    INSERT INTO task_dependencies (task_id, dependency_id)
                    VALUES (?, ?)
                ''', [(task.id, dep_id) for dep_id in task.dependencies])

            # Store subtasks
            if task.subtasks:
                cursor.executemany('''
                    INSERT INTO task_subtasks (parent_id, subtask_id)
                    VALUES (?, ?)
                ''', [(task.id, subtask_id) for subtask_id in task.subtasks])

            conn.commit()
            conn.close()

            # Update JSON storage
            await self._update_json_storage()

            return task.id

        except Exception as e:
            raise Exception(f"Error creating task: {str(e)}")

    async def get_task(self, task_id: str) -> Optional[TaskDefinition]:
        """Retrieve a task by ID"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('SELECT data FROM tasks WHERE id = ?', (task_id,))
            result = cursor.fetchone()

            if result:
                task_data = json.loads(result[0])
                return TaskDefinition(**task_data)

            return None

        except Exception as e:
            raise Exception(f"Error retrieving task: {str(e)}")

    async def update_task(self, task: TaskDefinition) -> None:
        """Update an existing task"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Update main task data
            cursor.execute('''
                UPDATE tasks
                SET data = ?, updated_at = ?, status = ?,
                    priority = ?, completion_percentage = ?,
                    assigned_agent = ?, assigned_division = ?
                WHERE id = ?
            ''', (
                json.dumps(task.dict()),
                task.updated_at,
                task.status,
                task.priority,
                task.completion_percentage,
                task.assigned_agent,
                task.assigned_division,
                task.id
            ))

            # Update dependencies
            cursor.execute('DELETE FROM task_dependencies WHERE task_id = ?', (task.id,))
            if task.dependencies:
                cursor.executemany('''
                    INSERT INTO task_dependencies (task_id, dependency_id)
                    VALUES (?, ?)
                ''', [(task.id, dep_id) for dep_id in task.dependencies])

            # Update subtasks
            cursor.execute('DELETE FROM task_subtasks WHERE parent_id = ?', (task.id,))
            if task.subtasks:
                cursor.executemany('''
                    INSERT INTO task_subtasks (parent_id, subtask_id)
                    VALUES (?, ?)
                ''', [(task.id, subtask_id) for subtask_id in task.subtasks])

            conn.commit()
            conn.close()

            # Update JSON storage
            await self._update_json_storage()

        except Exception as e:
            raise Exception(f"Error updating task: {str(e)}")

    async def delete_task(self, task_id: str) -> None:
        """Delete a task and its relationships"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Delete relationships first
            cursor.execute('DELETE FROM task_dependencies WHERE task_id = ? OR dependency_id = ?',
                         (task_id, task_id))
            cursor.execute('DELETE FROM task_subtasks WHERE parent_id = ? OR subtask_id = ?',
                         (task_id, task_id))

            # Delete task
            cursor.execute('DELETE FROM tasks WHERE id = ?', (task_id,))

            conn.commit()
            conn.close()

            # Update JSON storage
            await self._update_json_storage()

        except Exception as e:
            raise Exception(f"Error deleting task: {str(e)}")

    async def get_tasks(self,
                       status: Optional[TaskStatus] = None,
                       priority: Optional[TaskPriority] = None,
                       assigned_agent: Optional[str] = None,
                       assigned_division: Optional[str] = None) -> List[TaskDefinition]:
        """Retrieve tasks based on filters"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            query = 'SELECT data FROM tasks WHERE 1=1'
            params = []

            if status:
                query += ' AND status = ?'
                params.append(status)
            if priority:
                query += ' AND priority = ?'
                params.append(priority)
            if assigned_agent:
                query += ' AND assigned_agent = ?'
                params.append(assigned_agent)
            if assigned_division:
                query += ' AND assigned_division = ?'
                params.append(assigned_division)

            cursor.execute(query, params)
            results = cursor.fetchall()

            tasks = []
            for result in results:
                task_data = json.loads(result[0])
                tasks.append(TaskDefinition(**task_data))

            return tasks

        except Exception as e:
            raise Exception(f"Error retrieving tasks: {str(e)}")

    async def _update_json_storage(self):
        """Update JSON storage to match SQLite database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Get all tasks
            cursor.execute('SELECT data FROM tasks')
            results = cursor.fetchall()

            tasks = {}
            task_states = {
                "pending": [],
                "in_progress": [],
                "completed": [],
                "blocked": [],
                "failed": [],
                "on_hold": []
            }
            critical_tasks = []

            for result in results:
                task_data = json.loads(result[0])
                task = TaskDefinition(**task_data)

                tasks[task.id] = task.model_dump()
                task_states[task.status].append(task.id)

                if task.priority == TaskPriority.CRITICAL:
                    critical_tasks.append(task.id)

            json_data = {
                "tasks": tasks,
                "task_states": task_states,
                "critical_tasks": critical_tasks,
                "last_updated": datetime.now().isoformat()
            }

            with open(self.json_path, 'w') as f:
                json.dump(json_data, f, indent=2, default=lambda x: x.model_dump() if hasattr(x, 'model_dump') else x)

        except Exception as e:
            raise Exception(f"Error updating JSON storage: {str(e)}")

if __name__ == "__main__":
    # Test the storage implementation
    async def test_storage():
        storage = TaskStorage()

        # Create a test task
        task = TaskDefinition(
            title="Test Storage Task",
            description="Testing the unified storage implementation",
            priority=TaskPriority.HIGH,
            parent_id=None,
            assigned_agent=None,
            assigned_division=None,
            completion_percentage=0.0,
            started_at=None,
            completed_at=None,
            deadline=None,
            project_id=None,
            milestone=None,
            last_error=None
        )

        try:
            # Test create
            task_id = await storage.create_task(task)
            print(f"Created task: {task_id}")

            # Test retrieve
            retrieved_task = await storage.get_task(task_id)
            if retrieved_task:
                print(f"Retrieved task: {retrieved_task.model_dump()}")
            else:
                print("Task not found")

            # Test update
            if retrieved_task:
                retrieved_task.update_status(TaskStatus.IN_PROGRESS, "Starting work")
                await storage.update_task(retrieved_task)
                print("Updated task status")

            # Test query
            tasks = await storage.get_tasks(status=TaskStatus.IN_PROGRESS)
            print(f"Found {len(tasks)} tasks in progress")

            # Test delete
            await storage.delete_task(task_id)
            print("Deleted task")

        except Exception as e:
            print(f"Error in test: {str(e)}")

    asyncio.run(test_storage())
