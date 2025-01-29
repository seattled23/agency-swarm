from agency_swarm.tools import BaseTool
from pydantic import Field
import os
from dotenv import load_dotenv
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import ccxt
import ta

load_dotenv()

class BacktestingTool(BaseTool):
    """
    A tool for backtesting cryptocurrency trading strategies.
    Tests strategy performance on historical data and generates comprehensive performance metrics.
    """
    
    symbol: str = Field(
        ..., description="Trading pair symbol (e.g., 'BTC/USDT')"
    )
    timeframe: str = Field(
        ..., description="Analysis timeframe (e.g., '1h', '4h', '1d')"
    )
    strategy_type: str = Field(
        ..., description="Type of strategy to backtest (e.g., 'MA_Crossover', 'RSI_Reversal')"
    )
    initial_capital: float = Field(
        default=100.0, description="Initial capital for backtesting"
    )
    position_size: float = Field(
        default=0.02, description="Position size as fraction of capital (e.g., 0.02 for 2%)"
    )

    def run(self):
        """
        Performs backtesting of the specified trading strategy and returns performance metrics.
        """
        try:
            # Initialize exchange and fetch historical data
            exchange = ccxt.binance()
            
            # Calculate the start date (1 month of data)
            end_date = datetime.now()
            start_date = end_date - timedelta(days=30)
            
            # Fetch OHLCV data
            ohlcv = exchange.fetch_ohlcv(
                symbol=self.symbol,
                timeframe=self.timeframe,
                since=int(start_date.timestamp() * 1000),
                limit=1000
            )
            
            # Convert to DataFrame
            df = pd.DataFrame(
                ohlcv,
                columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
            )
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            # Initialize strategy parameters based on strategy type
            if self.strategy_type == 'MA_Crossover':
                # Add indicators for MA Crossover strategy
                df['sma_short'] = ta.trend.sma_indicator(df['close'], window=10)
                df['sma_long'] = ta.trend.sma_indicator(df['close'], window=20)
                
                # Generate signals
                df['signal'] = 0
                df.loc[df['sma_short'] > df['sma_long'], 'signal'] = 1
                df.loc[df['sma_short'] < df['sma_long'], 'signal'] = -1
                
            elif self.strategy_type == 'RSI_Reversal':
                # Add indicators for RSI Reversal strategy
                df['rsi'] = ta.momentum.rsi(df['close'], window=14)
                
                # Generate signals
                df['signal'] = 0
                df.loc[df['rsi'] < 30, 'signal'] = 1  # Oversold
                df.loc[df['rsi'] > 70, 'signal'] = -1  # Overbought
            
            # Calculate returns
            df['returns'] = df['close'].pct_change()
            df['strategy_returns'] = df['signal'].shift(1) * df['returns']
            
            # Calculate strategy metrics
            total_returns = (1 + df['strategy_returns'].fillna(0)).cumprod()[-1] - 1
            annual_returns = total_returns * (365 / 30)  # Annualized returns
            
            # Calculate Sharpe Ratio (assuming risk-free rate of 0.01)
            risk_free_rate = 0.01
            excess_returns = df['strategy_returns'].fillna(0) - risk_free_rate/365
            sharpe_ratio = np.sqrt(365) * excess_returns.mean() / excess_returns.std()
            
            # Calculate Maximum Drawdown
            cumulative_returns = (1 + df['strategy_returns'].fillna(0)).cumprod()
            rolling_max = cumulative_returns.expanding().max()
            drawdowns = cumulative_returns/rolling_max - 1
            max_drawdown = drawdowns.min()
            
            # Calculate win rate
            winning_trades = df[df['strategy_returns'] > 0]['strategy_returns'].count()
            total_trades = df[df['strategy_returns'] != 0]['strategy_returns'].count()
            win_rate = winning_trades / total_trades if total_trades > 0 else 0
            
            # Prepare results
            results = {
                'strategy_type': self.strategy_type,
                'symbol': self.symbol,
                'timeframe': self.timeframe,
                'initial_capital': self.initial_capital,
                'final_capital': self.initial_capital * (1 + total_returns),
                'total_return': total_returns * 100,
                'annual_return': annual_returns * 100,
                'sharpe_ratio': sharpe_ratio,
                'max_drawdown': max_drawdown * 100,
                'win_rate': win_rate * 100,
                'total_trades': total_trades,
                'test_period': {
                    'start': df['timestamp'].iloc[0].strftime('%Y-%m-%d %H:%M:%S'),
                    'end': df['timestamp'].iloc[-1].strftime('%Y-%m-%d %H:%M:%S')
                }
            }
            
            return str(results)
            
        except Exception as e:
            return f"Error during backtesting: {str(e)}"

if __name__ == "__main__":
    # Test the tool
    tool = BacktestingTool(
        symbol="BTC/USDT",
        timeframe="1h",
        strategy_type="MA_Crossover",
        initial_capital=100.0,
        position_size=0.02
    )
    print(tool.run()) 