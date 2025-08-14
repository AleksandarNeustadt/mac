import os

# Lista foldera u MAC projektu
folders = [
    "MAC/app/models",
    "MAC/app/controllers",
    "MAC/app/views/gui",
    "MAC/app/views/cli",
    "MAC/app/views/api",

    "MAC/system/cli",
    "MAC/system/db",
    "MAC/system/helpers",
    "MAC/system/managers",
    "MAC/system/config",
    "MAC/system/data/db",
    "MAC/system/data/media",
    "MAC/system/data/logs",

    "MAC/plugins/example_plugin",

    "MAC/tests"
]

# Lista fajlova i njihov sadržaj
files = {
    "MAC/README.md": "# MAC (Modularni Aplikacioni Core)\n\nOvo je osnovna struktura projekta.",

    "MAC/requirements.txt": "# Python dependencije\n",

    "MAC/main.py": "print('Pokreće se MAC aplikacija...')\n",

    "MAC/mac.py": "# CLI entry point\n\nif __name__ == '__main__':\n    print('MAC CLI aktivan')\n",

    "MAC/system/core.py": "# Sistem jezgro (opciono entry point za system logiku)\n",

    "MAC/system/config/.env": """# system/config/.env

APP_ENV=development
DEBUG=True
DB_DRIVER=sqlite
DB_NAME=app.db
API_KEY=your-api-key-here
SECRET_KEY=super-secret-key
DEFAULT_LANGUAGE=en
LOG_LEVEL=info
""",

    "MAC/system/config/config.json": """{
  "app_name": "MAC",
  "version": "0.1.0",
  "language": "en",
  "theme": "dark",
  "items_per_page": 10,
  "enable_plugins": true,
  "default_view": "gui"
}
""",

    "MAC/plugins/example_plugin/__init__.py": "# Primer plugin-a\n",

    "MAC/plugins/example_plugin/plugin.json": """{
  "name": "Example Plugin",
  "version": "1.0",
  "description": "Ovo je primer plugin-a za MAC"
}
"""
}

def create_mac_structure():
    for folder in folders:
        os.makedirs(folder, exist_ok=True)
        print(f"📁 Kreiran folder: {folder}")

    for path, content in files.items():
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
            print(f"📄 Kreiran fajl: {path}")

    print("\n✅ MAC projekat je uspešno kreiran!")

if __name__ == "__main__":
    create_mac_structure()
