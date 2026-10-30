"""Evidence operations for the state service."""

from __future__ import annotations

import json
import uuid
from typing import TYPE_CHECKING

from token_io_decoupling_core.binding import BindingError
from token_io_decoupling_core.models import (
    DatabaseKind,
)
from token_io_decoupling_core.rules import UnknownRuleNodeError
from token_io_decoupling_core.state_models import (
    EvidenceKind,
    EvidenceRecord,
    EvidenceSubmission,
    HostCapability,
    HostGuard,
    MutationReceipt,
)

if TYPE_CHECKING:
    from ..service import StateService

from .common import _hash_json, _json, _nonempty, _now, _one
from .errors import InvalidStateTransitionError, RevisionConflictError, WorkflowNotOpenError
from .identity import _require_confirmed_worker_event, _required_control, _worker_identity
from .native import _ensure_native_resolution
from .validation import (
    _epoch_snapshot,
    _epochs_cover_changed_dimensions,
    _validate_coverage_dimensions,
)


def workflow_record_evidence(
    self: StateService,
    submission: EvidenceSubmission,
    *,
    expected_revision: int,
    idempotency_key: str,
) -> MutationReceipt:
    """Persist typed evidence as references and indexes, never semantic bodies."""
    submission = EvidenceSubmission.model_validate(submission)
    binding = self._parent_binding({HostCapability.WORKFLOW_WRITE}, {HostGuard.PATH_BOUNDARY})
    context = self._rule_loader.load_context(submission.node_id.value)
    fact_keys = [fact.fact_key.value for fact in submission.facts]
    if len(fact_keys) != len(set(fact_keys)) or not set(fact_keys) <= set(context.required_facts):
        raise InvalidStateTransitionError("evidence facts must be unique registered facts")
    refs = submission.evidence_refs + [
        ref
        for fact in submission.facts
        if fact.judgment.status == "determined"
        for ref in fact.judgment.evidence
    ]
    if any(ref.kind.value not in context.required_evidence for ref in refs):
        raise InvalidStateTransitionError("evidence kind is not required by this checkpoint")
    _validate_coverage_dimensions(submission.node_id, submission.coverage_dimensions)
    path, root = self._root_database(binding, create=False)
    evidence_id = str(uuid.uuid4())
    payload_hash = _hash_json(
        {
            "operation": "workflow_record_evidence",
            "submission": submission.model_dump(mode="json"),
        }
    )
    facts_json = _json([item.model_dump(mode="json") for item in submission.facts])
    refs_json = _json([item.model_dump(mode="json") for item in refs])
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
            _nonempty(idempotency_key, "idempotency_key"),
            "workflow_record_evidence",
            payload_hash,
            current,
        )
        if replay is not None:
            return replay
        if current != expected_revision:
            raise RevisionConflictError(
                f"expected Revision {expected_revision}, current Revision is {current}"
            )
        _ensure_native_resolution(connection)
        request_id = submission.evidence_request_id
        if request_id is not None:
            request = _one(
                connection,
                "SELECT status,returned_revision FROM control_evidence_requests WHERE request_id=?",
                (request_id,),
            )
            if request is None or request[0] not in {"pending", "returned"}:
                raise InvalidStateTransitionError(
                    "returned evidence must match a pending Control request or an "
                    "unresolved Control request eligible for recovery"
                )
            if request[0] == "returned" and (
                int(control[13]) <= 0 or request[1] is None or int(request[1]) >= int(control[13])
            ):
                raise InvalidStateTransitionError(
                    "only a pre-recovery returned request may be re-returned"
                )
            if EvidenceKind.RETURNED_EVIDENCE.value not in {item.kind.value for item in refs}:
                raise InvalidStateTransitionError(
                    "requested evidence must include returned-evidence reference"
                )
        epochs = _epoch_snapshot(connection)
        new_revision = current + 1
        connection.execute(
            "INSERT INTO checkpoint_evidence "
            "(evidence_id,node_id,facts_json,evidence_refs_json,input_hash,rule_hash,"
            "coverage_json,evidence_request_id,implementation_epoch,documentation_epoch,"
            "git_metadata_epoch,basis_revision,recorded_revision,created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                evidence_id,
                submission.node_id.value,
                facts_json,
                refs_json,
                submission.input_hash,
                context.context_hash,
                _json([item.value for item in submission.coverage_dimensions]),
                request_id,
                epochs.implementation_content,
                epochs.documentation,
                epochs.git_metadata,
                current,
                new_revision,
                _now(),
            ),
        )
        if request_id is not None:
            connection.execute(
                "UPDATE control_evidence_requests SET status='returned',returned_revision=? "
                "WHERE request_id=?",
                (new_revision, request_id),
            )
        connection.execute(
            "UPDATE workflow_control SET revision=? WHERE singleton=1", (new_revision,)
        )
        self._record_binding_snapshot(connection, binding, new_revision)
        evidence = EvidenceRecord(
            evidence_id=evidence_id,
            node_id=submission.node_id,
            facts=submission.facts,
            evidence_refs=refs,
            coverage_dimensions=submission.coverage_dimensions,
            input_hash=submission.input_hash,
            rule_hash=context.context_hash,
            epochs=epochs,
            basis_revision=current,
            recorded_revision=new_revision,
            stale=False,
        )
        return self._store_receipt(
            connection,
            "operation_receipts",
            idempotency_key,
            "workflow_record_evidence",
            payload_hash,
            evidence.model_dump(mode="json"),
            new_revision,
        )


def worker_record_evidence(
    self: StateService,
    submission: EvidenceSubmission,
    *,
    expected_revision: int,
    idempotency_key: str,
) -> MutationReceipt:
    submission = EvidenceSubmission.model_validate(submission)
    binding = self._worker_binding({HostCapability.WORKER_WRITE})
    context = self._rule_loader.load_context(submission.node_id.value)
    keys = [fact.fact_key.value for fact in submission.facts]
    if len(keys) != len(set(keys)) or not set(keys) <= set(context.required_facts):
        raise InvalidStateTransitionError("evidence facts must be unique registered facts")
    evidence_kinds = {item.kind.value for item in submission.evidence_refs}
    evidence_kinds.update(
        reference.kind.value
        for fact in submission.facts
        if fact.judgment.status == "determined"
        for reference in fact.judgment.evidence
    )
    if not evidence_kinds <= set(context.required_evidence):
        raise InvalidStateTransitionError("evidence kind is not required by this checkpoint")
    _validate_coverage_dimensions(submission.node_id, submission.coverage_dimensions)
    path, root = self._worker_database(binding.current_session_id, binding, create=False)
    if not path.is_file():
        raise WorkflowNotOpenError("Worker store is not initialized")
    with self._existing_write_transaction(path, DatabaseKind.WORKER, root) as connection:
        identity = _worker_identity(connection, binding)
        _require_confirmed_worker_event(connection, identity[7])
        current = int(identity[9])
        payload_hash = _hash_json(
            {
                "operation": "worker_record_evidence",
                "submission": submission.model_dump(mode="json"),
            }
        )
        replay = self._find_receipt(
            connection,
            "worker_operation_receipts",
            _nonempty(idempotency_key, "idempotency_key"),
            "worker_record_evidence",
            payload_hash,
            current,
        )
        if replay is not None:
            return replay
        if current != expected_revision:
            raise RevisionConflictError(
                f"expected Revision {expected_revision}, current Revision is {current}"
            )
        active_row = _one(
            connection, "SELECT snapshot_json FROM assignment_snapshot WHERE singleton=1"
        )
        dispatch = json.loads(active_row[0]) if active_row else {}
        dispatch_epochs = dispatch.get("epochs", {})
        new_revision = current + 1
        evidence_id = str(uuid.uuid4())
        facts = _json([item.model_dump(mode="json") for item in submission.facts])
        refs = submission.evidence_refs + [
            reference
            for fact in submission.facts
            if fact.judgment.status == "determined"
            for reference in fact.judgment.evidence
        ]
        refs_json = _json([item.model_dump(mode="json") for item in refs])
        connection.execute(
            "INSERT INTO worker_checkpoint_evidence VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                evidence_id,
                submission.node_id.value,
                facts,
                refs_json,
                submission.input_hash,
                context.context_hash,
                _json([item.value for item in submission.coverage_dimensions]),
                int(dispatch_epochs.get("implementation_content", 0)),
                int(dispatch_epochs.get("documentation", 0)),
                int(dispatch_epochs.get("git_metadata", 0)),
                current,
                new_revision,
                _now(),
            ),
        )
        connection.execute(
            "UPDATE worker_identity SET revision=? WHERE singleton=1", (new_revision,)
        )
        result = {
            "evidence_id": evidence_id,
            "basis_revision": current,
            "recorded_revision": new_revision,
        }
        return self._store_receipt(
            connection,
            "worker_operation_receipts",
            idempotency_key,
            "worker_record_evidence",
            payload_hash,
            result,
            new_revision,
        )


def worker_get_evidence(self: StateService, evidence_id: str) -> dict[str, object]:
    binding = self._worker_binding({HostCapability.WORKER_READ})
    path, root = self._worker_database(binding.current_session_id, binding, create=False)
    with self._read_transaction(path, DatabaseKind.WORKER, root) as connection:
        identity = _worker_identity(connection, binding)
        _require_confirmed_worker_event(connection, identity[7])
        active = _one(connection, "SELECT event_id FROM worker_active_dispatch WHERE singleton=1")
        if active is None or active[0] != identity[7]:
            raise BindingError("Worker identity does not match the monotonic active dispatch")
        row = _one(
            connection,
            "SELECT * FROM worker_checkpoint_evidence WHERE evidence_id=?",
            (_nonempty(evidence_id, "evidence_id"),),
        )
        if row is None:
            raise WorkflowNotOpenError("Worker evidence not found")
        active_row = _one(
            connection, "SELECT snapshot_json FROM assignment_snapshot WHERE singleton=1"
        )
        active = json.loads(active_row[0]) if active_row else {}
        active_epochs = active.get("epochs", {})
        try:
            current_rule_hash = self._rule_loader.load_context(row[1]).context_hash
        except UnknownRuleNodeError:
            current_rule_hash = None
        stale = (
            _epochs_cover_changed_dimensions(
                json.loads(row[6]),
                (row[7], row[8], row[9]),
                active_epochs,
            )
            or current_rule_hash is None
            or row[5] != current_rule_hash
        )
        return {
            "evidence_id": row[0],
            "node_id": row[1],
            "facts": json.loads(row[2]),
            "evidence_refs": json.loads(row[3]),
            "input_hash": row[4],
            "rule_hash": row[5],
            "coverage_dimensions": json.loads(row[6]),
            "basis_revision": row[10],
            "recorded_revision": row[11],
            "epochs": {
                "implementation_content": row[7],
                "documentation": row[8],
                "git_metadata": row[9],
            },
            "stale": stale,
        }
