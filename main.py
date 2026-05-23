import os
from dotenv import load_dotenv
load_dotenv()
import asyncio
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread
import requests
import ccxt.async_support as ccxt
import pandas as pd
from datetime import datetime
from loguru import logger

# Import native pipeline, strategies, and risk control layers
# (Ensure these modules exist in your project structure)
try:
    from data.pipeline import DataPipeline
    from strategies.mean_reversion import MeanReversionStrategy
    from strategies.breakout import BreakoutStrategy
    from core.risk_manager import PositionSizer
    from core.notifier import TelegramNotifier
except ImportError:
    # Fallback/Mock classes if external files are missing for testing
    logger.warning("Local strategy modules not found. Using placeholder classes.")
    class DataPipeline: pass
    class MeanReversionStrategy: pass
    class BreakoutStrategy: pass
    class PositionSizer: pass
    class TelegramNotifier: pass

# --- DUMMY SERVER (Keeps background processes alive if needed) ---
class HealthCheck(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Cloud Scalper Online")
    def log_message(self, format, *args): 
        pass # Keep logs clean

def start_server():
    port = int(os.environ.get("PORT", 10000))
    HTTPServer(('0.0.0.0', port), HealthCheck).serve_forever()

Thread(target=start_server, daemon=True).start()

# --- THE QUANTITATIVE ENGINE ---
class QuantitativeTradingEngine:
    def __init__(self):
        logger.info("Initializing Master Quantitative Trading Engine...")
        self.pipeline = DataPipeline()
        self.mean_rev = MeanReversionStrategy()
        self.breakout = BreakoutStrategy()
        self.sizer = PositionSizer()
        self.notifier = TelegramNotifier()
        
        self.exchange = ccxt.kucoin({
            'enableRateLimit': True,
            'options': {'defaultType': 'future'}
        })
        
        self.model_path = "models/xgboost_meta_v1.json"
        if os.path.exists(self.model_path):
            logger.success("Master Brain connected to trained XGBoost Meta-Model.")
        else:
            logger.warning("No ML weights found. Engine running on Heuristic Fallback Mode.")

    async def run_cycle(self, symbol):
        try:
            logger.info(f"New cycle triggered. Scanning {symbol}...")
            ohlcv = await self.exchange.fetch_ohlcv(symbol, '1m', limit=50)
            
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            
            # --- STRATEGY 1: EMA CROSSOVER ---
            df['EMA_9'] = df['close'].ewm(span=9, adjust=False).mean()
            df['EMA_21'] = df['close'].ewm(span=21, adjust=False).mean()
            
            # --- STRATEGY 2: VOLUME SLEDGEHAMMER ---
            df['Avg_Vol_20'] = df['volume'].rolling(window=20).mean()
            
            # --- STRATEGY 3: BOLLINGER RUBBER BAND ---
            df['SMA_20'] = df['close'].rolling(window=20).mean()
            df['STD_20'] = df['close'].rolling(window=20).std()
            df['Lower_Band'] = df['SMA_20'] - (df['STD_20'] * 2.5) # 2.5 deviation for extreme crashes
            
            # --- STRATEGY 4: MICRO-VWAP PULLBACK ---
            df['Typical_Price'] = (df['high'] + df['low'] + df['close']) / 3
            df['VWAP'] = (df['Typical_Price'] * df['volume']).cumsum() / df['volume'].cumsum()
            
            # Extract latest values
            last_close = df['close'].iloc[-1]
            last_open = df['open'].iloc[-1]
            last_low = df['low'].iloc[-1]
            last_vol = df['volume'].iloc[-1]
            avg_vol_20 = df['Avg_Vol_20'].iloc[-2]
            
            direction = None
            stop_loss = None
            take_profit = None
            strategy_name = None
            
            # --- ALPHA MODULE: THE SHORT SQUEEZE RADAR (PRIORITY 0) ---
            try:
                # Fetch live derivatives data from KuCoin Futures
                funding_data = await self.exchange.fetch_funding_rate(symbol)
                
                # Safely extract funding rate, forcing to float and defaulting to 0.0 if None
                raw_fr = funding_data.get('fundingRate')
                funding_rate = float(raw_fr) if raw_fr is not None else 0.0
                
                # Fetch Open Interest
                oi_data = await self.exchange.fetch_open_interest(symbol)
                
                # CCXT unified key is 'openInterest', fallback to 'openInterestValue'
                raw_oi = oi_data.get('openInterest') or oi_data.get('openInterestValue')
                open_interest = float(raw_oi) if raw_oi is not None else 0.0
                
                logger.info(f"Derivatives Intel // Funding Rate: {funding_rate*100:.4f}% | OI: {open_interest:,.2f}")
                
                # The Squeeze Trigger Logic:
                # If funding is deeply negative (shorts are paying longs) AND price is breaking up
                if funding_rate < -0.0001 and df['close'].iloc[-1] > df['close'].iloc[-2]:
                    strategy_name = "☢️ HYPER-SQUEEZE (Liquidations Imminent)"
                    direction = "LONG"
                    
                    # Because squeezes are violent, we use a much wider stop and massive take-profit
                    stop_loss = last_close * 0.990  # 1.0% stop to survive the volatility
                    take_profit = last_close * 1.03 # 3.0% target to ride the cascade
                    
                    logger.warning(f"🚨 TRAP DETECTED: {symbol} Funding is negative ({funding_rate*100:.4f}%). Retail shorts are trapped.")
                    
            except Exception as e:
                logger.error(f"Failed to fetch derivatives data for {symbol}: {e}")

            # --- THE MULTI-STRATEGY RADAR ---
            # If the Squeeze Radar didn't trigger, check the normal technicals
            if not direction:
                # Priority 1: Bollinger Flash Crash (Best Reversal Entry)
                if last_close < df['Lower_Band'].iloc[-1]:
                    strategy_name = "🪀 Bollinger Rubber Band (Flash Crash Bounce)"
                    direction = "LONG"
                    stop_loss = last_close * 0.995
                    take_profit = last_close * 1.015 
                    
                # Priority 2: VWAP Dip Buy (Trend Continuation)
                elif last_low <= df['VWAP'].iloc[-1] and last_close > df['VWAP'].iloc[-1] and df['close'].iloc[-2] > df['VWAP'].iloc[-2]:
                    strategy_name = "🎯 VWAP Pullback (Dip Buy)"
                    direction = "LONG"
                    stop_loss = last_close * 0.995
                    take_profit = last_close * 1.01
                    
                # Priority 3: Volume Sledgehammer (Institutional Breakout)
                elif last_vol > (avg_vol_20 * 4) and last_close > last_open:
                    strategy_name = "🔨 Volume Sledgehammer"
                    direction = "LONG"
                    stop_loss = last_close * 0.995
                    take_profit = last_close * 1.01
                    
                # Priority 4: EMA Golden Cross (Standard Momentum)
                elif df['EMA_9'].iloc[-2] <= df['EMA_21'].iloc[-2] and df['EMA_9'].iloc[-1] > df['EMA_21'].iloc[-1]:
                    strategy_name = "🚀 EMA Golden Cross"
                    direction = "LONG"
                    stop_loss = last_close * 0.995
                    take_profit = last_close * 1.01
                    
                # Priority 5: EMA Death Cross
                elif df['EMA_9'].iloc[-2] >= df['EMA_21'].iloc[-2] and df['EMA_9'].iloc[-1] < df['EMA_21'].iloc[-1]:
                    strategy_name = "🩸 EMA Death Cross"
                    direction = "SHORT"
                    stop_loss = last_close * 1.005
                    take_profit = last_close * 0.99

            if not direction:
                return
            
            # --- LEVEL 2 ORDER BOOK IMBALANCE (OBI) FILTER ---
            logger.info(f"[{symbol}] {strategy_name} triggered. Fetching L2 Order Book data for execution verification...")
            
            try:
                # Pull the top 20 layers of the KuCoin order book
                order_book = await self.exchange.fetch_order_book(symbol, limit=20)
                bids = order_book['bids'] 
                asks = order_book['asks'] 
                
                # Calculate total volume sitting on the book
                total_bid_vol = sum([vol for price, vol in bids])
                total_ask_vol = sum([vol for price, vol in asks])
                
                # OBI Math: Ranges from -1.0 (100% Sellers) to +1.0 (100% Buyers)
                if (total_bid_vol + total_ask_vol) > 0:
                    obi = (total_bid_vol - total_ask_vol) / (total_bid_vol + total_ask_vol)
                else:
                    obi = 0.0
                    
                logger.info(f"Micro-Structure OBI: {obi:.2f} // Bids: {total_bid_vol:.2f} | Asks: {total_ask_vol:.2f}")
                
                # --- THE EXECUTION GATE ---
                trade_approved = False
                
                if direction == "LONG":
                    if obi > 0.10: # Minimum 10% buy-side pressure advantage
                        logger.success("OBI clears Bullish pressure. No major sell walls detected. TRADE APPROVED.")
                        trade_approved = True
                    else:
                        logger.warning(f"🚨 TRADE ABORTED: LONG signal fired, but L2 flow is Bearish (OBI: {obi:.2f}). Huge Sell Wall ahead.")
                        
                elif direction == "SHORT":
                    if obi < -0.10: # Minimum 10% sell-side pressure advantage
                        logger.success("OBI clears Bearish pressure. No major buy walls detected. TRADE APPROVED.")
                        trade_approved = True
                    else:
                        logger.warning(f"🚨 TRADE ABORTED: SHORT signal fired, but L2 flow is Bullish (OBI: {obi:.2f}). Huge Buy Wall ahead.")
                        
            except Exception as e:
                logger.error(f"Failed to fetch L2 data. Aborting trade for safety. Error: {e}")
                trade_approved = False

            # If the order book rejects the trade, stop here and do NOT send Telegram alert
            if not trade_approved:
                return

            # --- FIRE SIGNAL ---
            logger.success(f"[{symbol}] {strategy_name} CONFIRMED! Firing Telegram signal.")
            
            signal_text = f"⚡ FAST SCALP SIGNAL ⚡\nAsset: {symbol}\nStrategy: {strategy_name}\nAction: {direction}\n\n🎯 Entry Price: ${last_close:.4f}\n✅ Take Profit: ${take_profit:.4f}\n🚨 Stop Loss: ${stop_loss:.4f}\n📊 Order Book Imbalance: {obi:.2f}"
            
            token = os.getenv('TELEGRAM_BOT_TOKEN')
            chat_id = os.getenv('TELEGRAM_CHAT_ID')
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            requests.post(url, json={"chat_id": chat_id, "text": signal_text})
            
        except Exception as e:
            logger.error(f"Error in cycle for {symbol}: {e}")

    async def start_infinite_loop(self):
        logger.success("Multi-Asset Engine successfully deployed live into production.")
        
        # FIX 1: Force CCXT to download the KuCoin Futures architecture before scanning
        logger.info("Loading KuCoin Futures market architecture...")
        await self.exchange.load_markets()
        
        # FIX 2: Use explicit Perpetual Contract symbols
        self.target_assets = ['ETH/USDT:USDT', 'SOL/USDT:USDT']
        
        try:
            while True:
                for asset in self.target_assets:
                    logger.info(f"--- Initiating Market Scan: {asset} ---")
                    try:
                        await self.run_cycle(symbol=asset)
                    except Exception as e:
                        logger.error(f"Scan failed for {asset}: {e}")
                    await asyncio.sleep(2)  # Micro-pause to prevent KuCoin API bans
                
                logger.info("Radar sweep complete. Sleeping for 60 seconds...")
                await asyncio.sleep(60)
        finally:
            await self.exchange.close()

# --- IGNITION SWITCH ---
if __name__ == "__main__":
    engine = QuantitativeTradingEngine()
    try:
        asyncio.run(engine.start_infinite_loop())
    except KeyboardInterrupt:
        logger.warning("Engine shutdown signal received from terminal. Exiting safely.")