# =============================================================================
# File:        system/db/query_builder.py
# Purpose:     Tanak fluent QueryBuilder iznad QuerySpec-a
# Author:      Aleksandar Popović
# Created:     2025-08-12
# Updated:     2025-08-12
# =============================================================================

from __future__ import annotations
from system.db.query import QuerySpec
from system.db.manager.db_manager import DBManager


class QueryBuilder:
    def __init__(self, table: str):
        self._q = QuerySpec(table=table)

    def where(self, **filters) -> "QueryBuilder":
        self._q.add_where(**filters)
        return self

    def order_by(self, key: str, direction: str = "asc") -> "QueryBuilder":
        self._q.add_order(key, direction)
        return self

    def limit(self, n: int) -> "QueryBuilder":
        self._q.set_limit(n)
        return self

    def offset(self, n: int) -> "QueryBuilder":
        self._q.set_offset(n)
        return self

    def select(self, *cols: str) -> "QueryBuilder":
        self._q.set_select(*cols)
        return self

    def first(self):
        self._q.set_first(True)
        return DBManager.read_spec(self._q)

    def get(self):
        return DBManager.read_spec(self._q)
