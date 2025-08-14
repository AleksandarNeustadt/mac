# =============================================================================
# File:        tests/test_bulk_speed.py
# Purpose:     Brzi benchmark za DBManager (JSON i SQLite)
# Run:         pytest -q tests/test_bulk_speed.py -s
# =============================================================================
import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import time
import shutil
from datetime import datetime, timezone

from system.db.manager import DBManager

# Parametri benchmarka
N_RECORDS = 2000
N_UPDATE  = 500
NEEDLE_EMAIL = "user1000@x.com"
NEEDLE_EVERY = 400  # na svakih 400-ti zapis ubacujemo isti email radi where testa

# Izolovani resursi (da ne diramo postojeće fajlove)
TMP_ROOT = "system/data/tmp"
JSON_ROOT = os.path.join(TMP_ROOT, "db_json_bench")
SQLITE_DB = os.path.join(TMP_ROOT, "db_sqlite_bench.db")


def _prepare_dirs():
    os.makedirs(TMP_ROOT, exist_ok=True)
    # JSON root čistimo kompletno
    if os.path.isdir(JSON_ROOT):
        shutil.rmtree(JSON_ROOT, ignore_errors=True)
    os.makedirs(JSON_ROOT, exist_ok=True)
    # SQLite db fajl brišemo ako postoji
    if os.path.exists(SQLITE_DB):
        os.remove(SQLITE_DB)


def _gen_records(n: int):
    now = datetime.now(timezone.utc).isoformat()
    recs = []
    for i in range(1, n + 1):
        email = NEEDLE_EMAIL if (i % NEEDLE_EVERY == 0) else f"user{i}@x.com"
        recs.append({
            "name": f"User {i}",
            "email": email,
            "created_at": now,
            "updated_at": now,
        })
    return recs


def _bench_for(driver_key: str, table: str, db_path_or_root: str):
    """
    driver_key: 'json' | 'sqlite'
    db_path_or_root: JSON -> root dir, SQLITE -> putanja do .db fajla
    """
    print(f"\n=== Test: {driver_key.upper()} ===")
    if driver_key == "json":
        ctx_kwargs = {"driver": "json", "db_path": db_path_or_root}
    else:
        ctx_kwargs = {"driver": "sqlite", "db_path": db_path_or_root}

    with DBManager.with_driver(**ctx_kwargs):
        # Bulk insert
        records = _gen_records(N_RECORDS)
        t0 = time.perf_counter()
        ids = DBManager.bulk_create(table, records)
        t1 = time.perf_counter()
        assert ids and len(ids) == N_RECORDS, "Bulk insert nije vratio očekivan broj ID-jeva"
        last_id = DBManager.get_last_id(table)
        print(f"Bulk insert {N_RECORDS} zapisa: {t1 - t0:.4f} s, last_id={last_id}")

        # Find_by_pk za srednji ID
        mid_id = ids[len(ids)//2]
        t0 = time.perf_counter()
        rec = DBManager.find_by_pk(table, mid_id)
        t1 = time.perf_counter()
        print(f"Find_by_pk({mid_id}): {t1 - t0:.6f} s, rec={rec}")

        # Where(email=NEEDLE_EMAIL)
        t0 = time.perf_counter()
        matches = DBManager.where(table, email=NEEDLE_EMAIL)
        t1 = time.perf_counter()
        mcount = len(matches) if isinstance(matches, list) else 0
        print(f"Where(email=...): {mcount} rezultata za {t1 - t0:.6f} s")

        # Bulk update za prvih N_UPDATE ID-jeva
        update_ids = ids[:N_UPDATE]
        t0 = time.perf_counter()
        changed = DBManager.bulk_update(table, update_ids, {"name": "Updated Name"})
        t1 = time.perf_counter()
        print(f"Bulk update {N_UPDATE} zapisa: {t1 - t0:.4f} s, promenjeno={changed}")

        # Count
        t0 = time.perf_counter()
        c = DBManager.count(table)
        t1 = time.perf_counter()
        print(f"Count: {c} zapisa za {t1 - t0:.6f} s")

        # Minimalne asercije da test ne padne bezveze
        assert c == N_RECORDS, "Count se ne poklapa sa brojem ubačenih zapisa."
        assert changed == N_UPDATE, "Bulk update nije ažurirao očekivani broj redova."


def test_bulk_speed_refactor():
    _prepare_dirs()
    # dinamičan naziv tabele da izbegnemo sudar sa starim testovima
    table_name = f"bench_users_{int(time.time())}"

    # JSON
    _bench_for("json", table_name, JSON_ROOT)

    # SQLITE
    _bench_for("sqlite", table_name, SQLITE_DB)
