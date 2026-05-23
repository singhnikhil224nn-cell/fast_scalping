from abc import ABC, abstractmethod
import pandas as pd
from pydantic import BaseModel
from typing import Dict, Any

# We import RegimeState assuming it is implemented in filters.regime
from filters.regime import RegimeState

class StrategyResult(BaseModel):
    strategy_name: str
    score: float          # -2.0 (Strong Short) to +2.0 (Strong Long)
    confidence: float     # 0.0 to 1.0 (Based on indicator clarity)
    explanation: str      # Human/LLM-readable reasoning
    metadata: Dict[str, Any] = {} # Extra data (e.g., FVG size, OB levels)

class BaseStrategy(ABC):
    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    async def analyze(self, df: pd.DataFrame, regime: RegimeState) -> StrategyResult:
        """
        Analyzes the dataframe and returns a standardized StrategyResult.
        Must respect the allowed_strategies defined by the current RegimeState.
        """
        pass
