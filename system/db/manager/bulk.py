# =============================================================================
# File:        system/db/manager/bulk.py
# Purpose:     Uniformne bulk operacije (create/update/delete) + upsert
# =============================================================================
from __future__ import annotations

from typing import Any, Dict, List, Sequence, Iterable

from system.managers.error_manager import ErrorManager
from .helpers import _requires_init, now_iso


class DBBulkMixin:
    @_requires_init
    def bulk_create(cls, table: str, records: List[Dict[str, Any]]) -> List[int]:
        try:
            if not records:
                return []
            # upotpuni timestamps
            ts = now_iso()
            norm = []
            for r in records:
                rr = dict(r or {})
                rr.setdefault("created_at", ts)
                rr.setdefault("updated_at", rr["created_at"])
                norm.append(rr)

            if hasattr(cls._driver, "bulk_insert"):
                return cls._driver.bulk_insert(table, norm)

            ids: List[int] = []
            with cls.transaction():
                for r in norm:
                    row = cls.create(table, r)
                    if isinstance(row, dict) and "id" in row:
                        ids.append(int(row["id"]))
            return ids
        except Exception as e:
            ErrorManager.create(e)

    @_requires_init
    def bulk_update(cls, table: str, ids: List[int], patch: Dict[str, Any]) -> int:
        try:
            if not ids or not patch:
                return 0
            patch = dict(patch)
            patch["updated_at"] = now_iso()

            if hasattr(cls._driver, "bulk_update"):
                return cls._driver.bulk_update(table, ids, patch)

            changed = 0
            with cls.transaction():
                for i in ids:
                    if cls.update(table, i, patch):
                        changed += 1
            return changed
        except Exception as e:
            ErrorManager.create(e)

    # ---------- NOVO ----------
    @_requires_init
    def bulk_delete(cls, table: str, ids: Sequence[int]) -> int:
        """Obriši više redova po ID-jevima. Vraća broj obrisanih."""
        try:
            ids = list(ids or [])
            if not ids:
                return 0

            if hasattr(cls._driver, "bulk_delete"):
                return int(cls._driver.bulk_delete(table, ids))

            deleted = 0
            with cls.transaction():
                for i in ids:
                    if cls.delete(table, i):
                        deleted += 1
            return deleted
        except Exception as e:
            ErrorManager.create(e)

    @_requires_init
    def upsert(cls, table: str, data: Dict[str, Any], unique_by: Iterable[str]):
        """
        Upsert po jedinstvenim poljima (unique_by). Vraća upsertovani red (dict).
        Ako drajver ima native upsert -> koristi; inače fallback: first()+update()/create().
        """
        try:
            unique_by = list(unique_by or [])
            if not unique_by:
                raise ValueError("unique_by je obavezan za upsert()")

            payload = dict(data or {})
            # timestamps
            ts = now_iso()
            payload.setdefault("created_at", ts)
            payload["updated_at"] = ts

            if hasattr(cls._driver, "upsert"):
                return cls._driver.upsert(table, payload, unique_by)

            # Fallback: pronađi postojećeg po unique_by
            filters = {k: payload[k] for k in unique_by if k in payload}
            if not filters or len(filters) != len(unique_by):
                raise ValueError("Sva unique_by polja moraju biti prisutna u data payload-u za fallback upsert().")

            found = cls.first(table, **filters)
            if found:
                rid = found.get("id")
                cls.update(table, rid, payload)
                return cls.find_by_pk(table, rid)
            else:
                return cls.create(table, payload)
        except Exception as e:
            ErrorManager.create(e)

    @_requires_init
    def bulk_upsert(cls, table: str, records: List[Dict[str, Any]], unique_by: Iterable[str]) -> Dict[str, int]:
        """
        Bulk upsert. Vraća {"created": X, "updated": Y}
        Ako drajver nema native bulk_upsert -> radi u transakciji, iterativno.
        """
        try:
            unique_by = list(unique_by or [])
            if not unique_by:
                raise ValueError("unique_by je obavezan za bulk_upsert()")
            if not records:
                return {"created": 0, "updated": 0}

            # timestamps
            ts = now_iso()
            norm = []
            for r in records:
                rr = dict(r or {})
                rr.setdefault("created_at", ts)
                rr["updated_at"] = ts
                norm.append(rr)

            if hasattr(cls._driver, "bulk_upsert"):
                return dict(cls._driver.bulk_upsert(table, norm, unique_by))

            created = 0
            updated = 0
            with cls.transaction():
                for r in norm:
                    filters = {k: r[k] for k in unique_by if k in r}
                    if len(filters) != len(unique_by):
                        raise ValueError("Sva unique_by polja moraju biti prisutna u svakom zapisu (bulk_upsert).")
                    found = cls.first(table, **filters)
                    if found:
                        rid = found.get("id")
                        if cls.update(table, rid, r):
                            updated += 1
                    else:
                        cls.create(table, r)
                        created += 1
            return {"created": created, "updated": updated}
        except Exception as e:
            ErrorManager.create(e)
