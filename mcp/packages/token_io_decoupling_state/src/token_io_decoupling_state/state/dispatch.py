"""Dispatch operations for the state service."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from token_io_decoupling_core.models import (
    DatabaseKind,
)
from token_io_decoupling_core.state_models import (
    BindingIdentity,
    VerifiedChildBinding,
)

from token_io_decoupling_state.migrations.runner import (
    _migration_lock,
)

if TYPE_CHECKING:
    from ..service import StateService

from .common import _hash_json, _json, _now, _one
from .errors import WorkerInitializationError
from .identity import _required_control
from .native import _ensure_native_resolution


def _complete_worker_dispatch(
    self: StateService,
    parent: BindingIdentity,
    child: VerifiedChildBinding,
    event_id: str,
) -> None:
    root_path, root = self._root_database(parent, create=False)
    root_identity = (parent.project_id, parent.root_session_id, None)
    # Keep one Root file lock across each durable boundary. Each SQLite transaction still
    # commits separately in Worker-pending -> Root-ack -> Worker-confirm order.
    with _migration_lock(root_path, root, self._lock_timeout_seconds):
        with self._locked_write_connection(
            root_path,
            DatabaseKind.WORKFLOW,
            root,
            logical_identity=root_identity,
        ) as root_connection:
            event = _one(
                root_connection,
                "SELECT e.allocation_id,e.payload_json,e.payload_hash,e.status,e.sequence,"
                "o.status FROM workflow_dispatch_events AS e "
                "LEFT JOIN root_outbox AS o ON o.event_id=e.event_id WHERE e.event_id=?",
                (event_id,),
            )
            if event is None:
                raise WorkerInitializationError("committed Root dispatch event is missing")
            allocation_id, payload_json, payload_hash, event_status, sequence, outbox_status = event
            payload = json.loads(payload_json)
            if payload["worker_session_id"] != child.child_session_id:
                raise WorkerInitializationError("outbox Worker identity differs from trusted child")
            if _hash_json(payload) != payload_hash:
                raise WorkerInitializationError("Root outbox payload hash does not match")
            if event_status == "confirmed" and outbox_status in {"confirmed", None}:
                if self._worker_dispatch_is_confirmed(
                    parent,
                    child.child_session_id,
                    allocation_id,
                    event_id,
                    sequence,
                    payload,
                    payload_hash,
                ):
                    return
            _ensure_native_resolution(root_connection)

        worker_path, worker_root = self._worker_database(
            child.child_session_id, parent, create=False
        )
        if event_status == "confirmed" and not worker_path.exists():
            raise WorkerInitializationError(
                "confirmed Worker database is missing; refusing reinitialization"
            )
        worker_path, worker_root = self._worker_database(
            child.child_session_id, parent, create=not worker_path.exists()
        )
        with self._write_transaction(
            worker_path,
            DatabaseKind.WORKER,
            worker_root,
            logical_identity=(
                parent.project_id,
                parent.root_session_id,
                child.child_session_id,
            ),
        ) as worker_connection:
            identity = _one(worker_connection, "SELECT * FROM worker_identity WHERE singleton=1")
            snapshot = _json(payload)
            assignment_hash = _hash_json(payload)
            history = _one(
                worker_connection,
                "SELECT status,sequence,snapshot_json,assignment_hash "
                "FROM worker_dispatch_history WHERE event_id=?",
                (event_id,),
            )
            active = _one(
                worker_connection,
                "SELECT sequence FROM worker_active_dispatch WHERE singleton=1",
            )
            if history is not None:
                if identity is None or tuple(identity[index] for index in (1, 2, 3, 4)) != (
                    payload["project_id"],
                    payload["root_session_id"],
                    payload["worker_session_id"],
                    allocation_id,
                ):
                    raise WorkerInitializationError("Worker identity differs from dispatch history")
                if history[0] == "confirmed":
                    if history[3] != assignment_hash:
                        raise WorkerInitializationError("confirmed dispatch snapshot hash changed")
                else:
                    if identity[7] != event_id or identity[8] != assignment_hash:
                        raise WorkerInitializationError(
                            "pending dispatch is not the active Worker binding"
                        )
                    if active is None:
                        if sequence != 1:
                            raise WorkerInitializationError(
                                "pending dispatch sequence is inconsistent"
                            )
                    elif sequence <= int(active[0]):
                        raise WorkerInitializationError(
                            "pending dispatch would rewind the active pointer"
                        )
                    if history[2] != snapshot or history[3] != assignment_hash:
                        raise WorkerInitializationError(
                            "pending dispatch snapshot differs from its event"
                        )
            elif identity is None:
                if sequence != 1:
                    raise WorkerInitializationError("first Worker event must have sequence 1")
                current_snapshot = _one(
                    worker_connection,
                    "SELECT snapshot_json FROM assignment_snapshot WHERE singleton=1",
                )
                if current_snapshot is not None and current_snapshot[0] != snapshot:
                    raise WorkerInitializationError(
                        "unbound Worker store already contains another assignment"
                    )
                worker_connection.execute(
                    "INSERT OR IGNORE INTO assignment_snapshot "
                    "(singleton,snapshot_json,source_revision) VALUES (1,?,?)",
                    (snapshot, payload["source_revision"]),
                )
                worker_connection.execute(
                    """INSERT INTO worker_identity
                       (singleton,project_id,root_session_id,worker_session_id,allocation_id,
                        role,output_class,event_id,assignment_hash,revision,created_at)
                       VALUES (1,?,?,?,?,?,?,?,?,0,?)""",
                    (
                        payload["project_id"],
                        payload["root_session_id"],
                        payload["worker_session_id"],
                        allocation_id,
                        payload["role"],
                        payload["output_class"],
                        event_id,
                        assignment_hash,
                        _now(),
                    ),
                )
                worker_connection.execute(
                    "INSERT INTO worker_inbox(event_id,payload_hash,status,received_at) "
                    "VALUES (?,?,'pending',?)",
                    (event_id, payload_hash, _now()),
                )
                worker_connection.execute(
                    "INSERT INTO worker_dispatch_history "
                    "(event_id,sequence,snapshot_json,assignment_hash,status,received_at) "
                    "VALUES (?,?,?,?,'pending',?)",
                    (event_id, sequence, snapshot, assignment_hash, _now()),
                )
            else:
                expected = (
                    payload["project_id"],
                    payload["root_session_id"],
                    payload["worker_session_id"],
                    allocation_id,
                    payload["role"],
                    payload["output_class"],
                )
                actual = tuple(identity[index] for index in range(1, 7))
                if actual != expected:
                    raise WorkerInitializationError(
                        "Worker database is bound to another project, Root, session, "
                        "allocation, or role"
                    )
                if active is None or sequence <= int(active[0]):
                    raise WorkerInitializationError(
                        "missing dispatch history cannot be reconstructed behind the active pointer"
                    )
                worker_connection.execute(
                    "UPDATE assignment_snapshot SET snapshot_json=?,source_revision=? "
                    "WHERE singleton=1",
                    (snapshot, payload["source_revision"]),
                )
                worker_connection.execute(
                    "UPDATE worker_identity SET output_class=?,event_id=?,assignment_hash=? "
                    "WHERE singleton=1",
                    (payload["output_class"], event_id, assignment_hash),
                )
                worker_connection.execute(
                    "INSERT INTO worker_inbox(event_id,payload_hash,status,received_at) "
                    "VALUES (?,?,'pending',?)",
                    (event_id, payload_hash, _now()),
                )
                worker_connection.execute(
                    "INSERT INTO worker_dispatch_history "
                    "(event_id,sequence,snapshot_json,assignment_hash,status,received_at) "
                    "VALUES (?,?,?,?,'pending',?)",
                    (event_id, sequence, snapshot, assignment_hash, _now()),
                )

        with self._locked_write_connection(
            root_path,
            DatabaseKind.WORKFLOW,
            root,
            logical_identity=root_identity,
        ) as root_connection:
            _ensure_native_resolution(root_connection)
            current_event = _one(
                root_connection,
                "SELECT status FROM workflow_dispatch_events WHERE event_id=?",
                (event_id,),
            )
            if current_event is None:
                raise WorkerInitializationError("Root outbox event disappeared during dispatch")
            if current_event[0] == "pending":
                next_revision = int(_required_control(root_connection)[11]) + 1
                root_connection.execute(
                    "UPDATE root_outbox SET status='confirmed',confirmed_at=? WHERE event_id=?",
                    (_now(), event_id),
                )
                root_connection.execute(
                    "UPDATE workflow_dispatch_events SET status='confirmed',confirmed_at=? "
                    "WHERE event_id=?",
                    (_now(), event_id),
                )
                root_connection.execute(
                    "UPDATE allocations SET status='initialized' WHERE allocation_id=? "
                    "AND worker_event_id=?",
                    (allocation_id, event_id),
                )
                root_connection.execute(
                    "UPDATE workflow_control SET revision=? WHERE singleton=1",
                    (next_revision,),
                )
                self._record_binding_snapshot(root_connection, parent, next_revision)

        with self._write_transaction(
            worker_path,
            DatabaseKind.WORKER,
            worker_root,
            logical_identity=(
                parent.project_id,
                parent.root_session_id,
                child.child_session_id,
            ),
        ) as worker_connection:
            inbox = _one(
                worker_connection,
                "SELECT status,payload_hash FROM worker_inbox WHERE event_id=?",
                (event_id,),
            )
            if inbox is None or inbox[1] != payload_hash:
                raise WorkerInitializationError("Worker event receipt is missing or invalid")
            if inbox[0] == "pending":
                worker_connection.execute(
                    "UPDATE worker_inbox SET status='confirmed',confirmed_at=? WHERE event_id=?",
                    (_now(), event_id),
                )
                worker_connection.execute(
                    "UPDATE worker_dispatch_history SET status='confirmed',confirmed_at=? "
                    "WHERE event_id=?",
                    (_now(), event_id),
                )
                active = _one(
                    worker_connection,
                    "SELECT sequence FROM worker_active_dispatch WHERE singleton=1",
                )
                if active is None:
                    worker_connection.execute(
                        "INSERT INTO worker_active_dispatch VALUES (1,?,?)",
                        (event_id, sequence),
                    )
                elif sequence > int(active[0]):
                    worker_connection.execute(
                        "UPDATE worker_active_dispatch SET event_id=?,sequence=? WHERE singleton=1",
                        (event_id, sequence),
                    )


def _worker_dispatch_is_confirmed(
    self: StateService,
    parent: BindingIdentity,
    worker_session_id: str,
    allocation_id: str,
    event_id: str,
    sequence: int,
    payload: dict[str, object],
    payload_hash: str,
) -> bool:
    worker_path, worker_root = self._worker_database(worker_session_id, parent, create=False)
    if not worker_path.is_file():
        return False
    with self._read_transaction(worker_path, DatabaseKind.WORKER, worker_root) as connection:
        identity = _one(connection, "SELECT * FROM worker_identity WHERE singleton=1")
        inbox = _one(
            connection,
            "SELECT status,payload_hash FROM worker_inbox WHERE event_id=?",
            (event_id,),
        )
        history = _one(
            connection,
            "SELECT status,sequence,snapshot_json,assignment_hash "
            "FROM worker_dispatch_history WHERE event_id=?",
            (event_id,),
        )
        assignment = _one(
            connection, "SELECT snapshot_json FROM assignment_snapshot WHERE singleton=1"
        )
        active = _one(connection, "SELECT sequence FROM worker_active_dispatch WHERE singleton=1")
        expected_identity = (
            parent.project_id,
            parent.root_session_id,
            worker_session_id,
            allocation_id,
        )
        return (
            identity is not None
            and tuple(identity[index] for index in (1, 2, 3, 4)) == expected_identity
            and inbox is not None
            and inbox[0] == "confirmed"
            and inbox[1] == payload_hash
            and history is not None
            and history[0] == "confirmed"
            and int(history[1]) == sequence
            and history[2] == _json(payload)
            and history[3] == payload_hash
            and assignment is not None
            and _hash_json(json.loads(assignment[0])) == identity[8]
            and active is not None
            and int(active[0]) >= sequence
        )
