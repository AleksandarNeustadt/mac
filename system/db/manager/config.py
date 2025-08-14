# =============================================================================
# File:        system/db/manager/config.py
# Purpose:     Inicijalizacija, aktivacija i capability pregled
# =============================================================================
from __future__ import annotations

from typing import Any, Dict, Optional

from system.config.env import EnvLoader
from system.managers.error_manager import ErrorManager
from system.db.json_driver import JSONDriver
from system.db.sqlite_driver import SQLiteDriver
from system.db.query import DriverCapabilities

from .helpers import _log


class DBConfigMixin:
    _driver: Any = None
    _initialized: bool = False
    _config: Dict[str, Any] = {"driver": None, "params": {}, "source": None}

    @classmethod
    def initialize(cls, reload_env: bool = False) -> None:
        try:
            if cls._initialized and not reload_env:
                return

            EnvLoader.load()

            driver_key = (EnvLoader.get("DB_DRIVER", "json") or "json").strip().lower()
            db_path = (EnvLoader.get("DB_PATH", "system/data/db/") or "system/data/db/").strip()

            if driver_key == "json":
                params = {"root": db_path}
                cls._activate(driver_key, params, source="env")
            elif driver_key == "sqlite":
                sqlite_path = EnvLoader.get("SQLITE_PATH", f"{db_path.rstrip('/')}/app.db")
                params = {"path": sqlite_path}
                cls._activate(driver_key, params, source="env")
            else:
                raise ValueError(f"Nepoznat DB_DRIVER u .env: {driver_key}")

            cls._initialized = True
            _log("info", f"initialize -> driver={driver_key} source=env params={params}")
        except Exception as e:
            ErrorManager.create(e)

    @classmethod
    def shutdown(cls) -> None:
        try:
            if cls._driver and hasattr(cls._driver, "close"):
                cls._driver.close()
        except Exception as e:
            ErrorManager.create(e)
        finally:
            cls._driver = None
            cls._initialized = False
            cls._config = {"driver": None, "params": {}, "source": None}

    @classmethod
    def _activate(cls, driver_key: str, params: Dict[str, Any], *, source: str) -> None:
        """Uniformna aktivacija drajvera preko **params."""
        driver_key = (driver_key or "json").strip().lower()
        if driver_key == "json":
            cls._driver = JSONDriver(**(params or {}))
        elif driver_key == "sqlite":
            cls._driver = SQLiteDriver(**(params or {}))
        else:
            raise ValueError(f"Nepoznat driver_key: {driver_key}")

        cls._config = {"driver": driver_key, "params": dict(params or {}), "source": source}
        _log("info", f"activate -> driver={driver_key} source={source} params={params}")

    # ---------- Pogled u stanje ----------
    @classmethod
    def active_config(cls) -> Dict[str, Any]:
        return dict(cls._config)

    @classmethod
    def get_driver_key(cls) -> Optional[str]:
        return cls._config.get("driver")

    @classmethod
    def get_driver_name(cls) -> Optional[str]:
        return cls._driver.__class__.__name__ if cls._driver else None

    @classmethod
    def capabilities(cls) -> DriverCapabilities:
        from .helpers import _requires_init  # lokalni import da ne kvari classmethod
        @_requires_init
        def _capabilities(inner_cls):
            try:
                return inner_cls._driver.capabilities()
            except Exception as e:
                ErrorManager.create(e)
        return _capabilities.__get__(cls, cls.__class__)()  # izvrši pseudo-classmethod
