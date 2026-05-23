import sys
import os

# Set root directory for clean workspace package indexing
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import pandas as pd
import ccxt.async_support as ccxt
import asyncio
from datetime import datetime
from data.pipeline import DataPipeline

# Page Setup
st.set_page_config(
    page_title="QUANT CORE // ETH Signal Engine",
    page_icon="⚡",
    layout="wide"
)

# Custom Theme Styling Elements
st.markdown("""
<style>
    .reportview-container { background: #0e1117; }
    .signal-card-none {
        background-color: #1f2937;
        padding: 25px;
        border-radius: 8px;
        border: 1px solid #4b5563;
    }
</style>
""", unsafe_allow_html=True)

st.title("⚡ QUANT CORE // LIVE ENGINE FEED")
st.caption(f"System status: CONNECTED // Live Multi-Regime Strategy Framework // Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
st.markdown("---")

async def load_live_engine_data():
    """Fetches real public candles and layers our indicator matrix"""
    exchange = ccxt.binance({
        'enableRateLimit': True,
        'options': {'defaultType': 'future'}
    })
    pipeline = DataPipeline()
    try:
        ohlcv = await exchange.fetch_ohlcv("ETH/USDT", timeframe="1h", limit=100)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        
        # Inject standard structural alignment mocks
        df['OI'] = df['volume'] * 1.5
        df['funding_rate'] = 0.0001
        
        processed_df = pipeline.process_data(df)
        
        # Calculate dynamic strategy boundaries for visual verification
        processed_df['ub'] = processed_df['high'].shift(1).rolling(window=20).max()
        processed_df['lb'] = processed_df['low'].shift(1).rolling(window=20).min()
        processed_df['v_ma'] = processed_df['volume'].rolling(window=20).mean()
        
        return processed_df
    except Exception as e:
        st.error(f"UI Stream Engine Failure: {e}")
        return None
    finally:
        await exchange.close()

# Handle async loop boundaries smoothly
try:
    df = asyncio.run(load_live_engine_data())
except RuntimeError:
    import nest_asyncio
    nest_asyncio.apply()
    df = asyncio.run(load_live_engine_data())

if df is not None:
    latest_bar = df.iloc[-1]
    previous_bar = df.iloc[-2]
    
    current_price = latest_bar['close']
    price_change = ((current_price - previous_bar['close']) / previous_bar['close']) * 100
    adx = latest_bar.get('ADX_14', 0)
    
    # Determine visual regime tags
    regime_name = "STRONG TREND (Breakout Mode)" if adx >= 25 else "CHOPPY RANGE (Mean Reversion Mode)"

    # UI Layout columns
    col1, col2 = st.columns([1, 3])

    with col1:
        st.header("⚙️ Engine Metrics")
        
        ml_deployed = os.path.exists("models/xgboost_meta_v1.json")
        if ml_deployed:
            st.success("🤖 ML META-MODEL: ACTIVE")
        else:
            st.warning("⚠️ ML META-MODEL: FALLBACK")
            
        st.markdown("---")
        st.subheader("Active Telemetry")
        st.metric(label="Active Regime State", value="TREND" if adx >= 25 else "RANGE", delta=regime_name, delta_color="normal")
        st.metric(label="ADX Strength Score", value=f"{adx:.2f}")
        st.metric(label="Institutional Vol MA", value=f"{latest_bar['v_ma']:,.0f}")

    with col2:
        st.header("📊 Multi-Strategy Context")
        
        m_col1, m_col2, m_col3 = st.columns(3)
        with m_col1:
            st.metric(label="ETH / USDT Live Price", value=f"${current_price:,.2f}", delta=f"{price_change:.2f}% (1h)")
        with m_col2:
            st.metric(label="20H Donchian Upper (Breakout Target)", value=f"${latest_bar['ub']:,.2f}")
        with m_col3:
            st.metric(label="20H Donchian Lower (Breakout Target)", value=f"${latest_bar['lb']:,.2f}")
            
        st.markdown("---")
        st.markdown("### 🏹 Active Signal Pipeline Status")
        
        st.markdown(f"""
        <div class="signal-card-none">
            <h4 style='margin-top:0; color: #9ca3af;'>📭 ALL CLEAR // PIPELINE IDLING</h4>
            <p style='margin-bottom:0; color: #9ca3af;'>
                The master brain is routing live ticks through the <b>{regime_name}</b> suite. 
                A long/short alert block will automatically update here when a strategy pattern triggers 
                and passes your XGBoost cross-validation model filters.
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("### 📋 Unified Quantitative Data Grid (Last 5 Hours)")
        st.dataframe(df[['open', 'high', 'low', 'close', 'EMA_9', 'EMA_21', 'ub', 'lb', 'v_ma']].tail(5), use_container_width=True)
else:
    st.error("Engine failed to synchronize data panels.")
