import asyncio
import logging
from pathlib import Path
from agency_swarm import Agency
from datetime import datetime

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
import sys
sys.path.append(str(project_root))

# Import our agency
from crypto_trading_agency.agency import agency

async def main():
    """Run the Market Analysis System development phase with multiple agents."""
    try:
        logging.info("Starting Market Analysis System development phase")
        
        # Initial task assignment from Project Manager to Market Analyst
        response = await agency.project_manager.run(
            "We need to develop the Market Analysis System. Please coordinate with the Market Analyst "
            "to begin work on the following tasks:\n"
            "1. Enhance Technical Analysis Tool\n"
            "2. Implement Real-time Market Data Integration\n"
            "3. Develop ML-based Prediction System\n"
            "4. Implement Market Sentiment Analysis\n"
            "5. Perform System Integration\n"
            "\nPlease manage these tasks and ensure they meet our quality standards."
        )
        print("\nProject Manager Response:")
        print(response)
        
        # Market Analyst begins technical analysis enhancement
        response = await agency.market_analyst.run(
            "Please begin work on enhancing the Technical Analysis Tool. This includes:\n"
            "1. Implementing RSI, MACD, and Moving Averages\n"
            "2. Adding pattern recognition capabilities\n"
            "3. Ensuring proper error handling and validation\n"
            "Please coordinate with the Testing Agent for quality assurance."
        )
        print("\nMarket Analyst Response:")
        print(response)
        
        # Testing Agent provides QA support
        response = await agency.testing_agent.run(
            "Please work with the Market Analyst to ensure the Technical Analysis Tool meets our quality standards. "
            "Focus on:\n"
            "1. Unit test coverage\n"
            "2. Integration test scenarios\n"
            "3. Performance benchmarks"
        )
        print("\nTesting Agent Response:")
        print(response)
        
        # Planning Agent optimizes workflow
        response = await agency.planning_agent.run(
            "Please analyze the current development workflow of the Market Analysis System and provide "
            "optimization recommendations. Focus on:\n"
            "1. Resource utilization\n"
            "2. Task dependencies\n"
            "3. Critical path optimization"
        )
        print("\nPlanning Agent Response:")
        print(response)
        
        logging.info("Market Analysis System development phase initialized successfully")
        
    except Exception as e:
        logging.error(f"Error during Market Analysis System development: {str(e)}")
        import traceback
        traceback.print_exc()
        raise

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[
            logging.FileHandler('market_analysis_phase.log'),
            logging.StreamHandler()
        ]
    )
    
    # Run the multi-agent workflow
    asyncio.run(main()) 