"""Worker-side protocol for output materialization without a workflow dependency."""

from __future__ import annotations

from typing import Protocol

from token_io_decoupling_core.materialization_models import MaterializationRequest


class OutputMaterializer(Protocol):
    """Handle one already-schema-validated materialization action."""

    def execute(self, request: MaterializationRequest) -> dict[str, object]: ...

    def capability(self) -> dict[str, str]: ...
