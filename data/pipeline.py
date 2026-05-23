import pandas as pd
import numpy as np

class DataPipeline:
    def __init__(self):
        pass

    def process_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Processes raw vectors into a multi-timeframe indicator matrix.
        """
        processed_df = df.copy()

        # 1. Exponential Moving Averages (Trend Filters)
        processed_df['EMA_9'] = processed_df['close'].ewm(span=9, adjust=False).mean()
        processed_df['EMA_21'] = processed_df['close'].ewm(span=21, adjust=False).mean()

        # 2. Average True Range (Volatility Tracking)
        high_low = processed_df['high'] - processed_df['low']
        high_close = np.abs(processed_df['high'] - processed_df['close'].shift(1))
        low_close = np.abs(processed_df['low'] - processed_df['close'].shift(1))
        
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        processed_df['ATR_14'] = tr.rolling(window=14).mean()

        # 3. Average Directional Index (Regime Strengths)
        # Natively calculated without external ta dependencies for 0ms execution
        upmove = processed_df['high'].diff()
        downmove = processed_df['low'].diff()
        
        plus_dm = np.where((upmove > downmove) & (upmove > 0), upmove, 0)
        minus_dm = np.where((downmove > upmove) & (downmove > 0), downmove, 0)
        
        rs_tr = tr.rolling(window=14).sum()
        rs_pdm = pd.Series(plus_dm, index=df.index).rolling(window=14).sum()
        rs_mdm = pd.Series(minus_dm, index=df.index).rolling(window=14).sum()
        
        plus_di = 100 * (rs_pdm / (rs_tr + 1e-10))
        minus_di = 100 * (rs_mdm / (rs_tr + 1e-10))
        
        dx = 100 * np.abs(plus_di - minus_di) / (plus_di + minus_di + 1e-10)
        processed_df['ADX_14'] = pd.Series(dx).rolling(window=14).mean()

        return processed_df

    def calculate_trailing_stops(self, df: pd.DataFrame, direction: str, atr_multiplier: float = 2.0) -> pd.Series:
        """
        Dynamically adjusts risk tracking strings based on past high watermarks.
        """
        close_series = df['close']
        atr_series = df.get('ATR_14', close_series * 0.02)
        trailing_stop = pd.Series(index=df.index, dtype=float)
        
        if direction == "LONG":
            highest_high = close_series.cummax()
            trailing_stop = highest_high - (atr_series * atr_multiplier)
        elif direction == "SHORT":
            lowest_low = close_series.cummin()
            trailing_stop = lowest_low + (atr_series * atr_multiplier)
            
        return trailing_stop
