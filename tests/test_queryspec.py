from system.db.manager.db_manager import DBManager
from system.db.query import QuerySpec

TABLE = "tst_users_qs"

def test_queryspec_read_and_select():
    DBManager.create(TABLE, {"name": "Ana", "email": "ana@example.com", "age": 30})
    DBManager.create(TABLE, {"name": "Boris", "email": "boris@example.com", "age": 25})
    DBManager.create(TABLE, {"name": "Ceca", "email": "ceca@example.com", "age": 27})

    # READ_SPEC: first + select
    spec = QuerySpec(table=TABLE, where={"age": 25}, select=["id", "email"], first=True)
    row = DBManager.read_spec(spec)
    assert row and set(row.keys()) == {"id", "email"}

    # ORDER + LIMIT
    spec2 = QuerySpec(table=TABLE, where={}, first=False)
    spec2.order = [("age", "desc")]
    spec2.limit = 2
    res = DBManager.read_spec(spec2)
    assert isinstance(res, list) and len(res) == 2
    assert res[0]["age"] >= res[1]["age"]
