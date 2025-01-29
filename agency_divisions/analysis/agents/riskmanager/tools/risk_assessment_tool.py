from agency_swarm.tools import BaseTool
from pydantic import Field
import numpy as np
import pandas as pd
from typing import Dict, Any, Optional, List
import asyncio
from datetime import datetime, timedelta
import logging
import os
from scipy import stats
import json

class RiskAssessmentTool(BaseTool):
    """
    Tool for assessing portfolio risk metrics including VaR, position exposure,
    correlation risk, and overall portfolio health.
    """
    
    confidence_level: float = Field(
        default=0.95,
        description="Confidence level for VaR calculation (e.g., 0.95 for 95%)"
    )
    
    time_horizon: int = Field(
        default=1,
        description="Time horizon in days for risk calculations"
    )
    
    historical_window: int = Field(
        default=30,
        description="Historical window in days for volatility calculations"
    )

    def __init__(self, **data):
        super().__init__(**data)
        
        # Setup logging
        log_dir = "agency_divisions/analysis/logs/risk_assessment"
        os.makedirs(log_dir, exist_ok=True)
        logging.basicConfig(
            filename=f"{log_dir}/risk_assessment.log",
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger('RiskAssessmentTool')

    async def run(self, portfolio_state: Dict[str, Any], market_state: Dict[str, Any], 
                 risk_limits: Dict[str, float], **kwargs) -> Dict[str, Any]:
        """
        Executes risk assessment asynchronously
        """
        try:
            # Calculate core risk metrics
            position_metrics = await self._calculate_position_metrics(portfolio_state)
            portfolio_metrics = await self._calculate_portfolio_metrics(
                portfolio_state, market_state
            )
            var_metrics = await self._calculate_var_metrics(
                portfolio_state, market_state
            )
            
            # Check risk limits
            risk_breaches = await self._check_risk_limits(
                position_metrics, portfolio_metrics, var_metrics, risk_limits
            )
            
            # Generate assessment report
            assessment = {
                'timestamp': datetime.now().isoformat(),
                'position_metrics': position_metrics,
                'portfolio_metrics': portfolio_metrics,
                'var_metrics': var_metrics,
                'risk_breaches': risk_breaches,
                'risk_limits_exceeded': len(risk_breaches) > 0,
                'overall_risk_level': await self._determine_risk_level(
                    position_metrics, portfolio_metrics, var_metrics, risk_limits
                )
            }
            
            return assessment
            
        except Exception as e:
            self.logger.error(f"Error in risk assessment: {str(e)}")
            raise

    async def _calculate_position_metrics(self, portfolio_state: Dict[str, Any]) -> Dict[str, Any]:
        """Calculates position-level risk metrics"""
        try:
            total_capital = portfolio_state.get('total_capital', 0)
            positions = portfolio_state.get('positions', {})
            
            position_metrics = {}
            for symbol, position in positions.items():
                size = position.get('size', 0)
                entry_price = position.get('entry_price', 0)
                current_price = position.get('current_price', 0)
                
                position_value = size * current_price
                position_pnl = size * (current_price - entry_price)
                position_exposure = position_value / total_capital if total_capital > 0 else 0
                
                position_metrics[symbol] = {
                    'position_value': position_value,
                    'position_pnl': position_pnl,
                    'position_exposure': position_exposure,
                    'unrealized_pnl_pct': (position_pnl / (size * entry_price)) if size * entry_price != 0 else 0
                }
            
            return position_metrics
            
        except Exception as e:
            self.logger.error(f"Error calculating position metrics: {str(e)}")
            raise

    async def _calculate_portfolio_metrics(self, portfolio_state: Dict[str, Any], 
                                        market_state: Dict[str, Any]) -> Dict[str, Any]:
        """Calculates portfolio-level risk metrics"""
        try:
            total_capital = portfolio_state.get('total_capital', 0)
            allocated_capital = portfolio_state.get('allocated_capital', 0)
            positions = portfolio_state.get('positions', {})
            
            # Calculate portfolio values
            total_position_value = sum(
                pos.get('size', 0) * pos.get('current_price', 0)
                for pos in positions.values()
            )
            
            total_pnl = sum(
                pos.get('size', 0) * (pos.get('current_price', 0) - pos.get('entry_price', 0))
                for pos in positions.values()
            )
            
            # Calculate exposure metrics
            net_exposure = total_position_value / total_capital if total_capital > 0 else 0
            free_margin_ratio = (total_capital - allocated_capital) / total_capital if total_capital > 0 else 0
            
            # Calculate concentration metrics
            position_weights = {
                symbol: (pos.get('size', 0) * pos.get('current_price', 0)) / total_position_value
                for symbol, pos in positions.items()
            } if total_position_value > 0 else {}
            
            max_concentration = max(position_weights.values()) if position_weights else 0
            
            return {
                'total_position_value': total_position_value,
                'total_pnl': total_pnl,
                'net_exposure': net_exposure,
                'free_margin_ratio': free_margin_ratio,
                'position_weights': position_weights,
                'max_concentration': max_concentration,
                'portfolio_size': len(positions),
                'allocated_capital_ratio': allocated_capital / total_capital if total_capital > 0 else 0
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating portfolio metrics: {str(e)}")
            raise

    async def _calculate_var_metrics(self, portfolio_state: Dict[str, Any], 
                                  market_state: Dict[str, Any]) -> Dict[str, Any]:
        """Calculates Value at Risk (VaR) metrics"""
        try:
            positions = portfolio_state.get('positions', {})
            
            # Calculate portfolio returns (assuming we have historical data in market_state)
            portfolio_returns = []
            portfolio_value = sum(
                pos.get('size', 0) * pos.get('current_price', 0)
                for pos in positions.values()
            )
            
            if portfolio_value > 0:
                # Calculate parametric VaR
                returns_std = np.std(portfolio_returns) if portfolio_returns else 0
                z_score = stats.norm.ppf(1 - self.confidence_level)
                var_parametric = portfolio_value * z_score * returns_std * np.sqrt(self.time_horizon)
                
                # Calculate historical VaR
                var_historical = np.percentile(portfolio_returns, (1 - self.confidence_level) * 100) * portfolio_value \
                    if portfolio_returns else 0
                
                # Calculate Expected Shortfall (CVaR)
                tail_returns = [r for r in portfolio_returns if r <= var_historical / portfolio_value] \
                    if portfolio_returns else []
                cvar = np.mean(tail_returns) * portfolio_value if tail_returns else 0
                
                return {
                    'var_parametric': abs(var_parametric),
                    'var_historical': abs(var_historical),
                    'cvar': abs(cvar),
                    'var_pct_parametric': abs(var_parametric / portfolio_value) if portfolio_value > 0 else 0,
                    'confidence_level': self.confidence_level,
                    'time_horizon': self.time_horizon
                }
            
            return {
                'var_parametric': 0,
                'var_historical': 0,
                'cvar': 0,
                'var_pct_parametric': 0,
                'confidence_level': self.confidence_level,
                'time_horizon': self.time_horizon
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating VaR metrics: {str(e)}")
            raise

    async def _check_risk_limits(self, position_metrics: Dict[str, Any],
                               portfolio_metrics: Dict[str, Any],
                               var_metrics: Dict[str, Any],
                               risk_limits: Dict[str, float]) -> List[Dict[str, Any]]:
        """Checks for risk limit breaches"""
        try:
            breaches = []
            
            # Check position size limits
            for symbol, metrics in position_metrics.items():
                if metrics['position_exposure'] > risk_limits['max_position_size']:
                    breaches.append({
                        'type': 'position_size',
                        'symbol': symbol,
                        'current': metrics['position_exposure'],
                        'limit': risk_limits['max_position_size']
                    })
            
            # Check portfolio risk limits
            if portfolio_metrics['net_exposure'] > risk_limits['max_leverage']:
                breaches.append({
                    'type': 'leverage',
                    'current': portfolio_metrics['net_exposure'],
                    'limit': risk_limits['max_leverage']
                })
            
            if portfolio_metrics['free_margin_ratio'] < risk_limits['min_free_margin']:
                breaches.append({
                    'type': 'free_margin',
                    'current': portfolio_metrics['free_margin_ratio'],
                    'limit': risk_limits['min_free_margin']
                })
            
            # Check VaR limits
            if var_metrics['var_pct_parametric'] > risk_limits['max_portfolio_risk']:
                breaches.append({
                    'type': 'var',
                    'current': var_metrics['var_pct_parametric'],
                    'limit': risk_limits['max_portfolio_risk']
                })
            
            return breaches
            
        except Exception as e:
            self.logger.error(f"Error checking risk limits: {str(e)}")
            raise

    async def _determine_risk_level(self, position_metrics: Dict[str, Any],
                                  portfolio_metrics: Dict[str, Any],
                                  var_metrics: Dict[str, Any],
                                  risk_limits: Dict[str, float]) -> str:
        """Determines overall risk level based on metrics"""
        try:
            # Calculate risk scores
            position_risk_score = max(
                [metrics['position_exposure'] / risk_limits['max_position_size']
                 for metrics in position_metrics.values()],
                default=0
            )
            
            leverage_risk_score = portfolio_metrics['net_exposure'] / risk_limits['max_leverage']
            margin_risk_score = 1 - (portfolio_metrics['free_margin_ratio'] / risk_limits['min_free_margin'])
            var_risk_score = var_metrics['var_pct_parametric'] / risk_limits['max_portfolio_risk']
            
            # Calculate weighted average risk score
            risk_score = np.mean([
                position_risk_score * 0.3,
                leverage_risk_score * 0.3,
                margin_risk_score * 0.2,
                var_risk_score * 0.2
            ])
            
            # Determine risk level
            if risk_score >= 1.0:
                return "critical"
            elif risk_score >= 0.8:
                return "high"
            elif risk_score >= 0.5:
                return "medium"
            else:
                return "low"
                
        except Exception as e:
            self.logger.error(f"Error determining risk level: {str(e)}")
            raise

if __name__ == "__main__":
    # Test the risk assessment tool
    async def test_risk_assessment():
        tool = RiskAssessmentTool(
            confidence_level=0.95,
            time_horizon=1,
            historical_window=30
        )
        
        # Sample portfolio state
        portfolio_state = {
            "total_capital": 100000,
            "allocated_capital": 50000,
            "positions": {
                "BTC/USD": {
                    "size": 1.0,
                    "entry_price": 50000,
                    "current_price": 51000
                },
                "ETH/USD": {
                    "size": 10.0,
                    "entry_price": 3000,
                    "current_price": 3100
                }
            }
        }
        
        # Sample market state
        market_state = {
            "BTC/USD": {
                "volatility": 0.02,
                "returns": [-0.01, 0.02, 0.01, -0.015]
            },
            "ETH/USD": {
                "volatility": 0.03,
                "returns": [-0.02, 0.03, 0.01, -0.01]
            }
        }
        
        # Sample risk limits
        risk_limits = {
            "max_position_size": 0.05,
            "max_portfolio_risk": 0.02,
            "max_leverage": 3.0,
            "min_free_margin": 0.3
        }
        
        try:
            assessment = await tool.run(
                portfolio_state=portfolio_state,
                market_state=market_state,
                risk_limits=risk_limits
            )
            print(json.dumps(assessment, indent=2))
            
        except Exception as e:
            print(f"Error running risk assessment: {str(e)}")
    
    asyncio.run(test_risk_assessment()) 