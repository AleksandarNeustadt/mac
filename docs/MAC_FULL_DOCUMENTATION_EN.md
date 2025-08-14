# 📚 MAC – Modular Application Core
**Version:** v1.0.0-beta  
**Release Date:** 2025-08-13  
**Status:** Beta – stable core, ready for internal use, MVC layer in development.

---

## 1. Introduction

**MAC (Modular Application Core)** is a universal Python application core designed for:
- **Speed** – optimized for working with SQLite and JSON databases.
- **Stability** – uniform API, centralized error handling, transactions, and logging.
- **Simplicity** – syntax shorter and simpler than similar frameworks (e.g., Laravel).
- **Extensibility** – plugin system and event manager (`EventManager`) for integrations without modifying the core.

This system is the foundation for the future **MVC framework**, and the current version (`v1.0.0-beta`) includes:
- Complete **DB layer** with drivers (`SQLite`, `JSON`).
- **Managers** for files, logs, errors, and events.
- **Validation system** in the Model layer.
- **Batch/bulk operations** and upsert support.
- **Plugin system**.

---

## 2. System Architecture

### 2.1 Layer Overview
- **app/** → MVC layer (currently only models and controller/view structure).
- **system/** → Core infrastructure (databases, managers, handlers, helpers, configuration).
- **plugins/** → Modular extensions.
- **tests/** → Automated tests (PyTest).

```
┌──────────┐
│  app/    │  ← MVC layer (uses MAC Core API)
└─────┬────┘
      │
┌─────▼────┐
│ system/  │  ← DB, Managers, Handlers, Helpers, Config
└─────┬────┘
      │
┌─────▼────┐
│ plugins/ │  ← Integrations via events
└──────────┘
```

---

## 3. Directory Structure

| Folder / File              | Description |
|----------------------------|-------------|
| `app/`                     | MVC layer (models, controllers, views) |
| `system/db/`               | DB engine + drivers (SQLite/JSON) |
| `system/managers/`         | API layer for file, log, error, and event handling |
| `system/handlers/`         | Low-level handlers for I/O, validation, logs, errors |
| `system/config/`           | Configuration (EnvLoader, profiles) |
| `plugins/`                 | Extensions and integrations |
| `tests/`                   | PyTest test suite |
| `docs/`                    | Documentation |

---

## 4. Configuration

### 4.1 `EnvLoader`
- Loads `.env` from `system/config/`.
- API:
```python
EnvLoader.load()
driver = EnvLoader.get("DB_DRIVER", "json")
debug = EnvLoader.get_bool("DEBUG", False)
```

### 4.2 Environment Profiles
- `APP_ENV=development|test|production`  
- Automatically sets DB/log paths, SQLite PRAGMA settings, and log level.

---

## 5. Database Layer

### 5.1 `DBManager` and Mixins
- `DBConfigMixin` → initialization, active configuration.
- `DBCrudMixin` → CRUD API.
- `DBBulkMixin` → `bulk_create`, `bulk_update`, `bulk_delete`, `upsert`, `bulk_upsert`.
- `DBTransactionsMixin` → unified transaction context manager (works for SQLite and JSON).

### 5.2 Drivers
#### SQLiteDriver
- PRAGMA optimizations (`WAL`, `synchronous`).
- Prepared statements reuse.
- Bulk and upsert support.
- Unique indexes (`_ensure_unique_index`).

#### JSONDriver
- In-memory indexes (`_add_to_index`, `_drop_from_index`).
- Bulk operations.
- Upsert support.
- Planned atomic write (`temp → fsync → os.replace`).

### 5.3 Transactions
```python
with DBManager.transaction():
    User.create({"email": "a@b.com"})
    User.create({"email": "c@d.com"})
```

---

## 6. Model Layer

### 6.1 API
```python
user = User.create({"email": "a@b.com", "name": "Aleksandar"})
found = User.where("age", ">=", 18).order_by("created_at", "desc").first()
```

### 6.2 Validation
- `required` fields.
- `defaults` values.
- `validators` callable functions.
- `unique` check (driver-level).
- Automatic `created_at` / `updated_at` fields.

---

## 7. Managers and Handlers

- **ErrorManager** + **ErrorHandler** → centralized error handling.
- **LogManager** + **LogHandler** → logging (`info`, `warning`, `success`, `error`, `critical`).
- **EventManager** + **EventHandler** → event emission and registration.
- **FileManager** + **FileHandler** → file creation, reading, deletion, zip/unzip, listing.

---

## 8. Plugin System

- Registering a plugin hook:
```python
def register(app):
    app.events.on("db.after_create", lambda payload: print("New record:", payload))
```
- Events: `db.before_create`, `db.after_update`, `fs.file_created`, etc.

---

## 9. CLI Commands

Example:
```bash
python mac.py db:switch sqlite
python mac.py db:bench
python mac.py make:user name=Aleksandar
```

---

## 10. Testing and Benchmarking

- All CRUD tests parameterized (`json`, `sqlite`).
- Benchmark (`test_bulk_speed.py`) measures execution time for `N=1k/10k` inserts.
- Results stored in `system/data/logs/bench.json`.

---

## 11. Usage Examples

**Create & Query**
```python
User.create({"email": "a@b.com", "name": "Aleksandar"})
users = User.where("age", ">=", 18).select("id", "email").get()
```

**Transaction**
```python
with DBManager.transaction():
    User.create({"email": "x@y.com"})
    raise Exception("Rollback test")
```

**Bulk Insert**
```python
User.bulk_create([
    {"email": "a@b.com", "name": "A"},
    {"email": "b@c.com", "name": "B"}
])
```

---

## 12. Definition of Done (DoD)

- API stable, documented, and covered by tests (happy + edge cases).
- Logs with stable **error codes**.
- Benchmark results published.
- Minimum test coverage: **80%+**.
- Documentation kept up to date.

---

## 13. Version and Roadmap

**Current version:** `v1.0.0-beta`  
**Status:** Stable core, MVC integration in progress.  

**Next milestone (`v1.0.0-rc1`):**
- Atomic write for JSON.
- Structured JSON logging.
- DB event hooks.
- CLI migrations.

---
