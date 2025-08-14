import os
import sys
from pathlib import Path
import pytest

# Omogući import projekta kad se testovi pokreću iz bilo kog radnog dir-a
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from system.config.env import EnvLoader
from system.db.manager.db_manager import DBManager

@pytest.fixture(scope="session", autouse=True)
def ensure_env_and_init():
    """
    - Učitaj .env i inicijalizuj DBManager (poštuje env-first).
    - Ne dira DB_DRIVER iz .env (default ostaje JSON).
    """
    EnvLoader.load()
    DBManager.initialize()
    yield
    # uredno zatvaranje
    DBManager.shutdown()

@pytest.fixture(scope="session")
def sqlite_test_path():
    """
    Koristi poseban SQLite fajl za testove (da ne diramo produkcioni app.db).
    Ako postoji SQLITE_PATH, koristi <ime>_test.<ext>; inače DB_PATH/app_test.db
    """
    env_sqlite = EnvLoader.get("SQLITE_PATH", None)
    if env_sqlite:
        p = Path(env_sqlite)
        path = str(p.with_name(p.stem + "_test" + p.suffix))
    else:
        base = EnvLoader.get("DB_PATH", "system/data/db/").rstrip("/")
        path = f"{base}/app_test.db"
    return path

def _get_id(created):
    if isinstance(created, dict):
        return created.get("id")
    return created

@pytest.fixture
def make_rows():
    """
    Helper: kreiraj 3 standardna zapisa u zadatoj tabeli i vrati (id1,id2,id3).
    Ne radi initial read kako bismo izbegli "no such table" u čistom SQLite fajlu.
    """
    def _maker(api, table: str):
        c1 = api.create(table, {"name": "Ana", "email": "ana@example.com", "age": 30})
        c2 = api.create(table, {"name": "Boris", "email": "boris@example.com", "age": 25})
        c3 = api.create(table, {"name": "Ceca", "email": "ceca@example.com", "age": 27})
        return _get_id(c1), _get_id(c2), _get_id(c3)
    return _maker
