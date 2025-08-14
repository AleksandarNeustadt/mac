from system.db.manager.db_manager import DBManager

TABLE_TX = "tst_orders_tx"

def _tx_caps():
    caps = DBManager.capabilities()
    # tolerantno čitanje
    supports_tx = bool(getattr(caps, "transactions", False) or getattr(caps, "supports_transactions", False))
    supports_rb = bool(getattr(caps, "rollback", False) or getattr(caps, "supports_rollback", False))
    return supports_tx, supports_rb

def _count(table: str) -> int:
    return DBManager.count(table)

def test_transactions_on_default_driver():
    # clear by re-creating table entries fresh (no initial read)
    if _count(TABLE_TX) > 0:
        # best effort purge
        rows = DBManager.read(TABLE_TX, {})
        if isinstance(rows, list):
            for r in rows:
                if "id" in r:
                    DBManager.delete(TABLE_TX, r["id"])

    supports_tx, supports_rb = _tx_caps()

    if not supports_tx:
        DBManager.create(TABLE_TX, {"code": "ORD-1", "amount": 100})
        DBManager.create(TABLE_TX, {"code": "ORD-2", "amount": 200})
        assert _count(TABLE_TX) == 2
        return

    # commit
    with DBManager.transaction():
        DBManager.create(TABLE_TX, {"code": "ORD-1", "amount": 100})
        DBManager.create(TABLE_TX, {"code": "ORD-2", "amount": 200})
    assert _count(TABLE_TX) == 2

    if not supports_rb:
        return

    # rollback
    try:
        with DBManager.transaction():
            DBManager.create(TABLE_TX, {"code": "ORD-3", "amount": 300})
            raise RuntimeError("fail")
    except RuntimeError:
        pass
    assert DBManager.first(TABLE_TX, code="ORD-3") is None
