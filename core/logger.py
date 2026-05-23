import os
import csv
from datetime import datetime
from loguru import logger

class SystemPerformanceLogger:
    def __init__(self, log_directory: str = "logs", log_filename: str = "daily_telemetry.csv"):
        self.log_directory = log_directory
        self.log_filepath = os.path.join(self.log_directory, log_filename)
        self._ensure_log_structures_exist()

    def _ensure_log_structures_exist(self):
        """Creates the log folder and csv sheet with proper headings if missing."""
        if not os.path.exists(self.log_directory):
            os.makedirs(self.log_directory)
            logger.info(f"Created system logging directory path: {self.log_directory}")

        if not os.path.exists(self.log_filepath):
            with open(self.log_filepath, mode='w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    "Timestamp_UTC", 
                    "Asset", 
                    "Price_USD", 
                    "ADX_Strength", 
                    "ATR_Volatility",
                    "Regime_State", 
                    "Active_Signal"
                ])
            logger.success(f"Initialized new tracking spreadsheet: {self.log_filepath}")

    def log_session_snapshot(self, price: float, adx: float, atr: float, regime: str, signal: int):
        """Appends a fresh row of real quantitative metrics to the CSV file."""
        try:
            with open(self.log_filepath, mode='a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
                    "ETH/USDT",
                    round(price, 2),
                    round(adx, 2),
                    round(atr, 2),
                    regime,
                    "LONG" if signal == 1 else ("SHORT" if signal == -1 else "NEUTRAL")
                ])
            logger.info("Successfully persisted hourly market snapshot to filesystem records.")
        except Exception as e:
            logger.error(f"Failed to record data logging entry to CSV: {e}")
