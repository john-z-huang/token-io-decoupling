"""Storage operations for the state service."""

from __future__ import annotations

import sqlite3
from collections.abc import Generator
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import quote

from token_io_decoupling_core.binding import BindingError
from token_io_decoupling_core.models import (
    DatabaseKind,
)
from token_io_decoupling_core.state_models import (
    BindingIdentity,
    HostCapability,
    HostGuard,
    SessionRole,
    TrustedCapabilitySnapshot,
)

from token_io_decoupling_state.migrations.runner import (
    DatabaseIdentityMismatchError,
    _migration_lock,
    open_database_for_authorized_write,
    validate_connection_identity,
    validate_existing_connection,
)

if TYPE_CHECKING:
    from ..service import StateService

from .common import _hash_json, _json
from .errors import WorkflowNotOpenError
from .identity import (
    _ensure_derived_directory_chain,
    _require_capabilities,
    _require_guards,
    _safe_component,
    _validate_root_identity,
)
from .projection import _binding_payload


def _parent_binding(
    self: StateService,
    capabilities: set[HostCapability],
    guards: set[HostGuard],
) -> BindingIdentity:
    binding = self._binding_provider.current_binding()
    if binding.role is not SessionRole.PARENT:
        raise BindingError("operation requires the trusted Root parent Session")
    if binding.current_session_id != binding.root_session_id:
        raise BindingError("Root operations must run in the bound root Session")
    _require_capabilities(binding, capabilities)
    _require_guards(
        binding,
        guards | {HostGuard.IDENTITY_BOUND, HostGuard.SESSION_BOUND, HostGuard.PATH_BOUNDARY},
    )
    _safe_component(binding.project_id, "project_id")
    _safe_component(binding.root_session_id, "root_session_id")
    return binding


def _record_binding_snapshot(
    self: StateService,
    connection: sqlite3.Connection,
    binding: BindingIdentity,
    observed_revision: int,
) -> None:
    payload = _binding_payload(binding)
    snapshot_hash = _hash_json(payload)
    snapshot = TrustedCapabilitySnapshot(
        project_id=binding.project_id,
        root_session_id=binding.root_session_id,
        current_session_id=binding.current_session_id,
        role=binding.role,
        parent_session_id=binding.parent_session_id,
        capabilities=sorted(binding.capabilities, key=lambda item: item.value),
        guards=sorted(binding.guards, key=lambda item: item.value),
        snapshot_hash=snapshot_hash,
        observed_revision=observed_revision,
    )
    cursor = connection.execute(
        "UPDATE workflow_session_metadata SET capability_snapshot_json=?,"
        "capability_snapshot_hash=?,capability_observed_revision=? WHERE singleton=1",
        (
            _json(snapshot.model_dump(mode="json")),
            snapshot_hash,
            observed_revision,
        ),
    )
    if cursor.rowcount != 1:
        raise WorkflowNotOpenError("Root metadata row is missing")


def _worker_binding(self: StateService, capabilities: set[HostCapability]) -> BindingIdentity:
    binding = self._binding_provider.current_binding()
    if binding.role is not SessionRole.WORKER:
        raise BindingError("operation requires a verified Worker Session")
    if not binding.parent_session_id or binding.parent_session_id != binding.root_session_id:
        raise BindingError("Worker binding does not match its Root parent")
    _require_capabilities(binding, capabilities)
    _require_guards(
        binding,
        {
            HostGuard.IDENTITY_BOUND,
            HostGuard.SESSION_BOUND,
            HostGuard.PATH_BOUNDARY,
            HostGuard.WORKER_STORE_ISOLATION,
        },
    )
    _safe_component(binding.project_id, "project_id")
    _safe_component(binding.root_session_id, "root_session_id")
    _safe_component(binding.current_session_id, "worker_session_id")
    return binding


def _root_database(
    self: StateService, binding: BindingIdentity, *, create: bool
) -> tuple[Path, Path]:
    anchor = self._state_root.resolve(strict=False)
    root = (
        anchor
        / _safe_component(binding.project_id, "project_id")
        / _safe_component(binding.root_session_id, "root_session_id")
    )
    _ensure_derived_directory_chain(anchor, root, create=create)
    return root / "workflow.sqlite3", root


def _worker_database(
    self: StateService, worker_session_id: str, binding: BindingIdentity, *, create: bool
) -> tuple[Path, Path]:
    anchor = self._state_root.resolve(strict=False)
    root = (
        anchor
        / _safe_component(binding.project_id, "project_id")
        / _safe_component(binding.root_session_id, "root_session_id")
    )
    worker_dir = root / "subagents" / _safe_component(worker_session_id, "worker_session_id")
    _ensure_derived_directory_chain(anchor, worker_dir, create=create)
    return worker_dir / "worker.sqlite3", root


def _write_transaction(
    self: StateService,
    path: Path,
    kind: DatabaseKind,
    trusted_root: Path,
    *,
    logical_identity: tuple[str, str, str | None],
) -> Generator[sqlite3.Connection, None, None]:
    try:
        migrated = open_database_for_authorized_write(
            path,
            kind,
            trusted_root=trusted_root,
            expected_identity=logical_identity,
            lock_timeout_seconds=self._lock_timeout_seconds,
        )
    except DatabaseIdentityMismatchError as exc:
        raise BindingError(str(exc)) from exc
    migrated.close()
    with _migration_lock(path, trusted_root, self._lock_timeout_seconds):
        with self._locked_write_connection(
            path, kind, trusted_root, logical_identity=logical_identity
        ) as connection:
            yield connection


def _locked_write_connection(
    self: StateService,
    path: Path,
    kind: DatabaseKind,
    trusted_root: Path,
    *,
    logical_identity: tuple[str, str, str | None],
) -> Generator[sqlite3.Connection, None, None]:
    """Open one write transaction while the caller holds this database's migration lock."""
    uri = f"file:{quote(str(path), safe='/')}?mode=rw"
    connection = sqlite3.connect(
        uri, uri=True, timeout=self._lock_timeout_seconds, isolation_level=None
    )
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        validate_existing_connection(connection, kind)
        try:
            validate_connection_identity(connection, kind, logical_identity)
        except DatabaseIdentityMismatchError as exc:
            raise BindingError(str(exc)) from exc
        connection.execute("BEGIN IMMEDIATE")
        try:
            if kind is DatabaseKind.WORKFLOW:
                _validate_root_identity(connection, self._binding_provider.current_binding())
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
    finally:
        connection.close()


def _read_transaction(
    self: StateService,
    path: Path,
    kind: DatabaseKind,
    trusted_root: Path,
) -> Generator[sqlite3.Connection, None, None]:
    if not path.is_file():
        raise WorkflowNotOpenError("database does not exist; read access cannot initialize state")
    with _migration_lock(path, trusted_root, self._lock_timeout_seconds):
        uri = f"file:{quote(str(path), safe='/')}?mode=ro"
        connection = sqlite3.connect(
            uri, uri=True, timeout=self._lock_timeout_seconds, isolation_level=None
        )
        connection.row_factory = sqlite3.Row
        try:
            connection.execute("BEGIN")
            validate_existing_connection(connection, kind)
            if kind is DatabaseKind.WORKFLOW:
                _validate_root_identity(connection, self._binding_provider.current_binding())
            yield connection
            connection.rollback()
        finally:
            connection.close()


def _existing_write_transaction(
    self: StateService,
    path: Path,
    kind: DatabaseKind,
    trusted_root: Path,
) -> Generator[sqlite3.Connection, None, None]:
    uri = f"file:{quote(str(path), safe='/')}?mode=rw"
    with _migration_lock(path, trusted_root, self._lock_timeout_seconds):
        connection = sqlite3.connect(
            uri, uri=True, timeout=self._lock_timeout_seconds, isolation_level=None
        )
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            validate_existing_connection(connection, kind)
            connection.execute("BEGIN IMMEDIATE")
            try:
                if kind is DatabaseKind.WORKFLOW:
                    _validate_root_identity(connection, self._binding_provider.current_binding())
                yield connection
                connection.commit()
            except Exception:
                connection.rollback()
                raise
        finally:
            connection.close()
