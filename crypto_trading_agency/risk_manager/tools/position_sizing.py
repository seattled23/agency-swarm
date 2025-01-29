from agency_swarm.tools import BaseTool
from pydantic import Field
import os
from dotenv import load_dotenv
import pandas as pd
import numpy as np
import ccxt

load_dotenv()

class PositionSizingTool(BaseTool):
    """
    A tool for calculating optimal position sizes based on account balance,
    risk parameters, and market conditions.
    """
    
    symbol: str = Field(
        ..., description="Trading pair symbol (e.g., 'BTC/USDT')"
    )
    account_balance: float = Field(
        ..., description="Current account balance in quote currency"
    )
    risk_per_trade: float = Field(
        default=0.02, description="Maximum risk per trade as fraction of account (e.g., 0.02 for 2%)"
    )
    stop_loss_percent: float = Field(
        default=0.02, description="Stop loss percentage (e.g., 0.02 for 2%)"
    )
    max_position_size: float = Field(
        default=0.1, description="Maximum position size as fraction of account (e.g., 0.1 for 10%)"
    )

    def run(self):
        """
        Calculates optimal position size based on risk parameters and market conditions.
        Returns position sizing recommendations and risk metrics.
        """
        try:
            # Initialize exchange
            exchange = ccxt.binance()
            
            # Fetch current market price and 24h stats
            ticker = exchange.fetch_ticker(self.symbol)
            current_price = ticker['last']
            
            # Calculate position size based on risk
            risk_amount = self.account_balance * self.risk_per_trade
            stop_loss_distance = current_price * self.stop_loss_percent
            
            # Calculate position size in base currency
            position_size_risk = risk_amount / stop_loss_distance
            position_size_base = position_size_risk * current_price
            
            # Calculate position size based on max position limit
            max_position_value = self.account_balance * self.max_position_size
            position_size_max = max_position_value / current_price
            
            # Use the smaller of the two position sizes
            final_position_size = min(position_size_base, position_size_max)
            
            # Calculate additional risk metrics
            position_value = final_position_size * current_price
            account_risk_percent = (position_value * self.stop_loss_percent) / self.account_balance
            
            # Calculate volatility-based adjustment
            volatility = ticker['percentage'] / 100  # 24h price change percentage
            volatility_multiplier = 1.0
            if abs(volatility) > 0.05:  # If 24h change is more than 5%
                volatility_multiplier = 0.8  # Reduce position size by 20%
            
            final_position_size *= volatility_multiplier
            
            # Prepare results
            results = {
                'symbol': self.symbol,
                'current_price': current_price,
                'account_balance': self.account_balance,
                'position_sizing': {
                    'recommended_position_size': final_position_size,
                    'position_value': final_position_size * current_price,
                    'account_risk_percent': account_risk_percent * 100,
                    'stop_loss_price': current_price * (1 - self.stop_loss_percent),
                },
                'risk_metrics': {
                    'max_loss_amount': risk_amount,
                    'volatility_24h': volatility * 100,
                    'volatility_multiplier': volatility_multiplier,
                },
                'limits': {
                    'max_position_value': max_position_value,
                    'risk_per_trade': self.risk_per_trade * 100,
                    'stop_loss_percent': self.stop_loss_percent * 100,
                }
            }
            
            return str(results)
            
        except Exception as e:
            return f"Error calculating position size: {str(e)}"

if __name__ == "__main__":
    # Test the tool
    tool = PositionSizingTool(
        symbol="BTC/USDT",
        account_balance=100.0,
        risk_per_trade=0.02,
        stop_loss_percent=0.02,
        max_position_size=0.1
    )
    print(tool.run()) 