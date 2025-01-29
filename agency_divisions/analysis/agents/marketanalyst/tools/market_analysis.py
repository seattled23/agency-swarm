from agency_swarm.tools import BaseTool
from pydantic import Field
import os
from dotenv import load_dotenv
import ccxt
import pandas as pd
from datetime import datetime, timedelta

load_dotenv()

class MarketAnalysisTool(BaseTool):
    """
    Tool for analyzing cryptocurrency market data, including price action, volume, and technical indicators.
    Provides comprehensive market analysis across multiple timeframes.
    """
    symbol: str = Field(
        ..., description="Trading pair symbol (e.g., 'BTC/USDT')"
    )
    timeframe: str = Field(
        ..., description="Analysis timeframe (e.g., '1h', '4h', '1d')"
    )
    lookback_periods: int = Field(
        100, description="Number of periods to analyze"
    )
    exchange_id: str = Field(
        "binance", description="Exchange ID (default: 'binance')"
    )

    def run(self):
        """
        Performs market analysis for the specified trading pair and timeframe.
        """
        try:
            # Initialize exchange
            exchange_class = getattr(ccxt, self.exchange_id)
            exchange = exchange_class({
                'enableRateLimit': True,
            })
            
            # Fetch OHLCV data
            ohlcv = exchange.fetch_ohlcv(
                symbol=self.symbol,
                timeframe=self.timeframe,
                limit=self.lookback_periods
            )
            
            # Convert to DataFrame
            df = pd.DataFrame(
                ohlcv,
                columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
            )
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            # Calculate basic indicators
            df = self._calculate_indicators(df)
            
            # Generate analysis
            analysis = self._generate_analysis(df)
            
            return analysis
            
        except Exception as e:
            return f"Error performing market analysis: {str(e)}"

    def _calculate_indicators(self, df):
        """Calculates technical indicators"""
        # SMA
        df['sma_20'] = df['close'].rolling(window=20).mean()
        df['sma_50'] = df['close'].rolling(window=50).mean()
        
        # EMA
        df['ema_20'] = df['close'].ewm(span=20, adjust=False).mean()
        
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # MACD
        exp1 = df['close'].ewm(span=12, adjust=False).mean()
        exp2 = df['close'].ewm(span=26, adjust=False).mean()
        df['macd'] = exp1 - exp2
        df['signal'] = df['macd'].ewm(span=9, adjust=False).mean()
        
        # Bollinger Bands
        df['bb_middle'] = df['close'].rolling(window=20).mean()
        df['bb_upper'] = df['bb_middle'] + 2 * df['close'].rolling(window=20).std()
        df['bb_lower'] = df['bb_middle'] - 2 * df['close'].rolling(window=20).std()
        
        return df

    def _generate_analysis(self, df):
        """Generates market analysis report"""
        latest = df.iloc[-1]
        prev = df.iloc[-2]
        
        # Price action analysis
        price_change = ((latest['close'] - prev['close']) / prev['close']) * 100
        
        # Trend analysis
        trend = "Uptrend" if latest['close'] > latest['sma_20'] > latest['sma_50'] else \
               "Downtrend" if latest['close'] < latest['sma_20'] < latest['sma_50'] else \
               "Sideways"
        
        # RSI analysis
        rsi_condition = "Overbought" if latest['rsi'] > 70 else \
                       "Oversold" if latest['rsi'] < 30 else \
                       "Neutral"
        
        # MACD analysis
        macd_signal = "Bullish" if latest['macd'] > latest['signal'] else "Bearish"
        
        # Bollinger Bands analysis
        bb_position = "Upper Band Test" if latest['close'] >= latest['bb_upper'] else \
                     "Lower Band Test" if latest['close'] <= latest['bb_lower'] else \
                     "Middle Band"
        
        # Volume analysis
        avg_volume = df['volume'].mean()
        vol_condition = "High" if latest['volume'] > avg_volume * 1.5 else \
                       "Low" if latest['volume'] < avg_volume * 0.5 else \
                       "Normal"
        
        analysis = f"""# Market Analysis Report for {self.symbol}
        
## Price Action
- Current Price: {latest['close']:.2f}
- Price Change: {price_change:.2f}%
- Volume Condition: {vol_condition}

## Technical Analysis
- Trend: {trend}
- RSI ({latest['rsi']:.2f}): {rsi_condition}
- MACD Signal: {macd_signal}
- Bollinger Bands: {bb_position}

## Key Levels
- SMA 20: {latest['sma_20']:.2f}
- SMA 50: {latest['sma_50']:.2f}
- BB Upper: {latest['bb_upper']:.2f}
- BB Lower: {latest['bb_lower']:.2f}

## Summary
The market is currently in a {trend.lower()} with {rsi_condition.lower()} RSI conditions.
MACD indicates a {macd_signal.lower()} momentum.
Volume is {vol_condition.lower()} compared to average.
"""
        
        return analysis

if __name__ == "__main__":
    # Test the tool
    tool = MarketAnalysisTool(
        symbol="BTC/USDT",
        timeframe="1h",
        lookback_periods=100
    )
    print(tool.run()) 