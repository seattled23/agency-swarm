from agency_divisions.internal_operations.tools.async_agent_base import AsyncAgent
import asyncio
from typing import Dict, Any

class MarketAnalyst(AsyncAgent):
    """
    Market Analysis Agent responsible for analyzing market trends, identifying trading opportunities,
    and developing trading strategies.
    """
    def __init__(self):
        super().__init__(
            name="MarketAnalyst",
            description="Expert in market analysis, trend identification, and trading strategy development",
            instructions="./instructions.md",
            tools_folder="./tools",
            temperature=0.5,
            max_prompt_tokens=25000,
        ) 
        
        # Register message handlers
        self.register_handler("analysis_request", self._handle_analysis_request)
        self.register_handler("strategy_request", self._handle_strategy_request)
        self.register_handler("market_update", self._handle_market_update)
        
        # Initialize analysis state
        self._last_analysis_time = None
        self._current_market_state = {}
        self._active_strategies = {}

    async def _handle_analysis_request(self, message: Dict[str, Any]):
        """Handles requests for market analysis"""
        try:
            # Extract analysis parameters from message
            params = message.get("content", {})
            
            # Run market analysis tool
            analysis_tool = self.get_tool("MarketAnalysisTool")
            analysis_result = await analysis_tool.run_async(**params)
            
            # Send analysis results back to requester
            await self.send_message(
                receiver=message["sender"],
                content=analysis_result,
                message_type="analysis_response"
            )
            
            # Update internal state
            await self._update_state({
                "last_analysis": {
                    "timestamp": self._last_analysis_time,
                    "type": "market_analysis",
                    "params": params
                }
            })
            
        except Exception as e:
            self.logger.error(f"Error handling analysis request: {str(e)}")
            await self.send_message(
                receiver=message["sender"],
                content={"error": str(e)},
                message_type="error_response"
            )

    async def _handle_strategy_request(self, message: Dict[str, Any]):
        """Handles requests for trading strategy development"""
        try:
            # Extract strategy parameters from message
            params = message.get("content", {})
            
            # Run strategy development tool
            strategy_tool = self.get_tool("StrategyDevelopmentTool")
            strategy_result = await strategy_tool.run_async(**params)
            
            # Store active strategy
            strategy_id = strategy_result.get("strategy_id")
            if strategy_id:
                self._active_strategies[strategy_id] = strategy_result
            
            # Send strategy back to requester
            await self.send_message(
                receiver=message["sender"],
                content=strategy_result,
                message_type="strategy_response"
            )
            
            # Update internal state
            await self._update_state({
                "active_strategies": list(self._active_strategies.keys())
            })
            
        except Exception as e:
            self.logger.error(f"Error handling strategy request: {str(e)}")
            await self.send_message(
                receiver=message["sender"],
                content={"error": str(e)},
                message_type="error_response"
            )

    async def _handle_market_update(self, message: Dict[str, Any]):
        """Handles incoming market updates"""
        try:
            # Update current market state
            update_data = message.get("content", {})
            self._current_market_state.update(update_data)
            
            # Check if any strategies need adjustment
            await self._evaluate_strategies()
            
            # Update internal state
            await self._update_state({
                "market_state": self._current_market_state
            })
            
        except Exception as e:
            self.logger.error(f"Error handling market update: {str(e)}")

    async def _evaluate_strategies(self):
        """Evaluates and adjusts active strategies based on current market conditions"""
        try:
            for strategy_id, strategy in self._active_strategies.items():
                # Run strategy evaluation tool
                evaluation_tool = self.get_tool("StrategyEvaluationTool")
                evaluation_result = await evaluation_tool.run_async(
                    strategy=strategy,
                    market_state=self._current_market_state
                )
                
                # If adjustments are needed, notify strategy subscribers
                if evaluation_result.get("needs_adjustment"):
                    for subscriber in strategy.get("subscribers", []):
                        await self.send_message(
                            receiver=subscriber,
                            content={
                                "strategy_id": strategy_id,
                                "adjustments": evaluation_result["adjustments"]
                            },
                            message_type="strategy_adjustment"
                        )
                    
        except Exception as e:
            self.logger.error(f"Error evaluating strategies: {str(e)}")

    async def _perform_tasks(self):
        """Performs periodic tasks specific to the Market Analyst"""
        try:
            # Periodic market analysis
            current_time = asyncio.get_event_loop().time()
            if (not self._last_analysis_time or 
                current_time - self._last_analysis_time >= 300):  # 5 minutes
                
                analysis_tool = self.get_tool("MarketAnalysisTool")
                analysis_result = await analysis_tool.run_async()
                
                # Broadcast analysis to subscribers
                await self.send_message(
                    receiver="broadcast",
                    content=analysis_result,
                    message_type="periodic_analysis"
                )
                
                self._last_analysis_time = current_time
            
        except Exception as e:
            self.logger.error(f"Error in periodic tasks: {str(e)}")

if __name__ == "__main__":
    # Test the async Market Analyst
    async def test_market_analyst():
        analyst = MarketAnalyst()
        
        # Start the agent
        await analyst.start()
        
        # Simulate some market updates
        await analyst.send_message(
            "self",
            {
                "symbol": "BTC/USD",
                "price": 50000,
                "volume": 1000
            },
            "market_update"
        )
        
        # Run for a few minutes
        await asyncio.sleep(360)
        
        # Stop the agent
        await analyst.stop()
    
    asyncio.run(test_market_analyst()) 