from loguru import logger
from pydantic import BaseModel
from filters.regime import RegimeState
from ml.meta_model import MLPrediction

class SizingResult(BaseModel):
    suggested_risk_pct: float       # Percentage of total capital to risk (e.g., 0.015 for 1.5%)
    is_valid_size: bool             # False if calculated size is <= 0
    sizing_reasoning: str

class PositionSizer:
    def __init__(self):
        # Strict Institutional Constraints
        self.absolute_max_risk = 0.02      # Never risk > 2% of total equity on one setup
        self.base_kelly_fraction = 0.25    # Quarter-Kelly (Crypto fat-tails demand conservative Kelly)
        self.baseline_atr_pct = 0.03       # Baseline expected daily volatility (3%)

    def calculate_size(
        self, 
        regime: RegimeState, 
        ml_pred: MLPrediction, 
        confluence_confidence: float, 
        current_atr_pct: float
    ) -> SizingResult:
        """
        Calculates dynamic position size based on Edge (ML), Volatility, and Regime.
        """
        try:
            # 1. Base Kelly Calculation
            # Kelly % = W - [(1 - W) / R] 
            # W = Win Probability, R = Risk/Reward Ratio
            win_prob = ml_pred.probability_of_success
            # We use the regime's minimum required RR as a conservative baseline
            assumed_rr = regime.min_rr_threshold 
            
            if assumed_rr <= 0:
                return self._zero_size("Invalid Regime RR threshold.")

            kelly_pct = win_prob - ((1.0 - win_prob) / assumed_rr)
            
            # If Kelly is negative, the edge is mathematically mathematically invalid
            if kelly_pct <= 0:
                return self._zero_size("Negative Kelly fraction (No mathematical edge).")

            # 2. Apply Fractional Kelly (Safety Factor)
            raw_risk = kelly_pct * self.base_kelly_fraction

            # 3. Volatility Adjustment
            # If current volatility is double the baseline, we halve the position size.
            vol_adjustment_factor = self.baseline_atr_pct / max(current_atr_pct, 0.001)
            risk_adjusted_for_vol = raw_risk * vol_adjustment_factor

            # 4. Confidence & Regime Multipliers
            # Scale down if confluence confidence is low, and apply the Regime master risk control
            final_risk = risk_adjusted_for_vol * confluence_confidence * regime.risk_multiplier

            # 5. Hard Constraints Check
            final_risk = min(final_risk, self.absolute_max_risk)
            final_risk = round(final_risk, 4)

            if final_risk < 0.001: # Don't take trades risking less than 0.1% (waste of fees)
                return self._zero_size("Calculated risk too small after adjustments.")

            reasoning = (
                f"Sized at {final_risk*100:.2f}% risk. "
                f"(Base Kelly: {kelly_pct*100:.1f}%, Volatility Adj: {vol_adjustment_factor:.2f}x, "
                f"Regime Multiplier: {regime.risk_multiplier}x)"
            )

            return SizingResult(
                suggested_risk_pct=final_risk,
                is_valid_size=True,
                sizing_reasoning=reasoning
            )

        except Exception as e:
            logger.error(f"Sizing calculation error: {e}")
            return self._zero_size("Sizing calculation failed.")

    def _zero_size(self, reason: str) -> SizingResult:
        return SizingResult(suggested_risk_pct=0.0, is_valid_size=False, sizing_reasoning=reason)
