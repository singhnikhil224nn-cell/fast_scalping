
import os

import google.generativeai as genai

import logging

from dotenv import load_dotenv



load_dotenv()

logger = logging.getLogger(__name__)



class GeminiFilter:

    def __init__(self):

        api_key = os.environ.get("AIzaSyD49PIECK-1kxpTf2pstsGeAG-NPMtdwXM")

        if not api_key:

            logger.warning("Gemini API Key missing! AI Gate will default to PASS (Math Only).")

            self.active = False

            return

            

        genai.configure(api_key=api_key)

        # Using 1.5 Flash for ultra-low latency high-frequency trading

        self.model = genai.GenerativeModel('gemini-1.5-flash')

        self.active = True



    def evaluate_trade(self, symbol, direction, price, regime):

        if not self.active:

            return True 



        prompt = f"""

        You are an elite quantitative trading AI. 

        My technical math model just flagged a {direction} setup for {symbol} at ${price}.

        The current market regime is: {regime}.

        

        Based strictly on this technical context, does this setup have a high probability of success, or is it a false breakout?

        Respond with exactly one word: 'APPROVE' or 'REJECT'.

        """

        

        try:

            logger.info("🧠 Firing data payload to Gemini AI for verification...")

            response = self.model.generate_content(prompt)

            decision = response.text.strip().upper()

            

            logger.info(f"🧠 Gemini AI Response: {decision}")

            return "APPROVE" in decision

            

        except Exception as e:

            logger.error(f"Gemini API Error: {e}. Defaulting to math approval.")

            return True 

