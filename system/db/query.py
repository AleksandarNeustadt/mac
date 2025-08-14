# =============================================================================
# File:        system/db/query.py
# Purpose:     Formalna QuerySpec specifikacija + exceptions + capabilities
# Author:      Aleksandar Popović
# Created:     2025-08-12
# Updated:     2025-08-12
# =============================================================================

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Set


# ---------- Exceptions ----------
class DBError(Exception):
    """Bazna greška DB sloja."""
    pass


class CapabilityNotSupported(DBError):
    """Driver ne podržava traženu mogućnost (operator, order_by, limit/offset...)."""
    pass


class RecordNotFound(DBError):
    """Traženi zapis ne postoji."""
    pass


class ValidationError(DBError):
    """Neuspešna validacija podataka ili upita."""
    pass


# ---------- Capabilities ----------
@dataclass(frozen=True)
class DriverCapabilities:
    operators: Set[str] = frozenset()
    order_by: bool = False
    limit_offset: bool = False
    transactions: bool = False
    returning: bool = False  # da li create/update vraća ceo red “iz baze”


# ---------- QuerySpec ----------
@dataclass
class QuerySpec:
    table: str
    where: Dict[str, Any] = field(default_factory=dict)
    order_by: List[Tuple[str, str]] = field(default_factory=list)  # [("id","asc"), ("name","desc")]
    limit: Optional[int] = None
    offset: Optional[int] = None
    first: bool = False
    select: Optional[List[str]] = None  # None = sve kolone

    def add_where(self, **filters) -> "QuerySpec":
        self.where.update(filters)
        return self

    def add_order(self, key: str, direction: str = "asc") -> "QuerySpec":
        self.order_by.append((key, direction))
        return self

    def set_limit(self, n: int) -> "QuerySpec":
        self.limit = int(n)
        return self

    def set_offset(self, n: int) -> "QuerySpec":
        self.offset = int(n)
        return self

    def set_first(self, val: bool = True) -> "QuerySpec":
        self.first = bool(val)
        return self

    def set_select(self, *cols: str) -> "QuerySpec":
        self.select = list(cols) if cols else None
        return self
