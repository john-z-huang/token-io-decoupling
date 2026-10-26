"""Identity helpers for the state service."""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

from token_io_decoupling_core.binding import BindingError
from token_io_decoupling_core.state_models import (
    BindingIdentity,
    HostCapability,
    HostGuard,
    VerifiedChildBinding,
    WorkflowOpenRequest,
)

from .common import _SAFE_COMPONENT, _json, _one
from .errors import InvalidStateTransitionError, WorkflowNotOpenError


def _assert_workflow_identity(
    control: sqlite3.Row,
    binding: BindingIdentity,
    request: WorkflowOpenRequest,
) -> None:
    source = request.source
    expected = (
        binding.project_id,
        binding.root_session_id,
        request.mode_count.mode.value,
        request.mode_count.child_count,
        request.mode_source,
        source.uri,
        source.content_hash,
        _json([ref.model_dump(mode="json") for ref in request.semantic_references]),
    )
    actual = tuple(control[index] for index in (1, 2, 4, 5, 6, 7, 8, 9))
    if actual != expected:
        raise InvalidStateTransitionError(
            "reopen cannot replace the locked mode/count, source, or semantic references"
        )


def _required_control(connection: sqlite3.Connection) -> sqlite3.Row:
    row = _one(connection, "SELECT * FROM workflow_control WHERE singleton=1")
    if row is None:
        raise WorkflowNotOpenError("workflow_open must initialize the bound Root workflow first")
    return row


def _validate_root_identity(connection: sqlite3.Connection, binding: BindingIdentity) -> None:
    exists = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='workflow_control'"
    ).fetchone()
    if exists is None:
        return
    row = connection.execute(
        "SELECT project_id, root_session_id FROM workflow_control WHERE singleton=1"
    ).fetchone()
    if row is None:
        return
    if (row[0], row[1]) != (binding.project_id, binding.root_session_id):
        raise BindingError("Root database identity does not match the trusted runtime binding")


def _worker_identity(
    connection: sqlite3.Connection,
    binding: BindingIdentity | VerifiedChildBinding,
) -> sqlite3.Row:
    row = _one(connection, "SELECT * FROM worker_identity WHERE singleton=1")
    if row is None:
        raise WorkflowNotOpenError(
            "Worker database has not been initialized by a verified Root binding"
        )
    if isinstance(binding, VerifiedChildBinding):
        expected = (binding.project_id, binding.root_session_id, binding.child_session_id)
    else:
        expected = (binding.project_id, binding.root_session_id, binding.current_session_id)
    if (row[1], row[2], row[3]) != expected:
        raise BindingError("Worker database identity does not match the trusted runtime binding")
    return row


def _require_confirmed_worker_event(connection: sqlite3.Connection, event_id: str) -> None:
    row = _one(connection, "SELECT status FROM worker_inbox WHERE event_id=?", (event_id,))
    if row is None or row[0] != "confirmed":
        raise WorkflowNotOpenError("Root has not confirmed the Worker assignment event")


def _validate_child_binding(
    parent: BindingIdentity,
    child: VerifiedChildBinding,
    requested_session_id: str,
) -> None:
    if (
        child.project_id != parent.project_id
        or child.root_session_id != parent.root_session_id
        or child.parent_session_id != parent.current_session_id
        or child.child_session_id != requested_session_id
    ):
        raise BindingError(
            "host child verification does not match the Root, project, and requested Session"
        )
    _require_capabilities(
        child,
        {
            HostCapability.WORKER_READ,
            HostCapability.WORKER_WRITE,
            HostCapability.WORKER_STORE_CREATE,
        },
    )
    _require_guards(
        child,
        {
            HostGuard.IDENTITY_BOUND,
            HostGuard.SESSION_BOUND,
            HostGuard.PATH_BOUNDARY,
            HostGuard.PARENT_CHILD_RELATION,
            HostGuard.WORKER_STORE_ISOLATION,
        },
    )
    _safe_component(child.child_session_id, "worker_session_id")


def _require_capabilities(
    binding: BindingIdentity | VerifiedChildBinding, required: set[HostCapability]
) -> None:
    missing = required - binding.capabilities
    if missing:
        raise BindingError(
            f"required host capabilities are unavailable: {sorted(item.value for item in missing)}"
        )


def _require_guards(
    binding: BindingIdentity | VerifiedChildBinding, required: set[HostGuard]
) -> None:
    missing = required - binding.guards
    if missing:
        raise BindingError(
            "required host permission boundaries are unavailable: "
            f"{sorted(item.value for item in missing)}"
        )


def _safe_component(value: str, label: str) -> str:
    if not _SAFE_COMPONENT.fullmatch(value) or value in {".", ".."}:
        raise BindingError(f"trusted {label} is not a safe path component")
    return value


def _ensure_directory_chain(path: Path) -> None:
    absolute = Path(os.path.abspath(path))
    current = Path(absolute.anchor)
    for component in absolute.parts[1:]:
        current /= component
        if current.is_symlink():
            raise BindingError(f"symlink in state directory path: {current}")
        if current.exists():
            if not current.is_dir():
                raise BindingError(f"state path component is not a directory: {current}")
        else:
            current.mkdir(mode=0o700)


def _ensure_derived_directory_chain(anchor: Path, path: Path, *, create: bool) -> None:
    """Trust the configured anchor (after alias normalization), reject derived symlinks."""
    anchor = Path(os.path.abspath(anchor))
    path = Path(os.path.abspath(path))
    try:
        relative = path.relative_to(anchor)
    except ValueError as exc:
        raise BindingError("derived state path escaped the configured state root") from exc
    if not anchor.exists() and not create:
        return
    if create or anchor.exists():
        _ensure_directory_chain(anchor)
    current = anchor
    for component in relative.parts:
        current /= component
        if current.is_symlink():
            raise BindingError(f"symlink in derived state directory path: {current}")
        if current.exists():
            if not current.is_dir():
                raise BindingError(f"state path component is not a directory: {current}")
        elif create:
            current.mkdir(mode=0o700)
        else:
            return
