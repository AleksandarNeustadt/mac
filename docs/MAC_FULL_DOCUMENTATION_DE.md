# 📚 MAC – Modular Application Core
**Version:** v1.0.0-beta  
**Veröffentlichungsdatum:** 2025-08-13  
**Status:** Beta – stabiles Kernsystem, bereit für den internen Einsatz, MVC-Schicht in Entwicklung.

---

## 1. Einführung

**MAC (Modular Application Core)** ist ein universeller Python-Anwendungskern, entwickelt für:
- **Geschwindigkeit** – optimiert für die Arbeit mit SQLite- und JSON-Datenbanken.
- **Stabilität** – einheitliche API, zentrale Fehlerbehandlung, Transaktionen und Logging.
- **Einfachheit** – Syntax kürzer und einfacher als bei ähnlichen Frameworks (z. B. Laravel).
- **Erweiterbarkeit** – Plug-in-System und Ereignisverwaltung (`EventManager`) für Integrationen ohne Änderungen am Kern.

Dieses System bildet die Grundlage für ein zukünftiges **MVC-Framework**. Die aktuelle Version (`v1.0.0-beta`) beinhaltet:
- Vollständige **DB-Schicht** mit Treibern (`SQLite`, `JSON`).
- **Manager** für Dateien, Logs, Fehler und Ereignisse.
- **Validierungssystem** in der Model-Schicht.
- **Batch-/Bulk-Operationen** und Upsert-Unterstützung.
- **Plug-in-System**.

---

## 2. Systemarchitektur

### 2.1 Übersicht der Schichten
- **app/** → MVC-Schicht (derzeit nur Modelle und Struktur für Controller/Views).
- **system/** → Kerninfrastruktur (Datenbanken, Manager, Handler, Helfer, Konfiguration).
- **plugins/** → Modulare Erweiterungen.
- **tests/** → Automatisierte Tests (PyTest).

```
┌──────────┐
│  app/    │  ← MVC-Schicht (nutzt MAC Core API)
└─────┬────┘
      │
┌─────▼────┐
│ system/  │  ← DB, Manager, Handler, Helfer, Config
└─────┬────┘
      │
┌─────▼────┐
│ plugins/ │  ← Integrationen über Events
└──────────┘
```

---

## 3. Verzeichnisstruktur

| Ordner / Datei             | Beschreibung |
|----------------------------|--------------|
| `app/`                     | MVC-Schicht (Modelle, Controller, Views) |
| `system/db/`               | DB-Engine + Treiber (SQLite/JSON) |
| `system/managers/`         | API-Schicht für Datei-, Log-, Fehler- und Ereignisverwaltung |
| `system/handlers/`         | Low-Level-Handler für I/O, Validierung, Logs, Fehler |
| `system/config/`           | Konfiguration (EnvLoader, Profile) |
| `plugins/`                 | Erweiterungen und Integrationen |
| `tests/`                   | PyTest-Test-Suite |
| `docs/`                    | Dokumentation |

---

## 4. Konfiguration

### 4.1 `EnvLoader`
- Lädt `.env` aus `system/config/`.
- API:
```python
EnvLoader.load()
driver = EnvLoader.get("DB_DRIVER", "json")
debug = EnvLoader.get_bool("DEBUG", False)
```

### 4.2 Umgebungsprofile
- `APP_ENV=development|test|production`  
- Setzt automatisch DB-/Log-Pfade, SQLite-PRAGMA-Einstellungen und Log-Level.

---

## 5. Datenbankschicht

### 5.1 `DBManager` und Mixins
- `DBConfigMixin` → Initialisierung, aktive Konfiguration.
- `DBCrudMixin` → CRUD-API.
- `DBBulkMixin` → `bulk_create`, `bulk_update`, `bulk_delete`, `upsert`, `bulk_upsert`.
- `DBTransactionsMixin` → einheitlicher Transaktions-Context-Manager (funktioniert für SQLite und JSON).

### 5.2 Treiber
#### SQLiteDriver
- PRAGMA-Optimierungen (`WAL`, `synchronous`).
- Wiederverwendung von Prepared Statements.
- Bulk- und Upsert-Unterstützung.
- Eindeutige Indizes (`_ensure_unique_index`).

#### JSONDriver
- In-Memory-Indizes (`_add_to_index`, `_drop_from_index`).
- Bulk-Operationen.
- Upsert-Unterstützung.
- Geplanter Atomic Write (`temp → fsync → os.replace`).

### 5.3 Transaktionen
```python
with DBManager.transaction():
    User.create({"email": "a@b.com"})
    User.create({"email": "c@d.com"})
```

---

## 6. Model-Schicht

### 6.1 API
```python
user = User.create({"email": "a@b.com", "name": "Aleksandar"})
found = User.where("age", ">=", 18).order_by("created_at", "desc").first()
```

### 6.2 Validierung
- `required`-Felder.
- `defaults`-Werte.
- `validators`-Funktionen.
- `unique`-Prüfung (auf Treiberebene).
- Automatische Felder `created_at` / `updated_at`.

---

## 7. Manager und Handler

- **ErrorManager** + **ErrorHandler** → zentrale Fehlerbehandlung.
- **LogManager** + **LogHandler** → Logging (`info`, `warning`, `success`, `error`, `critical`).
- **EventManager** + **EventHandler** → Event-Auslösung und -Registrierung.
- **FileManager** + **FileHandler** → Dateierstellung, Lesen, Löschen, Zip/Unzip, Auflistung.

---

## 8. Plug-in-System

- Registrierung eines Plug-in-Hooks:
```python
def register(app):
    app.events.on("db.after_create", lambda payload: print("Neuer Eintrag:", payload))
```
- Events: `db.before_create`, `db.after_update`, `fs.file_created` usw.

---

## 9. CLI-Befehle

Beispiel:
```bash
python mac.py db:switch sqlite
python mac.py db:bench
python mac.py make:user name=Aleksandar
```

---

## 10. Tests und Benchmark

- Alle CRUD-Tests parametrisiert (`json`, `sqlite`).
- Benchmark (`test_bulk_speed.py`) misst die Ausführungszeit für `N=1k/10k` Inserts.
- Ergebnisse gespeichert in `system/data/logs/bench.json`.

---

## 11. Anwendungsbeispiele

**Erstellen & Abfragen**
```python
User.create({"email": "a@b.com", "name": "Aleksandar"})
users = User.where("age", ">=", 18).select("id", "email").get()
```

**Transaktion**
```python
with DBManager.transaction():
    User.create({"email": "x@y.com"})
    raise Exception("Rollback test")
```

**Bulk-Insert**
```python
User.bulk_create([
    {"email": "a@b.com", "name": "A"},
    {"email": "b@c.com", "name": "B"}
])
```

---

## 12. Definition of Done (DoD)

- API stabil, dokumentiert und durch Tests abgedeckt (Happy + Edge Cases).
- Logs mit stabilen **Error Codes**.
- Benchmark-Ergebnisse veröffentlicht.
- Mindest-Testabdeckung: **80%+**.
- Dokumentation aktuell gehalten.

---

## 13. Version und Roadmap

**Aktuelle Version:** `v1.0.0-beta`  
**Status:** Stabiles Kernsystem, MVC-Integration in Arbeit.  

**Nächster Meilenstein (`v1.0.0-rc1`):**
- Atomic Write für JSON.
- Strukturiertes JSON-Logging.
- DB-Event-Hooks.
- CLI-Migrationen.

---
