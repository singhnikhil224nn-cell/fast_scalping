import pandas as pd
from loguru import logger
from pydantic import BaseModel
from typing import Optional
from confluence.engine import ConfluenceResult
from filters.regime import RegimeState

class InitialExits(BaseModel):
    entry_price: float
    initial_sl: float
    tp1: float
    tp2: float
    expected_rr: float
    time_limit_bars: int
    management_rules: str

class ExitEngine:
    def __init__(self):
        # Volatility-based structural multipliers
        self.sl_atr_multiplier = 1.5      # SL is placed 1.5 ATRs away from entry/structure
        self.tp1_atr_multiplier = 2.0     # First scale-out at 2 ATRs (Asymmetric RR)
        self.tp2_atr_multiplier = 4.0     # Runner target at 4 ATRs
        self.max_trade_duration = 24      # Max bars a trade can stay open before Time Decay exit

    def calculate_exits(self, df: pd.DataFrame, confluence: ConfluenceResult, regime: RegimeState) -> InitialExits:
        """
        Calculates volatility-adjusted Entry, SL, and TP levels based on the current regime.
        """
        try:
            latest = df.iloc[-2]
            entry = latest['close']
            atr = latest.get('ATR_14', entry * 0.03) # Fallback to 3% if ATR missing
            
            # 1. Regime Adjustments
            # In ranging/choppy markets, we tighten targets. In strong trends, we expand the runner.
            tp1_mult = self.tp1_atr_multiplier
            tp2_mult = self.tp2_atr_multiplier
            
            if regime.regime.value in ["RANGE", "HIGH_VOLATILITY"]:
                tp1_mult *= 0.8  # Take profits faster in chop
                tp2_mult *= 0.5  # Don't expect massive runners
            elif regime.regime.value in ["STRONG_UPTREND", "STRONG_DOWNTREND"]:
                tp2_mult *= 1.5  # Let runners run in strong trends

            # 2. Calculate Levels based on Direction
            if confluence.direction == "LONG":
                # Structural SL approximation (in a real scenario, this snaps to nearest Swing Low)
                sl = entry - (atr * self.sl_atr_multiplier)
                tp1 = entry + (atr * tp1_mult)
                tp2 = entry + (atr * tp2_mult)
            elif confluence.direction == "SHORT":
                sl = entry + (atr * self.sl_atr_multiplier)
                tp1 = entry - (atr * tp1_mult)
                tp2 = entry - (atr * tp2_mult)
            else:
                raise ValueError("Cannot calculate exits for NEUTRAL setup.")

            # Calculate base Risk/Reward to TP1
            risk = abs(entry - sl)
            reward_tp1 = abs(tp1 - entry)
            rr_ratio = round(reward_tp1 / max(risk, 0.0001), 2)

            # 3. Dynamic Management Rules String (For downstream parsing/display)
            management_rules = (
                f"1. Move SL to Breakeven when price reaches TP1 ({tp1:.2f}). "
                f"2. Trail TP2 using {self.sl_atr_multiplier}x ATR. "
                f"3. Time Decay: Close trade if not in profit after {self.max_trade_duration} bars."
            )

            return InitialExits(
                entry_price=round(entry, 2),
                initial_sl=round(sl, 2),
                tp1=round(tp1, 2),
                tp2=round(tp2, 2),
                expected_rr=rr_ratio,
                time_limit_bars=self.max_trade_duration,
                management_rules=management_rules
            )

        except Exception as e:
            logger.error(f"Exit calculation failed: {e}")
            # Return safe default fail-state
            return InitialExits(
                entry_price=0.0, initial_sl=0.0, tp1=0.0, tp2=0.0, 
                expected_rr=0.0, time_limit_bars=0, management_rules="ERROR"
            )

    def evaluate_dynamic_exit(self, entry: float, current_price: float, current_atr: float, 
                              bars_held: int, direction: str, highest_profit_price: float) -> str:
        """
        Evaluates an in-progress trade for anomalous exit conditions (Time Decay, Trailing SL).
        Useful for Phase 10 Backtesting or if extending to a trade-management dashboard.
        """
        # Time Decay Exit
        if bars_held >= self.max_trade_duration:
            return "EXIT_TIME_DECAY"

        # Trailing Stop Logic (If price pulled back 2 ATRs from the highest recorded point)
        if direction == "LONG":
            trail_sl = highest_profit_price - (current_atr * 2.0)
            if current_price <= trail_sl and highest_profit_price > entry:
                return "EXIT_TRAILING_STOP"
                
        elif direction == "SHORT":
            trail_sl = highest_profit_price + (current_atr * 2.0)
            if current_price >= trail_sl and highest_profit_price < entry:
                return "EXIT_TRAILING_STOP"

        return "HOLD"
