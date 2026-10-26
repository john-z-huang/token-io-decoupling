"""Delegation operations for the state service."""

from __future__ import annotations

import json
import sqlite3
import uuid
from typing import TYPE_CHECKING

from token_io_decoupling_core.models import (
    DatabaseKind,
)
from token_io_decoupling_core.state_models import (
    AllocationRole,
    ChangeCategory,
    CheckpointNode,
    HostCapability,
    HostGuard,
    MutationReceipt,
    SliceCheckResult,
    SliceSpec,
)

if TYPE_CHECKING:
    from ..service import StateService

from .common import _hash_json, _json, _nonempty, _now, _one
from .errors import InvalidStateTransitionError
from .identity import _required_control, _validate_child_binding
from .native import _ensure_native_resolution
from .slice_validation import _check_slice, _slice_spec_hash
from .validation import _epoch_snapshot


def delegation_reserve(
    self: StateService, role: str, *, expected_revision: int, idempotency_key: str
) -> MutationReceipt:
    binding = self._parent_binding({HostCapability.WORKFLOW_WRITE}, {HostGuard.PATH_BOUNDARY})
    try:
        role = AllocationRole(role).value
    except ValueError as exc:
        raise InvalidStateTransitionError("unknown allocation role") from exc
    payload = {"role": role}

    def mutate(connection: sqlite3.Connection, revision: int) -> dict[str, object]:
        control = _required_control(connection)
        if control[4] != "Multi-Agent Coding":
            raise InvalidStateTransitionError("Single-Agent mode has no Worker allocations")
        if control[5] == 1 and role != AllocationRole.PRIMARY_OUTPUT.value:
            raise InvalidStateTransitionError("a single Worker slot is reserved for Primary Output")
        allocation = _one(
            connection,
            "SELECT allocation_id, slot FROM allocations "
            "WHERE status='unassigned' ORDER BY slot LIMIT 1",
        )
        if allocation is None:
            raise InvalidStateTransitionError("locked Worker allocation budget is exhausted")
        connection.execute(
            "UPDATE allocations SET role=?, status='reserved' WHERE allocation_id=?",
            (role, allocation[0]),
        )
        return {"allocation_id": allocation[0], "slot": allocation[1], "role": role}

    return self._mutate_root(
        binding, "delegation_reserve", payload, expected_revision, idempotency_key, mutate
    )


def slice_check(self: StateService, spec: SliceSpec) -> SliceCheckResult:
    spec = SliceSpec.model_validate(spec)
    if any(category not in set(ChangeCategory) for category in spec.change_categories):
        raise InvalidStateTransitionError("unknown change category")
    binding = self._parent_binding({HostCapability.WORKFLOW_READ}, {HostGuard.PATH_BOUNDARY})
    path, root = self._root_database(binding, create=False)
    with self._read_transaction(path, DatabaseKind.WORKFLOW, root) as connection:
        context = self._rule_loader.load_context(CheckpointNode.SLICE.value)
        control_context = self._rule_loader.load_context(CheckpointNode.CONTROL.value)
        checked = _check_slice(
            connection,
            spec,
            context.context_hash,
            control_context.context_hash,
        )
        return checked.model_copy(update={"input_hash": _slice_spec_hash(spec)})


def slice_release(
    self: StateService,
    spec: SliceSpec,
    *,
    expected_revision: int,
    idempotency_key: str,
) -> MutationReceipt:
    spec = SliceSpec.model_validate(spec)
    binding = self._parent_binding({HostCapability.WORKFLOW_WRITE}, {HostGuard.PATH_BOUNDARY})
    payload = spec.model_dump(mode="json")

    def mutate(connection: sqlite3.Connection, revision: int) -> dict[str, object]:
        context = self._rule_loader.load_context(CheckpointNode.SLICE.value)
        _ensure_native_resolution(connection)
        control_context = self._rule_loader.load_context(CheckpointNode.CONTROL.value)
        checked = _check_slice(
            connection,
            spec,
            context.context_hash,
            control_context.context_hash,
        )
        if not checked.eligible:
            raise InvalidStateTransitionError(checked.reason or "slice is not eligible")
        slice_id = str(uuid.uuid4())
        control = _required_control(connection)
        if control[4] == "Single-Agent Coding":
            connection.execute(
                "INSERT INTO root_slices (slice_id,objective_uri,objective_hash,return_uri,"
                "return_hash,boundary_uri,boundary_hash,authorized_paths_json,"
                "change_categories_json,status,created_revision,created_at,output_class,"
                "write_content_memo) VALUES (?,?,?,?,?,?,?,?,?,'released',?,?,?,?)",
                (
                    slice_id,
                    spec.objective.uri,
                    spec.objective.content_hash,
                    spec.return_conditions.uri,
                    spec.return_conditions.content_hash,
                    spec.unreleased_boundary.uri,
                    spec.unreleased_boundary.content_hash,
                    _json(spec.authorized_paths),
                    _json([x.value for x in spec.change_categories]),
                    revision,
                    _now(),
                    spec.output_class.value,
                    int(spec.write_content_memo),
                ),
            )
            connection.execute("UPDATE workflow_control SET lifecycle='running' WHERE singleton=1")
            return {"slice_id": slice_id, "allocation_id": "root", "status": "released"}
        connection.execute(
            """
            INSERT INTO workflow_slices (
                slice_id, allocation_id, output_class, objective_uri, objective_hash,
                return_conditions_uri, return_conditions_hash, unreleased_boundary_uri,
                unreleased_boundary_hash, authorized_paths_json, change_categories_json,
                write_content_memo, status, created_revision, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'released', ?, ?)
            """,
            (
                slice_id,
                spec.allocation_id,
                spec.output_class.value,
                spec.objective.uri,
                spec.objective.content_hash,
                spec.return_conditions.uri,
                spec.return_conditions.content_hash,
                spec.unreleased_boundary.uri,
                spec.unreleased_boundary.content_hash,
                _json(spec.authorized_paths),
                _json(spec.change_categories),
                int(spec.write_content_memo),
                revision,
                _now(),
            ),
        )
        connection.execute("UPDATE workflow_control SET lifecycle='running' WHERE singleton=1")
        return {"slice_id": slice_id, "allocation_id": spec.allocation_id, "status": "released"}

    return self._mutate_root(
        binding, "slice_release", payload, expected_revision, idempotency_key, mutate
    )


def delegation_bind(
    self: StateService,
    allocation_id: str,
    child_session_id: str,
    *,
    expected_revision: int,
    idempotency_key: str,
) -> MutationReceipt:
    binding = self._parent_binding(
        {
            HostCapability.WORKFLOW_WRITE,
            HostCapability.CHILD_IDENTITY_CHECK,
            HostCapability.WORKER_STORE_CREATE,
        },
        {HostGuard.PATH_BOUNDARY},
    )
    allocation_id = _nonempty(allocation_id, "allocation_id")
    child_session_id = _nonempty(child_session_id, "child_session_id")
    verified = self._binding_provider.verify_child_binding(binding, child_session_id)
    _validate_child_binding(binding, verified, child_session_id)
    payload: dict[str, object] = {
        "allocation_id": allocation_id,
        "child_session_id": child_session_id,
    }

    def mutate(connection: sqlite3.Connection, revision: int) -> dict[str, object]:
        allocation = _one(
            connection,
            "SELECT role, status, worker_session_id FROM allocations WHERE allocation_id=?",
            (allocation_id,),
        )
        if (
            allocation is None
            or allocation[0] is None
            or allocation[1] not in {"reserved", "initialized"}
        ):
            raise InvalidStateTransitionError(
                "allocation must have a reserved role or an initialized reusable identity"
            )
        first_binding = allocation[1] == "reserved" and allocation[2] is None
        if not first_binding and allocation[2] != child_session_id:
            raise InvalidStateTransitionError("allocation identity is immutable once bound")
        active_slice = _one(
            connection,
            """SELECT slice_id, output_class, objective_uri, objective_hash,
                      return_conditions_uri, return_conditions_hash,
                      unreleased_boundary_uri, unreleased_boundary_hash,
                      authorized_paths_json, change_categories_json, write_content_memo,
                      created_revision
               FROM workflow_slices WHERE allocation_id=? AND status='released'""",
            (allocation_id,),
        )
        if active_slice is None:
            raise InvalidStateTransitionError(
                "a released eligible Slice is required before binding"
            )
        event_id = str(uuid.uuid4())
        event_payload = {
            "event_id": event_id,
            "project_id": binding.project_id,
            "root_session_id": binding.root_session_id,
            "worker_session_id": child_session_id,
            "allocation_id": allocation_id,
            "role": allocation[0],
            "output_class": active_slice[1],
            "slice_id": active_slice[0],
            "objective": {"uri": active_slice[2], "content_hash": active_slice[3]},
            "return_conditions": {"uri": active_slice[4], "content_hash": active_slice[5]},
            "unreleased_boundary": {"uri": active_slice[6], "content_hash": active_slice[7]},
            "authorized_paths": json.loads(active_slice[8]),
            "change_categories": json.loads(active_slice[9]),
            "write_content_memo": bool(active_slice[10]),
            "source_revision": active_slice[11],
            "epochs": _epoch_snapshot(connection).model_dump(mode="json"),
        }
        event_json = _json(event_payload)
        event_hash = _hash_json(event_payload)
        if first_binding:
            connection.execute(
                "UPDATE allocations SET status='bound', worker_session_id=?, output_class=?, "
                "worker_event_id=? WHERE allocation_id=?",
                (child_session_id, active_slice[1], event_id, allocation_id),
            )
            connection.execute(
                """INSERT INTO root_outbox
                   (event_id, allocation_id, event_type, payload_json, payload_hash,
                    status, created_at)
                   VALUES (?, ?, 'worker_assignment', ?, ?, 'pending', ?)""",
                (event_id, allocation_id, event_json, event_hash, _now()),
            )
        else:
            connection.execute(
                "UPDATE allocations SET output_class=?,worker_event_id=? WHERE allocation_id=?",
                (active_slice[1], event_id, allocation_id),
            )
        sequence = connection.execute(
            "SELECT COALESCE(MAX(sequence),0)+1 FROM workflow_dispatch_events "
            "WHERE allocation_id=?",
            (allocation_id,),
        ).fetchone()[0]
        connection.execute(
            "INSERT INTO workflow_dispatch_events "
            "(event_id,allocation_id,slice_id,sequence,payload_json,payload_hash,"
            "status,created_at) "
            "VALUES (?,?,?,?,?,?,'pending',?)",
            (
                event_id,
                allocation_id,
                active_slice[0],
                sequence,
                event_json,
                event_hash,
                _now(),
            ),
        )
        return {
            "event_id": event_id,
            "allocation_id": allocation_id,
            "worker_session_id": child_session_id,
            "sequence": sequence,
        }

    receipt = self._mutate_root(
        binding, "delegation_bind", payload, expected_revision, idempotency_key, mutate
    )
    event_id = str(receipt.result["event_id"])
    self._complete_worker_dispatch(binding, verified, event_id)
    return receipt.model_copy(update={"current_revision": self.workflow_get_state().revision})
