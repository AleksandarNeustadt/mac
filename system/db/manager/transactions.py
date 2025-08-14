# =============================================================================
# File:        system/db/manager/transactions.py
# Purpose:     Transakcije
# =============================================================================
from __future__ import annotations

from system.managers.error_manager import ErrorManager
from .helpers import _requires_init


class DBTransactionsMixin:
    @_requires_init
    def transaction(cls):
        try:
            return cls._driver.transaction()
        except Exception as e:
            ErrorManager.create(e)
