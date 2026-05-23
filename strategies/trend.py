import pandas as pd
from loguru import logger
from strategies.base import BaseStrategy, StrategyResult
from filters.regime import RegimeState, MarketRegime

class TrendStrategy(BaseStrategy):
    def __init__(self):
        super().__init__(name="Trend Following")
        self.adx_min_threshold = 20.0

    async def analyze(self, df: pd.DataFrame, regime: RegimeState) -> StrategyResult:
        if 'trend' not in regime.allowed_strategies:
            return StrategyResult(
                strategy_name=self.name, score=0.0, confidence=0.0,
                explanation=f"Trend strategy disabled in {regime.regime.value}."
            )

        try:
            # 1. Zero-Lookahead Data Extraction
            latest = df.iloc[-2]
            ema9, ema21 = latest['EMA_9'], latest['EMA_21']
            ema50, ema200 = latest['EMA_50'], latest['EMA_200']
            adx = latest['ADX_14']
            close, open_px = latest['close'], latest['open']

            score, confidence = 0.0, 0.0
            explanation = "No clear trend continuation setup."

            # 2. Trend Alignment Logic
            is_bullish_alignment = (ema9 > ema21) and (ema21 > ema50) and (close > ema200)
            is_bearish_alignment = (ema9 < ema21) and (ema21 < ema50) and (close < ema200)
            
            # 3. Pullback / Continuation Logic
            # Look for red candles in an uptrend that tap the EMA21 (Value area)
            bullish_pullback = is_bullish_alignment and (close < open_px) and (latest['low'] <= ema21) and (close >= ema21)
            bearish_pullback = is_bearish_alignment and (close > open_px) and (latest['high'] >= ema21) and (close <= ema21)

            if adx >= self.adx_min_threshold:
                if bullish_pullback:
                    score = 1.2 if regime.regime == MarketRegime.WEAK_UPTREND else 1.8
                    confidence = min(adx / 50.0, 0.95) # Higher ADX = Higher Confidence
                    explanation = "Bullish pullback to EMA21 value area in aligned uptrend."
                
                elif bearish_pullback:
                    score = -1.2 if regime.regime == MarketRegime.WEAK_DOWNTREND else -1.8
                    confidence = min(adx / 50.0, 0.95)
                    explanation = "Bearish pullback to EMA21 value area in aligned downtrend."

            return StrategyResult(
                strategy_name=self.name,
                score=score,
                confidence=confidence,
                explanation=explanation,
                metadata={"adx": float(adx), "alignment": "bullish" if is_bullish_alignment else "bearish" if is_bearish_alignment else "mixed"}
            )

        except Exception as e:
            logger.error(f"Trend Strategy failed: {e}")
            return StrategyResult(strategy_name=self.name, score=0.0, confidence=0.0, explanation="Error")
