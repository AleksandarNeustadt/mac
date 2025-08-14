# ============================================================================
# File:       system/managers/log_manager.py
# Purpose:    LogManager klasa — klasni API sloj
# Author:     Aleksandar Popovic
# Created:    2025-08-07
# Updated:    2025-08-11
# ============================================================================

from system.handlers.log_handler import LogHandler
from system.helpers.core_helper import safe_call

class LogManager:
    _log_entries = []

    @classmethod
    def initialize(cls):
        cls._log_entries = []

    @classmethod
    def create(cls, level: str, message: str):
        """
        Centralni ulaz za log. Pamti u memoriji i delegira LogHandler-u.
        Ako odgovarajuća metoda ne postoji na LogHandler-u, koristi _write fallback.
        """
        level_upper = (level or "").upper()
        level_lower = level_upper.lower()

        # 1) upiši u internu memoriju
        cls._log_entries.append((level_upper, message))

        # 2) pokušaj preciznu metodu na LogHandler-u (info/warning/success/error/critical)
        method = getattr(LogHandler, level_lower, None)
        if callable(method):
            safe_call(method, message)
            return

        # 3) fallback — direktno zovi _write sa zadatim levelom
        safe_call(LogHandler._write, level_upper, message)

    @classmethod
    def read(cls, last_only: bool = False):
        if last_only and cls._log_entries:
            return cls._log_entries[-1]
        return cls._log_entries

    @classmethod
    def update(cls, index: int, new_message: str):
        if 0 <= index < len(cls._log_entries):
            level = cls._log_entries[index][0]
            cls._log_entries[index] = (level, new_message)

    @classmethod
    def delete(cls, index: int = None):
        if index is None:
            cls._log_entries.clear()
        elif 0 <= index < len(cls._log_entries):
            cls._log_entries.pop(index)

    # === Shortcut/proxy metode u duhu ergonomije API-ja ===

    @classmethod
    def info(cls, message: str):
        cls.create("INFO", message)

    @classmethod
    def warning(cls, message: str):
        cls.create("WARNING", message)

    @classmethod
    def success(cls, message: str):
        cls.create("SUCCESS", message)

    @classmethod
    def error(cls, message: str):
        cls.create("ERROR", message)

    @classmethod
    def critical(cls, message: str):
        cls.create("CRITICAL", message)
