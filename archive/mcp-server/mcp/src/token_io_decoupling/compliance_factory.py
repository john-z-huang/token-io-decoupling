"""Explicit startup loader for trusted operator compliance services."""

from __future__ import annotations

from importlib import import_module
from typing import Any

from token_io_decoupling_tools.compliance_preflight import CompliancePreflightService


class ComplianceFactoryError(ValueError):
    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(reason)


def load_compliance_service(factory_spec: str | None) -> CompliancePreflightService | None:
    """Load configured operator code only for an explicit startup option."""
    if factory_spec is None:
        return None
    module_name, separator, attribute_name = factory_spec.partition(":")
    if not separator or not module_name or not attribute_name or attribute_name.startswith("_"):
        raise ComplianceFactoryError("factory_spec_invalid")
    try:
        module = import_module(module_name)
        factory: Any = getattr(module, attribute_name)
    except Exception as exc:
        raise ComplianceFactoryError("factory_import_failed") from exc
    if not callable(factory):
        raise ComplianceFactoryError("factory_not_callable")
    try:
        service = factory()
    except Exception as exc:
        raise ComplianceFactoryError("factory_call_failed") from exc
    if not isinstance(service, CompliancePreflightService):
        raise ComplianceFactoryError("factory_result_invalid")
    return service
