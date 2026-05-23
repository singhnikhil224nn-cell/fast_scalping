from typing import List
from pydantic import BaseModel
from loguru import logger
from filters.regime import RegimeState
from strategies.base import StrategyResult
from confluence.weights import WeightManager

class ConfluenceResult(BaseModel):
    is_valid_setup: bool
    direction: str          # "LONG", "SHORT", "NEUTRAL"
    final_score: float      # Aggregated weighted score (-2.0 to +2.0)
    total_confidence: float # 0.0 to 1.0
    active_strategies: List[str]
    reasoning: str

class ConfluenceEngine:
    def __init__(self):
        self.weight_manager = WeightManager()
        self.min_activation_threshold = 1.25 # Minimum absolute score to trigger a signal setup

    async def evaluate(self, results: List[StrategyResult], regime: RegimeState) -> ConfluenceResult:
        if not results or regime.risk_multiplier == 0.0:
            return self._neutral_result("No active strategies or CRISIS regime active.")

        total_weighted_score = 0.0
        total_weight_applied = 0.0
        active_strats = []
        detailed_reasoning = []

        for result in results:
            if result.score == 0.0:
                continue # Strategy was neutral or disabled

            weight = self.weight_manager.calculate_weight(result, regime)
            if weight > 0:
                weighted_score = result.score * weight
                total_weighted_score += weighted_score
                total_weight_applied += weight
                active_strats.append(result.strategy_name)
                detailed_reasoning.append(f"[{result.strategy_name}: {result.score} (W: {weight:.2f}) - {result.explanation}]")

        if total_weight_applied == 0:
            return self._neutral_result("All strategies yielded zero weight or neutral scores.")

        # Normalize score back to a -2.0 to +2.0 scale
        normalized_score = round(total_weighted_score / total_weight_applied, 3)
        total_confidence = round(min(total_weight_applied / len(results), 1.0), 3)

        direction = "NEUTRAL"
        is_valid = False

        if normalized_score >= self.min_activation_threshold:
            direction = "LONG"
            is_valid = True
        elif normalized_score <= -self.min_activation_threshold:
            direction = "SHORT"
            is_valid = True

        return ConfluenceResult(
            is_valid_setup=is_valid,
            direction=direction,
            final_score=normalized_score,
            total_confidence=total_confidence,
            active_strategies=active_strats,
            reasoning=" | ".join(detailed_reasoning)
        )

    def _neutral_result(self, reason: str) -> ConfluenceResult:
        return ConfluenceResult(
            is_valid_setup=False, direction="NEUTRAL", final_score=0.0,
            total_confidence=0.0, active_strategies=[], reasoning=reason
        )
