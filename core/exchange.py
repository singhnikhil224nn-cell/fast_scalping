import ccxt.async_support as ccxt
import pandas as pd
from loguru import logger
from config.settings import settings

class BinanceClient:
    def __init__(self):
        # Configuration setup
        config = {
            'enableRateLimit': True,
            'options': {'defaultType': 'future'}
        }
        
        # Only inject keys if they are actually filled in inside your .env file
        if settings.BINANCE_API_KEY and settings.BINANCE_SECRET_KEY:
            config['apiKey'] = settings.BINANCE_API_KEY
            config['secret'] = settings.BINANCE_SECRET_KEY
            logger.info("Initializing Binance client with authenticated private credentials.")
        else:
            logger.warning("No API credentials detected. Initializing client in PUBLIC streaming mode.")
            
        self.exchange = ccxt.binance(config)

    async def fetch_ohlcv(self, symbol: str = "ETH/USDT", timeframe: str = "1h", limit: int = 500) -> pd.DataFrame:
        """Fetches public historical candles without requiring an account signature."""
        try:
            # Public method - works flawlessly globally without keys
            ohlcv = await self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            # Local fallback simulations for order flow engine components
            df['OI'] = df['volume'] * 1.5 
            df['funding_rate'] = 0.0001 

            return df
        except Exception as e:
            logger.error(f"Error fetching public data streams from Binance endpoints: {e}")
            raise
        finally:
            await self.exchange.close()
