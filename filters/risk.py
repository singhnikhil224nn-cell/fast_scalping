import pandas as pd
from loguru import logger
from pydantic import BaseModel
from confluence.engine import ConfluenceResult
from ml.meta_model import MLPrediction

class FilterResult(BaseModel):
    passed: bool
    reason: str

class RiskManager:
    def __init__(self):
        # System Circuit Breakers
        self.max_consecutive_losses = 3
        self.current_losses = 0
        self.cooldown_blocks = 0             # Number of system cycles to skip
        
        # Microstructure & Structural limits
        self.max_extension_atr = 3.5         # Max distance from EMA21 in ATRs
        self.min_volume_threshold = 0.35     # Volume must be > 35% of 20MA
        self.extreme_funding_rate = 0.015    # Danger zone for squeezes

    def apply_filters(self, df: pd.DataFrame, confluence: ConfluenceResult, ml_pred: MLPrediction) -> FilterResult:
        """Runs the generated setup through a gauntlet of anomaly and safety filters."""
        
        # 1. Base ML Check
        if not ml_pred.is_tradable:
            return FilterResult(passed=False, reason=f"ML Rejected: {ml_pred.explanation}")

        # 2. System Circuit Breaker (Cooldown)
        if self.cooldown_blocks > 0:
            self.cooldown_blocks -= 1
            return FilterResult(passed=False, reason=f"System cooling down. {self.cooldown_blocks} cycles remaining.")

        # 3. Consecutive Loss Protection
        if self.current_losses >= self.max_consecutive_losses:
            self.cooldown_blocks = 12 # Lock engine for 12 cycles to prevent tilt/regime lag
            self.current_losses = 0   # Reset after triggering
            logger.warning("Max drawdown reached. System entering cooldown.")
            return FilterResult(passed=False, reason="Max consecutive losses hit. Enforcing cooldown.")

        try:
            latest = df.iloc[-2]
            
            # 4. Overextension Filter (Mean Reversion Danger)
            # You don't buy after a massive vertical pump, even if indicators say LONG
            ema21 = latest.get('EMA_21', latest['close'])
            atr = latest.get('ATR_14', 1.0)
            distance_from_ema = abs(latest['close'] - ema21)
            
            if distance_from_ema > (atr * self.max_extension_atr):
                return FilterResult(
                    passed=False, 
                    reason=f"Price overextended ({distance_from_ema/atr:.1f} ATRs from EMA21). Rejecting due to rubber-band risk."
                )

            # 5. Liquidity Vacuum Filter
            volume_current = latest.get('volume', 1)
cat << 'EOF' > extras/gemini.py
import json
import aiohttp
import asyncio
from loguru import logger
from pydantic import BaseModel, Field
from typing import Optional

from filters.regime import RegimeState
from confluence.engine import ConfluenceResult
from ml.meta_model import MLPrediction

class GeminiVerdict(BaseModel):
    decision: str = Field(..., description="Must be exactly: APPROVE, WAIT, or REJECT")
    reasoning: str
    hidden_risks: str
    invalidation_level: str

class GeminiValidator:
    def __init__(self, api_key: str):
        self.api_key = api_key
        # Using Gemini 1.5 Flash for high speed & structured JSON output
        self.url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.api_key}"
        self.max_retries = 2
        self.timeout = aiohttp.ClientTimeout(total=10) # Strict 10-second timeout

    async def validate_setup(
        self, 
        regime: RegimeState, 
        confluence: ConfluenceResult, 
        ml_pred: MLPrediction, 
        latest_price: float
    ) -> GeminiVerdict:
        """
        Passes the quantitative setup to Gemini for discretionary contextual validation.
        """
        if not self.api_key:
            logger.warning("No Gemini API key provided. Bypassing AI validation (Auto-Approve).")
            return self._bypass_verdict("No API Key")

        prompt = self._build_prompt(regime, confluence, ml_pred, latest_price)
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "response_mime_type": "application/json",
                "temperature": 0.1 # Low temperature for analytical consistency
            }
        }

        for attempt in range(self.max_retries + 1):
            try:
                async with aiohttp.ClientSession(timeout=self.timeout) as session:
                    async with session.post(self.url, json=payload) as response:
                        if response.status == 429:
                            logger.warning(f"Gemini Rate Limit hit. Retrying in {2 ** attempt}s...")
                            await asyncio.sleep(2 ** attempt)
                            continue
                            
                        response.raise_for_status()
                        data = await response.json()
                        
                        raw_text = data['candidates'][0]['content']['parts'][0]['text']
                        parsed_json = json.loads(raw_text)
                        
                        return GeminiVerdict(**parsed_json)
                        
            except asyncio.TimeoutError:
                logger.error("Gemini API Timeout. Bypassing validation to prevent engine lag.")
                return self._bypass_verdict("Timeout")
            except Exception as e:
                logger.error(f"Gemini Validation Error (Attempt {attempt}): {e}")
                if attempt == self.max_retries:
                    return self._bypass_verdict(f"API Error: {str(e)}")

    def _build_prompt(self, regime: RegimeState, confluence: ConfluenceResult, ml_pred: MLPrediction, price: float) -> str:
        return f"""
        You are a Principal Quantitative Trader acting as Chief Risk Officer.
        Review the following algorithmic trading setup and provide a final verdict.
        
        MARKET CONTEXT:
        - Current Price: {price}
        - Macro Regime: {regime.regime.value} (Confidence: {regime.confidence})
        
        ALGORITHMIC SETUP:
        - Direction: {confluence.direction}
        - Confluence Score: {confluence.final_score} (-2.0 to +2.0 scale)
        - Active Strategies: {", ".join(confluence.active_strategies)}
        - ML Probability of Success: {ml_pred.probability_of_success * 100}%
        
        STRATEGY REASONING:
        {confluence.reasoning}
        
        TASK:
        Evaluate this setup for hidden microstructure risks, regime misalignment, or trap setups.
        Return ONLY a JSON object with the following keys:
        - "decision": "APPROVE", "WAIT", or "REJECT"
        - "reasoning": 1-2 sentence professional justification.
        - "hidden_risks": Identify 1 potential structural risk.
        - "invalidation_level": Briefly describe what invalidates this setup structurally.
        """

    def _bypass_verdict(self, reason: str) -> GeminiVerdict:
        """Failsafe verdict if the API is down, ensuring the system doesn't crash."""
        return GeminiVerdict(
            decision="APPROVE",
            reasoning=f"System auto-approved due to AI bypass ({reason}).",
            hidden_risks="Unknown (AI Offline)",
            invalidation_level="Standard Quant Rules Apply"
        )
