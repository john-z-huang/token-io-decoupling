"""Explicit trusted startup loader for output-materializer operator configuration."""

from __future__ import annotations

from importlib import import_module
from typing import Any

from token_io_decoupling_tools.output_materialization import OutputMaterializerConfig


class OutputMaterializerFactoryError(RuntimeError):
    """A bounded startup error that does not expose operator module details."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def load_output_materializer_config(
    factory_spec: str | None,
) -> OutputMaterializerConfig | None:
    """Load operator code only when the explicit startup option is present."""
    if factory_spec is None:
        return None
    module_name, separator, attribute_name = factory_spec.partition(":")
    if not separator or not module_name or not attribute_name or attribute_name.startswith("_"):
        raise OutputMaterializerFactoryError("factory_spec_invalid")
    try:
        module = import_module(module_name)
        factory: Any = getattr(module, attribute_name)
    except Exception as exc:
        raise OutputMaterializerFactoryError("factory_import_failed") from exc
    if not callable(factory):
        raise OutputMaterializerFactoryError("factory_not_callable")
    try:
        config = factory()
    except Exception as exc:
        raise OutputMaterializerFactoryError("factory_call_failed") from exc
    if not isinstance(config, OutputMaterializerConfig):
        raise OutputMaterializerFactoryError("factory_result_invalid")
    return config
