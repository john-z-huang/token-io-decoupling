from __future__ import annotations

import ast
import hashlib
import importlib
import os
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest
from token_io_decoupling_core.models import DatabaseKind
from token_io_decoupling_state.migrations import runner as migration_runner
from token_io_decoupling_state.migrations.runner import (
    MigrationHistoryError,
    _open_with_migrations,
    _package_migrations,
    open_database_for_authorized_write,
    read_schema_status,
)

MIGRATION_SHA256 = {
    "worker/v0001_initial.py": ("8d28209ef1b275ca8caa19976e910c8c11907a4fef356066fec02bb28562c151"),
    "worker/v0002_worker_identity.py": (
        "3ddfaada103709276bb3b19e04845b211b5af54d192da19ef0c9c986c63f7fe2"
    ),
    "worker/v0003_evidence_dispatch.py": (
        "6e8257d7c2f5fcd974cf657d0ccc0e53994a8da98c1a57f43deeb1f5390eccef"
    ),
    "workflow/v0001_initial.py": (
        "b2d9138a70fcae3989e8da5f1ee88b7d7ec3fdbc9c22364c3b329c1c05a3f9dc"
    ),
    "workflow/v0002_control_state.py": (
        "42f26bb4815bb10f76db2d92d32ea04e7a8770d84c657b8fc174189f05b3b3b6"
    ),
    "workflow/v0003_evidence_control.py": (
        "50af3a0237a95e178efd173143dbdfab3435289be33e2629dae29250d09f8d6c"
    ),
    "workflow/v0004_session_metadata.py": (
        "ff6fa2d3a76ac8fd4cf00821744c8ce546176c599843f9429874b03df21c6937"
    ),
    "workflow/v0005_native_resolution.py": (
        "3192f172ddedfc4af8dfd8f005b18a92a7f6e42336de1f440cab1729fa8772cc"
    ),
}


def test_historical_model_import_alias_is_removed_after_successful_migration_load() -> None:
    assert "token_io_mcp" not in sys.modules
    assert "token_io_mcp.models" not in sys.modules

    migrations = _package_migrations(DatabaseKind.WORKFLOW)
    first_module = importlib.import_module(migrations[0].upgrade.__module__)

    assert getattr(first_module, "DatabaseKind", None) is DatabaseKind
    assert "token_io_mcp" not in sys.modules
    assert "token_io_mcp.models" not in sys.modules


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


def test_renamed_v1_migration_adapter_imports_in_a_fresh_process() -> None:
    script = "\n".join(
        (
            "import sys",
            "from token_io_decoupling_core.models import DatabaseKind",
            "from token_io_decoupling_mcp.migrations.workflow import v0001_initial as adapter",
            "from token_io_decoupling_state.migrations.workflow import v0001_initial as canonical",
            "from token_io_decoupling_mcp.migrations.worker import v0001_initial as worker_adapter",
            "from token_io_decoupling_state.migrations.worker import v0001_initial "
            "as worker_canonical",
            "assert adapter.VERSION == 1",
            "assert worker_adapter.VERSION == 1",
            "assert canonical.DatabaseKind is DatabaseKind",
            "assert worker_canonical.DatabaseKind is DatabaseKind",
            "assert 'token_io_mcp' not in sys.modules",
            "assert 'token_io_mcp.models' not in sys.modules",
        )
    )
    subprocess.run(
        [sys.executable, "-c", script],
        cwd=Path(__file__).parents[1],
        env={**os.environ, "PYTHONPATH": ""},
        check=True,
        capture_output=True,
        text=True,
    )


def test_released_migration_sources_keep_checkpoint_sha256() -> None:
    for kind in DatabaseKind:
        for migration in _package_migrations(kind):
            module_name = migration.upgrade.__module__
            group, module = module_name.rsplit(".", 2)[-2:]
            relative = f"{group}/{module}.py"
            module_object = importlib.import_module(module_name)
            assert module_object.__file__ is not None
            source = Path(module_object.__file__)
            assert hashlib.sha256(source.read_bytes()).hexdigest() == MIGRATION_SHA256[relative]


def test_legacy_v4_history_is_read_and_upgraded_without_rewriting_checksums(tmp_path: Path) -> None:
    database = tmp_path / "workflow.sqlite3"
    migrations = _package_migrations(DatabaseKind.WORKFLOW)
    legacy_connection = _open_with_migrations(
        database,
        DatabaseKind.WORKFLOW,
        trusted_root=tmp_path,
        migrations=migrations[:4],
    )
    legacy_connection.close()

    status = read_schema_status(database, DatabaseKind.WORKFLOW, trusted_root=tmp_path)
    assert status.current_version == 4
    old_checksums = [item.checksum for item in migrations[:4]]
    upgraded = open_database_for_authorized_write(
        database, DatabaseKind.WORKFLOW, trusted_root=tmp_path
    )
    rows = upgraded.execute(
        "SELECT version, checksum FROM schema_migrations ORDER BY version"
    ).fetchall()
    upgraded.close()
    assert [row[1] for row in rows[:4]] == old_checksums
    assert rows[-1][0] == 5


def test_core_runtime_has_no_upward_package_imports() -> None:
    source_root = (
        Path(__file__).parents[1] / "packages/token_io_decoupling_core/src/token_io_decoupling_core"
    )
    forbidden = {
        "token_io_decoupling_state",
        "token_io_decoupling_transport",
        "token_io_decoupling_workflow",
        "token_io_decoupling_root",
        "token_io_decoupling_worker",
        "token_io_decoupling_shared",
        "token_io_decoupling",
    }
    for source in source_root.glob("*.py"):
        tree = ast.parse(source.read_text(encoding="utf-8"))
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".", 1)[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".", 1)[0])
        assert not imported.intersection(forbidden), source
