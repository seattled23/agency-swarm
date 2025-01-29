from agency_swarm.tools import BaseTool
from pydantic import Field
import os
from dotenv import load_dotenv
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import ccxt
import ta
from sklearn.preprocessing import MinMaxScaler
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout
from tensorflow.keras.optimizers import Adam
import joblib
import asyncio
import aiohttp
from concurrent.futures import ThreadPoolExecutor
import warnings
warnings.filterwarnings('ignore')

load_dotenv()

class MLAnalysisTool(BaseTool):
    """
    A tool for analyzing cryptocurrency market data using multiple machine learning models.
    Combines different ML approaches for price prediction and pattern recognition.
    """
    
    symbol: str = Field(
        ..., description="Trading pair symbol (e.g., 'BTC/USDT')"
    )
    timeframe: str = Field(
        ..., description="Analysis timeframe (e.g., '1h', '4h', '1d')"
    )
    prediction_horizon: int = Field(
        default=24, description="Number of periods to forecast ahead"
    )
    training_period: int = Field(
        default=1000, description="Number of historical periods to use for training"
    )

    def prepare_data(self, df):
        """
        Prepare data for machine learning models by adding features and handling missing values.
        """
        # Technical indicators as features
        df['sma_20'] = ta.trend.sma_indicator(df['close'], window=20)
        df['sma_50'] = ta.trend.sma_indicator(df['close'], window=50)
        df['rsi'] = ta.momentum.rsi(df['close'])
        df['macd'] = ta.trend.macd_diff(df['close'])
        df['bb_high'] = ta.volatility.bollinger_hband(df['close'])
        df['bb_low'] = ta.volatility.bollinger_lband(df['close'])
        df['atr'] = ta.volatility.average_true_range(df['high'], df['low'], df['close'])
        df['obv'] = ta.volume.on_balance_volume(df['close'], df['volume'])
        
        # Price changes and ratios
        df['price_change'] = df['close'].pct_change()
        df['volume_change'] = df['volume'].pct_change()
        df['high_low_ratio'] = df['high'] / df['low']
        
        # Lagged features
        for i in [1, 2, 3, 5, 8, 13]:
            df[f'close_lag_{i}'] = df['close'].shift(i)
            df[f'volume_lag_{i}'] = df['volume'].shift(i)
        
        # Rolling statistics
        df['rolling_mean'] = df['close'].rolling(window=20).mean()
        df['rolling_std'] = df['close'].rolling(window=20).std()
        df['rolling_volume'] = df['volume'].rolling(window=20).mean()
        
        # Target variable (future returns)
        df['target'] = df['close'].shift(-self.prediction_horizon).pct_change(self.prediction_horizon)
        
        # Drop missing values
        df.dropna(inplace=True)
        
        return df

    async def fetch_market_data(self):
        """
        Asynchronously fetch market data from exchange.
        """
        exchange = ccxt.binance()
        ohlcv = await exchange.fetch_ohlcv_async(
            symbol=self.symbol,
            timeframe=self.timeframe,
            limit=self.training_period
        )
        
        df = pd.DataFrame(
            ohlcv,
            columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
        )
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        return df

    def train_lstm_model(self, X_train, y_train, X_val, y_val):
        """
        Train an LSTM model for sequence prediction.
        """
        model = Sequential([
            LSTM(100, return_sequences=True, input_shape=(X_train.shape[1], X_train.shape[2])),
            Dropout(0.2),
            LSTM(50, return_sequences=False),
            Dropout(0.2),
            Dense(25),
            Dense(1)
        ])
        
        model.compile(optimizer=Adam(learning_rate=0.001), loss='mse')
        model.fit(
            X_train, y_train,
            validation_data=(X_val, y_val),
            epochs=50,
            batch_size=32,
            verbose=0
        )
        return model

    def train_ensemble_models(self, X_train, y_train):
        """
        Train ensemble models (Random Forest and Gradient Boosting).
        """
        models = {
            'rf': RandomForestRegressor(
                n_estimators=100,
                max_depth=10,
                n_jobs=-1,
                random_state=42
            ),
            'gb': GradientBoostingRegressor(
                n_estimators=100,
                max_depth=5,
                random_state=42
            )
        }
        
        for name, model in models.items():
            model.fit(X_train, y_train)
            
        return models

    def run(self):
        """
        Run the machine learning analysis pipeline.
        """
        try:
            # Fetch and prepare data
            df = asyncio.run(self.fetch_market_data())
            df = self.prepare_data(df)
            
            # Prepare features and target
            feature_columns = [col for col in df.columns if col not in ['timestamp', 'target']]
            X = df[feature_columns].values
            y = df['target'].values
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, shuffle=False
            )
            
            # Scale data
            scaler = MinMaxScaler()
            X_train_scaled = scaler.fit_transform(X_train)
            X_test_scaled = scaler.transform(X_test)
            
            # Prepare LSTM data
            def create_sequences(X, y, sequence_length=10):
                X_seq, y_seq = [], []
                for i in range(len(X) - sequence_length):
                    X_seq.append(X[i:i+sequence_length])
                    y_seq.append(y[i+sequence_length])
                return np.array(X_seq), np.array(y_seq)
            
            X_train_seq, y_train_seq = create_sequences(X_train_scaled, y_train)
            X_test_seq, y_test_seq = create_sequences(X_test_scaled, y_test)
            
            # Train models in parallel
            with ThreadPoolExecutor() as executor:
                # Train LSTM
                lstm_future = executor.submit(
                    self.train_lstm_model,
                    X_train_seq, y_train_seq,
                    X_test_seq, y_test_seq
                )
                
                # Train ensemble models
                ensemble_future = executor.submit(
                    self.train_ensemble_models,
                    X_train_scaled, y_train
                )
                
                lstm_model = lstm_future.result()
                ensemble_models = ensemble_future.result()
            
            # Make predictions
            lstm_pred = lstm_model.predict(X_test_seq)
            rf_pred = ensemble_models['rf'].predict(X_test_scaled)
            gb_pred = ensemble_models['gb'].predict(X_test_scaled)
            
            # Calculate metrics
            from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
            metrics = {}
            for name, pred in [('LSTM', lstm_pred), ('RF', rf_pred), ('GB', gb_pred)]:
                metrics[name] = {
                    'mse': mean_squared_error(y_test, pred),
                    'mae': mean_absolute_error(y_test, pred),
                    'r2': r2_score(y_test, pred)
                }
            
            # Make ensemble prediction for next period
            latest_data = df.iloc[-sequence_length:][feature_columns].values
            latest_scaled = scaler.transform(latest_data)
            
            lstm_next = lstm_model.predict(latest_scaled.reshape(1, sequence_length, -1))
            rf_next = ensemble_models['rf'].predict(latest_scaled[-1].reshape(1, -1))
            gb_next = ensemble_models['gb'].predict(latest_scaled[-1].reshape(1, -1))
            
            # Weighted ensemble prediction
            weights = {
                'LSTM': 0.4,
                'RF': 0.3,
                'GB': 0.3
            }
            
            ensemble_prediction = (
                lstm_next[0] * weights['LSTM'] +
                rf_next[0] * weights['RF'] +
                gb_next[0] * weights['GB']
            )
            
            # Save models for future use
            os.makedirs('models', exist_ok=True)
            lstm_model.save('models/lstm_model.h5')
            joblib.dump(ensemble_models['rf'], 'models/rf_model.joblib')
            joblib.dump(ensemble_models['gb'], 'models/gb_model.joblib')
            joblib.dump(scaler, 'models/scaler.joblib')
            
            # Prepare results
            results = {
                'symbol': self.symbol,
                'timeframe': self.timeframe,
                'prediction_horizon': self.prediction_horizon,
                'model_metrics': metrics,
                'predictions': {
                    'ensemble_prediction': float(ensemble_prediction),
                    'model_predictions': {
                        'lstm': float(lstm_next[0]),
                        'random_forest': float(rf_next[0]),
                        'gradient_boosting': float(gb_next[0])
                    }
                },
                'feature_importance': {
                    'random_forest': dict(zip(
                        feature_columns,
                        ensemble_models['rf'].feature_importances_
                    ))
                },
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            return str(results)
            
        except Exception as e:
            return f"Error performing ML analysis: {str(e)}"

if __name__ == "__main__":
    # Test the tool
    tool = MLAnalysisTool(
        symbol="BTC/USDT",
        timeframe="1h",
        prediction_horizon=24,
        training_period=1000
    )
    print(tool.run()) 