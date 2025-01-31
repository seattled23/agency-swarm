from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict
from uuid import uuid4

class TaskStatus(str, Enum):
    """Standardized task status states"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    FAILED = "failed"
    ON_HOLD = "on_hold"

class TaskPriority(str, Enum):
    """Standardized task priority levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class TaskMetrics(BaseModel):
    """Task performance and resource metrics"""
    execution_time: float = Field(0.0, description="Total execution time in seconds")
    completion_percentage: float = Field(0.0, description="Task completion percentage")
    resource_usage: Dict[str, float] = Field(default_factory=dict, description="Resource utilization metrics")
    dependencies_met: bool = Field(False, description="Whether all dependencies are satisfied")
    blocking_tasks: List[str] = Field(default_factory=list, description="List of tasks blocking this task")
    error_count: int = Field(0, description="Number of errors encountered")
    retry_count: int = Field(0, description="Number of retry attempts")

class MilestoneInfo(BaseModel):
    """Project milestone information"""
    name: str = Field(..., description="Name of the milestone")
    description: str = Field(..., description="Description of the milestone")
    deadline: Optional[str] = Field(None, description="Deadline for the milestone (ISO format)")
    progress: float = Field(0.0, description="Progress towards milestone completion")
    completed: bool = Field(False, description="Whether the milestone is completed")

class TaskDefinition(BaseModel):
    """
    Unified task model that combines features from all existing implementations
    and aligns with agency-swarm patterns.
    """
    model_config = ConfigDict(
        use_enum_values=True,
        json_encoders={
            datetime: lambda v: v.isoformat()
        }
    )

    # Core Fields
    id: str = Field(default_factory=lambda: f"TASK-{uuid4().hex[:8]}", description="Unique task identifier")
    title: str = Field(..., description="Task title")
    description: str = Field(..., description="Detailed task description")
    status: TaskStatus = Field(default=TaskStatus.PENDING, description="Current task status")
    priority: TaskPriority = Field(..., description="Task priority level")

    # Relationships
    parent_id: Optional[str] = Field(None, description="ID of parent task if this is a subtask")
    subtasks: List[str] = Field(default_factory=list, description="List of subtask IDs")
    dependencies: List[str] = Field(default_factory=list, description="List of dependent task IDs")

    # Assignment and Progress
    assigned_agent: Optional[str] = Field(None, description="ID of the assigned agent")
    assigned_division: Optional[str] = Field(None, description="Division responsible for the task")
    completion_percentage: float = Field(0.0, description="Task completion percentage")

    # Timing Information
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat(), description="Task creation timestamp")
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat(), description="Last update timestamp")
    started_at: Optional[str] = Field(None, description="When task execution started")
    completed_at: Optional[str] = Field(None, description="When task was completed")
    deadline: Optional[str] = Field(None, description="Task deadline (ISO format)")

    # Project Management
    project_id: Optional[str] = Field(None, description="Associated project ID")
    milestone: Optional[MilestoneInfo] = Field(None, description="Associated milestone information")
    tags: List[str] = Field(default_factory=list, description="Task categorization tags")

    # Metrics and Monitoring
    metrics: TaskMetrics = Field(default_factory=lambda: TaskMetrics(
        execution_time=0.0,
        completion_percentage=0.0,
        resource_usage={},
        dependencies_met=False,
        blocking_tasks=[],
        error_count=0,
        retry_count=0
    ), description="Task performance metrics")
    last_error: Optional[str] = Field(None, description="Last error message if any")

    # Additional Data
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional task-specific metadata")
    notes: List[str] = Field(default_factory=list, description="Task-related notes and comments")

    def update_status(self, new_status: TaskStatus, message: Optional[str] = None) -> None:
        """Update task status with proper timestamp management"""
        self.status = new_status
        self.updated_at = datetime.now().isoformat()

        if message:
            self.notes.append(f"[{self.updated_at}] Status changed to {new_status}: {message}")

        if new_status == TaskStatus.IN_PROGRESS and not self.started_at:
            self.started_at = self.updated_at
        elif new_status == TaskStatus.COMPLETED:
            self.completed_at = self.updated_at
            self.completion_percentage = 100.0

    def update_progress(self, percentage: float, message: Optional[str] = None) -> None:
        """Update task progress with validation"""
        if not 0 <= percentage <= 100:
            raise ValueError("Progress percentage must be between 0 and 100")

        self.completion_percentage = percentage
        self.updated_at = datetime.now().isoformat()

        if message:
            self.notes.append(f"[{self.updated_at}] Progress updated to {percentage}%: {message}")

    def add_subtask(self, subtask_id: str) -> None:
        """Add a subtask to this task"""
        if subtask_id not in self.subtasks:
            self.subtasks.append(subtask_id)
            self.updated_at = datetime.now().isoformat()

    def add_dependency(self, dependency_id: str) -> None:
        """Add a dependency to this task"""
        if dependency_id not in self.dependencies:
            self.dependencies.append(dependency_id)
            self.updated_at = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """Convert task to dictionary format"""
        return {
            k: v for k, v in self.model_dump(exclude_none=True).items()
            if v is not None and (not isinstance(v, (list, dict)) or v)
        }

    @classmethod
    def from_legacy_format(cls, legacy_task: Dict[str, Any]) -> "TaskDefinition":
        """Convert legacy task format to new unified format"""
        # Map old status values to new enum
        status_mapping = {
            "pending": TaskStatus.PENDING,
            "in_progress": TaskStatus.IN_PROGRESS,
            "completed": TaskStatus.COMPLETED,
            "on_hold": TaskStatus.ON_HOLD,
            "failed": TaskStatus.FAILED,
            "blocked": TaskStatus.BLOCKED
        }

        # Map old priority values to new enum
        priority_mapping = {
            "low": TaskPriority.LOW,
            "medium": TaskPriority.MEDIUM,
            "high": TaskPriority.HIGH,
            "critical": TaskPriority.CRITICAL
        }

        return cls(
            id=legacy_task.get("id") or f"TASK-{uuid4().hex[:8]}",
            title=legacy_task.get("title") or legacy_task.get("name", "Untitled Task"),
            description=legacy_task.get("description", ""),
            status=status_mapping.get(legacy_task.get("status", "pending").lower(), TaskStatus.PENDING),
            priority=priority_mapping.get(legacy_task.get("priority", "medium").lower(), TaskPriority.MEDIUM),
            subtasks=legacy_task.get("subtasks", []),
            dependencies=legacy_task.get("dependencies", []),
            completion_percentage=float(legacy_task.get("completion_percentage", 0.0)),
            metadata=legacy_task.get("metadata", {}),
            created_at=legacy_task.get("created_at", datetime.now().isoformat()),
            updated_at=legacy_task.get("updated_at", datetime.now().isoformat()),
            parent_id=None,
            assigned_agent=None,
            assigned_division=None,
            started_at=None,
            completed_at=None,
            deadline=None,
            project_id=None,
            milestone=None,
            last_error=None
        )

if __name__ == "__main__":
    # Test the unified task model
    task = TaskDefinition(
        title="Test Task",
        description="Testing the unified task model",
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

    # Test status updates
    task.update_status(TaskStatus.IN_PROGRESS, "Starting task execution")
    task.update_progress(50.0, "Halfway there")

    # Test subtask and dependency management
    subtask_id = f"TASK-{uuid4().hex[:8]}"
    task.add_subtask(subtask_id)
    task.add_dependency("TASK-123")

    # Test conversion to dictionary
    task_dict = task.to_dict()
    print("Task Dictionary:", task_dict)

    # Test legacy format conversion
    legacy_task = {
        "id": "TASK-OLD-1",
        "name": "Legacy Task",
        "description": "A task in legacy format",
        "status": "in_progress",
        "priority": "high",
        "completion_percentage": 75.0
    }
    converted_task = TaskDefinition.from_legacy_format(legacy_task)
    print("Converted Legacy Task:", converted_task.to_dict())
