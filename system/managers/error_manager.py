# ========================================================================
# File:       system/managers/error_manager.py
# Purpose:    CRUD menadžer za greške (sigurno logovanje)
# Author:     Aleksandar Popovic
# Created:    2025-08-07
# Updated:    2025-08-07
# ========================================================================

from system.handlers.error_handler import ErrorHandler
from system.managers.log_manager import LogManager
from system.helpers.core_helper import safe_call

class ErrorManager:
    _errors = []
    _dev_mode = True

    @classmethod
    def initialize(cls, dev_mode: bool = True):
        cls._dev_mode = dev_mode

    @classmethod
    def create(cls, error: Exception):
        cls._errors.append(error)
        formatted = ErrorHandler.format_error(error)
        trace = ErrorHandler.get_traceback(error)

        if cls._dev_mode:
            print(f"[ERROR]: {formatted}\n{trace}")

        safe_call(LogManager.create, "error", f"{formatted}\n{trace}")

    @classmethod
    def read(cls, last_only: bool = True):
        return cls._errors[-1] if last_only and cls._errors else cls._errors

    @classmethod
    def update(cls, index: int, new_error: Exception):
        if 0 <= index < len(cls._errors):
            cls._errors[index] = new_error

    @classmethod
    def delete(cls, index: int = None):
        if index is None:
            cls._errors.clear()
        elif 0 <= index < len(cls._errors):
            cls._errors.pop(index)
