# =============================================================================
# File:        system/db/sqlite_driver.py
# Purpose:     SQLite driver (kompatibilan) + performance:
#              - PRAGMA tuning (WAL, synchronous, busy_timeout, page/cache)
#              - Savepoint (ugnježdene) transakcije
#              - Brzi batch: bulk_insert / bulk_update
#              - Sigurni identifikatori, dinamične kolone (kao do sada)
# Author:      Aleksandar Popović (+ dorade za performanse)
# Updated:     2025-08-13
# =============================================================================
from __future__ import annotations

import os
import re
import sqlite3
import threading
from contextlib import contextmanager
from typing import Any, Dict, List, Optional

from system.config.env import EnvLoader
from system.db.base_driver import BaseDBDriver
from system.db.query import QuerySpec, DriverCapabilities

_SAFE_IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _safe_ident(name: str) -> str:
    if not _SAFE_IDENT.match(name or ""):
        raise ValueError(f"Invalid identifier: {name}")
    return name


class SQLiteDriver(BaseDBDriver):
    """
    Kompatibilan sa postojećim kodom:
      - __init__(**params) — očekuje 'path' u params
      - capabilities(), transaction(), create/read/update/delete(), get_last_id(), read_spec()
    NOVO:
      - ugnježdene transakcije (savepoints)
      - bulk_insert(records: List[dict]) -> List[int]
      - bulk_update(ids: List[int], patch: Dict[str, Any]) -> int
      - count(table, where=None) -> int  (brzi COUNT(*))
    """
    _LOCK = threading.RLock()

    def __init__(self, **params):
        db_path = params.get("path")
        if not db_path:
            # podrazumevana putanja ako nije zadata
            db_path = os.path.join("system", "data", "db", "app.db")

        self.db_file = os.path.abspath(db_path)

        # 🚧 Jasna zaštita: putanja ne sme biti direktorijum
        if os.path.isdir(self.db_file):
            raise RuntimeError(
                f"SQLite path '{self.db_file}' je direktorijum — očekivan je put do .db fajla. "
                f"Promeni 'path' (npr. system/data/db/app.db) ili preimenuj/ukloni folder."
            )

        dirpath = os.path.dirname(self.db_file) or "."
        if not os.path.exists(dirpath):
            os.makedirs(dirpath, exist_ok=True)

        # isolation_level=None -> ručno BEGIN/COMMIT (autocommit off)
        self.conn = sqlite3.connect(self.db_file, isolation_level=None, timeout=5.0, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row

        self._apply_pragmas()

        self._last_ids: Dict[str, int] = {}
        self._tx_depth = 0  # za savepoint-e

    # --- PRAGMA podešavanja (tunable preko .env) ---
    def _apply_pragmas(self) -> None:
        """
        Podržava sledeće .env varijable (sve opcione):
          - SQLITE_JOURNAL_MODE=wal|delete|truncate|persist|off|memory
          - SQLITE_WAL=true|false  (ako je JOURNAL_MODE izostavljen)
          - SQLITE_SYNCHRONOUS=OFF|NORMAL|FULL|EXTRA
          - SQLITE_TEMP_STORE=memory|file
          - SQLITE_PAGE_SIZE=4096 (ili drugi broj)
          - SQLITE_CACHE_PAGES=20000   (broj stranica u cache-u; koristi se negativna vrednost u PRAGMA)
          - SQLITE_CACHE_SIZE=20000    (KB; biće konvertovan u negativnu vrednost za PRAGMA)
          - SQLITE_BUSY_TIMEOUT_MS=4000
        """
        cur = self.conn.cursor()
        try:
            # Uključi FK
            cur.execute("PRAGMA foreign_keys = ON;")

            # Journal mode: prioritet ima eksplicitni JOURNAL_MODE, zatim boolean SQLITE_WAL
            jm = EnvLoader.get("SQLITE_JOURNAL_MODE", None)
            if jm:
                jm = str(jm).strip().lower()
                cur.execute(f"PRAGMA journal_mode = {jm};")
            else:
                wal_on = EnvLoader.get_bool("SQLITE_WAL", True)
                if wal_on:
                    try:
                        cur.execute("PRAGMA journal_mode = wal;")
                    except sqlite3.Error:
                        pass  # fallback ispod

            # Synchronous
            sync = (EnvLoader.get("SQLITE_SYNCHRONOUS", "NORMAL") or "NORMAL").upper()
            if sync not in ("OFF", "NORMAL", "FULL", "EXTRA"):
                sync = "NORMAL"
            cur.execute(f"PRAGMA synchronous = {sync};")

            # Page size (pre kreiranja tabela ima efekta; pylno ok i posle)
            page_size = EnvLoader.get("SQLITE_PAGE_SIZE", None)
            if page_size and str(page_size).isdigit():
                try:
                    cur.execute(f"PRAGMA page_size = {int(page_size)};")
                except sqlite3.Error:
                    pass

            # Cache: ili broj stranica (CACHE_PAGES) ili KB (CACHE_SIZE)
            cache_pages = EnvLoader.get("SQLITE_CACHE_PAGES", None)
            cache_size_kb = EnvLoader.get("SQLITE_CACHE_SIZE", None)
            if cache_pages and str(cache_pages).isdigit():
                try:
                    cur.execute(f"PRAGMA cache_size = {-int(cache_pages)};")
                except sqlite3.Error:
                    pass
            elif cache_size_kb and str(cache_size_kb).isdigit():
                try:
                    cur.execute(f"PRAGMA cache_size = {-int(cache_size_kb)};")
                except sqlite3.Error:
                    pass

            # Temp store
            temp_store = EnvLoader.get("SQLITE_TEMP_STORE", None)
            if temp_store:
                cur.execute(f"PRAGMA temp_store = {temp_store};")

            # Busy timeout
            try:
                bt = int(EnvLoader.get("SQLITE_BUSY_TIMEOUT_MS", "4000") or 4000)
            except ValueError:
                bt = 4000
            cur.execute(f"PRAGMA busy_timeout = {bt};")

        finally:
            cur.close()

    # --- lifecycle ---
    def close(self) -> None:
        try:
            self.conn.close()
        except Exception:
            pass

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass

    # --- capabilities (kompatibilno) ---
    def capabilities(self) -> DriverCapabilities:
        return DriverCapabilities(
            operators=frozenset({"=", "!=", "<", "<=", ">", ">=", "in", "like", "startswith", "endswith", "contains"}),
            order_by=True,
            limit_offset=True,
            transactions=True,
            returning=True
        )

    # --- transakcije (sa savepointima) ---
    @contextmanager
    def transaction(self):
        with self._LOCK:
            cur = self.conn.cursor()
            try:
                if self._tx_depth == 0:
                    cur.execute("BEGIN;")
                else:
                    cur.execute(f"SAVEPOINT sp_{self._tx_depth+1};")
                self._tx_depth += 1
                yield
                self._tx_depth -= 1
                if self._tx_depth == 0:
                    cur.execute("COMMIT;")
                else:
                    cur.execute(f"RELEASE SAVEPOINT sp_{self._tx_depth+1};")
            except Exception:
                self._tx_depth -= 1
                if self._tx_depth == 0:
                    cur.execute("ROLLBACK;")
                else:
                    cur.execute(f"ROLLBACK TO SAVEPOINT sp_{self._tx_depth+1};")
                raise
            finally:
                cur.close()

    # --- helpers ---
    def _ensure_table(self, table: str, sample: Optional[Dict[str, Any]] = None) -> None:
        """
        Minimalna, fleksibilna šema — kompatibilno sa starom verzijom:
          - fiksne kolone: id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT, updated_at TEXT
          - dinamične kolone izvedene iz sample keys (TEXT/INTEGER/REAL)
        Ako tabela ne postoji → kreiraj; ako kolona fali → ALTER TABLE ADD COLUMN.
        """
        t = _safe_ident(table)
        cur = self.conn.cursor()

        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS "{t}" (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT,
                updated_at TEXT
            );
        """)

        if sample:
            cur.execute(f'PRAGMA table_info("{t}");')
            existing_cols = {row["name"] for row in cur.fetchall()}
            for k, v in sample.items():
                if k in ("id", "created_at", "updated_at"):
                    continue
                if k not in existing_cols:
                    col = _safe_ident(k)
                    sqltype = "TEXT"
                    if isinstance(v, bool): sqltype = "INTEGER"
                    elif isinstance(v, int): sqltype = "INTEGER"
                    elif isinstance(v, float): sqltype = "REAL"
                    cur.execute(f'ALTER TABLE "{t}" ADD COLUMN "{col}" {sqltype};')

        cur.close()

    def _insert(self, table: str, data: Dict[str, Any]) -> int:
        t = _safe_ident(table)
        self._ensure_table(t, sample=data)

        cols = [k for k in data.keys()]
        vals = [data[k] for k in cols]
        cols_q = ", ".join([f'"{_safe_ident(c)}"' for c in cols])
        params_q = ", ".join(["?"] * len(vals))

        cur = self.conn.cursor()
        try:
            cur.execute(f'INSERT INTO "{t}" ({cols_q}) VALUES ({params_q});', vals)
            last_id = self.conn.execute("SELECT last_insert_rowid();").fetchone()[0]
            self._last_ids[t] = int(last_id)
            return int(last_id)
        finally:
            cur.close()

    def _insert_many(self, table: str, rows: List[Dict[str, Any]]) -> List[int]:
        """Brz batch insert — koristi jedan pripremljen statement + executemany."""
        if not rows:
            return []

        t = _safe_ident(table)
        self._ensure_table(t, sample=rows[0])

        cols = list(rows[0].keys())
        cols_q = ", ".join([f'"{_safe_ident(c)}"' for c in cols])
        params_q = ", ".join(["?"] * len(cols))
        values = [[r.get(c) for c in cols] for r in rows]

        cur = self.conn.cursor()
        try:
            cur.executemany(f'INSERT INTO "{t}" ({cols_q}) VALUES ({params_q});', values)
            last = self.conn.execute("SELECT last_insert_rowid();").fetchone()[0]
            n = len(rows)
            ids = list(range(int(last) - n + 1, int(last) + 1))
            if ids:
                self._last_ids[t] = ids[-1]
            return ids
        finally:
            cur.close()

    def _update(self, table: str, id_value: Any, data: Dict[str, Any]) -> bool:
        t = _safe_ident(table)
        if not data:
            return False
        sets = ", ".join([f'"{_safe_ident(k)}" = ?' for k in data.keys()])
        vals = [data[k] for k in data.keys()] + [id_value]
        cur = self.conn.cursor()
        try:
            cur.execute(f'UPDATE "{t}" SET {sets} WHERE id = ?;', vals)
            return (cur.rowcount or 0) > 0
        finally:
            cur.close()

    def _bulk_update(self, table: str, ids: List[int], patch: Dict[str, Any]) -> int:
        if not ids or not patch:
            return 0
        t = _safe_ident(table)
        sets = ", ".join([f'"{_safe_ident(k)}" = ?' for k in patch.keys()])
        vals = [patch[k] for k in patch.keys()]
        placeholders = ", ".join(["?"] * len(ids))
        sql = f'UPDATE "{t}" SET {sets} WHERE id IN ({placeholders});'
        cur = self.conn.cursor()
        try:
            cur.execute(sql, vals + ids)
            return cur.rowcount or 0
        finally:
            cur.close()

    def _delete(self, table: str, id_value: Any) -> bool:
        t = _safe_ident(table)
        cur = self.conn.cursor()
        try:
            cur.execute(f'DELETE FROM "{t}" WHERE id = ?;', (id_value,))
            return (cur.rowcount or 0) > 0
        finally:
            cur.close()

    def _select(
        self,
        table: str,
        where: Optional[Dict[str, Any]] = None,
        first: bool = False,
        order_by: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        select_fields: Optional[List[str]] = None
    ):
        t = _safe_ident(table)

        sel = "*"
        if select_fields:
            sel = ", ".join([f'"{_safe_ident(c)}"' for c in select_fields])

        sql = [f'SELECT {sel} FROM "{t}"']
        params: List[Any] = []

        if where:
            clauses: List[str] = []
            for k, v in where.items():
                col = _safe_ident(k)
                if isinstance(v, dict):
                    for op, val in v.items():
                        if op in ("=", "!=", "<", "<=", ">", ">="):
                            clauses.append(f'"{col}" {op} ?')
                            params.append(val)
                        elif op == "in":
                            if not val:
                                clauses.append("1=0")
                            else:
                                placeholders = ", ".join(["?"] * len(val))
                                clauses.append(f'"{col}" IN ({placeholders})')
                                params.extend(list(val))
                        elif op == "like":
                            clauses.append(f'"{col}" LIKE ?')
                            params.append(f"%{val}%")
                        elif op == "startswith":
                            clauses.append(f'"{col}" LIKE ?')
                            params.append(f"{val}%")
                        elif op == "endswith":
                            clauses.append(f'"{col}" LIKE ?')
                            params.append(f"%{val}")
                        elif op == "contains":
                            clauses.append(f'"{col}" LIKE ?')
                            params.append(f"%{val}%")
                        else:
                            clauses.append(f'"{col}" = ?')
                            params.append(val)
                else:
                    clauses.append(f'"{col}" = ?')
                    params.append(v)
            if clauses:
                sql.append("WHERE " + " AND ".join(clauses))

        if order_by:
            ob = order_by.strip().split()
            col = _safe_ident(ob[0])
            desc = len(ob) > 1 and ob[1].lower() == "desc"
            sql.append(f'ORDER BY "{col}" {"DESC" if desc else "ASC"}')

        if first:
            sql.append("LIMIT 1")
        else:
            if limit is not None:
                sql.append(f"LIMIT {int(limit)}")
            if offset is not None:
                sql.append(f"OFFSET {int(offset)}")

        final = " ".join(sql) + ";"
        cur = self.conn.cursor()
        try:
            cur.execute(final, params)
            rows = cur.fetchall()
        finally:
            cur.close()

        def to_dict(row: sqlite3.Row):
            return {k: row[k] for k in row.keys()}

        if first:
            return to_dict(rows[0]) if rows else None
        return [to_dict(r) for r in rows]

    # --- CRUD (kompatibilno ponašanje) ---
    def create(self, table: str, data: Dict[str, Any]):
        new_id = self._insert(table, dict(data or {}))
        return self._select(table, where={"id": new_id}, first=True)

    def read(self, table: str, query: Optional[Dict[str, Any]] = None):
        q = dict(query or {})
        # kompatibilnost: dozvoli read(table, {"id": X})
        if "id" in q and "where" not in q:
            q["where"] = {"id": q.pop("id")}
        where = q.get("where") or {}
        first = bool(q.get("first"))
        order_by = q.get("order_by")
        limit = q.get("limit")
        offset = q.get("offset")
        select_fields = q.get("select")
        return self._select(
            table,
            where=where,
            first=first,
            order_by=order_by,
            limit=limit,
            offset=offset,
            select_fields=select_fields
        )

    # --- NOVO: brzi COUNT(*) sa opcionim where filterom ---
    def count(self, table: str, where: dict | None = None) -> int:
        t = _safe_ident(table)
        sql = f'SELECT COUNT(*) FROM "{t}"'
        params: List[Any] = []
        if where:
            clauses: List[str] = []
            for k, v in where.items():
                col = _safe_ident(k)
                clauses.append(f'"{col}" = ?')
                params.append(v)
            if clauses:
                sql += " WHERE " + " AND ".join(clauses)
        cur = self.conn.cursor()
        try:
            cur.execute(sql + ";", params)
            row = cur.fetchone()
            return int(row[0]) if row else 0
        finally:
            cur.close()

    def update(self, table: str, id_value: Any, data: Dict[str, Any]) -> bool:
        return self._update(table, id_value, dict(data or {}))

    def delete(self, table: str, id_value: Any) -> bool:
        return self._delete(table, id_value)

    def get_last_id(self, table: str) -> Optional[int]:
        return self._last_ids.get(_safe_ident(table))

    def read_spec(self, spec: QuerySpec):
        fields = getattr(spec, "select", None) or None
        order_by = None
        if getattr(spec, "order", None):
            fld, direction = spec.order[0]
            order_by = fld + (" desc" if direction.lower() == "desc" else "")
        return self._select(
            spec.table,
            where=spec.where or {},
            first=bool(spec.first),
            order_by=order_by,
            limit=spec.limit,
            offset=spec.offset,
            select_fields=fields,
        )

    # --- Brze batch operacije ---
    def bulk_insert(self, table: str, records: List[Dict[str, Any]]) -> List[int]:
        if not records:
            return []
        with self.transaction():
            return self._insert_many(table, records)

    def bulk_update(self, table: str, ids: List[int], patch: Dict[str, Any]) -> int:
        if not ids or not patch:
            return 0
        with self.transaction():
            return self._bulk_update(table, ids, patch)
    
    # --- Brze batch operacije (dopune) ---
    def bulk_delete(self, table: str, ids: List[int]) -> int:
        if not ids:
            return 0
        t = _safe_ident(table)
        placeholders = ", ".join(["?"] * len(ids))
        sql = f'DELETE FROM "{t}" WHERE id IN ({placeholders});'
        with self.transaction():
            cur = self.conn.cursor()
            try:
                cur.execute(sql, ids)
                return cur.rowcount or 0
            finally:
                cur.close()

    def _ensure_unique_index(self, table: str, cols: List[str]) -> str:
        """Kreira UNIQUE indeks za upsert ako ne postoji. Vraća ime indeksa."""
        t = _safe_ident(table)
        cols_safe = [_safe_ident(c) for c in cols]
        idx = f"uniq_{t}__{'__'.join(cols_safe)}"
        cur = self.conn.cursor()
        try:
            # proveri da li postoji
            cur.execute(f'PRAGMA index_list("{t}");')
            existing = {row["name"] for row in cur.fetchall()}
            if idx not in existing:
                cols_sql = ", ".join([f'"{c}"' for c in cols_safe])
                cur.execute(f'CREATE UNIQUE INDEX IF NOT EXISTS "{idx}" ON "{t}" ({cols_sql});')
            return idx
        finally:
            cur.close()

    def upsert(self, table: str, data: Dict[str, Any], unique_by: List[str]):
        """
        Native UPSERT preko ON CONFLICT. Vraća kompletan red posle upserta.
        """
        if not unique_by:
            raise ValueError("unique_by je obavezan za upsert() u SQLiteDriver")

        t = _safe_ident(table)
        self._ensure_table(t, sample=data)
        self._ensure_unique_index(t, unique_by)

        # pripremi kolone i vrednosti
        cols = list(data.keys())
        vals = [data[c] for c in cols]
        cols_sql = ", ".join([f'"{_safe_ident(c)}"' for c in cols])
        params_sql = ", ".join(["?"] * len(cols))

        # polja koja se ažuriraju na konfliktu (sva osim id i unique_by)
        update_cols = [c for c in cols if c not in set(["id", *unique_by])]
        set_sql = ", ".join([f'"{_safe_ident(c)}"=excluded."{_safe_ident(c)}"' for c in update_cols]) or '"id"="id"'

        sql = f'''
            INSERT INTO "{t}" ({cols_sql}) VALUES ({params_sql})
            ON CONFLICT ({", ".join([f'"{_safe_ident(c)}"' for c in unique_by])})
            DO UPDATE SET {set_sql};
        '''
        with self.transaction():
            cur = self.conn.cursor()
            try:
                cur.execute(sql, vals)
            finally:
                cur.close()

        # vrati upsertovani red na osnovu unique_by filtera
        where = {k: data[k] for k in unique_by}
        return self._select(t, where=where, first=True)
    
    def bulk_upsert(self, table: str, records: List[Dict[str, Any]], unique_by: List[str]) -> Dict[str, int]:
        if not records:
            return {"created": 0, "updated": 0}
        t = _safe_ident(table)
        self._ensure_table(t, sample=records[0])
        self._ensure_unique_index(t, unique_by)

        cols = list(records[0].keys())
        cols_sql = ", ".join([f'"{_safe_ident(c)}"' for c in cols])
        params_sql = ", ".join(["?"] * len(cols))
        update_cols = [c for c in cols if c not in set(["id", *unique_by])]
        set_sql = ", ".join([f'"{_safe_ident(c)}"=excluded."{_safe_ident(c)}"' for c in update_cols]) or '"id"="id"'

        sql = f'''
            INSERT INTO "{t}" ({cols_sql}) VALUES ({params_sql})
            ON CONFLICT ({", ".join([f'"{_safe_ident(c)}"' for c in unique_by])})
            DO UPDATE SET {set_sql};
        '''

        created = 0
        updated = 0
        with self.transaction():
            cur = self.conn.cursor()
            try:
                for r in records:
                    vals = [r.get(c) for c in cols]
                    before = self._select(t, where={k: r[k] for k in unique_by}, first=True)
                    cur.execute(sql, vals)
                    after = self._select(t, where={k: r[k] for k in unique_by}, first=True)
                    if before is None and after is not None:
                        created += 1
                    elif before is not None:
                        updated += 1
            finally:
                cur.close()
        return {"created": created, "updated": updated}


