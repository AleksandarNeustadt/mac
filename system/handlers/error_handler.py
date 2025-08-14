# ========================================================================
# File:       system/handlers/error_handler.py
# Purpose:    Formatira i priprema greške za ErrorManager
# Author:     Aleksandar Popovic
# Created:    2025-08-07
# Updated:    2025-08-07
# ========================================================================

import traceback

class ErrorHandler:
    @staticmethod
    def format_error(error: Exception) -> str:
        return f"{type(error).__name__}: {str(error)}"

    @staticmethod
    def get_traceback(error: Exception) -> str:
        return traceback.format_exc()

    @staticmethod
    def display(error: Exception, dev_mode: bool = True):
        """Prikazuje grešku u dev režimu, bez logovanja."""
        if dev_mode:
            formatted = ErrorHandler.format_error(error)
            trace = ErrorHandler.get_traceback(error)
            print(f"[ERROR]: {formatted}\n{trace}")
