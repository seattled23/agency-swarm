from agency_divisions.internal_operations.tools.async_agent_base import AsyncAgent
import asyncio
from typing import Dict, Any, List
from datetime import datetime

class RiskManager(AsyncAgent):
    """
    Risk Manager Agent responsible for managing trading risks, position sizing,
    and portfolio exposure across all trading strategies.
    """
    
    def __init__(self):
        super().__init__(
            name="RiskManager",
            description="Expert in risk management, position sizing, and portfolio exposure control",
            instructions="./instructions.md",
            tools_folder="./tools",
            temperature=0.5,
            max_prompt_tokens=25000
        )
        
        # Register message handlers
        self.register_handler("risk_assessment_request", self._handle_risk_assessment)
        self.register_handler("position_size_request", self._handle_position_sizing)
        self.register_handler("portfolio_update", self._handle_portfolio_update)
        self.register_handler("market_update", self._handle_market_update)
        self.register_handler("strategy_signal", self._handle_strategy_signal)
        
        # Initialize risk management state
        self._portfolio_state = {
            "total_capital": 0.0,
            "allocated_capital": 0.0,
            "positions": {},
            "risk_metrics": {},
            "last_assessment_time": None
        }
        
        self._risk_limits = {
            "max_position_size": 0.05,  # 5% of total capital
            "max_portfolio_risk": 0.02,  # 2% daily VaR
            "max_leverage": 3.0,         # 3x max leverage
            "min_free_margin": 0.3       # 30% min free margin
        }
        
        self._market_state = {}
        self._active_strategies = {}

    async def _handle_risk_assessment(self, message: Dict[str, Any]):
        """Handles requests for risk assessment"""
        try:
            # Extract assessment parameters
            params = message.get("content", {})
            
            # Run risk assessment tool
            assessment_tool = self.get_tool("RiskAssessmentTool")
            assessment_result = await assessment_tool.run_async(
                portfolio_state=self._portfolio_state,
                market_state=self._market_state,
                risk_limits=self._risk_limits,
                **params
            )
            
            # Send assessment results back
            await self.send_message(
                receiver=message["sender"],
                content=assessment_result,
                message_type="risk_assessment_response"
            )
            
            # Update internal state
            await self._update_state({
                "last_assessment": {
                    "timestamp": datetime.now().isoformat(),
                    "type": "risk_assessment",
                    "result": assessment_result
                }
            })
            
        except Exception as e:
            self.logger.error(f"Error handling risk assessment: {str(e)}")
            await self.send_message(
                receiver=message["sender"],
                content={"error": str(e)},
                message_type="error_response"
            )

    async def _handle_position_sizing(self, message: Dict[str, Any]):
        """Handles requests for position sizing calculations"""
        try:
            # Extract position parameters
            params = message.get("content", {})
            
            # Run position sizing tool
            sizing_tool = self.get_tool("PositionSizingTool")
            sizing_result = await sizing_tool.run_async(
                portfolio_state=self._portfolio_state,
                risk_limits=self._risk_limits,
                **params
            )
            
            # Send sizing results back
            await self.send_message(
                receiver=message["sender"],
                content=sizing_result,
                message_type="position_size_response"
            )
            
        except Exception as e:
            self.logger.error(f"Error handling position sizing: {str(e)}")
            await self.send_message(
                receiver=message["sender"],
                content={"error": str(e)},
                message_type="error_response"
            )

    async def _handle_portfolio_update(self, message: Dict[str, Any]):
        """Handles portfolio state updates"""
        try:
            update_data = message.get("content", {})
            
            # Update portfolio state
            self._portfolio_state.update(update_data)
            
            # Run portfolio risk check
            await self._check_portfolio_risk()
            
            # Update internal state
            await self._update_state({
                "portfolio_state": self._portfolio_state
            })
            
        except Exception as e:
            self.logger.error(f"Error handling portfolio update: {str(e)}")

    async def _handle_market_update(self, message: Dict[str, Any]):
        """Handles market state updates"""
        try:
            update_data = message.get("content", {})
            
            # Update market state
            self._market_state.update(update_data)
            
            # Check if risk assessment needed
            await self._check_risk_conditions()
            
        except Exception as e:
            self.logger.error(f"Error handling market update: {str(e)}")

    async def _handle_strategy_signal(self, message: Dict[str, Any]):
        """Handles incoming strategy signals"""
        try:
            signal_data = message.get("content", {})
            strategy_id = signal_data.get("strategy_id")
            
            # Validate signal against risk parameters
            validation_tool = self.get_tool("SignalValidationTool")
            validation_result = await validation_tool.run_async(
                signal=signal_data,
                portfolio_state=self._portfolio_state,
                risk_limits=self._risk_limits
            )
            
            # Send validation response
            await self.send_message(
                receiver=message["sender"],
                content=validation_result,
                message_type="signal_validation_response"
            )
            
        except Exception as e:
            self.logger.error(f"Error handling strategy signal: {str(e)}")

    async def _check_portfolio_risk(self):
        """Checks overall portfolio risk metrics"""
        try:
            risk_tool = self.get_tool("RiskAssessmentTool")
            risk_assessment = await risk_tool.run_async(
                portfolio_state=self._portfolio_state,
                market_state=self._market_state,
                risk_limits=self._risk_limits
            )
            
            # If risk limits exceeded, notify subscribers
            if risk_assessment.get("risk_limits_exceeded"):
                await self.send_message(
                    receiver="broadcast",
                    content=risk_assessment,
                    message_type="risk_alert"
                )
                
        except Exception as e:
            self.logger.error(f"Error checking portfolio risk: {str(e)}")

    async def _check_risk_conditions(self):
        """Checks if market conditions warrant risk reassessment"""
        try:
            conditions_tool = self.get_tool("MarketConditionsTool")
            conditions = await conditions_tool.run_async(
                market_state=self._market_state
            )
            
            if conditions.get("requires_assessment"):
                await self._check_portfolio_risk()
                
        except Exception as e:
            self.logger.error(f"Error checking risk conditions: {str(e)}")

    async def _perform_tasks(self):
        """Performs periodic risk management tasks"""
        try:
            current_time = asyncio.get_event_loop().time()
            
            # Periodic risk assessment (every 15 minutes)
            if (not self._portfolio_state["last_assessment_time"] or 
                current_time - self._portfolio_state["last_assessment_time"] >= 900):
                
                await self._check_portfolio_risk()
                self._portfolio_state["last_assessment_time"] = current_time
                
        except Exception as e:
            self.logger.error(f"Error in periodic tasks: {str(e)}")

if __name__ == "__main__":
    # Test the Risk Manager
    async def test_risk_manager():
        manager = RiskManager()
        
        # Start the agent
        await manager.start()
        
        # Simulate portfolio update
        await manager.send_message(
            "self",
            {
                "total_capital": 100000,
                "allocated_capital": 50000,
                "positions": {
                    "BTC/USD": {
                        "size": 1.0,
                        "entry_price": 50000,
                        "current_price": 51000
                    }
                }
            },
            "portfolio_update"
        )
        
        # Run for a few minutes
        await asyncio.sleep(360)
        
        # Stop the agent
        await manager.stop()
    
    asyncio.run(test_risk_manager()) 