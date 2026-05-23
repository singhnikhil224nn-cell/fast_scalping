from typing import Dict
from filters.regime import RegimeState, MarketRegime
from strategies.base import StrategyResult

class WeightManager:
    def __init__(self):
        # Base weight multipliers for strategies based on Regime
        # 1.0 = Standard, >1.0 = Boosted, <1.0 = Penalized
        self.regime_weight_matrix = {
            MarketRegime.STRONG_UPTREND:   {"Trend Following": 1.5, "Smart Money Concepts": 1.2, "Order Flow": 1.0},
            MarketRegime.WEAK_UPTREND:     {"Trend Following": 1.2, "Smart Money Concepts": 1.5, "Order Flow": 1.0},
            MarketRegime.RANGE:            {"Trend Following": 0.0, "Smart Money Concepts": 1.0, "Order Flow": 1.5},
            MarketRegime.WEAK_DOWNTREND:   {"Trend Following": 1.2, "Smart Money Concepts": 1.5, "Order Flow": 1.0},
            MarketRegime.STRONG_DOWNTREND: {"Trend Following": 1.5, "Smart Money Concepts": 1.2, "Order Flow": 1.0},
            MarketRegime.HIGH_VOLATILITY:  {"Trend Following": 0.5, "Smart Money Concepts": 0.5, "Order Flow": 2.0},
            MarketRegime.CRISIS:           {"Trend Following": 0.0, "Smart Money Concepts": 0.0, "Order Flow": 0.0}
        }

        # Simulated rolling 30-day accuracy (Phase 10 Backtesting/DB will update this dynamically later)
        self.rolling_accuracy = {
            "Trend Following": 0.65,
            "Smart Money Concepts": 0.68,
            "Order Flow": 0.60
        }

    def calculate_weight(self, result: StrategyResult, regime: RegimeState) -> float:
        """
        Formula: Base Regime Multiplier * Rolling Accuracy * Strategy Confidence
        """
        regime_multiplier = self.regime_weight_matrix.get(regime.regime, {}).get(result.strategy_name, 1.0)
        historical_accuracy = self.rolling_accuracy.get(result.strategy_name, 0.5)
        
        # Final weight bounds check
        weight = regime_multiplier * historical_accuracy * result.confidence
        return max(0.0, round(weight, 3))
