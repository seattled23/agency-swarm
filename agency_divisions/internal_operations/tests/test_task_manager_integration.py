import asyncio
import pytest
from datetime import datetime
from agency_divisions.internal_operations.agents.taskmanager.taskmanager import TaskManager
from agency_divisions.market_analysis.market_analyst import MarketAnalyst
from agency_divisions.risk_management.risk_manager import RiskManager

class TestTaskManagerIntegration:
    """Integration tests for Task Manager with other agents"""
    
    @pytest.fixture
    async def setup_agents(self):
        """Setup test agents"""
        task_manager = TaskManager()
        market_analyst = MarketAnalyst()
        risk_manager = RiskManager()
        
        # Start all agents
        await asyncio.gather(
            task_manager.start(),
            market_analyst.start(),
            risk_manager.start()
        )
        
        yield {
            "task_manager": task_manager,
            "market_analyst": market_analyst,
            "risk_manager": risk_manager
        }
        
        # Cleanup
        await asyncio.gather(
            task_manager.stop(),
            market_analyst.stop(),
            risk_manager.stop()
        )

    @pytest.mark.asyncio
    async def test_task_creation_and_assignment(self, setup_agents):
        """Test task creation and assignment workflow"""
        agents = await setup_agents
        task_manager = agents["task_manager"]
        market_analyst = agents["market_analyst"]
        
        # Create a market analysis task
        task_data = {
            "name": "Market Analysis Task",
            "description": "Analyze BTC/USD market trends",
            "priority": "high",
            "dependencies": [],
            "metadata": {
                "symbol": "BTC/USD",
                "timeframe": "1h",
                "indicators": ["SMA", "RSI"]
            }
        }
        
        # Send task creation request
        await task_manager.send_message(
            "self",
            task_data,
            "task_creation_request"
        )
        
        # Wait for task assignment
        await asyncio.sleep(2)
        
        # Verify task was assigned to market analyst
        delegation_tool = task_manager.get_tool("TaskDelegationTool")
        delegation_tool.operation = "get_tasks"
        delegation_tool.data = {
            "filters": {
                "assigned_agent": market_analyst.id
            }
        }
        
        result = await delegation_tool.run_async()
        assert len(result["tasks"]) > 0
        task = result["tasks"][0]
        assert task["name"] == "Market Analysis Task"
        assert task["status"] == "assigned"

    @pytest.mark.asyncio
    async def test_task_dependencies(self, setup_agents):
        """Test handling of task dependencies"""
        agents = await setup_agents
        task_manager = agents["task_manager"]
        market_analyst = agents["market_analyst"]
        risk_manager = agents["risk_manager"]
        
        # Create dependent tasks
        analysis_task = {
            "name": "Market Analysis",
            "description": "Analyze market conditions",
            "priority": "high",
            "dependencies": [],
            "metadata": {
                "symbol": "ETH/USD",
                "timeframe": "4h"
            }
        }
        
        # Send first task
        await task_manager.send_message(
            "self",
            analysis_task,
            "task_creation_request"
        )
        
        await asyncio.sleep(1)
        
        # Get the analysis task ID
        delegation_tool = task_manager.get_tool("TaskDelegationTool")
        delegation_tool.operation = "get_tasks"
        delegation_tool.data = {
            "filters": {
                "name": "Market Analysis"
            }
        }
        result = await delegation_tool.run_async()
        analysis_task_id = result["tasks"][0]["id"]
        
        # Create dependent risk assessment task
        risk_task = {
            "name": "Risk Assessment",
            "description": "Assess trading risks",
            "priority": "high",
            "dependencies": [analysis_task_id],
            "metadata": {
                "symbol": "ETH/USD",
                "risk_metrics": ["VaR", "Sharpe"]
            }
        }
        
        # Send second task
        await task_manager.send_message(
            "self",
            risk_task,
            "task_creation_request"
        )
        
        await asyncio.sleep(1)
        
        # Verify risk task is pending
        delegation_tool.operation = "get_tasks"
        delegation_tool.data = {
            "filters": {
                "name": "Risk Assessment"
            }
        }
        result = await delegation_tool.run_async()
        risk_task = result["tasks"][0]
        assert risk_task["status"] == "pending"
        
        # Complete analysis task
        delegation_tool.operation = "update_task"
        delegation_tool.data = {
            "task_id": analysis_task_id,
            "updates": {
                "status": "completed",
                "completion_percentage": 100.0
            }
        }
        await delegation_tool.run_async()
        
        await asyncio.sleep(1)
        
        # Verify risk task is now assigned
        delegation_tool.operation = "get_tasks"
        delegation_tool.data = {
            "filters": {
                "name": "Risk Assessment"
            }
        }
        result = await delegation_tool.run_async()
        risk_task = result["tasks"][0]
        assert risk_task["status"] == "assigned"
        assert risk_task["assigned_agent"] == risk_manager.id

    @pytest.mark.asyncio
    async def test_task_progress_monitoring(self, setup_agents):
        """Test monitoring of task progress and updates"""
        agents = await setup_agents
        task_manager = agents["task_manager"]
        market_analyst = agents["market_analyst"]
        
        # Create a task
        task_data = {
            "name": "Long Analysis",
            "description": "Extended market analysis",
            "priority": "medium",
            "dependencies": [],
            "metadata": {
                "symbol": "BTC/USD",
                "timeframe": "1d"
            }
        }
        
        # Send task creation request
        await task_manager.send_message(
            "self",
            task_data,
            "task_creation_request"
        )
        
        await asyncio.sleep(1)
        
        # Get task ID
        delegation_tool = task_manager.get_tool("TaskDelegationTool")
        delegation_tool.operation = "get_tasks"
        delegation_tool.data = {
            "filters": {
                "name": "Long Analysis"
            }
        }
        result = await delegation_tool.run_async()
        task_id = result["tasks"][0]["id"]
        
        # Simulate progress updates
        progress_updates = [25, 50, 75, 100]
        for progress in progress_updates:
            delegation_tool.operation = "update_task"
            delegation_tool.data = {
                "task_id": task_id,
                "updates": {
                    "completion_percentage": float(progress),
                    "status": "completed" if progress == 100 else "in_progress"
                }
            }
            await delegation_tool.run_async()
            await asyncio.sleep(0.5)
        
        # Verify final task state
        delegation_tool.operation = "get_tasks"
        delegation_tool.data = {
            "filters": {
                "task_id": task_id
            }
        }
        result = await delegation_tool.run_async()
        task = result["tasks"][0]
        assert task["status"] == "completed"
        assert task["completion_percentage"] == 100.0

    @pytest.mark.asyncio
    async def test_error_handling(self, setup_agents):
        """Test error handling and recovery"""
        agents = await setup_agents
        task_manager = agents["task_manager"]
        
        # Create a task with invalid data
        invalid_task = {
            "name": "Invalid Task",
            "description": "Task with invalid data",
            "priority": "invalid_priority",
            "dependencies": ["non_existent_task"]
        }
        
        # Send invalid task creation request
        await task_manager.send_message(
            "self",
            invalid_task,
            "task_creation_request"
        )
        
        await asyncio.sleep(1)
        
        # Verify error handling
        delegation_tool = task_manager.get_tool("TaskDelegationTool")
        delegation_tool.operation = "get_tasks"
        delegation_tool.data = {
            "filters": {
                "name": "Invalid Task"
            }
        }
        result = await delegation_tool.run_async()
        assert len(result["tasks"]) == 0  # Task should not be created

    @pytest.mark.asyncio
    async def test_agent_status_handling(self, setup_agents):
        """Test handling of agent status updates"""
        agents = await setup_agents
        task_manager = agents["task_manager"]
        market_analyst = agents["market_analyst"]
        
        # Send agent status update
        await task_manager.send_message(
            market_analyst.id,
            {
                "status": "busy",
                "current_task": "existing_analysis",
                "capacity": 0.8
            },
            "agent_status_update"
        )
        
        await asyncio.sleep(1)
        
        # Create a new task
        task_data = {
            "name": "New Analysis",
            "description": "New market analysis",
            "priority": "high",
            "dependencies": []
        }
        
        # Send task creation request
        await task_manager.send_message(
            "self",
            task_data,
            "task_creation_request"
        )
        
        await asyncio.sleep(1)
        
        # Verify task is not assigned to busy agent
        delegation_tool = task_manager.get_tool("TaskDelegationTool")
        delegation_tool.operation = "get_tasks"
        delegation_tool.data = {
            "filters": {
                "name": "New Analysis"
            }
        }
        result = await delegation_tool.run_async()
        task = result["tasks"][0]
        assert task["assigned_agent"] != market_analyst.id

if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 