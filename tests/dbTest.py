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


def resolve_sqlite_test_path() -> str:
    """
    Odredi putanju do SQLite fajla za testiranje:
    - Ako SQLITE_PATH pokazuje na fajl → koristi <ime>_test.<ext>
    - Ako SQLITE_PATH pokazuje na folder → koristi <folder>/app_test.db
    - Ako nije postavljen → koristi DB_PATH/app_test.db
    """
    raw = (EnvLoader.get("SQLITE_PATH", "") or "").strip()
    if raw:
        p = Path(raw)
        # Ako je fajl sa ekstenzijom
        if p.suffix:
            return str(p.with_name(p.stem + "_test" + p.suffix).resolve())
        # Ako je direktorijum
        base_dir = p if p.is_dir() or not p.suffix else p.parent
        return str((base_dir / "app_test.db").resolve())

    # Fallback: DB_PATH/app_test.db
    base = Path(EnvLoader.get("DB_PATH", "system/data/db/")).resolve()
    return str((base / "app_test.db").resolve())


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
    Poseban SQLite fajl za testove.
    """
    path = resolve_sqlite_test_path()
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    print("SQLite test DB:", path)
    return path


def _get_id(created):
    if isinstance(created, dict):
        return created.get("id")
    return created


@pytest.fixture
def make_rows():
    """
    Helper: kreiraj 3 standardna zapisa u zadatoj tabeli i vrati (id1,id2,id3).
    """
    def _maker(api, table: str):
        c1 = api.create(table, {"name": "Ana", "email": "ana@example.com", "age": 30})
        c2 = api.create(table, {"name": "Boris", "email": "boris@example.com", "age": 25})
        c3 = api.create(table, {"name": "Ceca", "email": "ceca@example.com", "age": 27})
        return _get_id(c1), _get_id(c2), _get_id(c3)
    return _maker
