import asyncio
import json
import logging
import os
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).resolve().parents[3]
import sys
sys.path.append(str(project_root))

from crypto_trading_agency.planning_agent.tools.project_tracker import ProjectTracker
from crypto_trading_agency.planning_agent.tools.task_delegation import TaskDelegationTool, TaskPriority, TaskStatus

async def create_task(name: str, description: str, priority: TaskPriority, deadline: str, agent: str) -> dict:
    """Helper function to create and assign a task."""
    task_delegator = TaskDelegationTool(
        task_name=name,
        task_description=description,
        priority=priority,
        deadline=deadline
    )
    
    # Create and assign the task
    task_result = await task_delegator.create_task()
    assignment_result = await task_delegator.assign_task(agent)
    
    return {
        "task_id": task_result["task_id"],
        "status": assignment_result["status"]
    }

async def main():
    """Initialize project tracking and create initial tasks."""
    try:
        # Load project specification
        with open('crypto_trading_agency/planning_agent/project_spec.json', 'r') as f:
            project_spec = json.load(f)
        
        # Initialize project tracker
        tracker = ProjectTracker(
            project_spec=project_spec,
            tracking_mode="async",
            update_interval=300
        )
        
        # Analyze project structure
        structure = tracker.analyze_project_structure()
        print("\nProject Structure Analysis:")
        print(json.dumps(structure, indent=2))
        
        # Create tasks for Market Analysis System (M1)
        m1_tasks = [
            # Technical Analysis Enhancement
            await create_task(
                "Enhance Technical Analysis Tool",
                "Implement advanced technical indicators and pattern recognition including RSI, MACD, Moving Averages, and chart patterns",
                TaskPriority.HIGH,
                "2024-02-05T00:00:00",
                "market_analyst"
            ),
            # Real-time Market Data Integration
            await create_task(
                "Implement Real-time Market Data Integration",
                "Set up real-time data feeds, websocket connections, and market data processing pipeline",
                TaskPriority.HIGH,
                "2024-02-05T00:00:00",
                "market_analyst"
            ),
            # ML-based Prediction System
            await create_task(
                "Develop ML-based Prediction System",
                "Create and train machine learning models for market prediction, including price movement and trend analysis",
                TaskPriority.HIGH,
                "2024-02-05T00:00:00",
                "market_analyst"
            ),
            # Market Sentiment Analysis
            await create_task(
                "Implement Market Sentiment Analysis",
                "Develop tools for analyzing market sentiment, social media trends, and on-chain metrics",
                TaskPriority.MEDIUM,
                "2024-02-05T00:00:00",
                "market_analyst"
            ),
            # System Integration Testing
            await create_task(
                "Perform Market Analysis System Integration",
                "Integrate and test all market analysis components together, ensure proper data flow and error handling",
                TaskPriority.HIGH,
                "2024-02-05T00:00:00",
                "market_analyst"
            )
        ]
        
        # Update project status with all new tasks
        status_update = {
            "milestone_updates": {
                "m1": {
                    "status": "in_progress",
                    "progress": 0.1
                }
            },
            "task_updates": [
                {
                    "id": task["task_id"],
                    "status": "active"
                }
                for task in m1_tasks
            ]
        }
        
        updated_state = tracker.update_project_status(status_update)
        print("\nUpdated Project State:")
        print(json.dumps(updated_state, indent=2))
        
    except Exception as e:
        logging.error(f"Error during project initialization: {str(e)}")
        import traceback
        traceback.print_exc()
        raise

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s'
    )
    
    # Run the initialization
    asyncio.run(main()) 