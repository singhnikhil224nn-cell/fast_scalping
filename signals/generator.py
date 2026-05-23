import pandas as pd
from typing import Optional
from loguru import logger
from pydantic import BaseModel
import asyncio

# Import all engine components
from filters.regime import RegimeDetector
from strategies.smc import SMCStrategy
from strategies.trend import TrendStrategy
from strategies.order_flow import OrderFlowStrategy
from confluence.engine import ConfluenceEngine
from ml.features import FeaturePipeline
from ml.meta_model import MetaModel
from filters.risk import RiskManager
from filters.sizing import PositionSizer
from signals.exits import ExitEngine
from extras.gemini import GeminiValidator

class FinalSignal(BaseModel):
    timestamp: str
    asset: str
    direction: str
    entry_price: float
    stop_loss: float
    take_profit_1: float
    take_profit_2: float
    risk_reward_ratio: float
    suggested_risk_pct: float
    regime_context: str
    confluence_score: float
    ml_probability: float
    active_strategies: list[str]
    management_rules: str
    gemini_verdict: str
    gemini_reasoning: str
    is_approved: bool

class SignalGenerator:
    def __init__(self, gemini_api_key: str = ""):
        # Initialize the entire pipeline
        self.regime_detector = RegimeDetector()
        self.strategies = [SMCStrategy(), TrendStrategy(), OrderFlowStrategy()]
        self.confluence_engine = ConfluenceEngine()
        self.feature_pipeline = FeaturePipeline()
        self.meta_model = MetaModel()
        self.risk_manager = RiskManager()
        self.position_sizer = PositionSizer()
        self.exit_engine = ExitEngine()
        self.gemini_validator = GeminiValidator(api_key=gemini_api_key)

    async def generate(self, df: pd.DataFrame, asset: str = "ETH/USDT") -> Optional[FinalSignal]:
        """
        The Master Orchestration Loop. Runs the entire 9-phase pipeline sequentially.
        """
        try:
            latest_price = df.iloc[-1]['close']
            timestamp = str(df.index[-1] if 'datetime' not in df.columns else df.iloc[-1]['datetime'])
            current_atr_pct = df.iloc[-2].get('ATR_14', latest_price * 0.03) / latest_price

            # PHASE 2: Detect Regime
            regime = await self.regime_detector.detect(df)
            if regime.risk_multiplier == 0.0:
                return None # Crisis Mode, abort processing

            # PHASE 3: Run Core Strategies
            strategy_tasks = [strat.analyze(df, regime) for strat in self.strategies]
            strategy_results = await asyncio.gather(*strategy_tasks)

            # PHASE 4: Confluence Aggregation
            confluence = await self.confluence_engine.evaluate(strategy_results, regime)
            if not confluence.is_valid_setup:
                return None # No consensus, abort

            # PHASE 5: Meta Model AI Prediction
            features = self.feature_pipeline.build_features(df, confluence, regime)
            ml_pred = await self.meta_model.predict(features)

            # PHASE 6: Strict Risk Filtering
            risk_check = self.risk_manager.apply_filters(df, confluence, ml_pred)
            if not risk_check.passed:
                logger.debug(f"Signal rejected by Risk Manager: {risk_check.reason}")
                return None

            # PHASE 8: Dynamic Position Sizing
            sizing = self.position_sizer.calculate_size(regime, ml_pred, confluence.total_confidence, current_atr_pct)
            if not sizing.is_valid_size:
                return None

            # PHASE 9: Calculate Exits
            exits = self.exit_engine.calculate_exits(df, confluence, regime)

            # PHASE 7: Discretionary AI Validation (Gemini)
            gemini_verdict = await self.gemini_validator.validate_setup(regime, confluence, ml_pred, latest_price)
            
            is_approved = gemini_verdict.decision == "APPROVE"

            # 10. Package Output
            signal = FinalSignal(
                timestamp=timestamp,
                asset=asset,
                direction=confluence.direction,
                entry_price=exits.entry_price,
                stop_loss=exits.initial_sl,
                take_profit_1=exits.tp1,
                take_profit_2=exits.tp2,
                risk_reward_ratio=exits.expected_rr,
                suggested_risk_pct=sizing.suggested_risk_pct,
                regime_context=f"{regime.regime.value} (Conf: {regime.confidence:.2f})",
                confluence_score=confluence.final_score,
                ml_probability=round(ml_pred.probability_of_success, 3),
                active_strategies=confluence.active_strategies,
                management_rules=exits.management_rules,
                gemini_verdict=gemini_verdict.decision,
                gemini_reasoning=gemini_verdict.reasoning,
                is_approved=is_approved
            )

            if is_approved:
                logger.success(f"HIGH-QUALITY SIGNAL GENERATED: {asset} {signal.direction}")
            else:
                logger.warning(f"Signal Vetoed by Gemini: {gemini_verdict.reasoning}")

            return signal

        except Exception as e:
            logger.error(f"Critical error in Signal Pipeline: {e}")
            return None
