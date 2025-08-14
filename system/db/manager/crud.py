# =============================================================================
# File:        system/db/manager/crud.py
# Purpose:     CRUD i ORM helper-i + QuerySpec
# =============================================================================
from __future__ import annotations

from typing import Any, Dict, Optional, List

from system.managers.error_manager import ErrorManager
from system.db.query import QuerySpec
from .helpers import _requires_init, now_iso


class DBCrudMixin:
    # ---------- CRUD ----------
    @_requires_init
    def create(cls, table: str, data: Dict[str, Any]):
        try:
            data = dict(data or {})
            data.setdefault("created_at", now_iso())
            data.setdefault("updated_at", data["created_at"])
            res = cls._driver.create(table, data)
            if isinstance(res, int):
                return cls.find_by_pk(table, res)
            return res
        except Exception as e:
            ErrorManager.create(e)

    @_requires_init
    def read(cls, table: str, query: Optional[Dict[str, Any]] = None):
        try:
            return cls._driver.read(table, query or {})
        except Exception as e:
            ErrorManager.create(e)

    @_requires_init
    def update(cls, table: str, id_value: Any, data: Dict[str, Any]):
        try:
            data = dict(data or {})
            data["updated_at"] = now_iso()
            return cls._driver.update(table, id_value, data)
        except Exception as e:
            ErrorManager.create(e)

    @_requires_init
    def delete(cls, table: str, id_value: Any):
        try:
            return cls._driver.delete(table, id_value)
        except Exception as e:
            ErrorManager.create(e)

    # ---------- QuerySpec ----------
    @_requires_init
    def read_spec(cls, spec: QuerySpec):
        try:
            return cls._driver.read_spec(spec)
        except Exception as e:
            ErrorManager.create(e)

    @_requires_init
    def find_by_pk(cls, table: str, value: Any, pk_field: str = "id"):
        try:
            spec = QuerySpec(table=table, where={pk_field: value}, first=True)
            return cls._driver.read_spec(spec)
        except Exception as e:
            ErrorManager.create(e)

    # ---------- ORM helpers ----------
    @_requires_init
    def all(cls, table: str, order_by: Optional[str] = None, limit: Optional[int] = None, offset: Optional[int] = None):
        try:
            query: Dict[str, Any] = {}
            if order_by:
                query["order_by"] = order_by
            if limit is not None:
                query["limit"] = int(limit)
            if offset is not None:
                query["offset"] = int(offset)
            return cls.read(table, query=query if query else None)
        except Exception as e:
            ErrorManager.create(e)

    @_requires_init
    def find(cls, table: str, id_value: Any):
        try:
            return cls.find_by_pk(table, id_value)
        except Exception as e:
            ErrorManager.create(e)

    @_requires_init
    def where(cls, table: str, order_by: Optional[str] = None, limit: Optional[int] = None,
              offset: Optional[int] = None, **filters):
        try:
            query: Dict[str, Any] = {"where": filters}
            if order_by:
                query["order_by"] = order_by
            if limit is not None:
                query["limit"] = int(limit)
            if offset is not None:
                query["offset"] = int(offset)
            return cls.read(table, query=query)
        except Exception as e:
            ErrorManager.create(e)

    @_requires_init
    def first(cls, table: str, **filters):
        try:
            return cls.read(table, query={"where": filters, "first": True})
        except Exception as e:
            ErrorManager.create(e)

    @_requires_init
    def exists(cls, table: str, **filters) -> bool:
        try:
            result = cls.read(table, query={"where": filters, "first": True})
            return result is not None
        except Exception as e:
            ErrorManager.create(e)
            return False

    @_requires_init
    def count(cls, table: str, **filters) -> int:
        try:
            # Brzi put ako driver zna COUNT(*)
            if hasattr(cls._driver, "count"):
                return int(cls._driver.count(table, filters or None))
            # Fallback: pročitaj pa prebroj
            result = cls.read(table, query={"where": filters} if filters else {})
            return len(result) if isinstance(result, list) else 0
        except Exception as e:
            ErrorManager.create(e)
            return 0

    @_requires_init
    def paginate(cls, table: str, page: int = 1, per_page: int = 10, **filters):
        try:
            result = cls.read(table, query={"where": filters} if filters else {})
            if not isinstance(result, list):
                return []
            start = (page - 1) * per_page
            end = start + per_page
            return result[start:end]
        except Exception as e:
            ErrorManager.create(e)
            return []

    @_requires_init
    def get_last_id(cls, table: str):
        try:
            return cls._driver.get_last_id(table)
        except Exception as e:
            ErrorManager.create(e)

    @_requires_init
    def pluck(cls, table: str, column: str, **filters):
        try:
            result = cls.read(table, query={"where": filters} if filters else {})
            if isinstance(result, list):
                return [row.get(column) for row in result]
            return []
        except Exception as e:
            ErrorManager.create(e)
            return []

    @_requires_init
    def first_or_create(cls, table: str, defaults: Optional[Dict[str, Any]] = None, **filters):
        try:
            found = cls.first(table, **filters)
            if found:
                return found
            data = {**filters, **(defaults or {})}
            return cls.create(table, data)
        except Exception as e:
            ErrorManager.create(e)

    @_requires_init
    def raw(cls, table: str):
        try:
            if hasattr(cls._driver, "_load_table"):
                return cls._driver._load_table(table)  # debug path za JSON
            return cls._driver.read(table, {})
        except Exception as e:
            ErrorManager.create(e)

    @_requires_init
    def select(cls, table: str, fields, **filters):
        try:
            spec = QuerySpec(table=table, where=filters, select=list(fields))
            return cls.read_spec(spec)
        except Exception as e:
            ErrorManager.create(e)
