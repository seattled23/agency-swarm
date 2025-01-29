from agency_swarm.tools import BaseTool
from pydantic import Field
import os
from dotenv import load_dotenv
import pandas as pd
import numpy as np
from datetime import datetime
import ccxt
import ta
import joblib
import asyncio
import websockets
import json
from collections import deque
import tensorflow as tf

load_dotenv()

class RealtimeAnalysisTool(BaseTool):
    """
    A tool for real-time analysis of cryptocurrency market data using pre-trained models.
    Processes streaming data and provides live predictions and alerts.
    """
    
    symbol: str = Field(
        ..., description="Trading pair symbol (e.g., 'BTC/USDT')"
    )
    timeframe: str = Field(
        ..., description="Analysis timeframe (e.g., '1m', '5m', '15m')"
    )
    buffer_size: int = Field(
        default=100, description="Number of recent data points to keep in memory"
    )
    alert_threshold: float = Field(
        default=0.02, description="Price movement threshold for alerts (e.g., 0.02 for 2%)"
    )

    async def process_realtime_data(self):
        """
        Process real-time market data and generate predictions.
        """
        try:
            # Load pre-trained models
            lstm_model = tf.keras.models.load_model('models/lstm_model.h5')
            rf_model = joblib.load('models/rf_model.joblib')
            gb_model = joblib.load('models/gb_model.joblib')
            scaler = joblib.load('models/scaler.joblib')
            
            # Initialize data buffer
            price_buffer = deque(maxlen=self.buffer_size)
            volume_buffer = deque(maxlen=self.buffer_size)
            
            # Initialize exchange and websocket connection
            exchange = ccxt.binance()
            ws_url = f"wss://stream.binance.com:9443/ws/{self.symbol.lower().replace('/', '')}@kline_{self.timeframe}"
            
            async with websockets.connect(ws_url) as websocket:
                while True:
                    try:
                        message = await websocket.recv()
                        data = json.loads(message)
                        
                        if 'k' in data:
                            kline = data['k']
                            
                            # Extract current candle data
                            current_price = float(kline['c'])
                            current_volume = float(kline['v'])
                            
                            # Update buffers
                            price_buffer.append(current_price)
                            volume_buffer.append(current_volume)
                            
                            if len(price_buffer) >= self.buffer_size:
                                # Prepare features
                                df = pd.DataFrame({
                                    'close': list(price_buffer),
                                    'volume': list(volume_buffer)
                                })
                                
                                # Add technical indicators
                                df['sma_20'] = ta.trend.sma_indicator(df['close'], window=20)
                                df['rsi'] = ta.momentum.rsi(df['close'])
                                df['macd'] = ta.trend.macd_diff(df['close'])
                                df['bb_high'] = ta.volatility.bollinger_hband(df['close'])
                                df['bb_low'] = ta.volatility.bollinger_lband(df['close'])
                                df['obv'] = ta.volume.on_balance_volume(df['close'], df['volume'])
                                
                                # Price changes and ratios
                                df['price_change'] = df['close'].pct_change()
                                df['volume_change'] = df['volume'].pct_change()
                                
                                # Scale features
                                features = df.iloc[-1:].values
                                scaled_features = scaler.transform(features)
                                
                                # Generate predictions
                                lstm_pred = lstm_model.predict(
                                    scaled_features.reshape(1, 1, -1),
                                    verbose=0
                                )
                                rf_pred = rf_model.predict(scaled_features)
                                gb_pred = gb_model.predict(scaled_features)
                                
                                # Weighted ensemble prediction
                                weights = {'LSTM': 0.4, 'RF': 0.3, 'GB': 0.3}
                                ensemble_pred = (
                                    lstm_pred[0] * weights['LSTM'] +
                                    rf_pred[0] * weights['RF'] +
                                    gb_pred[0] * weights['GB']
                                )
                                
                                # Calculate price movement
                                price_movement = (current_price - list(price_buffer)[-2]) / list(price_buffer)[-2]
                                
                                # Generate analysis results
                                analysis = {
                                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                    'symbol': self.symbol,
                                    'current_price': current_price,
                                    'price_movement': price_movement,
                                    'predictions': {
                                        'ensemble': float(ensemble_pred),
                                        'lstm': float(lstm_pred[0]),
                                        'random_forest': float(rf_pred[0]),
                                        'gradient_boosting': float(gb_pred[0])
                                    },
                                    'technical_indicators': {
                                        'rsi': float(df['rsi'].iloc[-1]),
                                        'macd': float(df['macd'].iloc[-1]),
                                        'sma_20': float(df['sma_20'].iloc[-1])
                                    },
                                    'alerts': []
                                }
                                
                                # Generate alerts
                                if abs(price_movement) >= self.alert_threshold:
                                    analysis['alerts'].append({
                                        'type': 'price_movement',
                                        'message': f"Significant price movement detected: {price_movement:.2%}"
                                    })
                                
                                if analysis['technical_indicators']['rsi'] > 70:
                                    analysis['alerts'].append({
                                        'type': 'overbought',
                                        'message': "RSI indicates overbought conditions"
                                    })
                                elif analysis['technical_indicators']['rsi'] < 30:
                                    analysis['alerts'].append({
                                        'type': 'oversold',
                                        'message': "RSI indicates oversold conditions"
                                    })
                                
                                return str(analysis)
                            
                    except Exception as e:
                        return f"Error processing real-time data: {str(e)}"
                        
        except Exception as e:
            return f"Error initializing real-time analysis: {str(e)}"

    def run(self):
        """
        Run the real-time analysis pipeline.
        """
        try:
            return asyncio.run(self.process_realtime_data())
        except Exception as e:
            return f"Error in real-time analysis: {str(e)}"

if __name__ == "__main__":
    # Test the tool
    tool = RealtimeAnalysisTool(
        symbol="BTC/USDT",
        timeframe="1m",
        buffer_size=100,
        alert_threshold=0.02
    )
    print(tool.run()) 