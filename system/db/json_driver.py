# ========================================================================
# File:       system/db/json_driver.py
# Purpose:    Brži i bezbedniji JSON drajver (atomski upis, mini-indeksi, batch)
#             Kompatibilan sa starim i novim pozivima (dict i list where stil)
#             read_spec prihvata QuerySpec ili (table, spec_dict)
# Author:     Aleksandar Popovic
# Updated:    2025-08-13
# ========================================================================

from __future__ import annotations
import os, json, threading, tempfile
from typing import Any, Dict, List, Optional, Tuple, Union
from contextlib import contextmanager

from system.db.base_driver import BaseDBDriver

# --- atomic write helpers ----------------------------------------------------

def _fsync_dir(path: str) -> None:
    d = os.path.dirname(os.path.abspath(path)) or "."
    try:
        fd = os.open(d, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    except Exception:
        pass

def _atomic_write(path: str, text: str) -> None:
    folder = os.path.dirname(path) or "."
    os.makedirs(folder, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", delete=False, dir=folder, encoding="utf-8") as tf:
        tmp = tf.name
        tf.write(text)
        tf.flush()
        os.fsync(tf.fileno())
    os.replace(tmp, path)
    _fsync_dir(path)

_LOCK = threading.RLock()

# ---------------------------------------------------------------------------

class JSONDriver(BaseDBDriver):
    """
    Uniformni konstruktor: __init__(**params)  -> očekuje 'root' (default: system/data/db)
    Kompatibilan API:
      - capabilities(), transaction()
      - create(table, record) -> int
      - read(table, query_dict) -> List[dict]
      - update(table, spec_dict, patch) -> int
      - delete(table, spec_dict) -> int
      - get_last_id(table) -> Optional[int]
      - read_spec(QuerySpec | (table, spec_dict)) -> List[dict]
      - bulk_insert, bulk_update
    """
    def __init__(self, **params):
        root = params.get("root") or os.path.join("system", "data", "db")
        self.root = root
        os.makedirs(self.root, exist_ok=True)
        self._cache: Dict[str, List[Dict[str, Any]]] = {}
        self._last_id: Dict[str, int] = {}
        self._indexes: Dict[str, Dict[str, Dict[Any, set]]] = {}  # table -> field -> value -> set(ids)
        self._tx_depth = 0
        self._snapshot = None
        self._snapshot_last = None

    # -------- capabilities ---------------------------------------------------
    def capabilities(self) -> Dict[str, Any]:
        return {
            "transactions": True,
            "nested_transactions": True,
            "bulk_insert": True,
            "select_project": True,
            "raw_sql": False,
        }

    # -------- storage --------------------------------------------------------
    def _get_table_path(self, table: str) -> str:
        return os.path.join(self.root, f"{table}.json")

    def _load_table(self, table: str) -> List[Dict[str, Any]]:
        path = self._get_table_path(table)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        else:
            data = []
        self._cache[table] = data
        last = 0
        for r in data:
            rid = r.get("id")
            if isinstance(rid, int) and rid > last:
                last = rid
        self._last_id[table] = last
        self._indexes[table] = {}
        return data

    def _ensure_loaded(self, table: str) -> List[Dict[str, Any]]:
        if table not in self._cache:
            return self._load_table(table)
        return self._cache[table]

    def _save_table(self, table: str) -> None:
        path = self._get_table_path(table)
        _atomic_write(path, json.dumps(self._cache[table], ensure_ascii=False))

    def _generate_id(self, table: str) -> int:
        last = self._last_id.get(table, 0) + 1
        self._last_id[table] = last
        return last

    def _add_to_index(self, table: str, record: Dict[str, Any], fields: List[str]):
        idx_tbl = self._indexes.setdefault(table, {})
        for f in fields:
            val = record.get(f)
            if val is None:
                continue
            idx = idx_tbl.setdefault(f, {})
            s = idx.setdefault(val, set())
            s.add(record["id"])

    def _drop_from_index(self, table: str, record: Dict[str, Any]):
        idx_tbl = self._indexes.get(table, {})
        for f, buckets in idx_tbl.items():
            val = record.get(f)
            if val in buckets:
                buckets[val].discard(record["id"])
                if not buckets[val]:
                    buckets.pop(val, None)

    # -------- transactions ---------------------------------------------------
    @contextmanager
    def transaction(self):
        with _LOCK:
            self._tx_depth += 1
            if self._tx_depth == 1:
                self._snapshot = {t: [r.copy() for r in data] for t, data in self._cache.items()}
                self._snapshot_last = self._last_id.copy()
            try:
                yield
                self._tx_depth -= 1
                if self._tx_depth == 0:
                    for t in list(self._cache.keys()):
                        self._save_table(t)
                    self._snapshot = None
                    self._snapshot_last = None
            except Exception:
                self._tx_depth -= 1
                self._cache = {t: [r.copy() for r in data] for t, data in self._snapshot.items()}
                self._last_id = self._snapshot_last.copy()
                self._indexes = {}
                for t, data in self._cache.items():
                    for rec in data:
                        self._add_to_index(t, rec, ["id"])
                self._snapshot = None
                self._snapshot_last = None
                raise

    # -------- where normalization -------------------------------------------
    @staticmethod
    def _normalize_where(where: Union[None, Dict[str, Any], List[Tuple[str, str, Any]]]) -> List[Tuple[str, str, Any]]:
        """
        Prihvata:
          - None
          - dict: {"email": "a@x", "age": {">=": 18}, "id": {"in": [1,2]}}
          - list: [("email","==","a@x"), ("age",">=",18), ("id","in",[1,2])]
        Vraća listu trojki (field, op, value) sa normalizovanim operatorima.
        """
        if where is None:
            return []

        # već je list[(f,op,v)]
        if isinstance(where, list):
            out: List[Tuple[str, str, Any]] = []
            for item in where:
                if isinstance(item, (tuple, list)) and len(item) == 3:
                    f, op, v = item
                    # normalizuj '=' u '=='
                    op = "==" if op == "=" else op
                    out.append((str(f), str(op), v))
            return out

        # dict stil
        if isinstance(where, dict):
            triples: List[Tuple[str, str, Any]] = []
            for k, v in where.items():
                if isinstance(v, dict):
                    for op, val in v.items():
                        opn = "==" if op == "=" else str(op)
                        triples.append((str(k), opn, val))
                else:
                    triples.append((str(k), "==", v))
            return triples

        # fallback — nepoznat format
        return []

    # -------- filtering/ordering/limit --------------------------------------
    def _apply_where(self, data: List[Dict[str, Any]], where_norm: List[Tuple[str, str, Any]], table: str) -> List[Dict[str, Any]]:
        if not where_norm:
            return data

        # indeks brzi put (samo za '==')
        idx_tbl = self._indexes.get(table, {})
        eq_filters = [(f, v) for (f, op, v) in where_norm if op == "==" and f in idx_tbl]
        if eq_filters:
            sets = []
            for f, v in eq_filters:
                ids = idx_tbl[f].get(v, set())
                sets.append(ids)
            if sets:
                candidate_ids = set.intersection(*sets) if len(sets) > 1 else sets[0]
                data = [d for d in data if d.get("id") in candidate_ids]

        for (field, op, value) in where_norm:
            if op == "==":
                data = [d for d in data if d.get(field) == value]
            elif op == "!=":
                data = [d for d in data if d.get(field) != value]
            elif op == "in":
                data = [d for d in data if d.get(field) in (value or [])]
            elif op == "like":
                s = str(value).lower()
                data = [d for d in data if s in str(d.get(field, "")).lower()]
            elif op == ">":
                data = [d for d in data if d.get(field) is not None and d.get(field) > value]
            elif op == "<":
                data = [d for d in data if d.get(field) is not None and d.get(field) < value]
            elif op == ">=":
                data = [d for d in data if d.get(field) is not None and d.get(field) >= value]
            elif op == "<=":
                data = [d for d in data if d.get(field) is not None and d.get(field) <= value]
        return data

    @staticmethod
    def _apply_order_limit_offset(data: List[Dict[str, Any]], spec: Dict[str, Any]) -> List[Dict[str, Any]]:
        # order: podržavamo i stari "order_by": "col desc" i novi "order": [("col","desc")]
        if "order" in spec and isinstance(spec["order"], list) and spec["order"]:
            for (field, direction) in spec["order"]:
                data.sort(key=lambda x: x.get(field), reverse=(str(direction).lower() == "desc"))
        elif "order_by" in spec and isinstance(spec["order_by"], str):
            parts = spec["order_by"].strip().split()
            field = parts[0]
            desc = len(parts) > 1 and parts[1].lower() == "desc"
            data.sort(key=lambda x: x.get(field), reverse=desc)

        off = spec.get("offset", 0) or 0
        lim = spec.get("limit", None)
        if lim is not None:
            data = data[off: off + lim]
        else:
            data = data[off:]

        # select projection (stari: select_fields u read_spec; novi: select: [...])
        select = spec.get("select")
        if select:
            data = [{k: r.get(k) for k in select} for r in data]
        return data

    # -------- CRUD -----------------------------------------------------------
    def create(self, table: str, record: Dict[str, Any]) -> int:
        with _LOCK:
            data = self._ensure_loaded(table)
            if "id" not in record or record["id"] is None:
                record["id"] = self._generate_id(table)
            data.append(record)
            self._add_to_index(table, record, ["id"])
            if self._tx_depth == 0:
                self._save_table(table)
            return record["id"]

    def read(self, table: str, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        with _LOCK:
            data = list(self._ensure_loaded(table))
            # normalizuj where bez obzira na stil
            where_norm = self._normalize_where(query.get("where"))
            data = self._apply_where(data, where_norm, table)
            # old flag: first
            if query.get("first"):
                data = self._apply_order_limit_offset(data, {"limit": 1})
                return data[0] if data else None
            # order/limit/offset/select
            data = self._apply_order_limit_offset(data, query)
            return data

    def update(self, table: str, spec: Dict[str, Any], patch: Dict[str, Any]) -> int:
        with _LOCK:
            data = self._ensure_loaded(table)
            targets = self.read_spec(table, spec)  # koristi isti normalization put
            changed = 0
            target_ids = {t["id"] for t in (targets or [])}
            for i, rec in enumerate(data):
                if rec.get("id") in target_ids:
                    self._drop_from_index(table, rec)
                    rec.update(patch)
                    self._add_to_index(table, rec, ["id"])
                    changed += 1
            if changed and self._tx_depth == 0:
                self._save_table(table)
            return changed

    def delete(self, table: str, spec: Dict[str, Any]) -> int:
        with _LOCK:
            data = self._ensure_loaded(table)
            targets = self.read_spec(table, spec)
            target_ids = {t["id"] for t in (targets or [])}
            kept = []
            deleted = 0
            for rec in data:
                if rec.get("id") in target_ids:
                    self._drop_from_index(table, rec)
                    deleted += 1
                else:
                    kept.append(rec)
            self._cache[table] = kept
            if deleted and self._tx_depth == 0:
                self._save_table(table)
            return deleted

    def get_last_id(self, table: str) -> Optional[int]:
        return self._last_id.get(table)

    # -------- read_spec (kompatibilno) --------------------------------------
    def read_spec(self, arg1, spec: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Podržava:
          - read_spec(QuerySpec)
          - read_spec(table: str, spec_dict: dict)
        """
        # varijanta A: QuerySpec objekat
        if spec is None and hasattr(arg1, "table"):
            qs = arg1
            table = qs.table
            # QuerySpec.where je obično dict
            normalized = {
                "where": qs.where or {},
                "limit": qs.limit,
                "offset": qs.offset,
                "select": getattr(qs, "select", None),
            }
            if getattr(qs, "order", None):
                normalized["order"] = qs.order  # [("col","asc/desc")]
            return self.read(table, normalized)

        # varijanta B: (table, spec_dict)
        table = arg1
        query = dict(spec or {})
        # harmonizuj ključeve (dozvoljavamo i "first")
        return self.read(table, query)

    # -------- Bulk -----------------------------------------------------------
    def bulk_insert(self, table: str, records: List[Dict[str, Any]]) -> List[int]:
        with self.transaction():
            ids = []
            for r in records:
                ids.append(self.create(table, r))
            return ids

    def bulk_update(self, table: str, where_ids: List[int], patch: Dict[str, Any]) -> int:
        spec = {"where": [("id", "in", list(where_ids))]}
        with self.transaction():
            return self.update(table, spec, patch)
    
    # --- NOVO: count() za JSON driver (brzo, koristi keš ako postoji) ---
    def count(self, table: str, where: dict | None = None) -> int:
        # Pokušaj da koristiš in-memory keš ako ga drajver održava
        try:
            cache = getattr(self, "_tables", None) or getattr(self, "_cache", None)
            if isinstance(cache, dict) and table in cache:
                rows = cache[table]
            else:
                rows = self._load_table(table)
        except Exception:
            # konzervativno – uvek možemo da učitamo sa diska
            rows = self._load_table(table)

        if where:
            try:
                norm = self._normalize_where(where)
                rows = self._apply_where(rows, norm)
            except Exception:
                # ultra-fallback ako privatne metode nisu dostupne
                def _match(row):
                    for k, v in where.items():
                        if isinstance(v, dict):
                            # minimalni set operatera; po potrebi proširi
                            if "=" in v and row.get(k) != v["="]:
                                return False
                            elif "in" in v and row.get(k) not in set(v["in"]):
                                return False
                            elif "like" in v and v["like"] not in str(row.get(k, "")):
                                return False
                        else:
                            if row.get(k) != v:
                                return False
                    return True
                rows = [r for r in rows if _match(r)]

        # Ako rows može biti generator, pretvori u list za tačan len()
        try:
            return len(rows)
        except TypeError:
            return sum(1 for _ in rows)
    
    # --- NOVO: brisanje u seriji po ID-jevima ---
    def bulk_delete(self, table: str, ids: List[int]) -> int:
        self._ensure_loaded(table)
        ids_set = set(int(i) for i in (ids or []))
        if not ids_set:
            return 0
        before = len(self._tables[table]["rows"])
        # skini iz indeksa pre brisanja
        for row in list(self._tables[table]["rows"]):
            if int(row.get("id", -1)) in ids_set:
                self._drop_from_index(table, row)
        # filtriraj
        self._tables[table]["rows"] = [r for r in self._tables[table]["rows"] if int(r.get("id", -1)) not in ids_set]
        self._save_table(table)
        return before - len(self._tables[table]["rows"])

    # --- NOVO: single upsert po unique_by poljima ---
    def upsert(self, table: str, data: Dict[str, Any], unique_by: List[str]):
        if not unique_by:
            raise ValueError("unique_by je obavezan za upsert() u JSONDriver")
        self._ensure_loaded(table)
        # nadji postojeći red
        filt = {k: data[k] for k in unique_by if k in data}
        if len(filt) != len(unique_by):
            raise ValueError("Sva unique_by polja moraju biti prisutna u data payload-u.")
        norm = self._normalize_where(filt)
        rows = self._apply_where(self._tables[table]["rows"], norm)
        if rows:
            # update first match
            row = rows[0]
            rid = int(row["id"])
            self._drop_from_index(table, row)
            row.update(data)
            self._add_to_index(table, row)
            self._save_table(table)
            return row
        else:
            # create
            new_row = dict(data)
            new_row["id"] = self._generate_id(table)
            self._tables[table]["rows"].append(new_row)
            self._add_to_index(table, new_row)
            self._save_table(table)
            return new_row

    # --- NOVO: bulk upsert ---
    def bulk_upsert(self, table: str, records: List[Dict[str, Any]], unique_by: List[str]) -> Dict[str, int]:
        if not records:
            return {"created": 0, "updated": 0}
        self._ensure_loaded(table)
        created = 0
        updated = 0
        for r in records:
            filt = {k: r[k] for k in unique_by if k in r}
            if len(filt) != len(unique_by):
                raise ValueError("Sva unique_by polja moraju biti prisutna u svakom zapisu (bulk_upsert).")
            norm = self._normalize_where(filt)
            rows = self._apply_where(self._tables[table]["rows"], norm)
            if rows:
                row = rows[0]
                self._drop_from_index(table, row)
                row.update(r)
                self._add_to_index(table, row)
                updated += 1
            else:
                new_row = dict(r)
                new_row["id"] = self._generate_id(table)
                self._tables[table]["rows"].append(new_row)
                self._add_to_index(table, new_row)
                created += 1
        self._save_table(table)
        return {"created": created, "updated": updated}

