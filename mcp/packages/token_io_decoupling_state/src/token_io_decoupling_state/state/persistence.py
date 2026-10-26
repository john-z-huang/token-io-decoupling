"""Persistence operations for the state service."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Callable
from typing import TYPE_CHECKING

from token_io_decoupling_core.models import (
    DatabaseKind,
)
from token_io_decoupling_core.state_models import (
    BindingIdentity,
    MutationReceipt,
)

if TYPE_CHECKING:
    from ..service import StateService

from .common import _hash_json, _json, _nonempty, _now, _one
from .errors import IdempotencyConflictError, RevisionConflictError, WorkflowNotOpenError
from .identity import _require_confirmed_worker_event, _required_control, _worker_identity
from .native import _ensure_native_resolution


def _mutate_root(
    self: StateService,
    binding: BindingIdentity,
    operation: str,
    payload: dict[str, object],
    expected_revision: int,
    idempotency_key: str,
    mutation: Callable[[sqlite3.Connection, int], dict[str, object]],
) -> MutationReceipt:
    key = _nonempty(idempotency_key, "idempotency_key")
    if type(expected_revision) is not int or expected_revision < 0:
        raise ValueError("expected_revision must be a non-negative integer")
    path, root = self._root_database(binding, create=True)
    payload_hash = _hash_json({"operation": operation, "payload": payload})
    with self._write_transaction(
        path,
        DatabaseKind.WORKFLOW,
        root,
        logical_identity=(binding.project_id, binding.root_session_id, None),
    ) as connection:
        control = _required_control(connection)
        current = int(control[11])
        replay = self._find_receipt(
            connection, "operation_receipts", key, operation, payload_hash, current
        )
        if replay is not None:
            return replay
        if expected_revision != current:
            raise RevisionConflictError(
                f"expected Revision {expected_revision}, current Revision is {current}"
            )
        _ensure_native_resolution(connection)
        next_revision = current + 1
        result = mutation(connection, next_revision)
        connection.execute(
            "UPDATE workflow_control SET revision=? WHERE singleton=1", (next_revision,)
        )
        self._record_binding_snapshot(connection, binding, next_revision)
        return self._store_receipt(
            connection,
            "operation_receipts",
            key,
            operation,
            payload_hash,
            result,
            next_revision,
        )


def _mutate_worker(
    self: StateService,
    binding: BindingIdentity,
    operation: str,
    payload: dict[str, object],
    expected_revision: int,
    idempotency_key: str,
    mutation: Callable[[sqlite3.Connection, int], dict[str, object]],
) -> MutationReceipt:
    key = _nonempty(idempotency_key, "idempotency_key")
    if type(expected_revision) is not int or expected_revision < 0:
        raise ValueError("expected_revision must be a non-negative integer")
    path, root = self._worker_database(binding.current_session_id, binding, create=False)
    if not path.is_file():
        raise WorkflowNotOpenError("Worker store is initialized only after Root identity binding")
    payload_hash = _hash_json({"operation": operation, "payload": payload})
    with self._existing_write_transaction(path, DatabaseKind.WORKER, root) as connection:
        identity = _worker_identity(connection, binding)
        _require_confirmed_worker_event(connection, identity[7])
        current = int(identity[9])
        replay = self._find_receipt(
            connection,
            "worker_operation_receipts",
            key,
            operation,
            payload_hash,
            current,
        )
        if replay is not None:
            return replay
        if expected_revision != current:
            raise RevisionConflictError(
                f"expected Revision {expected_revision}, current Revision is {current}"
            )
        next_revision = current + 1
        result = mutation(connection, next_revision)
        connection.execute(
            "UPDATE worker_identity SET revision=? WHERE singleton=1", (next_revision,)
        )
        return self._store_receipt(
            connection,
            "worker_operation_receipts",
            key,
            operation,
            payload_hash,
            result,
            next_revision,
        )


def _find_receipt(
    self: StateService,
    connection: sqlite3.Connection,
    table: str,
    key: str,
    operation: str,
    payload_hash: str,
    current_revision: int,
) -> MutationReceipt | None:
    if table not in {"operation_receipts", "worker_operation_receipts"}:
        raise AssertionError("untrusted receipt table")
    row = _one(
        connection,
        f"SELECT operation, payload_hash, result_json, receipt_revision FROM {table} "
        "WHERE idempotency_key=?",
        (key,),
    )
    if row is None:
        return None
    if row[0] != operation or row[1] != payload_hash:
        raise IdempotencyConflictError("idempotency key was already used with another payload")
    return MutationReceipt(
        operation=operation,
        payload_hash=payload_hash,
        result=json.loads(row[2]),
        receipt_revision=row[3],
        current_revision=current_revision,
        replayed=True,
    )


def _store_receipt(
    self: StateService,
    connection: sqlite3.Connection,
    table: str,
    key: str,
    operation: str,
    payload_hash: str,
    result: dict[str, object],
    revision: int,
) -> MutationReceipt:
    if table not in {"operation_receipts", "worker_operation_receipts"}:
        raise AssertionError("untrusted receipt table")
    connection.execute(
        f"INSERT INTO {table} "
        "(idempotency_key, operation, payload_hash, result_json, receipt_revision, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (key, operation, payload_hash, _json(result), revision, _now()),
    )
    return MutationReceipt(
        operation=operation,
        payload_hash=payload_hash,
        result=result,
        receipt_revision=revision,
        current_revision=revision,
        replayed=False,
    )
