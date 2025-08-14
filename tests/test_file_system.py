# ============================================================================
# File:       tests/test_file_system.py
# Purpose:    Testiranje FileManager + ErrorManager + LogManager
# Author:     Aleksandar Popovic
# Created:    2025-08-07
# Updated:    2025-08-07
# ============================================================================

import os
import sys

# 📌 Omogući uvoz modula iz glavnog foldera
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from system.managers.file_manager import FileManager
from system.managers.error_manager import ErrorManager
from system.managers.log_manager import LogManager
from system.config.env import EnvLoader

def run_tests():
    print("📦 Pokrećem testiranje fajl sistema...")

    # 🔧 Inicijalizacija okruženja i menadžera
    EnvLoader.load()
    ErrorManager.initialize(dev_mode=True)
    LogManager.initialize()

    # 🔧 Provera da li logovanje radi
    LogManager.create("error", "🔧 Test log unosa - simulacija greške.")

    test_dir = "system/data/tmp"
    os.makedirs(test_dir, exist_ok=True)
    test_file = f"{test_dir}/test_file.txt"

    # 1️⃣ Kreiranje fajla
    FileManager.create(test_file, "Ovo je test.")
    assert FileManager.exists(test_file), "❌ Fajl NIJE kreiran."
    print("✅ Fajl uspešno kreiran.")

    # 2️⃣ Čitanje sadržaja
    content = FileManager.read(test_file)
    assert content == "Ovo je test.", "❌ Neispravan sadržaj fajla."
    print("✅ Sadržaj fajla je ispravan.")

    # 3️⃣ Ažuriranje fajla
    FileManager.update(test_file, "Novi sadržaj.")
    assert FileManager.read(test_file) == "Novi sadržaj.", "❌ Ažuriranje nije uspelo."
    print("✅ Fajl uspešno ažuriran.")

    # 4️⃣ Brisanje fajla
    FileManager.delete(test_file)
    assert not FileManager.exists(test_file), "❌ Fajl NIJE obrisan."
    print("✅ Fajl uspešno obrisan.")

    # 5️⃣ Simulacija greške: čitanje nepostojećeg fajla
    FileManager.read(f"{test_dir}/ne_postoji.txt")
    print("✅ Greška simulirana – očekujemo log zapis.")

    # 6️⃣ Provera da je log fajl kreiran i sadrži zapis
    log_path = EnvLoader.get("LOG_FILE_PATH", "system/data/logs/app.log")
    assert os.path.exists(log_path), "❌ Log fajl NIJE kreiran."

    with open(log_path, "r", encoding="utf-8") as f:
        log_content = f.read()
        print("📝 Sadržaj log fajla:\n")
        print(log_content)
        if "[ERROR]" not in log_content:
            print("❌ Greška NIJE zabeležena u log fajlu.")
            raise AssertionError("Log fajl ne sadrži očekivani [ERROR] unos.")

    print("✅ Log fajl kreiran i sadrži grešku.")
    print("\n🎉 SVI TESTOVI SU USPEŠNO PROŠLI!\n")

if __name__ == "__main__":
    run_tests()
