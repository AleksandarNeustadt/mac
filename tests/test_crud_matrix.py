from system.db.manager.db_manager import DBManager

TABLE = "tst_users_matrix"

def _shape_of(api, table: str):
    row = api.first(table, email="ana@example.com")
    return {k: v for k, v in (row or {}).items() if k != "id"}

def test_crud_on_default_driver(make_rows):
    id1, id2, id3 = make_rows(DBManager, TABLE)

    r1 = DBManager.find_by_pk(TABLE, id1)
    assert r1 and r1["id"] == id1

    assert DBManager.exists(TABLE, email="boris@example.com")
    assert DBManager.count(TABLE) == 3

    ok = DBManager.update(TABLE, id1, {"age": 31})
    assert ok
    r1b = DBManager.find_by_pk(TABLE, id1)
    assert r1b["age"] == 31

    names = DBManager.pluck(TABLE, "name")
    assert set(names) >= {"Ana", "Boris", "Ceca"}

    page1 = DBManager.paginate(TABLE, page=1, per_page=2)
    page2 = DBManager.paginate(TABLE, page=2, per_page=2)
    assert len(page1) == 2 and len(page2) == 1

    sample = DBManager.select(TABLE, ["id", "name"], age=31)
    assert isinstance(sample, list) and sample and set(sample[0].keys()) == {"id", "name"}

def test_json_vs_sqlite_shape_parity(sqlite_test_path, make_rows):
    # default (json iz .env) – pripremi shape
    make_rows(DBManager, TABLE)
    shape_default = _shape_of(DBManager, TABLE)

    # sqlite (privremeno) – pripremi shape
    with DBManager.with_driver("sqlite", sqlite_test_path):
        make_rows(DBManager, TABLE)
        shape_sqlite = _shape_of(DBManager, TABLE)

    assert set(shape_default.keys()) == set(shape_sqlite.keys())
