from agency_swarm.tools import BaseTool
from pydantic import Field
import os
from dotenv import load_dotenv
import ccxt.async_support as ccxt
import pandas as pd
import numpy as np
from typing import Optional, Dict, Any
import asyncio
import aiohttp
import json
from datetime import datetime, timedelta
import logging

load_dotenv()

class MarketAnalysisTool(BaseTool):
    """
    Asynchronous tool for analyzing cryptocurrency market data.
    Provides analysis of price action, volume, and technical indicators.
    """
    
    symbol: str = Field(
        default="BTC/USD",
        description="Trading pair symbol to analyze"
    )
    
    timeframe: str = Field(
        default="1h",
        description="Timeframe for analysis (e.g., '1m', '5m', '1h', '1d')"
    )
    
    lookback_periods: int = Field(
        default=100,
        description="Number of periods to look back for analysis"
    )
    
    exchange_id: str = Field(
        default="binance",
        description="Exchange ID to fetch data from"
    )

    def __init__(self, **data):
        super().__init__(**data)
        self.exchange = getattr(ccxt, self.exchange_id)({
            'apiKey': os.getenv(f'{self.exchange_id.upper()}_API_KEY'),
            'secret': os.getenv(f'{self.exchange_id.upper()}_SECRET'),
            'enableRateLimit': True,
        })
        
        # Setup logging
        log_dir = "agency_divisions/analysis/logs/market_analysis"
        os.makedirs(log_dir, exist_ok=True)
        logging.basicConfig(
            filename=f"{log_dir}/market_analysis.log",
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger('MarketAnalysisTool')

    async def run(self) -> Dict[str, Any]:
        """
        Executes market analysis asynchronously
        """
        try:
            # Fetch OHLCV data
            ohlcv = await self._fetch_ohlcv()
            
            if ohlcv is None or len(ohlcv) < self.lookback_periods:
                raise ValueError("Insufficient data for analysis")
            
            # Convert to DataFrame
            df = pd.DataFrame(
                ohlcv,
                columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
            )
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            # Calculate indicators
            indicators = await self._calculate_indicators(df)
            
            # Generate analysis
            analysis = await self._generate_analysis(df, indicators)
            
            # Cache results
            await self._cache_results(analysis)
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"Error in market analysis: {str(e)}")
            raise
        
        finally:
            await self.exchange.close()

    async def _fetch_ohlcv(self) -> Optional[list]:
        """Fetches OHLCV data from the exchange"""
        try:
            ohlcv = await self.exchange.fetch_ohlcv(
                symbol=self.symbol,
                timeframe=self.timeframe,
                limit=self.lookback_periods
            )
            return ohlcv
            
        except Exception as e:
            self.logger.error(f"Error fetching OHLCV data: {str(e)}")
            raise

    async def _calculate_indicators(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Calculates technical indicators asynchronously"""
        try:
            # Simple Moving Averages
            df['sma_20'] = df['close'].rolling(window=20).mean()
            df['sma_50'] = df['close'].rolling(window=50).mean()
            
            # Exponential Moving Averages
            df['ema_12'] = df['close'].ewm(span=12, adjust=False).mean()
            df['ema_26'] = df['close'].ewm(span=26, adjust=False).mean()
            
            # MACD
            df['macd'] = df['ema_12'] - df['ema_26']
            df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
            df['macd_hist'] = df['macd'] - df['macd_signal']
            
            # RSI
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            df['rsi'] = 100 - (100 / (1 + rs))
            
            # Bollinger Bands
            df['bb_middle'] = df['close'].rolling(window=20).mean()
            bb_std = df['close'].rolling(window=20).std()
            df['bb_upper'] = df['bb_middle'] + (bb_std * 2)
            df['bb_lower'] = df['bb_middle'] - (bb_std * 2)
            
            # Volume analysis
            df['volume_sma'] = df['volume'].rolling(window=20).mean()
            df['volume_ratio'] = df['volume'] / df['volume_sma']
            
            return {
                'last_close': df['close'].iloc[-1],
                'sma_20': df['sma_20'].iloc[-1],
                'sma_50': df['sma_50'].iloc[-1],
                'macd': df['macd'].iloc[-1],
                'macd_signal': df['macd_signal'].iloc[-1],
                'macd_hist': df['macd_hist'].iloc[-1],
                'rsi': df['rsi'].iloc[-1],
                'bb_upper': df['bb_upper'].iloc[-1],
                'bb_middle': df['bb_middle'].iloc[-1],
                'bb_lower': df['bb_lower'].iloc[-1],
                'volume_ratio': df['volume_ratio'].iloc[-1]
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating indicators: {str(e)}")
            raise

    async def _generate_analysis(self, df: pd.DataFrame, indicators: Dict[str, Any]) -> Dict[str, Any]:
        """Generates market analysis report asynchronously"""
        try:
            # Trend Analysis
            trend = "neutral"
            if (indicators['sma_20'] > indicators['sma_50']):
                trend = "bullish"
            elif (indicators['sma_20'] < indicators['sma_50']):
                trend = "bearish"
            
            # RSI Analysis
            rsi_signal = "neutral"
            if indicators['rsi'] > 70:
                rsi_signal = "overbought"
            elif indicators['rsi'] < 30:
                rsi_signal = "oversold"
            
            # MACD Analysis
            macd_signal = "neutral"
            if (indicators['macd'] > indicators['macd_signal']):
                macd_signal = "bullish"
            elif (indicators['macd'] < indicators['macd_signal']):
                macd_signal = "bearish"
            
            # Bollinger Bands Analysis
            bb_signal = "neutral"
            if df['close'].iloc[-1] > indicators['bb_upper']:
                bb_signal = "overbought"
            elif df['close'].iloc[-1] < indicators['bb_lower']:
                bb_signal = "oversold"
            
            # Volume Analysis
            volume_signal = "normal"
            if indicators['volume_ratio'] > 1.5:
                volume_signal = "high"
            elif indicators['volume_ratio'] < 0.5:
                volume_signal = "low"
            
            return {
                'timestamp': datetime.now().isoformat(),
                'symbol': self.symbol,
                'timeframe': self.timeframe,
                'price_action': {
                    'last_close': indicators['last_close'],
                    'trend': trend,
                    'sma_20': indicators['sma_20'],
                    'sma_50': indicators['sma_50']
                },
                'technical_indicators': {
                    'rsi': {
                        'value': indicators['rsi'],
                        'signal': rsi_signal
                    },
                    'macd': {
                        'value': indicators['macd'],
                        'signal': macd_signal,
                        'histogram': indicators['macd_hist']
                    },
                    'bollinger_bands': {
                        'upper': indicators['bb_upper'],
                        'middle': indicators['bb_middle'],
                        'lower': indicators['bb_lower'],
                        'signal': bb_signal
                    }
                },
                'volume_analysis': {
                    'ratio': indicators['volume_ratio'],
                    'signal': volume_signal
                },
                'summary': {
                    'trend': trend,
                    'signals': {
                        'rsi': rsi_signal,
                        'macd': macd_signal,
                        'bollinger': bb_signal,
                        'volume': volume_signal
                    }
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error generating analysis: {str(e)}")
            raise

    async def _cache_results(self, analysis: Dict[str, Any]):
        """Caches analysis results asynchronously"""
        try:
            cache_dir = "agency_divisions/analysis/data/market_analysis_cache"
            os.makedirs(cache_dir, exist_ok=True)
            
            cache_file = f"{cache_dir}/{self.symbol.replace('/', '_')}_{self.timeframe}.json"
            
            async with aiofiles.open(cache_file, 'w') as f:
                await f.write(json.dumps(analysis, indent=2))
                
        except Exception as e:
            self.logger.error(f"Error caching results: {str(e)}")
            # Don't raise here as this is not critical for the analysis

if __name__ == "__main__":
    async def test_market_analysis():
        tool = MarketAnalysisTool(
            symbol="BTC/USDT",
            timeframe="1h",
            lookback_periods=100,
            exchange_id="binance"
        )
        
        try:
            analysis = await tool.run()
            print(json.dumps(analysis, indent=2))
            
        except Exception as e:
            print(f"Error running market analysis: {str(e)}")
    
    asyncio.run(test_market_analysis()) 