# ========================================================================
# File:       system/config/env.py
# Purpose:    Učitavanje .env fajla i pristup varijablama
# Author:     Aleksandar Popovic
# Created:    2025-08-07
# Updated:    2025-08-12 (auto-load, traženje root .env, helpers)
# ========================================================================

import os
from pathlib import Path
from dotenv import load_dotenv


class EnvLoader:
    """
    Jednostavan loader koji:
    - pronađe .env u root-u projekta (ili pored ovog fajla kao fallback),
    - učita ga samo jednom (idempotentno),
    - oslanja se na os.environ za overrides (npr. u testovima).
    """
    _loaded = False
    _loaded_path: Path | None = None

    @staticmethod
    def _find_env_path() -> Path | None:
        # Pokušaj 1: projektni root (dve ili tri nivoa iznad ovog fajla)
        here = Path(__file__).resolve()
        candidates = [
            here.parents[3] / ".env" if len(here.parents) >= 4 else None,  # npr. <repo>/.env
            here.parents[2] / ".env" if len(here.parents) >= 3 else None,  # fallback
            here.parents[1] / ".env" if len(here.parents) >= 2 else None,  # fallback
            Path(__file__).parent / ".env",                                  # lokalno pored env.py
        ]
        for p in candidates:
            if p and p.exists():
                return p
        return None

    @classmethod
    def load(cls, force: bool = False) -> None:
        if cls._loaded and not force:
            return
        env_path = cls._find_env_path()
        if env_path:
            load_dotenv(dotenv_path=env_path, override=False)  # .env -> os.environ (ne pregazi već postavljeno)
            cls._loaded_path = env_path
        else:
            # Ako nema .env, i dalje radimo sa čistim os.environ
            cls._loaded_path = None
        cls._loaded = True

    @classmethod
    def get(cls, key: str, default=None):
        if not cls._loaded:
            cls.load()
        return os.getenv(key, default)

    @classmethod
    def get_bool(cls, key: str, default: bool = False) -> bool:
        val = cls.get(key, None)
        if val is None:
            return default
        return str(val).strip().lower() in ("1", "true", "yes", "y", "on")

    @classmethod
    def debug_info(cls) -> dict:
        """Povratna informacija gde je učitan .env i da li je aktivan autoload."""
        return {
            "loaded": cls._loaded,
            "env_path": str(cls._loaded_path) if cls._loaded_path else None,
        }
