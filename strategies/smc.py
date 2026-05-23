import pandas as pd
from loguru import logger
from strategies.base import BaseStrategy, StrategyResult
from filters.regime import RegimeState, MarketRegime

class SMCStrategy(BaseStrategy):
    def __init__(self):
        super().__init__(name="Smart Money Concepts")
        # FVG must be at least 0.5 of current ATR to filter out noise
        self.fvg_min_size_atr = 0.5 
    
    async def analyze(self, df: pd.DataFrame, regime: RegimeState) -> StrategyResult:
        # 1. Regime Check: Instantly exit if SMC is not allowed right now
        if 'smc' not in regime.allowed_strategies:
            return StrategyResult(
                strategy_name=self.name,
                score=0.0,
                confidence=0.0,
                explanation=f"SMC disabled in {regime.regime.value} regime."
            )
        
        try:
            # 2. Vectorized FVG Logic (Zero Lookahead Bias)
            # Index -1 is forming (unclosed), -2 is last closed, -3 is middle, -4 is first
            latest = df.iloc[-2]
            prev_1 = df.iloc[-3]
            prev_2 = df.iloc[-4]
            atr = df.iloc[-2]['ATR_14']
            
            # Bullish FVG: Low of candle 3 is higher than High of candle 1
            bullish_fvg = latest['low'] > prev_2['high']
            # Bearish FVG: High of candle 3 is lower than Low of candle 1
            bearish_fvg = latest['high'] < prev_2['low']
            
            fvg_size = abs(latest['low'] - prev_2['high']) if bullish_fvg else abs(prev_2['low'] - latest['high'])
            is_significant = fvg_size > (atr * self.fvg_min_size_atr)
            
            score, confidence = 0.0, 0.0
            explanation = "No significant SMC displacement detected."
            
            # 3. Contextual Scoring based on Regime
            if bullish_fvg and is_significant:
                if regime.regime in [MarketRegime.STRONG_UPTREND, MarketRegime.WEAK_UPTREND]:
                    score, confidence = 1.5, 0.85
                    explanation = f"Significant Bullish FVG formed, confirming {regime.regime.value}."
                elif regime.regime == MarketRegime.RANGE:
                    score, confidence = 0.5, 0.5
                    explanation = "Bullish FVG formed in RANGE. Potential liquidity grab."
            
            elif bearish_fvg and is_significant:
                if regime.regime in [MarketRegime.STRONG_DOWNTREND, MarketRegime.WEAK_DOWNTREND]:
                    score, confidence = -1.5, 0.85
                    explanation = f"Significant Bearish FVG formed, confirming {regime.regime.value}."
                elif regime.regime == MarketRegime.RANGE:
                    score, confidence = -0.5, 0.5
                    explanation = "Bearish FVG formed in RANGE. Potential liquidity grab."

            return StrategyResult(
                strategy_name=self.name,
                score=score,
                confidence=confidence,
                explanation=explanation,
                metadata={"fvg_size": float(fvg_size) if is_significant else 0.0}
            )

        except Exception as e:
            logger.error(f"SMC Strategy execution failed: {e}")
            return StrategyResult(
                strategy_name=self.name, score=0.0, confidence=0.0, explanation="Execution Error"
            )
