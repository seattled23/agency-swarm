from agency_swarm.tools import BaseTool
from pydantic import Field
import os
from dotenv import load_dotenv
import pandas as pd
import numpy as np
import ccxt
from datetime import datetime
import json

load_dotenv()

class PaperTradingTool(BaseTool):
    """
    A tool for executing and tracking paper trades in the cryptocurrency market.
    Simulates real trading without using actual funds.
    """
    
    symbol: str = Field(
        ..., description="Trading pair symbol (e.g., 'BTC/USDT')"
    )
    side: str = Field(
        ..., description="Trade side ('buy' or 'sell')"
    )
    amount: float = Field(
        ..., description="Trade amount in base currency"
    )
    price: float = Field(
        None, description="Limit price (optional, uses market price if not specified)"
    )
    stop_loss: float = Field(
        None, description="Stop loss price (optional)"
    )
    take_profit: float = Field(
        None, description="Take profit price (optional)"
    )

    def run(self):
        """
        Executes a paper trade and returns the trade details and current position status.
        """
        try:
            # Initialize exchange
            exchange = ccxt.binance()
            
            # Get current market data
            ticker = exchange.fetch_ticker(self.symbol)
            current_price = ticker['last']
            
            # Initialize trade price
            execution_price = self.price if self.price else current_price
            
            # Calculate trade value
            trade_value = self.amount * execution_price
            
            # Load existing paper trading history
            history_file = 'paper_trading_history.json'
            if os.path.exists(history_file):
                with open(history_file, 'r') as f:
                    history = json.load(f)
            else:
                history = {
                    'trades': [],
                    'positions': {},
                    'balance': 1000.0  # Initial paper trading balance
                }
            
            # Create trade record
            trade = {
                'id': len(history['trades']) + 1,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'symbol': self.symbol,
                'side': self.side,
                'amount': self.amount,
                'price': execution_price,
                'value': trade_value,
                'stop_loss': self.stop_loss,
                'take_profit': self.take_profit,
                'status': 'open',
                'pnl': 0.0
            }
            
            # Update position
            position_key = self.symbol
            if position_key not in history['positions']:
                history['positions'][position_key] = {
                    'amount': 0.0,
                    'average_price': 0.0,
                    'unrealized_pnl': 0.0
                }
            
            position = history['positions'][position_key]
            
            # Update position based on trade side
            if self.side == 'buy':
                new_amount = position['amount'] + self.amount
                if new_amount == 0:
                    position['average_price'] = 0.0
                else:
                    position['average_price'] = (
                        (position['amount'] * position['average_price'] + trade_value) / new_amount
                    )
                position['amount'] = new_amount
            else:  # sell
                new_amount = position['amount'] - self.amount
                if abs(new_amount) < 1e-8:  # Close to zero
                    position['amount'] = 0.0
                    position['average_price'] = 0.0
                else:
                    position['amount'] = new_amount
            
            # Calculate unrealized P&L
            if position['amount'] != 0:
                position['unrealized_pnl'] = (
                    position['amount'] * (current_price - position['average_price'])
                )
            else:
                position['unrealized_pnl'] = 0.0
            
            # Update history
            history['trades'].append(trade)
            
            # Save updated history
            with open(history_file, 'w') as f:
                json.dump(history, f, indent=4)
            
            # Prepare results
            results = {
                'trade': trade,
                'position': {
                    'symbol': self.symbol,
                    'current_amount': position['amount'],
                    'average_price': position['average_price'],
                    'current_price': current_price,
                    'unrealized_pnl': position['unrealized_pnl']
                },
                'market_data': {
                    'bid': ticker['bid'],
                    'ask': ticker['ask'],
                    'volume_24h': ticker['quoteVolume'],
                    'price_change_24h': ticker['percentage']
                }
            }
            
            return str(results)
            
        except Exception as e:
            return f"Error executing paper trade: {str(e)}"

if __name__ == "__main__":
    # Test the tool
    tool = PaperTradingTool(
        symbol="BTC/USDT",
        side="buy",
        amount=0.001,
        stop_loss=19000.0,
        take_profit=21000.0
    )
    print(tool.run()) 