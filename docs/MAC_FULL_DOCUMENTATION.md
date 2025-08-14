# 📚 MAC – Modular Application Core
**Verzija:** v1.0.0-beta  
**Datum izdavanja:** 2025-08-13  
**Status:** Beta – stabilno jezgro, spremno za internu upotrebu, MVC sloj u izradi.

---

## 1. Uvod

**MAC (Modular Application Core)** je univerzalni Python aplikacioni core dizajniran za:
- **Brzinu** – optimizovano za rad sa SQLite i JSON bazama.
- **Stabilnost** – uniforman API, centralizovano rukovanje greškama, transakcijama i logovanjem.
- **Jednostavnost** – sintaksa kraća i jednostavnija od sličnih framework-a (npr. Laravel).
- **Proširivost** – plugin sistem i događaji (`EventManager`) za integracije bez menjanja core-a.

Ovaj sistem je osnova za budući **MVC framework**, a trenutna verzija (`v1.0.0-beta`) uključuje:
- Kompletan **DB sloj** sa driverima (`SQLite`, `JSON`).
- **Menadžere** za fajlove, logove, greške i događaje.
- **Validacioni sistem** u Model sloju.
- **Batch/bulk operacije** i upsert podršku.
- **Plugin sistem**.

---

## 2. Arhitektura sistema

### 2.1 Pregled slojeva
- **app/** → MVC sloj (trenutno samo modeli i struktura kontrolera/pogleda).
- **system/** → Core infrastruktura (baze, menadžeri, handleri, helperi, konfiguracija).
- **plugins/** → Modularna proširenja.
- **tests/** → Automatizovani testovi (PyTest).

```
┌──────────┐
│  app/    │  ← MVC sloj (koristi MAC Core API)
└─────┬────┘
      │
┌─────▼────┐
│ system/  │  ← DB, Manageri, Handleri, Helperi, Config
└─────┬────┘
      │
┌─────▼────┐
│ plugins/ │  ← Integracije putem eventova
└──────────┘
```

---

## 3. Struktura direktorijuma

| Folder / Fajl              | Opis |
|----------------------------|------|
| `app/`                     | MVC sloj (modeli, kontroleri, view-i) |
| `system/db/`               | DB engine + driveri (SQLite/JSON) |
| `system/managers/`         | API sloj za rad sa fajlovima, logovima, greškama, događajima |
| `system/handlers/`         | Niskonivski handleri za I/O, validaciju, logove, greške |
| `system/config/`           | Konfiguracija (EnvLoader, profiles) |
| `plugins/`                 | Proširenja i integracije |
| `tests/`                   | PyTest testovi |
| `docs/`                    | Dokumentacija |

---

## 4. Konfiguracija

### 4.1 `EnvLoader`
- Učitava `.env` iz `system/config/`.
- API:
```python
EnvLoader.load()
driver = EnvLoader.get("DB_DRIVER", "json")
debug = EnvLoader.get_bool("DEBUG", False)
```

### 4.2 Profili okruženja
- `APP_ENV=development|test|production`  
- Automatski određuje putanje za DB/logove, SQLite PRAGMA podešavanja i log level.

---

## 5. Baza podataka (DB sloj)

### 5.1 `DBManager` i miksevi
- `DBConfigMixin` → inicijalizacija, aktivna konfiguracija.
- `DBCrudMixin` → CRUD API.
- `DBBulkMixin` → `bulk_create`, `bulk_update`, `bulk_delete`, `upsert`, `bulk_upsert`.
- `DBTransactionsMixin` → uniformni context manager za transakcije (radi i za SQLite i za JSON).

### 5.2 Driveri
#### SQLiteDriver
- PRAGMA optimizacije (`WAL`, `synchronous`).
- Prepared statements reuse.
- Bulk i upsert podrška.
- Unique indeksi (`_ensure_unique_index`).

#### JSONDriver
- In-memory indeksi (`_add_to_index`, `_drop_from_index`).
- Bulk operacije.
- Upsert podrška.
- Planiran atomic write (`temp → fsync → os.replace`).

### 5.3 Transakcije
```python
with DBManager.transaction():
    User.create({"email": "a@b.com"})
    User.create({"email": "c@d.com"})
```

---

## 6. Model sloj

### 6.1 API
```python
user = User.create({"email": "a@b.com", "name": "Aleksandar"})
found = User.where("age", ">=", 18).order_by("created_at", "desc").first()
```

### 6.2 Validacija
- `required` polja.
- `defaults` vrednosti.
- `validators` callable funkcije.
- `unique` provera (na drajver nivou).
- Automatski `created_at`/`updated_at`.

---

## 7. Menadžeri i handleri

- **ErrorManager** + **ErrorHandler** → uniformno rukovanje greškama.
- **LogManager** + **LogHandler** → logovanje (`info`, `warning`, `success`, `error`, `critical`).
- **EventManager** + **EventHandler** → emit i registracija događaja.
- **FileManager** + **FileHandler** → kreiranje, čitanje, brisanje, zip/unzip, listing.

---

## 8. Plugin sistem

- Plugin registruje hook:
```python
def register(app):
    app.events.on("db.after_create", lambda payload: print("New record:", payload))
```
- Eventovi: `db.before_create`, `db.after_update`, `fs.file_created`, itd.

---

## 9. CLI komande

Primer:
```bash
python mac.py db:switch sqlite
python mac.py db:bench
python mac.py make:user name=Aleksandar
```

---

## 10. Testiranje i benchmark

- Svi CRUD testovi parametrizovani (`json`, `sqlite`).
- Benchmark (`test_bulk_speed.py`) meri vreme za `N=1k/10k` insert-a.
- Rezultati se čuvaju u `system/data/logs/bench.json`.

---

## 11. Primeri korišćenja

**Create & Query**
```python
User.create({"email": "a@b.com", "name": "Aleksandar"})
users = User.where("age", ">=", 18).select("id", "email").get()
```

**Transakcija**
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

- API stabilan, dokumentovan i pokriven testovima (happy + edge cases).
- Logovi sa stabilnim **error codes**.
- Benchmark rezultat objavljen.
- Minimalna pokrivenost testovima: **80%+**.
- Dokumentacija ažurna.

---

## 13. Verzije i plan razvoja

**Trenutna verzija:** `v1.0.0-beta`  
**Status:** Stabilno jezgro, MVC integracija u izradi.  

**Sledeći milestone (`v1.0.0-rc1`):**
- Atomic write za JSON.
- Structured JSON logging.
- DB event hook-ovi.
- CLI migracije.

---
