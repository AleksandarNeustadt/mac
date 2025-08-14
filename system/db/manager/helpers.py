# =============================================================================
# File:        system/db/manager/helpers.py
# Purpose:     Zajednički helper-i za DBManager podmodule
# Author:      Aleksandar Popović (+ dorade)
# Updated:     2025-08-13
# =============================================================================
from __future__ import annotations

from functools import wraps
from datetime import datetime, timezone

# --- opciono logovanje preko LogManager-a (tiho fallback na print) ---
try:
    from system.managers.log_manager import LogManager
    _HAS_LOG = True
except Exception:
    _HAS_LOG = False


def _log(level: str, msg: str):
    if _HAS_LOG and hasattr(LogManager, level):
        getattr(LogManager, level)(f"[DBManager] {msg}")
    else:
        print(f"[DBManager:{level.upper()}] {msg}")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _requires_init(fn):
    """Dekorator koji obezbeđuje da je DBManager inicijalizovan pre poziva metode."""
    @wraps(fn)
    def wrapper(cls, *a, **kw):
        if not getattr(cls, "_initialized", False):
            # lazy init
            cls.initialize()
        return fn(cls, *a, **kw)
    return classmethod(wrapper)
