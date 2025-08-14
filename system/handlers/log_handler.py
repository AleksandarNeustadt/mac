# ============================================================================
# File:       system/handlers/log_handler.py
# Purpose:    Pisanje logova na osnovu nivoa (INFO, ERROR, ...)
# Author:     Aleksandar Popovic
# Created:    2025-08-07
# Updated:    2025-08-11
# ============================================================================

import os
from datetime import datetime
from system.config.env import EnvLoader

class LogHandler:
    log_file_path = EnvLoader.get("LOG_FILE_PATH", "system/data/logs/app.log")

    @staticmethod
    def _ensure_log_dir():
        try:
            os.makedirs(os.path.dirname(LogHandler.log_file_path), exist_ok=True)
        except Exception as e:
            print(f"❌ Ne mogu kreirati log direktorijum: {e}")

    @staticmethod
    def _write(level, message):
        try:
            LogHandler._ensure_log_dir()
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_entry = f"[{level.upper()}] {timestamp} - {message}\n"
            with open(LogHandler.log_file_path, "a", encoding="utf-8") as f:
                f.write(log_entry)
        except Exception as e:
            print(f"❌ Neuspelo logovanje: {e}")

    @staticmethod
    def info(message):
        LogHandler._write("INFO", message)

    @staticmethod
    def warning(message):
        LogHandler._write("WARNING", message)

    @staticmethod
    def success(message):
        LogHandler._write("SUCCESS", message)

    @staticmethod
    def error(message):
        LogHandler._write("ERROR", message)

    @staticmethod
    def critical(message):
        LogHandler._write("CRITICAL", message)
