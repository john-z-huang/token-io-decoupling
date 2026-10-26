"""Worker operations for the state service."""

from __future__ import annotations

import json
import sqlite3
import uuid
from typing import TYPE_CHECKING

from token_io_decoupling_core.binding import BindingError
from token_io_decoupling_core.models import (
    DatabaseKind,
)
from token_io_decoupling_core.state_models import (
    BlockerRecord,
    HostCapability,
    HostGuard,
    MutationReceipt,
    OutputClass,
    ProgressRecord,
    WorkerState,
)

if TYPE_CHECKING:
    from ..service import StateService

from .common import _hash_json, _json, _nonempty, _now, _one
from .errors import InvalidStateTransitionError, WorkflowNotOpenError
from .identity import _require_confirmed_worker_event, _validate_child_binding, _worker_identity


def worker_get_assignment(self: StateService) -> dict[str, object]:
    binding = self._worker_binding({HostCapability.WORKER_READ})
    path, root = self._worker_database(binding.current_session_id, binding, create=False)
    with self._read_transaction(path, DatabaseKind.WORKER, root) as connection:
        identity = _worker_identity(connection, binding)
        _require_confirmed_worker_event(connection, identity[7])
        row = _one(connection, "SELECT snapshot_json FROM assignment_snapshot WHERE singleton=1")
        if row is None:
            raise WorkflowNotOpenError("Worker assignment snapshot is missing")
        snapshot = json.loads(row[0])
        if _hash_json(snapshot) != identity[8]:
            raise BindingError("Worker assignment snapshot hash differs from its bound identity")
        return snapshot


def worker_get_dispatch(self: StateService, event_id: str) -> dict[str, object]:
    """Read this bound Worker's immutable dispatch history by event identity."""
    binding = self._worker_binding({HostCapability.WORKER_READ})
    path, root = self._worker_database(binding.current_session_id, binding, create=False)
    with self._read_transaction(path, DatabaseKind.WORKER, root) as connection:
        identity = _worker_identity(connection, binding)
        row = _one(
            connection,
            "SELECT snapshot_json,assignment_hash,status,sequence "
            "FROM worker_dispatch_history WHERE event_id=?",
            (_nonempty(event_id, "event_id"),),
        )
        if row is None:
            raise WorkflowNotOpenError("Worker dispatch event not found")
        snapshot = json.loads(row[0])
        if _hash_json(snapshot) != row[1]:
            raise BindingError("dispatch history snapshot hash differs from its receipt")
        if row[2] != "confirmed":
            raise WorkflowNotOpenError("Worker dispatch event is not confirmed")
        if identity[3] != binding.current_session_id:
            raise BindingError("dispatch history is not bound to this Worker")
        return {"event_id": event_id, "sequence": row[3], "snapshot": snapshot}


def worker_get_state(self: StateService) -> WorkerState:
    binding = self._worker_binding({HostCapability.WORKER_READ})
    path, root = self._worker_database(binding.current_session_id, binding, create=False)
    with self._read_transaction(path, DatabaseKind.WORKER, root) as connection:
        identity = _worker_identity(connection, binding)
        _require_confirmed_worker_event(connection, identity[7])
        progress = [
            json.loads(row[0])
            for row in connection.execute(
                "SELECT progress_json FROM worker_progress ORDER BY updated_at, progress_key"
            )
        ]
        blockers = [
            json.loads(row[0])
            for row in connection.execute(
                "SELECT blocker_json FROM worker_blockers ORDER BY reported_at, blocker_id"
            )
        ]
        return WorkerState(
            allocation_id=identity[4],
            worker_session_id=identity[3],
            role=identity[5],
            output_class=OutputClass(identity[6]),
            revision=identity[9],
            progress=progress,
            blockers=blockers,
        )


def worker_get_recovery_context(self: StateService) -> dict[str, object]:
    return {
        "assignment": self.worker_get_assignment(),
        "state": self.worker_get_state().model_dump(mode="json"),
    }


def worker_record_progress(
    self: StateService,
    record: ProgressRecord,
    *,
    expected_revision: int,
    idempotency_key: str,
) -> MutationReceipt:
    record = ProgressRecord.model_validate(record)
    binding = self._worker_binding({HostCapability.WORKER_WRITE})
    payload = record.model_dump(mode="json")

    def mutate(connection: sqlite3.Connection, revision: int) -> dict[str, object]:
        key = str(uuid.uuid4())
        connection.execute(
            "INSERT INTO worker_progress(progress_key, progress_json, updated_at) VALUES (?, ?, ?)",
            (key, _json(payload), _now()),
        )
        return {"progress_id": key, "status": record.status}

    return self._mutate_worker(
        binding, "worker_record_progress", payload, expected_revision, idempotency_key, mutate
    )


def worker_report_blocker(
    self: StateService,
    blocker: BlockerRecord,
    *,
    expected_revision: int,
    idempotency_key: str,
) -> MutationReceipt:
    blocker = BlockerRecord.model_validate(blocker)
    binding = self._worker_binding({HostCapability.WORKER_WRITE})
    payload = blocker.model_dump(mode="json")

    def mutate(connection: sqlite3.Connection, revision: int) -> dict[str, object]:
        connection.execute(
            """INSERT INTO worker_blockers(blocker_id, blocker_json, reported_at)
               VALUES (?, ?, ?) ON CONFLICT(blocker_id) DO UPDATE SET
               blocker_json=excluded.blocker_json, reported_at=excluded.reported_at""",
            (blocker.blocker_id, _json(payload), _now()),
        )
        return {"blocker_id": blocker.blocker_id, "recorded": True}

    return self._mutate_worker(
        binding, "worker_report_blocker", payload, expected_revision, idempotency_key, mutate
    )


def parent_get_worker_summary(self: StateService, allocation_id: str) -> WorkerState:
    binding = self._parent_binding(
        {
            HostCapability.WORKFLOW_READ,
            HostCapability.CHILD_IDENTITY_CHECK,
            HostCapability.PARENT_SUMMARY_READ,
        },
        {HostGuard.PATH_BOUNDARY},
    )
    allocation_id = _nonempty(allocation_id, "allocation_id")
    root_path, root = self._root_database(binding, create=False)
    with self._read_transaction(root_path, DatabaseKind.WORKFLOW, root) as connection:
        row = _one(
            connection,
            "SELECT worker_session_id, status FROM allocations WHERE allocation_id=?",
            (allocation_id,),
        )
        if row is None or row[0] is None or row[1] != "initialized":
            raise InvalidStateTransitionError("Worker allocation is not initialized")
        worker_session_id = row[0]
    verified = self._binding_provider.verify_child_binding(binding, worker_session_id)
    _validate_child_binding(binding, verified, worker_session_id)
    if HostCapability.PARENT_SUMMARY_READ not in verified.capabilities:
        raise BindingError("host did not authorize parent summary access to this Worker")
    worker_path, worker_root = self._worker_database(worker_session_id, binding, create=False)
    with self._read_transaction(worker_path, DatabaseKind.WORKER, worker_root) as connection:
        identity = _worker_identity(connection, verified)
        _require_confirmed_worker_event(connection, identity[7])
        progress = [
            json.loads(item[0])
            for item in connection.execute(
                "SELECT progress_json FROM worker_progress ORDER BY updated_at, progress_key"
            )
        ]
        blockers = [
            json.loads(item[0])
            for item in connection.execute(
                "SELECT blocker_json FROM worker_blockers ORDER BY reported_at, blocker_id"
            )
        ]
        return WorkerState(
            allocation_id=identity[4],
            worker_session_id=identity[3],
            role=identity[5],
            output_class=OutputClass(identity[6]),
            revision=identity[9],
            progress=progress,
            blockers=blockers,
        )
