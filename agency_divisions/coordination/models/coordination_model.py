from datetime import datetime
from typing import Optional, Dict, List, Any
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict
import uuid

class WorkflowState(str, Enum):
    """States for workflow execution"""
    PENDING = "pending"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class WorkflowStepType(str, Enum):
    """Types of workflow steps"""
    TASK = "task"
    DECISION = "decision"
    PARALLEL = "parallel"
    SEQUENCE = "sequence"
    CONDITION = "condition"
    LOOP = "loop"
    EVENT = "event"

class WorkflowStep(BaseModel):
    """Represents a single step in a workflow"""
    model_config = ConfigDict(
        use_enum_values=True,
        json_encoders={
            datetime: lambda v: v.isoformat()
        }
    )

    id: str = Field(default_factory=lambda: f"step_{uuid.uuid4().hex[:8]}")
    type: WorkflowStepType
    name: str
    description: str
    agent_id: Optional[str] = None
    requires: List[str] = Field(default_factory=list)  # IDs of required steps
    config: Dict[str, Any] = Field(default_factory=dict)
    state: WorkflowState = Field(default=WorkflowState.PENDING)
    result: Optional[Dict[str, Any]] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None

class Workflow(BaseModel):
    """Represents a complete workflow definition"""
    model_config = ConfigDict(
        use_enum_values=True,
        json_encoders={
            datetime: lambda v: v.isoformat()
        }
    )

    id: str = Field(default_factory=lambda: f"workflow_{uuid.uuid4().hex[:8]}")
    name: str
    description: str
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    state: WorkflowState = Field(default=WorkflowState.PENDING)
    steps: Dict[str, WorkflowStep] = Field(default_factory=dict)
    variables: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def add_step(self, step: WorkflowStep) -> None:
        """Add a step to the workflow"""
        self.steps[step.id] = step
        self.updated_at = datetime.now()

    def update_step_state(self, step_id: str, state: WorkflowState, result: Optional[Dict[str, Any]] = None) -> None:
        """Update the state of a workflow step"""
        if step_id in self.steps:
            step = self.steps[step_id]
            step.state = state
            if result:
                step.result = result
            if state == WorkflowState.ACTIVE and not step.started_at:
                step.started_at = datetime.now()
            elif state in [WorkflowState.COMPLETED, WorkflowState.FAILED]:
                step.completed_at = datetime.now()
            self.updated_at = datetime.now()

    def get_next_steps(self) -> List[WorkflowStep]:
        """Get list of steps that are ready to be executed"""
        ready_steps = []
        for step in self.steps.values():
            if step.state == WorkflowState.PENDING:
                # Check if all required steps are completed
                requirements_met = all(
                    self.steps[req].state == WorkflowState.COMPLETED
                    for req in step.requires
                    if req in self.steps
                )
                if requirements_met:
                    ready_steps.append(step)
        return ready_steps

    def is_completed(self) -> bool:
        """Check if the workflow is completed"""
        return all(
            step.state in [WorkflowState.COMPLETED, WorkflowState.CANCELLED]
            for step in self.steps.values()
        )

    def get_step_dependencies(self, step_id: str) -> List[WorkflowStep]:
        """Get all steps that depend on a given step"""
        dependent_steps = []
        for step in self.steps.values():
            if step_id in step.requires:
                dependent_steps.append(step)
        return dependent_steps

    def validate_workflow(self) -> bool:
        """Validate workflow structure and dependencies"""
        # Check for circular dependencies
        visited = set()
        path = set()

        def has_cycle(step_id: str) -> bool:
            if step_id in path:
                return True
            if step_id in visited:
                return False
            visited.add(step_id)
            path.add(step_id)
            step = self.steps.get(step_id)
            if step:
                for req in step.requires:
                    if has_cycle(req):
                        return True
            path.remove(step_id)
            return False

        # Check each step
        for step_id in self.steps:
            if has_cycle(step_id):
                return False

        # Validate step references
        for step in self.steps.values():
            for req in step.requires:
                if req not in self.steps:
                    return False

        return True

if __name__ == "__main__":
    # Test workflow creation
    workflow = Workflow(
        name="Test Workflow",
        description="Testing workflow model"
    )

    # Create steps
    step1 = WorkflowStep(
        type=WorkflowStepType.TASK,
        name="Data Collection",
        description="Collect initial data",
        agent_id="agent1"
    )

    step2 = WorkflowStep(
        type=WorkflowStepType.TASK,
        name="Data Processing",
        description="Process collected data",
        agent_id="agent2",
        requires=[step1.id]
    )

    # Add steps to workflow
    workflow.add_step(step1)
    workflow.add_step(step2)

    # Validate workflow
    is_valid = workflow.validate_workflow()
    print(f"Workflow is valid: {is_valid}")

    # Test step execution
    workflow.update_step_state(step1.id, WorkflowState.COMPLETED, {"data": "processed"})
    next_steps = workflow.get_next_steps()
    print(f"Next steps to execute: {[step.name for step in next_steps]}")