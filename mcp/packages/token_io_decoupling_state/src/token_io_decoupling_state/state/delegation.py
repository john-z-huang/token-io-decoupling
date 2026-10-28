"""Delegation operations for the state service."""

from __future__ import annotations

import json
import os
import sqlite3
import stat
import uuid
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import quote

from token_io_decoupling_core.models import (
    DatabaseKind,
)
from token_io_decoupling_core.state_models import (
    AllocationRole,
    BindingIdentity,
    ChangeCategory,
    CheckpointNode,
    DelegationBudgetApproval,
    DelegationUnreserveRequest,
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
    self: StateService,
    role: str,
    *,
    expected_revision: int,
    idempotency_key: str,
    budget_approval: DelegationBudgetApproval | None = None,
) -> MutationReceipt:
    binding = self._parent_binding({HostCapability.WORKFLOW_WRITE}, {HostGuard.PATH_BOUNDARY})
    try:
        role = AllocationRole(role).value
    except ValueError as exc:
        raise InvalidStateTransitionError("unknown allocation role") from exc
    if budget_approval is not None:
        budget_approval = DelegationBudgetApproval.model_validate(budget_approval)
    payload = {"role": role}
    if budget_approval is not None:
        payload["budget_approval"] = budget_approval.model_dump(mode="json")

    def mutate(connection: sqlite3.Connection, revision: int) -> dict[str, object]:
        control = _required_control(connection)
        if control[4] != "Multi-Agent Coding":
            raise InvalidStateTransitionError("Single-Agent mode has no Worker allocations")
        already_claimed = _one(
            connection,
            "SELECT allocation_id FROM allocations WHERE role=? LIMIT 1",
            (role,),
        )
        if already_claimed is not None:
            raise InvalidStateTransitionError(
                "an allocation already claims this role in this Session"
            )
        allocation = _one(
            connection,
            "SELECT allocation_id, slot FROM allocations "
            "WHERE status='unassigned' ORDER BY slot LIMIT 1",
        )
        if allocation is None:
            if budget_approval is None:
                raise InvalidStateTransitionError(
                    "locked Worker allocation budget is exhausted; "
                    "explicit user approval is required"
                )
            previous_count = int(control[5])
            if budget_approval.requested_child_count != previous_count + 1:
                raise InvalidStateTransitionError(
                    "budget approval must authorize exactly one additional child slot"
                )
            approval_ref = budget_approval.user_approval
            approval_semantic_ref = {
                "uri": approval_ref.uri,
                "content_hash": approval_ref.content_hash,
            }
            semantic_references = json.loads(control[9])
            original_source = {"uri": control[7], "content_hash": control[8]}
            if original_source not in semantic_references:
                semantic_references.append(original_source)
            if approval_semantic_ref not in semantic_references:
                semantic_references.append(approval_semantic_ref)
            connection.execute(
                "UPDATE workflow_control SET child_count=?, mode_source='explicit', "
                "source_uri=?, source_hash=?, semantic_references_json=? WHERE singleton=1",
                (
                    budget_approval.requested_child_count,
                    approval_ref.uri,
                    approval_ref.content_hash,
                    _json(semantic_references),
                ),
            )
            allocation_id = str(uuid.uuid4())
            allocation = (allocation_id, previous_count)
            connection.execute(
                "INSERT INTO allocations(allocation_id, slot, role, status, created_at) "
                "VALUES (?, ?, NULL, 'unassigned', ?)",
                (allocation_id, previous_count, _now()),
            )
        elif budget_approval is not None:
            raise InvalidStateTransitionError(
                "budget approval is accepted only after the locked budget is exhausted"
            )
        connection.execute(
            "UPDATE allocations SET role=?, status='reserved' WHERE allocation_id=?",
            (role, allocation[0]),
        )
        result: dict[str, object] = {
            "allocation_id": allocation[0],
            "slot": allocation[1],
            "role": role,
        }
        if budget_approval is not None:
            result["budget_approval_audit"] = {
                "previous_child_count": int(control[5]),
                "approved_child_count": budget_approval.requested_child_count,
                "user_approval": budget_approval.user_approval.model_dump(mode="json"),
                "reviewed_by_root": True,
                "authority_limit": (
                    "Root attestation with referenced user evidence; not cryptographic host proof"
                ),
            }
        return result

    return self._mutate_root(
        binding, "delegation_reserve", payload, expected_revision, idempotency_key, mutate
    )


def _assert_no_worker_identity_for_allocation(
    self: StateService,
    binding: BindingIdentity,
    root_connection: sqlite3.Connection,
    allocation_id: str,
) -> None:
    _, root = self._root_database(binding, create=False)
    subagents = root / "subagents"

    def directory_snapshot() -> tuple[os.stat_result | None, tuple[Path, ...]]:
        try:
            info = subagents.lstat()
        except FileNotFoundError:
            return None, ()
        except OSError as exc:
            raise InvalidStateTransitionError(
                "existing Worker identity history cannot be inspected safely"
            ) from exc
        if not stat.S_ISDIR(info.st_mode):
            raise InvalidStateTransitionError(
                "existing Worker identity history cannot be inspected safely"
            )
        try:
            entries = tuple(sorted(subagents.iterdir(), key=lambda item: item.name))
        except OSError as exc:
            raise InvalidStateTransitionError(
                "existing Worker identity history cannot be inspected safely"
            ) from exc
        return info, entries

    def same_metadata(before: os.stat_result, after: os.stat_result) -> bool:
        return (
            before.st_dev == after.st_dev
            and before.st_ino == after.st_ino
            and before.st_size == after.st_size
            and before.st_mtime_ns == after.st_mtime_ns
            and before.st_ctime_ns == after.st_ctime_ns
        )

    def reject_sidecars(worker_database: Path, *, changed: bool = False) -> None:
        message = (
            "existing Worker identity history changed while being inspected"
            if changed
            else "existing Worker identity database has an unreadable sidecar"
        )
        for suffix in ("-wal", "-shm", "-journal"):
            sidecar = Path(f"{worker_database}{suffix}")
            try:
                sidecar.lstat()
            except FileNotFoundError:
                continue
            except OSError as exc:
                raise InvalidStateTransitionError(
                    "existing Worker identity history cannot be inspected safely"
                ) from exc
            raise InvalidStateTransitionError(message)

    initial_directory_info, worker_directories = directory_snapshot()
    for worker_directory in worker_directories:
        try:
            worker_directory_info = worker_directory.lstat()
        except OSError as exc:
            raise InvalidStateTransitionError(
                "existing Worker identity history cannot be inspected safely"
            ) from exc
        if not stat.S_ISDIR(worker_directory_info.st_mode):
            raise InvalidStateTransitionError(
                "existing Worker identity history contains an unexpected path"
            )

        worker_database = worker_directory / "worker.sqlite3"
        try:
            database_info = worker_database.lstat()
        except OSError as exc:
            raise InvalidStateTransitionError(
                "existing Worker identity history is missing or inaccessible"
            ) from exc
        if not stat.S_ISREG(database_info.st_mode):
            raise InvalidStateTransitionError(
                "existing Worker identity database is not a regular file"
            )
        reject_sidecars(worker_database)

        connection: sqlite3.Connection | None = None
        try:
            database_uri = f"file:{quote(str(worker_database), safe='/')}?mode=ro&immutable=1"
            connection = sqlite3.connect(database_uri, uri=True)
            connection.execute("PRAGMA query_only = ON")
            identity_table = connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='worker_identity'"
            ).fetchone()
            if identity_table is None:
                raise InvalidStateTransitionError(
                    "existing Worker database has no verifiable identity"
                )
            columns = {
                str(row[1]) for row in connection.execute("PRAGMA table_info(worker_identity)")
            }
            if not {
                "singleton",
                "project_id",
                "root_session_id",
                "worker_session_id",
                "allocation_id",
            }.issubset(columns):
                raise InvalidStateTransitionError(
                    "existing Worker database identity schema is incomplete"
                )
            identity_rows = connection.execute(
                "SELECT singleton,project_id,root_session_id,worker_session_id,allocation_id "
                "FROM worker_identity"
            ).fetchall()
        except InvalidStateTransitionError:
            raise
        except (OSError, sqlite3.Error, ValueError) as exc:
            raise InvalidStateTransitionError(
                "existing Worker identity history is corrupt or unverifiable"
            ) from exc
        finally:
            if connection is not None:
                connection.close()

        reject_sidecars(worker_database, changed=True)
        try:
            final_directory_info = worker_directory.lstat()
            final_database_info = worker_database.lstat()
        except OSError as exc:
            raise InvalidStateTransitionError(
                "existing Worker identity history changed while being inspected"
            ) from exc
        if (
            not stat.S_ISDIR(final_directory_info.st_mode)
            or not same_metadata(worker_directory_info, final_directory_info)
            or not stat.S_ISREG(final_database_info.st_mode)
            or not same_metadata(database_info, final_database_info)
        ):
            raise InvalidStateTransitionError(
                "existing Worker identity history changed while being inspected"
            )

        if len(identity_rows) != 1:
            raise InvalidStateTransitionError(
                "existing Worker database has missing or ambiguous identity"
            )
        singleton, project_id, root_session_id, worker_session_id, recorded_allocation_id = (
            identity_rows[0]
        )
        if (
            type(singleton) is not int
            or singleton != 1
            or project_id != binding.project_id
            or root_session_id != binding.root_session_id
            or worker_session_id != worker_directory.name
            or not isinstance(recorded_allocation_id, str)
            or not recorded_allocation_id.strip()
        ):
            raise InvalidStateTransitionError(
                "existing Worker database identity is unknown or inconsistent"
            )
        if recorded_allocation_id == allocation_id:
            raise InvalidStateTransitionError(
                "Worker identity history proves this allocation may have been created"
            )
        root_allocation = _one(
            root_connection,
            "SELECT status,worker_session_id FROM allocations WHERE allocation_id=?",
            (recorded_allocation_id,),
        )
        if (
            root_allocation is None
            or root_allocation[0] not in {"bound", "initialized"}
            or root_allocation[1] != worker_session_id
        ):
            raise InvalidStateTransitionError(
                "existing Worker database identity does not match a bound Root allocation"
            )

    final_directory_info, final_worker_directories = directory_snapshot()
    if (
        (initial_directory_info is None) != (final_directory_info is None)
        or tuple(item.name for item in worker_directories)
        != tuple(item.name for item in final_worker_directories)
        or (
            initial_directory_info is not None
            and final_directory_info is not None
            and not same_metadata(initial_directory_info, final_directory_info)
        )
    ):
        raise InvalidStateTransitionError("Worker identity history changed while being inspected")


def delegation_unreserve(
    self: StateService,
    request: DelegationUnreserveRequest,
) -> MutationReceipt:
    request = DelegationUnreserveRequest.model_validate(request)
    binding = self._parent_binding({HostCapability.WORKFLOW_WRITE}, {HostGuard.PATH_BOUNDARY})
    proof = request.creation_not_started_reference.model_dump(mode="json")
    payload = {
        "allocation_id": request.allocation_id,
        "creation_not_started": request.creation_not_started,
        "creation_not_started_reference": proof,
    }

    def mutate(connection: sqlite3.Connection, revision: int) -> dict[str, object]:
        control = _required_control(connection)
        if control[4] != "Multi-Agent Coding":
            raise InvalidStateTransitionError("Single-Agent mode has no Worker allocations")
        allocation = _one(
            connection,
            "SELECT allocation_id,slot,role,status,worker_session_id,worker_event_id,output_class "
            "FROM allocations WHERE allocation_id=?",
            (request.allocation_id,),
        )
        if allocation is None or allocation[3] != "reserved" or allocation[2] is None:
            raise InvalidStateTransitionError(
                "only a reserved allocation with an assigned role can be unreserved"
            )
        if any(allocation[index] is not None for index in (4, 5, 6)):
            raise InvalidStateTransitionError(
                "allocation identity, event, or output history blocks unreserve"
            )

        for table, query in (
            (
                "Slice",
                "SELECT 1 FROM workflow_slices WHERE allocation_id=? LIMIT 1",
            ),
            (
                "Root outbox",
                "SELECT 1 FROM root_outbox WHERE allocation_id=? LIMIT 1",
            ),
            (
                "dispatch",
                "SELECT 1 FROM workflow_dispatch_events WHERE allocation_id=? LIMIT 1",
            ),
        ):
            if _one(connection, query, (request.allocation_id,)) is not None:
                raise InvalidStateTransitionError(f"{table} history blocks unreserve")

        bind_receipts = connection.execute(
            "SELECT result_json FROM operation_receipts WHERE operation='delegation_bind'"
        ).fetchall()
        for receipt_row in bind_receipts:
            try:
                receipt_result = json.loads(receipt_row[0])
            except (TypeError, json.JSONDecodeError) as exc:
                raise InvalidStateTransitionError(
                    "a delegation bind receipt cannot be verified"
                ) from exc
            if (
                not isinstance(receipt_result, dict)
                or not isinstance(receipt_result.get("allocation_id"), str)
                or not receipt_result["allocation_id"].strip()
            ):
                raise InvalidStateTransitionError("a delegation bind receipt cannot be verified")
            if receipt_result["allocation_id"] == request.allocation_id:
                raise InvalidStateTransitionError(
                    "delegation bind receipt history blocks unreserve"
                )

        _assert_no_worker_identity_for_allocation(self, binding, connection, request.allocation_id)
        cursor = connection.execute(
            "UPDATE allocations SET role=NULL,status='unassigned' "
            "WHERE allocation_id=? AND status='reserved'",
            (request.allocation_id,),
        )
        if cursor.rowcount != 1:
            raise InvalidStateTransitionError(
                "allocation changed while unreserve was being applied"
            )
        return {
            "allocation_id": request.allocation_id,
            "slot": int(allocation[1]),
            "role": None,
            "status": "unassigned",
            "creation_not_started": True,
            "proof": proof,
            "root_attestation": {
                "reviewed_by_root": True,
                "authority_limit": "Root attestation with referenced evidence; not host proof",
            },
        }

    return self._mutate_root(
        binding,
        "delegation_unreserve",
        payload,
        request.expected_revision,
        request.idempotency_key,
        mutate,
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
        if first_binding:
            duplicate_role = _one(
                connection,
                "SELECT allocation_id FROM allocations WHERE role=? "
                "AND worker_session_id IS NOT NULL "
                "AND allocation_id!=? LIMIT 1",
                (allocation[0], allocation_id),
            )
            if duplicate_role is not None:
                raise InvalidStateTransitionError(
                    "another created child already occupies this role in the current Session"
                )
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
