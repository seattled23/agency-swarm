import asyncio
import logging
from pathlib import Path
from alignment_agent import AlignmentAgent
from tools.safety_monitor import SafetyMonitor
from tools.behavior_analysis import BehaviorAnalysisTool

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('alignment_deployment.log'),
        logging.StreamHandler()
    ]
)

async def deploy_alignment_agent():
    """Deploy and initialize the Alignment Agent with monitoring tools."""
    try:
        logging.info("Starting Alignment Agent deployment...")
        
        # Initialize Alignment Agent
        alignment = AlignmentAgent()
        logging.info("Alignment Agent initialized")
        
        # Initialize Safety Monitor for each agent
        monitors = {}
        for agent_id in ["planning_agent", "testing_agent"]:  # Add other agents as needed
            monitor = SafetyMonitor(
                target_agent=agent_id,
                safety_threshold=0.95,
                monitoring_interval=1.0
            )
            monitors[agent_id] = monitor
            await monitor.start_monitoring()
            logging.info(f"Safety monitoring started for {agent_id}")
        
        # Initialize Behavior Analysis for each agent
        analyzers = {}
        for agent_id in ["planning_agent", "testing_agent"]:  # Add other agents as needed
            analyzer = BehaviorAnalysisTool(
                agent_id=agent_id,
                analysis_window=100,
                anomaly_threshold=0.8
            )
            analyzers[agent_id] = analyzer
            await analyzer.run()
            logging.info(f"Behavior analysis initialized for {agent_id}")
        
        logging.info("Alignment Agent deployment completed successfully")
        return {
            'status': 'deployed',
            'alignment_agent': alignment,
            'safety_monitors': monitors,
            'behavior_analyzers': analyzers
        }
        
    except Exception as e:
        logging.error(f"Error during Alignment Agent deployment: {str(e)}")
        raise

if __name__ == "__main__":
    # Deploy Alignment Agent
    asyncio.run(deploy_alignment_agent()) 