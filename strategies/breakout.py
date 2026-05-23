import pandas as pd
import numpy as np

class BreakoutStrategy:
    def __init__(self, channel_period: int = 20, volume_ma_period: int = 20):
        self.channel_period = channel_period
        self.volume_ma_period = volume_ma_period

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df_out = df.copy()
        df_out['strategy_signal'] = 0
        adx_val = df_out.get('ADX_14', 0)

        # 1. Channels & Volume MA
        df_out['ub'] = df_out['high'].shift(1).rolling(window=self.channel_period).max()
        df_out['lb'] = df_out['low'].shift(1).rolling(window=self.channel_period).min()
        df_out['v_ma'] = df_out['volume'].rolling(window=self.volume_ma_period).mean()

        # 2. Assign Conditions
        long_cond = (df_out['close'] > df_out['ub']) & (df_out['volume'] > df_out['v_ma'] * 1.3) & (adx_val > 25)
        short_cond = (df_out['close'] < df_out['lb']) & (df_out['volume'] > df_out['v_ma'] * 1.3) & (adx_val > 25)

        # 3. Apply Flags
        df_out.loc[long_cond, 'strategy_signal'] = 1
        df_out.loc[short_cond, 'strategy_signal'] = -1

        return df_out
