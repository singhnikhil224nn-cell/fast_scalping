import sys
import os
import asyncio
import ccxt.async_support as ccxt
import pandas as pd
import numpy as np
from loguru import logger

# Set root directory for clean workspace package indexing
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.pipeline import DataPipeline
from strategies.mean_reversion import MeanReversionStrategy
from strategies.breakout import BreakoutStrategy

async def run_historical_backtest():
    logger.info("Initializing Quantitative Backtest Engine with Trailing Stops...")
    exchange = ccxt.binance({'enableRateLimit': True, 'options': {'defaultType': 'future'}})
    pipeline = DataPipeline()
    mean_rev = MeanReversionStrategy()
    breakout = BreakoutStrategy()
    
    try:
        logger.info("Downloading deep historical data bars from Binance...")
        ohlcv = await exchange.fetch_ohlcv("ETH/USDT", timeframe="1h", limit=500)
        
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        df['OI'] = df['volume'] * 1.5
        df['funding_rate'] = 0.0001
        
        # 1. Process Core Data Indicators
        df = pipeline.process_data(df)
        
        # 2. Extract Base Strategy Signals
        df = mean_rev.generate_signals(df)
        df.rename(columns={'strategy_signal': 'mean_rev_sig'}, inplace=True)
        
        df = breakout.generate_signals(df)
        df.rename(columns={'strategy_signal': 'breakout_sig'}, inplace=True)
        
        # 3. Apply Multi-Regime Signal Matrix
        df['base_signal'] = 0
        df.loc[df['ADX_14'] < 25, 'base_signal'] = df['mean_rev_sig']
        df.loc[df['ADX_14'] >= 25, 'base_signal'] = df['breakout_sig']
        
        # 4. Process Trailing Risk Management Logic
        df['final_signal'] = df['base_signal']
        highest_price = df['close'].cummax()
        lowest_price = df['close'].cummin()
        atr_buffer = df['ATR_14'] * 2.0
        
        # Dynamic Risk Boundaries
        df['long_stop'] = highest_price - atr_buffer
        df['short_stop'] = lowest_low = lowest_price + atr_buffer
        
        # Trailing Exit Triggers (Forces signal to neutral if hit)
        long_stopped = (df['base_signal'].shift(1) == 1) & (df['close'] < df['long_stop'].shift(1))
        short_stopped = (df['base_signal'].shift(1) == -1) & (df['close'] > df['short_stop'].shift(1))
        
        df.loc[long_stopped | short_stopped, 'final_signal'] = 0
        
        # 5. Compute Returns Portfolio Accounting
        df['market_returns'] = df['close'].pct_change()
        df['strategy_returns'] = df['final_signal'].shift(1) * df['market_returns']
        
        df['cum_market_returns'] = (1 + df['market_returns'].fillna(0)).cumprod() - 1
        df['cum_strategy_returns'] = (1 + df['strategy_returns'].fillna(0)).cumprod() - 1
        
        final_market_perf = df['cum_market_returns'].iloc[-1] * 100
        final_strat_perf = df['cum_strategy_returns'].iloc[-1] * 100
        total_trades = df['final_signal'].diff().abs().sum() / 2
        
        print("\n" + "="*50)
        print("📊 TRAILING RISK BACKTEST PERFORMANCE REPORT")
        print("="*50)
        print(f"Total Rebalancing Trades Executed : {total_trades:.0f}")
        print(f"Buy & Hold Market Performance     : {final_market_perf:.2f}%")
        print(f"Multi-Regime Strategy (Trailing)  : {final_strat_perf:.2f}%")
        print(f"Net Alpha Over Market Asset       : {final_strat_perf - final_market_perf:.2f}%")
        print("="*50 + "\n")
        
    except Exception as e:
        logger.error(f"Trailing backtest execution failed: {e}")
    finally:
        await exchange.close()

if __name__ == "__main__":
    asyncio.run(run_historical_backtest())
