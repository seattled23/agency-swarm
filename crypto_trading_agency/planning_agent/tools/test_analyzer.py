import asyncio
import logging
import os
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).resolve().parents[3]
sys.path.append(str(project_root))

from crypto_trading_agency.planning_agent.tools.system_analyzer import SystemAnalyzer

async def main():
    """Run the system analyzer test."""
    try:
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] %(message)s'
        )
        
        # Create results directory if it doesn't exist
        os.makedirs("analysis_results", exist_ok=True)
        
        # Initialize analyzer with longer duration for testing
        analyzer = SystemAnalyzer(
            target_components=["planning_agent"],
            metrics_to_collect=["performance", "resources", "capabilities"],
            analysis_duration=60,
            data_processing_mode="batch"
        )
        
        # Run the analyzer and get results
        results = await analyzer.run()
        print("\nAnalysis Results:")
        print(results)
        return results
        
    except Exception as e:
        logging.error(f"Error during analysis: {str(e)}")
        import traceback
        traceback.print_exc()
        raise

if __name__ == "__main__":
    try:
        # Run with proper asyncio event loop
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nAnalysis interrupted by user")
    except Exception as e:
        print(f"\nError: {str(e)}") 