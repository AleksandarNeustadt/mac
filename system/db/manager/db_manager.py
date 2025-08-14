# =============================================================================
# File:        system/db/manager/db_manager.py
# Purpose:     Tanka "fasada" klasa koja spaja sve mixin-ove u DBManager
# =============================================================================
from __future__ import annotations

from .config import DBConfigMixin
from .driver_switch import DBDriverSwitchMixin
from .transactions import DBTransactionsMixin
from .crud import DBCrudMixin
from .bulk import DBBulkMixin


class DBManager(DBConfigMixin, DBDriverSwitchMixin, DBTransactionsMixin, DBCrudMixin, DBBulkMixin):
    """
    Centralna DB klasa (isti javni API kao pre refaktora).
    - initialize(), shutdown(), active_config(), get_driver_key(), get_driver_name(), capabilities()
    - switch_driver(), with_driver()
    - transaction()
    - create/read/update/delete + ORM helperi
    - bulk_create(), bulk_update()
    """
    pass
