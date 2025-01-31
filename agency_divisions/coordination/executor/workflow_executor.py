import asyncio
from typing import Dict, Optional, List, Any, Callable, Awaitable
from datetime import datetime
import logging
from pathlib import Path
import json

from ..models.coordination_model import (
    Workflow,
    WorkflowStep,
    WorkflowState,
    WorkflowStepType
)
from ...communication.services.communication_service import CommunicationService
from ...communication.models.message_model import MessageType, MessagePriority

class WorkflowExecutor:
    """
    Manages the execution of workflows and coordinates between agents.
    """
    def __init__(
        self,
        comm_service: CommunicationService,
        log_path: Optional[Path] = None
    ):
        self.comm_service = comm_service
        self.active_workflows: Dict[str, Workflow] = {}
        self.step_handlers: Dict[WorkflowStepType, Callable[[WorkflowStep], Awaitable[Dict[str, Any]]]] = {}
        self._setup_logging(log_path)
        self._register_default_handlers()

    def _setup_logging(self, log_path: Optional[Path] = None):
        """Set up executor logging"""
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger("WorkflowExecutor")
        if log_path:
            file_handler = logging.FileHandler(log_path / "workflow_executor.log")
            file_handler.setFormatter(logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            ))
            self.logger.addHandler(file_handler)

    def _register_default_handlers(self):
        """Register default step type handlers"""
        self.register_handler(WorkflowStepType.TASK, self._handle_task)
        self.register_handler(WorkflowStepType.DECISION, self._handle_decision)
        self.register_handler(WorkflowStepType.PARALLEL, self._handle_parallel)
        self.register_handler(WorkflowStepType.SEQUENCE, self._handle_sequence)

    def register_handler(
        self,
        step_type: WorkflowStepType,
        handler: Callable[[WorkflowStep], Awaitable[Dict[str, Any]]]
    ):
        """Register a handler for a specific step type"""
        self.step_handlers[step_type] = handler
        self.logger.info(f"Registered handler for step type: {step_type}")

    async def start_workflow(self, workflow: Workflow) -> None:
        """Start execution of a workflow"""
        if not workflow.validate_workflow():
            raise ValueError("Invalid workflow configuration")

        self.active_workflows[workflow.id] = workflow
        workflow.state = WorkflowState.ACTIVE
        self.logger.info(f"Started workflow: {workflow.id}")

        # Start initial steps
        initial_steps = workflow.get_next_steps()
        for step in initial_steps:
            await self._execute_step(workflow.id, step.id)

    async def _execute_step(self, workflow_id: str, step_id: str) -> None:
        """Execute a single workflow step"""
        workflow = self.active_workflows.get(workflow_id)
        if not workflow:
            return

        step = workflow.steps.get(step_id)
        if not step or step.state != WorkflowState.PENDING:
            return

        try:
            # Update step state
            workflow.update_step_state(step_id, WorkflowState.ACTIVE)
            self.logger.info(f"Executing step: {step_id} in workflow: {workflow_id}")

            # Execute step handler
            handler = self.step_handlers.get(step.type)
            if handler:
                result = await handler(step)
                workflow.update_step_state(step_id, WorkflowState.COMPLETED, result)
                self.logger.info(f"Completed step: {step_id}")

                # Execute next steps
                next_steps = workflow.get_next_steps()
                for next_step in next_steps:
                    await self._execute_step(workflow_id, next_step.id)

                # Check if workflow is completed
                if workflow.is_completed():
                    workflow.state = WorkflowState.COMPLETED
                    self.logger.info(f"Workflow completed: {workflow_id}")

        except Exception as e:
            workflow.update_step_state(step_id, WorkflowState.FAILED)
            step.error = str(e)
            self.logger.error(f"Error executing step {step_id}: {str(e)}")

    async def _handle_task(self, step: WorkflowStep) -> Dict[str, Any]:
        """Handle execution of a task step"""
        if not step.agent_id:
            raise ValueError("Task step requires an agent_id")

        # Create task assignment message
        await self.comm_service.send_task_assignment(
            task=step,
            sender_id="workflow_executor",
            receiver_id=step.agent_id,
            priority=MessagePriority.HIGH
        )

        # Wait for task completion
        while True:
            message = await self.comm_service.broker.receive("workflow_executor", timeout=1.0)
            if message and message.type == MessageType.STATUS_UPDATE:
                if message.content.get("task_id") == step.id:
                    if message.content.get("status") == WorkflowState.COMPLETED:
                        return message.content.get("result", {})
                    elif message.content.get("status") == WorkflowState.FAILED:
                        raise Exception(message.content.get("error", "Task execution failed"))
            await asyncio.sleep(1)

    async def _handle_decision(self, step: WorkflowStep) -> Dict[str, Any]:
        """Handle execution of a decision step"""
        condition = step.config.get("condition")
        if not condition:
            raise ValueError("Decision step requires a condition")

        # Evaluate condition
        result = await self._evaluate_condition(condition, step.config.get("variables", {}))
        return {"decision": result}

    async def _handle_parallel(self, step: WorkflowStep) -> Dict[str, Any]:
        """Handle execution of parallel steps"""
        substeps = step.config.get("steps", [])
        if not substeps:
            raise ValueError("Parallel step requires substeps")

        # Execute all substeps concurrently
        tasks = [self._execute_substep(substep) for substep in substeps]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        return {"results": results}

    async def _handle_sequence(self, step: WorkflowStep) -> Dict[str, Any]:
        """Handle execution of sequential steps"""
        substeps = step.config.get("steps", [])
        if not substeps:
            raise ValueError("Sequence step requires substeps")

        results = []
        for substep in substeps:
            result = await self._execute_substep(substep)
            results.append(result)

        return {"results": results}

    async def _execute_substep(self, substep: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a substep within a parallel or sequence step"""
        step = WorkflowStep(**substep)
        handler = self.step_handlers.get(step.type)
        if handler:
            return await handler(step)
        raise ValueError(f"No handler for step type: {step.type}")

    async def _evaluate_condition(self, condition: str, variables: Dict[str, Any]) -> bool:
        """Evaluate a condition expression"""
        try:
            # Basic condition evaluation - in production, use a proper expression evaluator
            return eval(condition, {"__builtins__": {}}, variables)
        except Exception as e:
            raise ValueError(f"Error evaluating condition: {str(e)}")

    async def pause_workflow(self, workflow_id: str) -> None:
        """Pause a workflow execution"""
        if workflow_id in self.active_workflows:
            workflow = self.active_workflows[workflow_id]
            workflow.state = WorkflowState.PAUSED
            self.logger.info(f"Paused workflow: {workflow_id}")

    async def resume_workflow(self, workflow_id: str) -> None:
        """Resume a paused workflow"""
        if workflow_id in self.active_workflows:
            workflow = self.active_workflows[workflow_id]
            if workflow.state == WorkflowState.PAUSED:
                workflow.state = WorkflowState.ACTIVE
                self.logger.info(f"Resumed workflow: {workflow_id}")
                # Resume execution of pending steps
                next_steps = workflow.get_next_steps()
                for step in next_steps:
                    await self._execute_step(workflow_id, step.id)

    async def cancel_workflow(self, workflow_id: str) -> None:
        """Cancel a workflow execution"""
        if workflow_id in self.active_workflows:
            workflow = self.active_workflows[workflow_id]
            workflow.state = WorkflowState.CANCELLED
            self.logger.info(f"Cancelled workflow: {workflow_id}")

if __name__ == "__main__":
    async def test_executor():
        # Create communication service
        comm_service = CommunicationService()

        # Create executor
        executor = WorkflowExecutor(comm_service)

        # Create test workflow
        workflow = Workflow(
            name="Test Workflow",
            description="Testing workflow execution"
        )

        # Add test steps
        step1 = WorkflowStep(
            type=WorkflowStepType.TASK,
            name="Initial Task",
            description="First task in workflow",
            agent_id="agent1"
        )

        step2 = WorkflowStep(
            type=WorkflowStepType.DECISION,
            name="Decision Point",
            description="Decide next action",
            config={
                "condition": "value > 10",
                "variables": {"value": 15}
            }
        )

        workflow.add_step(step1)
        workflow.add_step(step2)

        # Start workflow
        await executor.start_workflow(workflow)

        # Wait for completion
        while workflow.state == WorkflowState.ACTIVE:
            await asyncio.sleep(1)

        print(f"Workflow completed with state: {workflow.state}")

    # Run test
    asyncio.run(test_executor())