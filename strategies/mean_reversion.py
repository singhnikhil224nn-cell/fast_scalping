import pandas as pd
import numpy as np

class MeanReversionStrategy:
    def __init__(self, rsi_period: int = 14, bb_period: int = 20, bb_std: float = 2.0):
        self.rsi_period = rsi_period
        self.bb_period = bb_period
        self.bb_std = bb_std

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Scans vectors for statistical extremes to trade back toward the mean.
        """
        # Ensure deep copy to protect underlying data stream
        signals_df = df.copy()
        signals_df['strategy_signal'] = 0  # Default: Neutral
        
        # 1. Calculate Bollinger Bands natively if not present
        if 'BBM_20_2.0' not in signals_df.columns:
            sma = signals_df['close'].rolling(window=self.bb_period).mean()
            rstd = signals_df['close'].rolling(window=self.bb_period).std()
            signals_df['BBU'] = sma + (self.bb_std * rstd)
            signals_df['BBL'] = sma - (self.bb_std * rstd)
        else:
            signals_df['BBU'] = signals_df['BBU_20_2.0']
            signals_df['BBL'] = signals_df['BBL_20_2.0']

        # 2. Calculate RSI natively if missing
        if 'RSI_14' not in signals_df.columns:
            delta = signals_df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=self.rsi_period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=self.rsi_period).mean()
            rs = gain / (loss + 1e-10)
            signals_df['RSI'] = 100 - (100 / (1 + rs))
        else:
            signals_df['RSI'] = signals_df['RSI_14']

        # 3. Vectorized Signal Generation (Executes instantly at 0ms latency)
        # LONG: Price crosses BELOW lower Bollinger Band AND RSI is Oversold (< 30)
        long_condition = (signals_df['close'] <= signals_df['BBL']) & (signals_df['RSI'] <= 33)
        
        # SHORT: Price crosses ABOVE upper Bollinger Band AND RSI is Overbought (> 70)
        short_condition = (signals_df['close'] >= signals_df['BBU']) & (signals_df['RSI'] >= 67)

        signals_df.loc[long_condition, 'strategy_signal'] = 1
        signals_df.loc[short_condition, 'strategy_signal'] = -1

        return signals_df
