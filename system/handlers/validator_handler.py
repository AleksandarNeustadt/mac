# ============================================================================
# File:       system/handlers/validator_handler.py
# Purpose:    Core validacija po šemi (lightweight)
# Author:     Aleksandar Popovic
# Created:    2025-08-13
# ============================================================================

from __future__ import annotations
from datetime import datetime
from typing import Any, Callable, Dict, Optional

class ValidationError(Exception):
    """Baca se kada validacija ne uspe. errors = { field: message }"""
    def __init__(self, errors: Dict[str, str]):
        super().__init__("Validation failed")
        self.errors = errors

class ValidatorHandler:
    @staticmethod
    def validate(
        data: Dict[str, Any],
        schema: Dict[str, Any],
        *,
        profile: str = "create",                  # "create" | "update"
        partial: bool = False,
        unique_check: Optional[Callable[[str, Any, Optional[Any]], bool]] = None,
        exclude_pk: Optional[Any] = None,         # koristi se kod update-a za unique
    ) -> Dict[str, Any]:
        """
        Očekivana šema (sve je opciono, uz razuman default):
        {
          "fields":    { "name": str, "email": str, "age": int, "created_at": str, "updated_at": str },
          "required":  ["name", "email"],    # ili dict po profilu: {"create":[...], "update":[...]}
          "defaults":  { "age": 18 },        # vrednost ili callable()
          "validators": {
              "email": lambda v: bool(re.match(r"...", str(v))),
              "age":   lambda v: 0 <= int(v) <= 150
          },
          "coerce":    { "age": int },       # pretvaranje tipova pre type-checka
          "transform": { "name": str.strip },# transform pre svega
          "unique":    ["email"],            # proverava se ako je prosleđen unique_check
          "immutable": ["email"]             # zabranjeno menjati kod update
        }
        """
        errors: Dict[str, str] = {}

        fields     = schema.get("fields", {}) or {}
        required   = schema.get("required", []) or []
        defaults   = schema.get("defaults", {}) or {}
        validators = schema.get("validators", {}) or {}
        coerce_map = schema.get("coerce", {}) or {}
        transform  = schema.get("transform", {}) or {}
        unique_ls  = schema.get("unique", []) or []
        immutable  = schema.get("immutable", []) or []

        # dozvoli formu required po profilu
        if isinstance(required, dict):
            required = required.get(profile, []) or []

        # 0) transform (pre svega)
        for f, fn in transform.items():
            if f in data and data[f] is not None:
                try:
                    data[f] = fn(data[f])
                except Exception as e:
                    errors[f] = f"Transform error: {e}"

        # 1) defaults (primeni ako nema vrednosti)
        for f, dv in defaults.items():
            if f not in data or data[f] is None:
                data[f] = dv() if callable(dv) else dv

        # 2) required (uz partial semantiku na update-u)
        for f in required:
            if partial and f not in data:
                continue
            if f not in data or (data.get(f) in (None, "", []) and data.get(f) != 0):
                errors[f] = "This field is required"

        # 3) immutable (na update ne sme biti menjano)
        if profile == "update":
            for f in immutable:
                if f in data:
                    errors[f] = "This field is immutable"

        # 4) coerce (pretvaranje tipova)
        for f, fn in coerce_map.items():
            if f in data and data[f] is not None:
                try:
                    data[f] = fn(data[f])
                except Exception as e:
                    errors[f] = f"Coerce error: {e}"

        # 5) type check
        for f, expected_type in fields.items():
            if f in data and data[f] is not None:
                if not isinstance(data[f], expected_type):
                    errors[f] = f"Expected type {expected_type.__name__}, got {type(data[f]).__name__}"

        # 6) custom validators (callable po polju)
        for f, rule in validators.items():
            if f in data and data[f] is not None:
                try:
                    ok = rule(data[f]) if callable(rule) else True
                    if not ok:
                        errors[f] = "Validation rule failed"
                except Exception as e:
                    errors[f] = f"Validator error: {e}"

        # 7) unique (ako postoji hook)
        if unique_check:
            for f in unique_ls:
                if f in data and data[f] is not None:
                    try:
                        # unique_check vrati True ako JE jedinstveno (nema drugog reda sa istom vrednošću)
                        if not unique_check(f, data[f], exclude_pk):
                            errors[f] = "Must be unique"
                    except Exception as e:
                        errors[f] = f"Unique check error: {e}"

        # 8) timestamps
        now_iso = datetime.utcnow().isoformat()
        if "created_at" in fields and profile == "create" and "created_at" not in data:
            data["created_at"] = now_iso
        if "updated_at" in fields:
            data["updated_at"] = now_iso

        if errors:
            raise ValidationError(errors)
        return data
