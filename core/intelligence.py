import os
import json
from google import genai
from google.genai import types
from loguru import logger

class GeminiIntelligenceGate:
    def __init__(self):
        self.api_key = os.environ.get("GEMINI_API_KEY", "")
        self.active = bool(self.api_key)
        if self.active:
            self.client = genai.Client()
            logger.success("Gemini Intelligence Layer successfully authenticated and armed.")
        else:
            logger.warning("GEMINI_API_KEY missing in environment variables.")

    def analyze_market_narrative(self, raw_news_headlines: list) -> dict:
        if not self.active or not raw_news_headlines:
            return {"sentiment_score": 0.0, "risk_multiplier": 1.0, "regime_override": "NONE"}
        context_payload = "\n".join([f"- {headline}" for headline in raw_news_headlines])
        prompt = (
            "Analyze the following raw market data feed headlines for Ethereum and determine the immediate fundamental impact:\n"
            f"{context_payload}\n\n"
            "Return a strictly formatted JSON object containing:\n"
            "1. 'sentiment_score': a float between -1.0 and 1.0.\n"
            "2. 'risk_multiplier': a float between 0.0 and 1.0.\n"
            "3. 'regime_override': exactly one of: 'NONE', 'FORCED_SIDEWAYS', or 'SHUTDOWN'."
        )
        try:
            response = self.client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                config=types.GenerateContentConfig(response_mime_type="application/json")
            )
            return json.loads(response.text.strip())
        except Exception as e:
            logger.error(f"Failed to pass information through Gemini Intelligence Gate: {e}")
            return {"sentiment_score": 0.0, "risk_multiplier": 1.0, "regime_override": "NONE"}
