"""Explicit trusted startup injection for read-only Serena Memory tools."""

from __future__ import annotations

from importlib import import_module
from typing import Any

from token_io_decoupling_workflow.serena_memory import SerenaMemoryReadService


class SerenaMemoryFactoryError(Exception):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def load_serena_memory_service(factory_spec: str | None) -> SerenaMemoryReadService | None:
    """Import operator code only for the explicit MODULE:CALLABLE startup option."""
    if factory_spec is None:
        return None
    module_name, separator, attribute_name = factory_spec.partition(":")
    if not separator or not module_name or not attribute_name or attribute_name.startswith("_"):
        raise SerenaMemoryFactoryError("factory_spec_invalid")
    try:
        module = import_module(module_name)
        factory: Any = getattr(module, attribute_name)
    except Exception as exc:
        raise SerenaMemoryFactoryError("factory_import_failed") from exc
    if not callable(factory):
        raise SerenaMemoryFactoryError("factory_not_callable")
    try:
        service = factory()
    except Exception as exc:
        raise SerenaMemoryFactoryError("factory_call_failed") from exc
    if not isinstance(service, SerenaMemoryReadService):
        raise SerenaMemoryFactoryError("factory_result_invalid")
    return service
