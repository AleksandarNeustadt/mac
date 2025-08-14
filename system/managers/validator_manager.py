# ============================================================================
# File:       system/managers/validator_manager.py
# Purpose:    Centralni API za validaciju (bez CRUD registry-ja)
# Author:     Aleksandar Popovic
# Created:    2025-08-13
# ============================================================================

from __future__ import annotations
from typing import Any, Dict, Optional, Callable

from system.handlers.validator_handler import ValidatorHandler, ValidationError
from system.managers.error_manager import ErrorManager
from system.managers.log_manager import LogManager

class ValidatorManager:
    @classmethod
    def initialize(cls):
        # zadržavamo signature radi konzistencije sa ostalim managerima
        pass

    @staticmethod
    def validate(
        data: Dict[str, Any],
        schema: Dict[str, Any],
        *,
        profile: str = "create",
        partial: bool = False,
        unique_check: Optional[Callable[[str, Any, Optional[Any]], bool]] = None,
        exclude_pk: Optional[Any] = None,
    ) -> Dict[str, Any]:
        try:
            return ValidatorHandler.validate(
                data, schema, profile=profile, partial=partial,
                unique_check=unique_check, exclude_pk=exclude_pk
            )
        except ValidationError as ve:
            ErrorManager.create(ve)
            LogManager.warning(f"Validation failed: {ve.errors}")
            raise
        except Exception as e:
            ErrorManager.create(e)
            LogManager.error(f"Unexpected validation error: {e}")
            raise
