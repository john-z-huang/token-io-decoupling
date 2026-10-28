from __future__ import annotations

import importlib
import sys
from types import ModuleType

import pytest
from token_io_decoupling_core.models import DatabaseKind
from token_io_decoupling_state.migrations import runner as migration_runner
from token_io_decoupling_state.migrations.runner import (
    MigrationHistoryError,
    _package_migrations,
)


def test_historical_model_import_alias_is_removed_after_failed_migration_load(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_import = importlib.import_module

    def fail_on_initial_migration(name: str, package: str | None = None) -> ModuleType:
        if name == "token_io_decoupling_state.migrations.workflow.v0001_initial":
            assert getattr(sys.modules["token_io_mcp.models"], "DatabaseKind", None) is DatabaseKind
            raise RuntimeError("injected migration import failure")
        return original_import(name, package)

    monkeypatch.setattr(migration_runner.importlib, "import_module", fail_on_initial_migration)
    with pytest.raises(RuntimeError, match="injected migration import failure"):
        _package_migrations(DatabaseKind.WORKFLOW)

    assert "token_io_mcp" not in sys.modules
    assert "token_io_mcp.models" not in sys.modules


def test_historical_model_import_alias_rejects_and_preserves_conflicting_modules(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    package = ModuleType("token_io_mcp")
    package.__dict__["__path__"] = []
    models = ModuleType("token_io_mcp.models")
    models.__dict__["DatabaseKind"] = object()
    package.__dict__["models"] = models
    monkeypatch.setitem(sys.modules, "token_io_mcp", package)
    monkeypatch.setitem(sys.modules, "token_io_mcp.models", models)

    with pytest.raises(
        MigrationHistoryError, match="conflicting historical migration model import"
    ):
        _package_migrations(DatabaseKind.WORKFLOW)

    assert sys.modules["token_io_mcp"] is package
    assert sys.modules["token_io_mcp.models"] is models
