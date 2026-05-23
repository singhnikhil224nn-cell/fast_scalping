import pandas as pd
from typing import Dict
from confluence.engine import ConfluenceResult
from filters.regime import RegimeState

class FeaturePipeline:
    def __init__(self):
        # Map categorical regimes to ordinal/numerical values for XGBoost
        self.regime_map = {
            "STRONG_UPTREND": 2, "WEAK_UPTREND": 1, "RANGE": 0,
            "WEAK_DOWNTREND": -1, "STRONG_DOWNTREND": -2,
            "HIGH_VOLATILITY": -3, "CRISIS": -99
        }

    def build_features(self, df: pd.DataFrame, confluence: ConfluenceResult, regime: RegimeState) -> Dict[str, float]:
        """
        Flattens the current state into a 1D feature array for the ML Meta Model.
        """
        # Always use iloc[-2] to avoid lookahead bias on the currently forming candle
        latest = df.iloc[-2]
        prev = df.iloc[-3]

        features = {
            "confluence_score": float(confluence.final_score),
            "confluence_confidence": float(confluence.total_confidence),
            "regime_encoded": float(self.regime_map.get(regime.regime.value, 0)),
            "regime_confidence": float(regime.confidence),
            "atr_ratio": float(latest.get('ATR_14', 1.0) / latest.get('close', 1.0)), # Volatility normalization
            "adx_14": float(latest.get('ADX_14', 0.0)),
            "active_strategy_count": float(len(confluence.active_strategies))
        }
        
        # Add derivative data if it exists in the shared dataframe
        features["funding_rate"] = float(latest.get("funding_rate", 0.0))
        oi_current = latest.get("OI", 1.0)
        oi_prev = prev.get("OI", 1.0)
        features["oi_delta"] = float((oi_current - oi_prev) / oi_prev) if oi_prev != 0 else 0.0

        return features
