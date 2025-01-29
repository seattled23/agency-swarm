import os
import asyncio
import logging
from pathlib import Path
from dotenv import load_dotenv
from agency_swarm.util.oai import init_openai
from run_agency import AgencyRunner

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('agency.log'),
        logging.StreamHandler()
    ]
)

def setup_directories():
    """Create necessary directories if they don't exist."""
    directories = [
        "logs",
        "data",
        "agency_divisions/planning/data",
        "agency_divisions/internal_operations/data",
        "agency_divisions/analysis/data",
        "agency_divisions/projects/data",
        "agency_divisions/upgrades/data",
        "agency_divisions/research/data",
        "agency_divisions/data_management/data",
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        logging.info(f"Created directory: {directory}")

async def main():
    try:
        # Load environment variables
        load_dotenv()
        
        # Set up directories
        setup_directories()
        
        # Initialize OpenAI client
        openai_key = os.getenv("OPENAI_API_KEY")
        if not openai_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")
        init_openai(api_key=openai_key)
        
        # Create and start the agency
        agency = AgencyRunner()
        
        # Start all agents
        await agency.start_agents()
        
        # Start monitoring
        monitor_task = asyncio.create_task(agency.monitor_agents())
        
        try:
            # Keep running until interrupted
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logging.info("Shutdown signal received")
            await agency.shutdown()
            await monitor_task
            
    except Exception as e:
        logging.error(f"Error during initialization: {str(e)}")
        raise

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Agency shutdown complete")
    except Exception as e:
        logging.error(f"Fatal error: {str(e)}")
        raise 