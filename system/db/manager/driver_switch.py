# =============================================================================
# File:        system/db/manager/driver_switch.py
# Purpose:     Prebacivanje drajvera (trajni/privremeni) i context manager
# =============================================================================
from __future__ import annotations

from typing import Any, Dict, Optional
from contextlib import contextmanager

from system.config.env import EnvLoader
from system.managers.error_manager import ErrorManager
from .helpers import _log


class DBDriverSwitchMixin:
    @classmethod
    def switch_driver(cls, driver: str, db_path: Optional[str] = None, *, enforce: bool = False) -> str:
        try:
            if not getattr(cls, "_initialized", False):
                cls.initialize()

            if cls._config.get("source") == "env" and not enforce:
                _log("warning", "switch_driver refused: source=env (use enforce=True or with_driver)")
                raise RuntimeError(
                    "Aktivni drajver potiče iz .env — trajna promena bez enforce=True nije dozvoljena. "
                    "Za privremeni prelaz koristi with_driver(...)."
                )

            driver_key = (driver or "").strip().lower()
            if not driver_key:
                raise ValueError("driver je obavezan za switch_driver")

            if driver_key == "json":
                root = db_path or EnvLoader.get("DB_PATH", "system/data/db/")
                params = {"root": root}
            elif driver_key == "sqlite":
                if db_path:
                    sqlite_path = db_path
                else:
                    base = EnvLoader.get("SQLITE_PATH", None)
                    if not base:
                        base = f"{EnvLoader.get('DB_PATH', 'system/data/db/').rstrip('/')}/app.db"
                    sqlite_path = base
                params = {"path": sqlite_path}
            else:
                raise ValueError(f"Nepodržan driver u switch_driver: {driver_key}")

            cls._activate(driver_key, params, source="override")
            cls._initialized = True
            _log("info", f"switch_driver -> driver={driver_key} source=override params={params}")
            return driver_key
        except Exception as e:
            ErrorManager.create(e)

    @classmethod
    @contextmanager
    def with_driver(cls, driver: str, db_path: Optional[str] = None):
        if not getattr(cls, "_initialized", False):
            cls.initialize()

        prev_driver = cls._driver
        prev_cfg = dict(cls._config)

        try:
            driver_key = (driver or "").strip().lower()
            if not driver_key:
                raise ValueError("driver je obavezan za with_driver")

            if driver_key == "json":
                root = db_path or EnvLoader.get("DB_PATH", "system/data/db/")
                params = {"root": root}
            elif driver_key == "sqlite":
                if db_path:
                    sqlite_path = db_path
                else:
                    base = EnvLoader.get("SQLITE_PATH", None)
                    if not base:
                        base = f"{EnvLoader.get('DB_PATH', 'system/data/db/').rstrip('/')}/app.db"
                    sqlite_path = base
                params = {"path": sqlite_path}
            else:
                raise ValueError(f"Nepodržan driver u with_driver: {driver_key}")

            cls._activate(driver_key, params, source="context")
            yield cls

        except Exception as e:
            ErrorManager.create(e)
            raise
        finally:
            cls._driver = prev_driver
            cls._config = prev_cfg
            _log("info", f"restore (from context) -> driver={prev_cfg.get('driver')} source={prev_cfg.get('source')}")
