# =============================================================================
# File:        system/db/model.py
# Purpose:     Bazni Model sa ORM helperima, QueryBuilder-om i centralnom validacijom
# Author:      Aleksandar Popović
# Created:     2025-08-08
# Updated:     2025-08-13
# =============================================================================

from __future__ import annotations
from typing import Any, Dict, Optional

from system.db.manager.db_manager import DBManager
from system.db.query_builder import QueryBuilder
from system.managers.validator_manager import ValidatorManager


class Model:
    """
    Bazna Model klasa:
    - Zadržava postojeći DX (create/update/where/...).
    - Opciona šema po modelu preko __schema__ (dict) za centralnu validaciju.
    - Automatski 'unique' check preko aktivnog DB drajvera (DBManager.where).
    """

    table: Optional[str] = None
    pk_field: str = "id"

    # Opciona šema u child klasama:
    # __schema__ = {
    #   "fields":    { "id": int, "name": str, "email": str, "created_at": str, "updated_at": str },
    #   "required":  { "create": ["name", "email"], "update": [] },
    #   "defaults":  { "age": 18 },
    #   "validators":{ "email": lambda v: bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", str(v))) },
    #   "coerce":    { "age": int },
    #   "transform": { "name": str.strip },
    #   "unique":    ["email"],
    #   "immutable": ["email"]
    # }
    __schema__: Optional[Dict[str, Any]] = None

    # --------------------------------------------------------------------- #
    # QueryBuilder / Read helpers
    # --------------------------------------------------------------------- #

    @classmethod
    def query(cls) -> QueryBuilder:
        return QueryBuilder(cls.table)

    @classmethod
    def all(cls, order_by=None, limit=None, offset=None):
        return DBManager.all(cls.table, order_by=order_by, limit=limit, offset=offset)

    @classmethod
    def find(cls, value):
        return DBManager.find_by_pk(cls.table, cls.pk_field, value)

    @classmethod
    def where(cls, order_by=None, limit=None, offset=None, **filters):
        return DBManager.where(cls.table, order_by=order_by, limit=limit, offset=offset, **filters)

    @classmethod
    def first(cls, **filters):
        return DBManager.first(cls.table, **filters)

    @classmethod
    def exists(cls, **filters):
        return DBManager.exists(cls.table, **filters)

    @classmethod
    def count(cls, **filters):
        return DBManager.count(cls.table, **filters)

    @classmethod
    def paginate(cls, page=1, per_page=10, **filters):
        return DBManager.paginate(cls.table, page, per_page, **filters)

    @classmethod
    def pluck(cls, column, **filters):
        return DBManager.pluck(cls.table, column, **filters)

    @classmethod
    def first_or_create(cls, defaults=None, **filters):
        return DBManager.first_or_create(cls.table, defaults=defaults, **filters)

    @classmethod
    def last_id(cls):
        return DBManager.get_last_id(cls.table)

    @classmethod
    def raw(cls):
        return DBManager.raw(cls.table)

    @classmethod
    def driver(cls):
        return DBManager.get_driver_name()

    # --------------------------------------------------------------------- #
    # Write helpers (sa validacijom)
    # --------------------------------------------------------------------- #

    @classmethod
    def create(cls, **data):
        """Create sa opcionalnom validacijom preko __schema__."""
        data = cls._apply_validation(data, profile="create", exclude_pk=None)
        return DBManager.create(cls.table, data)

    @classmethod
    def update(cls, id, **data):
        """Update sa opcionalnom validacijom preko __schema__ (partial update)."""
        data = cls._apply_validation(data, profile="update", exclude_pk=id, partial=True)
        return DBManager.update(cls.table, id, data)

    @classmethod
    def delete(cls, id):
        return DBManager.delete(cls.table, id)

    # --------------------------------------------------------------------- #
    # Validation glue
    # --------------------------------------------------------------------- #

    @classmethod
    def _apply_validation(cls, data: Dict[str, Any], *, profile: str, exclude_pk: Any, partial: bool = False):
        """
        Ako model ima __schema__, pokreće centralnu validaciju.
        - profile: "create" ili "update"
        - exclude_pk: koristi se u unique proveri da dozvoli istu vrednost na istom zapisu
        - partial: True za update (dozvoljava da required polja budu izostavljena ako se ne menjaju)
        """
        schema = getattr(cls, "__schema__", None)
        if not schema:
            return data  # nema šeme -> bez validacije

        return ValidatorManager.validate(
            data,
            schema,
            profile=profile,
            partial=partial,
            unique_check=cls._unique_check,
            exclude_pk=exclude_pk,
        )

    @classmethod
    def _unique_check(cls, field: str, value: Any, exclude_pk: Optional[Any] = None) -> bool:
        """
        Vraća True ako JE jedinstveno (tj. ne postoji DRUGI zapis sa tom vrednošću).
        Koristi DBManager.where i isključuje zapis sa pk == exclude_pk (kod update-a).
        """
        try:
            rows = DBManager.where(cls.table, **{field: value}) or []
            for r in rows:
                rid = r.get(cls.pk_field)
                if exclude_pk is not None and rid == exclude_pk:
                    # isti zapis koji menjamo — ignorišemo ga
                    continue
                # našli smo drugi zapis sa istom vrednošću
                return False
            return True
        except Exception:
            # Ako DB sloj prijavi problem, fail-open (ili promeni u False po izboru)
            return True
