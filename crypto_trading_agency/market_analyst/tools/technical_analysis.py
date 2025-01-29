from agency_swarm.tools import BaseTool
from pydantic import Field
import os
from dotenv import load_dotenv
import pandas as pd
import numpy as np
import ccxt
import ta

load_dotenv()

class TechnicalAnalysisTool(BaseTool):
    """
    A tool for performing technical analysis on cryptocurrency price data.
    Uses various technical indicators to analyze market conditions and identify potential trading opportunities.
    """
    
    symbol: str = Field(
        ..., description="Trading pair symbol (e.g., 'BTC/USDT')"
    )
    timeframe: str = Field(
        ..., description="Analysis timeframe (e.g., '1h', '4h', '1d')"
    )
    limit: int = Field(
        default=100, description="Number of candles to analyze"
    )

    def run(self):
        """
        Performs technical analysis on the specified trading pair and timeframe.
        Returns a comprehensive analysis including various technical indicators.
        """
        try:
            # Initialize exchange (using Binance as default)
            exchange = ccxt.binance()
            
            # Fetch OHLCV data
            ohlcv = exchange.fetch_ohlcv(
                symbol=self.symbol,
                timeframe=self.timeframe,
                limit=self.limit
            )
            
            # Convert to DataFrame
            df = pd.DataFrame(
                ohlcv,
                columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
            )
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            # Calculate technical indicators
            # Trend Indicators
            df['sma_20'] = ta.trend.sma_indicator(df['close'], window=20)
            df['ema_20'] = ta.trend.ema_indicator(df['close'], window=20)
            df['macd'] = ta.trend.macd_diff(df['close'])
            
            # Momentum Indicators
            df['rsi'] = ta.momentum.rsi(df['close'])
            df['stoch'] = ta.momentum.stoch(df['high'], df['low'], df['close'])
            
            # Volatility Indicators
            df['bb_high'] = ta.volatility.bollinger_hband(df['close'])
            df['bb_low'] = ta.volatility.bollinger_lband(df['close'])
            
            # Volume Indicators
            df['obv'] = ta.volume.on_balance_volume(df['close'], df['volume'])
            
            # Get latest values
            latest = df.iloc[-1]
            
            # Prepare analysis
            analysis = {
                'symbol': self.symbol,
                'timeframe': self.timeframe,
                'timestamp': latest['timestamp'].strftime('%Y-%m-%d %H:%M:%S'),
                'price': latest['close'],
                'indicators': {
                    'trend': {
                        'sma_20': latest['sma_20'],
                        'ema_20': latest['ema_20'],
                        'macd': latest['macd'],
                        'trend_direction': 'bullish' if latest['close'] > latest['sma_20'] else 'bearish'
                    },
                    'momentum': {
                        'rsi': latest['rsi'],
                        'stochastic': latest['stoch'],
                        'momentum_signal': 'overbought' if latest['rsi'] > 70 else 'oversold' if latest['rsi'] < 30 else 'neutral'
                    },
                    'volatility': {
                        'bb_high': latest['bb_high'],
                        'bb_low': latest['bb_low'],
                        'bb_position': (latest['close'] - latest['bb_low']) / (latest['bb_high'] - latest['bb_low'])
                    },
                    'volume': {
                        'current_volume': latest['volume'],
                        'obv': latest['obv']
                    }
                }
            }
            
            return str(analysis)
            
        except Exception as e:
            return f"Error performing technical analysis: {str(e)}"

if __name__ == "__main__":
    # Test the tool
    tool = TechnicalAnalysisTool(
        symbol="BTC/USDT",
        timeframe="1h"
    )
    print(tool.run()) 