import asyncio
import json
from pathlib import Path
from typing import Dict, Any
import logging
from datetime import datetime

from ..models.task_model import TaskDefinition, TaskStatus, TaskPriority
from ..storage.task_storage import TaskStorage
from ..services.task_service import TaskService

class TaskMigration:
    """
    Migration utility to move tasks from the old JSON-based system
    to the new unified task management system.
    """

    def __init__(self,
                 old_tasks_path: str = "task_tracking.json",
                 backup_dir: str = "backups"):
        self.old_tasks_path = Path(old_tasks_path)
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(parents=True, exist_ok=True)

        self.service = TaskService()
        self.setup_logging()

    def setup_logging(self):
        """Set up logging for the migration process"""
        log_dir = Path("logs/migrations")
        log_dir.mkdir(parents=True, exist_ok=True)

        logging.basicConfig(
            filename=log_dir / f"task_migration_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log",
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger('TaskMigration')

    def backup_old_tasks(self):
        """Create a backup of the old tasks file"""
        if not self.old_tasks_path.exists():
            raise FileNotFoundError(f"Old tasks file not found: {self.old_tasks_path}")

        backup_path = self.backup_dir / f"task_tracking_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        backup_path.write_text(self.old_tasks_path.read_text())
        self.logger.info(f"Created backup at {backup_path}")

    def load_old_tasks(self) -> Dict[str, Any]:
        """Load tasks from the old JSON file"""
        if not self.old_tasks_path.exists():
            raise FileNotFoundError(f"Old tasks file not found: {self.old_tasks_path}")

        with open(self.old_tasks_path, 'r') as f:
            return json.load(f)

    async def migrate_tasks(self):
        """Migrate tasks from the old system to the new one"""
        try:
            # Create backup first
            self.backup_old_tasks()

            # Load old tasks
            old_data = self.load_old_tasks()
            tasks_data = old_data.get("tasks", {})

            # Track migration progress
            total_tasks = len(tasks_data)
            migrated = 0
            failed = []

            self.logger.info(f"Starting migration of {total_tasks} tasks")

            # First pass: Create all tasks without dependencies
            task_id_map = {}  # old_id -> new_id
            for old_id, task_data in tasks_data.items():
                try:
                    # Create task without dependencies first
                    new_task = await self.service.create_task(
                        title=task_data["title"],
                        description=task_data["description"],
                        priority=TaskPriority(task_data["priority"].lower()),
                        metadata={
                            "original_id": old_id,
                            "migration_date": datetime.now().isoformat()
                        }
                    )

                    task_id_map[old_id] = new_task.id
                    migrated += 1

                    self.logger.info(f"Migrated task {old_id} -> {new_task.id}")

                except Exception as e:
                    self.logger.error(f"Error migrating task {old_id}: {str(e)}")
                    failed.append(old_id)

            # Second pass: Update dependencies and subtasks
            for old_id, task_data in tasks_data.items():
                if old_id in failed:
                    continue

                try:
                    new_id = task_id_map[old_id]
                    task = await self.service.storage.get_task(new_id)
                    if not task:
                        self.logger.error(f"Task {new_id} not found during relationship update")
                        failed.append(old_id)
                        continue

                    # Map old dependencies to new IDs
                    new_dependencies = []
                    for dep_id in task_data.get("dependencies", []):
                        if dep_id in task_id_map:
                            new_dependencies.append(task_id_map[dep_id])

                    # Map old subtasks to new IDs
                    new_subtasks = []
                    for subtask_id in task_data.get("subtasks", []):
                        if subtask_id in task_id_map:
                            new_subtasks.append(task_id_map[subtask_id])

                    # Update task with relationships
                    task.dependencies = new_dependencies
                    task.subtasks = new_subtasks

                    # Set status based on old task state
                    old_status = task_data.get("status", "pending").lower()
                    task.status = TaskStatus(old_status)

                    # Update task
                    await self.service.storage.update_task(task)

                    self.logger.info(f"Updated relationships for task {old_id} -> {new_id}")

                except Exception as e:
                    self.logger.error(f"Error updating relationships for task {old_id}: {str(e)}")
                    failed.append(old_id)

            # Final pass: Rebuild caches
            await self.service.rebuild_caches()

            # Log migration results
            success_rate = (migrated - len(failed)) / total_tasks * 100
            self.logger.info(f"""
                Migration completed:
                - Total tasks: {total_tasks}
                - Successfully migrated: {migrated - len(failed)}
                - Failed: {len(failed)}
                - Success rate: {success_rate:.2f}%
            """)

            if failed:
                self.logger.warning(f"Failed to migrate tasks: {failed}")

            return {
                "total": total_tasks,
                "migrated": migrated - len(failed),
                "failed": failed,
                "success_rate": success_rate
            }

        except Exception as e:
            self.logger.error(f"Migration failed: {str(e)}")
            raise

async def run_migration():
    """Run the task migration"""
    migration = TaskMigration()

    try:
        results = await migration.migrate_tasks()
        print("Migration Results:")
        print(f"Total tasks: {results['total']}")
        print(f"Successfully migrated: {results['migrated']}")
        print(f"Failed: {len(results['failed'])}")
        print(f"Success rate: {results['success_rate']:.2f}%")

        if results['failed']:
            print("\nFailed tasks:")
            for task_id in results['failed']:
                print(f"- {task_id}")

    except Exception as e:
        print(f"Migration failed: {str(e)}")

if __name__ == "__main__":
    asyncio.run(run_migration())