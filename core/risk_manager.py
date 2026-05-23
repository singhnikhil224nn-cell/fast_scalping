import numpy as np
from loguru import logger

class PositionSizer:
    def __init__(self, max_account_risk_pct: float = 0.02, kelly_fraction: float = 0.25):
        """
        Initializes the dynamic risk management engine.
        :param max_account_risk_pct: Maximum percent of account equity to risk on a single trade (Default: 2%)
        :param kelly_fraction: Aggression constraint factor (Quarter-Kelly approximation to avoid over-leverage)
        """
        self.max_account_risk_pct = max_account_risk_pct
        self.kelly_fraction = kelly_fraction

    def calculate_position_size(self, account_equity: float, current_price: float, atr: float, win_rate: float = 0.55) -> dict:
        """
        Calculates exact mathematical position sizing and leverage allocations.
        """
        try:
            if account_equity <= 0 or current_price <= 0 or atr <= 0:
                return {"quantity": 0.0, "leverage": 1.0, "risk_capital": 0.0}

            # 1. Calculate Risk Per Unit Asset based on 1.5x ATR Structural Stop
            risk_per_unit = atr * 1.5
            
            # 2. Apply Fractional Kelly Criterion to determine optimal equity allocation risk
            # Kelly % = w - ((1 - w) / R) -> Approximated with a conservative variance scale
            reward_risk_ratio = 2.0 # Target minimum risk-to-reward structural profile
            kelly_pct = win_rate - ((1.0 - win_rate) / reward_risk_ratio)
            
            # Constrain risk bounds safely between 0.5% and your maximum safety cap (2%)
            calculated_risk_fraction = max(0.005, min(self.max_account_risk_pct, kelly_pct * self.kelly_fraction))
            risk_capital = account_equity * calculated_risk_fraction

            # 3. Derive exact position size quantity
            position_quantity = risk_capital / risk_per_unit
            notional_value = position_quantity * current_price
            
            # 4. Calculate necessary baseline leverage allocation
            suggested_leverage = max(1.0, min(20.0, notional_value / account_equity))

            return {
                "risk_capital": round(risk_capital, 2),
                "allocated_risk_pct": round(calculated_risk_fraction * 100, 2),
                "quantity": round(position_quantity, 4),
                "notional_usd": round(notional_value, 2),
                "suggested_leverage": round(suggested_leverage, 1)
            }

        except Exception as e:
            logger.error(f"Error executing mathematical risk positioning metrics: {e}")
            return {"quantity": 0.0, "leverage": 1.0, "risk_capital": 0.0}
