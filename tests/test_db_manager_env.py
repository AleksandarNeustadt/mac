from pprint import pprint
from system.db.manager.db_manager import DBManager
from system.config.env import EnvLoader

def test_env_initialize_and_active_config(ensure_env_and_init):
    cfg = DBManager.active_config()
    assert cfg.get("driver") in ("json", "sqlite")
    assert cfg.get("source") == "env"
    assert isinstance(cfg.get("params"), dict)
    # debug info postoji i .env je učitan
    info = EnvLoader.debug_info()
    assert info["loaded"] is True

def test_switch_driver_refused_without_enforce(ensure_env_and_init):
    before = DBManager.get_driver_key()
    DBManager.switch_driver("sqlite")  # bez enforce -> treba odbiti
    after = DBManager.get_driver_key()
    assert after == before  # i dalje smo na .env drajveru

def test_with_driver_restores_env_after_block(sqlite_test_path, ensure_env_and_init):
    default = DBManager.active_config()
    with DBManager.with_driver("sqlite", sqlite_test_path):
        in_ctx = DBManager.active_config()
        assert in_ctx["driver"] == "sqlite"
        assert in_ctx["source"] == "context"
    restored = DBManager.active_config()
    assert restored == default
