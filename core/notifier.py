import os
import logging
import requests

logger = logging.getLogger(__name__)

class TelegramNotifier:
    def __init__(self):
        # Securely grab keys from Render environment variables
        self.token = os.environ.get('TELEGRAM_BOT_TOKEN', '8992654694:AAHXHrcq8YsppzFUlSRH99CAdQ9dmUUnnQo')
        self.chat_id = os.environ.get('TELEGRAM_CHAT_ID', '7366145742')
        self.active = bool(self.token and self.chat_id)
        
        if self.active:
            logger.info("Telegram Notifier core successfully initialized via standard HTTP.")
        else:
            logger.warning("Telegram Notifier missing keys. Running in silent mode.")

    async def send_signal_alert(self, signal_data: dict):
        direction_emoji = "🚀 LONG SETUP" if signal_data.get('direction', '') == "LONG" else "🩸 SHORT SETUP"
        
        message_text = (
            f"⚡ **QUANT CORE // POSITION EMITTED** ⚡\n"
            f"-----------------------------------\n"
            f"**Asset:** {signal_data.get('symbol', 'ETH/USDT')}\n"
            f"**Action:** {direction_emoji}\n"
            f"**Regime Context:** {signal_data.get('regime', 'N/A')}\n"
            f"-----------------------------------\n"
            f"**Entry Range:** {signal_data.get('entry_range', 'N/A')}\n"
            f"**Stop Loss:** {signal_data.get('stop_loss', 'N/A')}\n"
            f"**Take Profit 1:** {signal_data.get('tp1', 'N/A')}\n"
            f"**Take Profit 2:** {signal_data.get('tp2', 'N/A')}\n"
            f"-----------------------------------\n"
            f"**XGBoost Probability:** {signal_data.get('ml_prob', 'N/A')}\n"
            f"**Allocation Risk:** {signal_data.get('risk_size', 'N/A')}\n"
            f"-----------------------------------\n"
            f"🕒 *Timestamp:* {signal_data.get('timestamp', 'N/A')} UTC"
        )

        if self.active:
            try:
                url = f"https://api.telegram.org/bot{self.token}/sendMessage"
                payload = {
                    "chat_id": self.chat_id,
                    "text": message_text,
                    "parse_mode": "Markdown"
                }
                response = requests.post(url, json=payload)
                
                if response.status_code == 200:
                    logger.info("Signal alert successfully dispatched to Telegram mobile endpoint.")
                else:
                    logger.error(f"Failed to transmit Telegram dispatch: {response.text}")
            except Exception as e:
                logger.error(f"Failed to transmit Telegram dispatch: {e}")
        else:
            logger.info(f"--- SIMULATED TELEGRAM OUTBOUND DISPATCH ---\n{message_text}")
