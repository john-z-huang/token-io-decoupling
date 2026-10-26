"""Control operations for the state service."""

from __future__ import annotations

import json
import uuid
from typing import TYPE_CHECKING

from pydantic import TypeAdapter
from token_io_decoupling_core.models import (
    DatabaseKind,
)
from token_io_decoupling_core.state_models import (
    CheckpointConfirmationTransition,
    CheckpointNode,
    ControlTransitionRequest,
    EpochAdvanceTransition,
    HostCapability,
    HostGuard,
    MutationReceipt,
    NativeReconcileResolutionTransition,
    NativeReconcileTransition,
    SessionAuditTransition,
    WorkflowTransitionRequest,
)

if TYPE_CHECKING:
    from ..service import StateService

from .common import _hash_json, _json, _nonempty, _now, _one
from .errors import InvalidStateTransitionError, RevisionConflictError
from .identity import _required_control
from .native import _ensure_native_resolution
from .validation import (
    _epoch_snapshot,
    _evaluation_epochs_are_current,
    _validate_acceptance_history,
)


def workflow_transition(self: StateService, request: WorkflowTransitionRequest) -> MutationReceipt:
    request = TypeAdapter(WorkflowTransitionRequest).validate_python(request)
    if isinstance(request, SessionAuditTransition):
        return self._update_session_audit(request)
    if isinstance(request, EpochAdvanceTransition):
        return self.workflow_advance_epoch(
            request.dimension,
            expected_revision=request.expected_revision,
            idempotency_key=request.idempotency_key,
        )
    if isinstance(request, NativeReconcileTransition):
        result = self.workflow_reconcile(
            request.snapshot,
            confirm=True,
            expected_revision=request.expected_revision,
            idempotency_key=request.idempotency_key,
        )
        reconcile_payload = {
            "snapshot": request.snapshot.model_dump(mode="json"),
            "confirm": True,
            "expected_revision": request.expected_revision,
        }
        return MutationReceipt(
            operation="workflow_reconcile",
            payload_hash=_hash_json(
                {"operation": "workflow_reconcile", "payload": reconcile_payload}
            ),
            result=result.model_dump(mode="json"),
            receipt_revision=result.result_revision,
            current_revision=result.current_revision,
            replayed=result.replayed,
        )
    if isinstance(request, NativeReconcileResolutionTransition):
        return self._resolve_native_reconcile(request)
    if isinstance(request, CheckpointConfirmationTransition):
        return self._confirm_checkpoint(request)
    assert isinstance(request, ControlTransitionRequest)
    binding = self._parent_binding({HostCapability.WORKFLOW_WRITE}, {HostGuard.PATH_BOUNDARY})
    path, root = self._root_database(binding, create=False)
    payload = request.model_dump(mode="json")
    with self._write_transaction(
        path,
        DatabaseKind.WORKFLOW,
        root,
        logical_identity=(binding.project_id, binding.root_session_id, None),
    ) as connection:
        control = _required_control(connection)
        current = int(control[11])
        idempotency_key = _nonempty(request.idempotency_key, "idempotency_key")
        payload_hash = _hash_json({"operation": "workflow_transition", "payload": payload})
        replay = self._find_receipt(
            connection,
            "operation_receipts",
            idempotency_key,
            "workflow_transition",
            payload_hash,
            current,
        )
        if replay is not None:
            return replay
        if current != request.expected_revision:
            raise RevisionConflictError("workflow changed after evaluation")
        _ensure_native_resolution(connection)
        ev = _one(
            connection,
            "SELECT node_id,outcome,branch,implementation_epoch,documentation_epoch,"
            "git_metadata_epoch,result_revision,slice_ids_json,evidence_request_id "
            "FROM checkpoint_evaluations "
            "WHERE evaluation_id=?",
            (request.evaluation_id,),
        )
        if ev is None or ev[0] != "control" or ev[1] != "ready" or ev[2] != request.outcome:
            raise InvalidStateTransitionError(
                "transition requires a current ready Control evaluation for that outcome"
            )
        epochs = _epoch_snapshot(connection)
        if ev[6] != current or tuple(ev[3:6]) != (
            epochs.implementation_content,
            epochs.documentation,
            epochs.git_metadata,
        ):
            raise InvalidStateTransitionError("Control evaluation is stale")
        evaluated_slices = json.loads(ev[7])
        requested_slices = sorted(request.slice_ids)
        if requested_slices != evaluated_slices:
            raise InvalidStateTransitionError(
                "Control transition must name the exact Slice set bound by its evaluation"
            )
        if request.outcome == "continue" and ev[8] is not None:
            returned = _one(
                connection,
                "SELECT status,returned_revision FROM control_evidence_requests WHERE request_id=?",
                (ev[8],),
            )
            if (
                returned is None
                or returned[0] != "returned"
                or returned[1] is None
                or int(returned[1]) <= int(control[13])
            ):
                raise InvalidStateTransitionError(
                    "Continue requires fresh returned evidence after Native recovery"
                )
        current_rules = self._rule_loader.load_context("control")
        stored_rule = _one(
            connection,
            "SELECT rule_hash FROM checkpoint_evaluations WHERE evaluation_id=?",
            (request.evaluation_id,),
        )
        if stored_rule is None or stored_rule[0] != current_rules.context_hash:
            raise InvalidStateTransitionError(
                "Control rule or owner content changed after evaluation"
            )
        if request.outcome == "continue":
            if _one(connection, "SELECT 1 FROM control_transitions WHERE outcome='stop'"):
                raise InvalidStateTransitionError("Stop is terminal")
            if evaluated_slices:
                marks = ",".join("?" for _ in evaluated_slices)
                connection.execute(
                    f"UPDATE workflow_slices SET status='closed' "
                    f"WHERE status='released' AND slice_id IN ({marks})",
                    evaluated_slices,
                )
                connection.execute(
                    f"UPDATE root_slices SET status='closed' "
                    f"WHERE status='released' AND slice_id IN ({marks})",
                    evaluated_slices,
                )
        elif request.outcome == "amend":
            if request.amended_contract is None:
                raise InvalidStateTransitionError("Amend requires a new Contract reference")
            if evaluated_slices:
                marks = ",".join("?" for _ in evaluated_slices)
                connection.execute(
                    f"UPDATE workflow_slices SET status='closed' "
                    f"WHERE status='released' AND slice_id IN ({marks})",
                    evaluated_slices,
                )
                connection.execute(
                    f"UPDATE root_slices SET status='closed' "
                    f"WHERE status='released' AND slice_id IN ({marks})",
                    evaluated_slices,
                )
            connection.execute(
                "UPDATE workflow_control SET source_uri=?,source_hash=? WHERE singleton=1",
                (request.amended_contract.uri, request.amended_contract.content_hash),
            )
            connection.execute(
                "UPDATE checkpoint_evaluations SET outcome='incomplete' "
                "WHERE node_id IN ('contract','decision')"
            )
        else:
            if evaluated_slices:
                marks = ",".join("?" for _ in evaluated_slices)
                connection.execute(
                    f"UPDATE workflow_slices SET status='closed' "
                    f"WHERE status='released' AND slice_id IN ({marks})",
                    evaluated_slices,
                )
                connection.execute(
                    f"UPDATE root_slices SET status='closed' "
                    f"WHERE status='released' AND slice_id IN ({marks})",
                    evaluated_slices,
                )
            connection.execute(
                "UPDATE workflow_control SET lifecycle='interrupted' WHERE singleton=1"
            )
        new_revision = current + 1
        transition_id = str(uuid.uuid4())
        connection.execute(
            "INSERT INTO control_transitions "
            "(transition_id,evaluation_id,outcome,slice_ids_json,from_revision,to_revision,"
            "created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                transition_id,
                request.evaluation_id,
                request.outcome,
                _json(evaluated_slices),
                current,
                new_revision,
                _now(),
            ),
        )
        connection.execute(
            "UPDATE workflow_control SET revision=? WHERE singleton=1", (new_revision,)
        )
        self._record_binding_snapshot(connection, binding, new_revision)
        if request.outcome == "continue" and ev[8] is not None:
            connection.execute(
                "UPDATE control_evidence_requests SET status='resolved' WHERE request_id=?",
                (ev[8],),
            )
        return self._store_receipt(
            connection,
            "operation_receipts",
            idempotency_key,
            "workflow_transition",
            payload_hash,
            {"transition_id": transition_id, "outcome": request.outcome},
            new_revision,
        )


def _update_session_audit(self: StateService, request: SessionAuditTransition) -> MutationReceipt:
    binding = self._parent_binding({HostCapability.WORKFLOW_WRITE}, {HostGuard.PATH_BOUNDARY})
    path, root = self._root_database(binding, create=False)
    payload = request.model_dump(mode="json")
    payload_hash = _hash_json({"operation": "workflow_transition", "payload": payload})
    with self._write_transaction(
        path,
        DatabaseKind.WORKFLOW,
        root,
        logical_identity=(binding.project_id, binding.root_session_id, None),
    ) as connection:
        control = _required_control(connection)
        current = int(control[11])
        replay = self._find_receipt(
            connection,
            "operation_receipts",
            request.idempotency_key,
            "workflow_transition",
            payload_hash,
            current,
        )
        if replay is not None:
            return replay
        if current != request.expected_revision:
            raise RevisionConflictError("workflow changed before session-audit update")
        _ensure_native_resolution(connection)
        if request.session_audit.worker_log_visibility == "Not applicable" and _one(
            connection, "SELECT 1 FROM allocations WHERE status IN ('bound','initialized')"
        ):
            raise InvalidStateTransitionError(
                "Worker log Not applicable requires that no Worker was created"
            )
        new_revision = current + 1
        connection.execute(
            "UPDATE workflow_session_metadata SET session_audit_json=? WHERE singleton=1",
            (_json(request.session_audit.model_dump(mode="json")),),
        )
        connection.execute(
            "UPDATE workflow_control SET revision=? WHERE singleton=1", (new_revision,)
        )
        self._record_binding_snapshot(connection, binding, new_revision)
        return self._store_receipt(
            connection,
            "operation_receipts",
            request.idempotency_key,
            "workflow_transition",
            payload_hash,
            {"session_audit": request.session_audit.model_dump(mode="json")},
            new_revision,
        )


def _confirm_checkpoint(
    self: StateService, request: CheckpointConfirmationTransition
) -> MutationReceipt:
    binding = self._parent_binding({HostCapability.WORKFLOW_WRITE}, {HostGuard.PATH_BOUNDARY})
    path, root = self._root_database(binding, create=False)
    payload = request.model_dump(mode="json")
    with self._write_transaction(
        path,
        DatabaseKind.WORKFLOW,
        root,
        logical_identity=(binding.project_id, binding.root_session_id, None),
    ) as connection:
        control = _required_control(connection)
        current = int(control[11])
        payload_hash = _hash_json(payload)
        replay = self._find_receipt(
            connection,
            "operation_receipts",
            request.idempotency_key,
            "workflow_transition",
            payload_hash,
            current,
        )
        if replay is not None:
            return replay
        if current != request.expected_revision:
            raise RevisionConflictError("workflow changed after checkpoint evaluation")
        _ensure_native_resolution(connection)
        evaluation = _one(
            connection,
            "SELECT node_id,outcome,branch,rule_hash,implementation_epoch,documentation_epoch,"
            "git_metadata_epoch,result_revision FROM checkpoint_evaluations "
            "WHERE evaluation_id=?",
            (request.evaluation_id,),
        )
        if evaluation is None or evaluation[1] != "ready" or evaluation[7] != current:
            raise InvalidStateTransitionError(
                "checkpoint confirmation requires a current ready evaluation"
            )
        if not _evaluation_epochs_are_current(
            evaluation[0], tuple(evaluation[4:7]), _epoch_snapshot(connection)
        ):
            raise InvalidStateTransitionError("checkpoint evaluation is stale")
        context = self._rule_loader.load_context(evaluation[0])
        if evaluation[3] != context.context_hash:
            raise InvalidStateTransitionError("checkpoint rules changed after evaluation")
        if evaluation[2] in {
            "blocked",
            "failure",
            "inconclusive",
            "incomplete",
            "amend",
            "stop",
            "evidence-on-demand",
            "request evidence",
        }:
            raise InvalidStateTransitionError(
                "a blocked or non-success branch cannot be confirmed as passed"
            )
        if evaluation[0] == CheckpointNode.ACCEPTANCE.value:
            if evaluation[2] != "complete":
                raise InvalidStateTransitionError("Acceptance requires the complete branch")
            history_errors = _validate_acceptance_history(connection, self._rule_loader)
            if history_errors:
                raise InvalidStateTransitionError(
                    "Acceptance prerequisites are stale or unsuccessful"
                )
            if _one(connection, "SELECT 1 FROM workflow_slices WHERE status='released'") or _one(
                connection, "SELECT 1 FROM root_slices WHERE status='released'"
            ):
                raise InvalidStateTransitionError("Acceptance cannot complete with an active Slice")
            connection.execute("UPDATE workflow_slices SET status='closed' WHERE status='released'")
            connection.execute("UPDATE root_slices SET status='closed' WHERE status='released'")
            connection.execute(
                "UPDATE workflow_control SET lifecycle='completed' WHERE singleton=1"
            )
        new_revision = current + 1
        confirmation_id = str(uuid.uuid4())
        connection.execute(
            "INSERT INTO checkpoint_confirmations VALUES (?, ?, ?, ?, ?, ?)",
            (
                confirmation_id,
                request.evaluation_id,
                evaluation[0],
                current,
                new_revision,
                _now(),
            ),
        )
        connection.execute(
            "UPDATE workflow_control SET revision=? WHERE singleton=1", (new_revision,)
        )
        self._record_binding_snapshot(connection, binding, new_revision)
        return self._store_receipt(
            connection,
            "operation_receipts",
            request.idempotency_key,
            "workflow_transition",
            payload_hash,
            {"confirmation_id": confirmation_id, "node_id": evaluation[0]},
            new_revision,
        )
