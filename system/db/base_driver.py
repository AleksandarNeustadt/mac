# =============================================================================
# File:        system/db/base_driver.py
# Purpose:     Apstraktna baza za sve drajvere (JSON, SQLite, MySQL...)
# Author:      Aleksandar Popović
# Created:     2025-08-07
# Updated:     2025-08-07
# =============================================================================

# =============================================================================
# File:        system/db/base_driver.py
# Purpose:     Jedinstven interfejs za sve DB drajvere
# =============================================================================
from __future__ import annotations
from abc import ABC, abstractmethod
from contextlib import contextmanager
from typing import Any, Dict, Optional

from system.db.query import QuerySpec, DriverCapabilities


class BaseDBDriver(ABC):
    """Svi drajveri moraju implementirati isti API."""

    # --- Meta/capabilities ---
    @abstractmethod
    def capabilities(self) -> DriverCapabilities:
        """Vrati DriverCapabilities (operators, order_by, limit_offset, transactions, returning)."""

    # --- Lifecycle / konekcija ---
    def close(self) -> None:
        """Opcionalno: uredno zatvaranje konekcije (SQLite)."""
        return None

    # --- Transakcije ---
    @abstractmethod
    def transaction(self):
        """
        Vraća context manager koji obezbeđuje transakciju.
        Ako drajver ne podržava, može vratiti no-op context manager.
        """
        raise NotImplementedError

    # --- Osnovni CRUD ---
    @abstractmethod
    def create(self, table: str, data: Dict[str, Any]):
        """Kreiraj zapis; može vratiti ceo zapis ili ID."""

    @abstractmethod
    def read(self, table: str, query: Optional[Dict[str, Any]] = None):
        """Pročitaj zapise po query dict-u (where/order_by/limit/offset/first/id)."""

    @abstractmethod
    def update(self, table: str, id_value: Any, data: Dict[str, Any]) -> bool:
        """Ažuriraj zapis po primarnom ključu. Vraća True/False."""

    @abstractmethod
    def delete(self, table: str, id_value: Any) -> bool:
        """Obriši zapis po primarnom ključu. Vraća True/False."""

    @abstractmethod
    def get_last_id(self, table: str) -> Optional[int]:
        """Vrati poslednji ID (ako ima smisla), inače None."""

    # --- QuerySpec put ---
    @abstractmethod
    def read_spec(self, spec: QuerySpec):
        """Napredniji upit kroz QuerySpec (where/order/select/limit/offset/first)."""
