import pandas as pd
from loguru import logger
from strategies.base import BaseStrategy, StrategyResult
from filters.regime import RegimeState

class OrderFlowStrategy(BaseStrategy):
    def __init__(self):
        super().__init__(name="Order Flow & Positioning")

    async def analyze(self, df: pd.DataFrame, regime: RegimeState) -> StrategyResult:
        if 'order_flow' not in regime.allowed_strategies:
            return StrategyResult(
                strategy_name=self.name, score=0.0, confidence=0.0,
                explanation=f"Order flow disabled in {regime.regime.value}."
            )

        try:
            # Requires OI and Funding data in the dataframe
            if 'OI' not in df.columns or 'funding_rate' not in df.columns:
                return StrategyResult(
                    strategy_name=self.name, score=0.0, confidence=0.0,
                    explanation="Missing OI/Funding data."
                )

            current = df.iloc[-2]
            previous = df.iloc[-3]
            
            price_delta = (current['close'] - previous['close']) / previous['close']
            oi_delta = (current['OI'] - previous['OI']) / previous['OI']
            funding = current['funding_rate']

            score, confidence = 0.0, 0.0
            explanation = "Order flow neutral."

            # 1. Aggressive Longs (Price UP, OI UP)
            if price_delta > 0.002 and oi_delta > 0.01:
                score = 1.0
                confidence = 0.7
                explanation = "Aggressive long positioning (Price & OI expanding)."
                if funding > 0.01: # Danger of long squeeze
                    score = -0.5
                    explanation = "High funding + OI expansion warns of long squeeze."

            # 2. Aggressive Shorts (Price DOWN, OI UP)
            elif price_delta < -0.002 and oi_delta > 0.01:
                score = -1.0
                confidence = 0.7
                explanation = "Aggressive short positioning (Price drop & OI expanding)."
                if funding < -0.01: # Danger of short squeeze
                    score = 0.5
                    explanation = "Negative funding + OI expansion warns of short squeeze."

            # 3. Long Capitulation (Price DOWN, OI DOWN sharply)
            elif price_delta < -0.005 and oi_delta < -0.02:
                score = 1.5 # Reversal signal
                confidence = 0.8
                explanation = "Long capitulation / Stop run detected. Potential reversal."

            # 4. Short Capitulation (Price UP, OI DOWN sharply)
            elif price_delta > 0.005 and oi_delta < -0.02:
                score = -1.5 # Reversal signal
                confidence = 0.8
                explanation = "Short squeeze detected. Upside momentum exhausting."

            return StrategyResult(
                strategy_name=self.name,
                score=score,
                confidence=confidence,
                explanation=explanation,
                metadata={"oi_delta": float(oi_delta), "funding": float(funding)}
            )

        except Exception as e:
            logger.error(f"Order Flow Strategy failed: {e}")
            return StrategyResult(strategy_name=self.name, score=0.0, confidence=0.0, explanation="Error")
