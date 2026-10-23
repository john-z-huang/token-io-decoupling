"""Deterministic Root/Worker state services behind a fail-closed host binding."""

from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import uuid
from collections.abc import Callable, Generator, Mapping
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from urllib.parse import quote

from pydantic import TypeAdapter

from token_io_mcp.binding import BindingError, BindingProvider
from token_io_mcp.migrations.runner import (
    DEFAULT_LOCK_TIMEOUT_SECONDS,
    DatabaseIdentityMismatchError,
    _migration_lock,
    open_database_for_authorized_write,
    validate_connection_identity,
    validate_existing_connection,
)
from token_io_mcp.models import CodingMode, DatabaseKind, RuleContext, SemanticRef
from token_io_mcp.rules import RuleLoader
from token_io_mcp.state_models import (
    AllocationRole,
    AllocationState,
    AllocationStatus,
    BindingIdentity,
    BlockerRecord,
    ChangeCategory,
    CheckpointConfirmationTransition,
    CheckpointEvaluation,
    CheckpointNode,
    ControlTransitionRequest,
    EpochAdvanceTransition,
    EpochDimension,
    EpochSnapshot,
    EvidenceKind,
    EvidenceRecord,
    EvidenceSubmission,
    FactKey,
    HostCapability,
    HostGuard,
    LegalBranch,
    ModeCount,
    MutationReceipt,
    NativeReconcileTransition,
    NativeWorkflowSnapshot,
    OutputClass,
    ProgressRecord,
    ReconcileResult,
    SessionRole,
    SliceCheckResult,
    SliceSpec,
    VerifiedChildBinding,
    WorkerState,
    WorkflowOpenRequest,
    WorkflowState,
    WorkflowTransitionRequest,
)

DEFAULT_STATE_ROOT = Path.home() / ".local" / "state" / "token-io-decoupling"
_SAFE_COMPONENT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_WORKER_OUTPUT_CLASSES = {OutputClass.CODE_CONFIGURATION, OutputClass.SKILL_INSTRUCTIONS}


class StateServiceError(RuntimeError):
    """Base error for deterministic state operations."""


class WorkflowNotOpenError(StateServiceError):
    """No compatible workflow record exists for this trusted binding."""


class RevisionConflictError(StateServiceError):
    """The caller's expected Revision does not match current state."""


class IdempotencyConflictError(StateServiceError):
    """An idempotency key was reused with another operation or payload."""


class InvalidStateTransitionError(StateServiceError):
    """The requested operation violates the locked mode/allocation/slice state."""


class WorkerInitializationError(StateServiceError):
    """A committed Root event cannot safely initialize or recover its Worker store."""


class StateService:
    """Root and Worker state access; callers cannot provide database paths or identity."""

    def __init__(
        self,
        binding_provider: BindingProvider | None = None,
        *,
        state_root: Path | str | None = None,
        lock_timeout_seconds: float = DEFAULT_LOCK_TIMEOUT_SECONDS,
        rule_loader: RuleLoader | None = None,
    ) -> None:
        if binding_provider is None:
            from token_io_mcp.binding import DenyingBindingProvider

            binding_provider = DenyingBindingProvider()
        self._binding_provider = binding_provider
        self._state_root = Path(state_root) if state_root is not None else DEFAULT_STATE_ROOT
        self._rule_loader = rule_loader or RuleLoader()
        if lock_timeout_seconds <= 0:
            raise ValueError("lock_timeout_seconds must be positive")
        self._lock_timeout_seconds = lock_timeout_seconds

    def workflow_record_evidence(
        self,
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
        if len(fact_keys) != len(set(fact_keys)) or not set(fact_keys) <= set(
            context.required_facts
        ):
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
            request_id = submission.evidence_request_id
            if request_id is not None:
                request = _one(
                    connection,
                    "SELECT status FROM control_evidence_requests WHERE request_id=?",
                    (request_id,),
                )
                if request is None or request[0] != "pending":
                    raise InvalidStateTransitionError(
                        "returned evidence must match a pending Control request"
                    )
                if EvidenceKind.RETURNED_EVIDENCE.value not in {
                    item.kind.value for item in refs
                }:
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
        self, submission: EvidenceSubmission, *, expected_revision: int, idempotency_key: str
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
                "INSERT INTO worker_checkpoint_evidence VALUES "
                "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
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

    def worker_get_evidence(self, evidence_id: str) -> dict[str, object]:
        binding = self._worker_binding({HostCapability.WORKER_READ})
        path, root = self._worker_database(binding.current_session_id, binding, create=False)
        with self._read_transaction(path, DatabaseKind.WORKER, root) as connection:
            identity = _worker_identity(connection, binding)
            _require_confirmed_worker_event(connection, identity[7])
            active = _one(
                connection, "SELECT event_id FROM worker_active_dispatch WHERE singleton=1"
            )
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
            stale = (
                _epochs_cover_changed_dimensions(
                    json.loads(row[6]),
                    (row[7], row[8], row[9]),
                    active_epochs,
                )
                or row[5] != self._rule_loader.load_context(row[1]).context_hash
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

    def workflow_evaluate(
        self,
        node_id: CheckpointNode,
        *,
        expected_revision: int,
        idempotency_key: str,
        branch: str | None = None,
        input_hash: str | None = None,
        slice_ids: list[str] | None = None,
    ) -> CheckpointEvaluation:
        node_id = CheckpointNode(node_id)
        binding = self._parent_binding({HostCapability.WORKFLOW_WRITE}, {HostGuard.PATH_BOUNDARY})
        path, root = self._root_database(binding, create=False)
        payload = {
            "node_id": node_id.value,
            "branch": branch,
            "input_hash": input_hash,
            "slice_ids": sorted(slice_ids) if slice_ids is not None else None,
            "expected_revision": expected_revision,
        }
        payload_hash = _hash_json({"operation": "workflow_evaluate", "payload": payload})
        key = _nonempty(idempotency_key, "idempotency_key")
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
                key,
                "workflow_evaluate",
                payload_hash,
                current,
            )
            if replay is not None:
                return CheckpointEvaluation.model_validate_json(_json(replay.result))
            if type(expected_revision) is not int or expected_revision < 0:
                raise ValueError("expected_revision must be a non-negative integer")
            if expected_revision != current:
                raise RevisionConflictError(
                    f"expected Revision {expected_revision}, current Revision is {current}"
                )
            context = self._rule_loader.load_context(node_id.value)
            if branch is not None and branch not in context.legal_branches:
                raise InvalidStateTransitionError(
                    "evaluation branch is not legal for this checkpoint"
                )
            facts, refs, basis, stored_input = _latest_evidence(
                connection, node_id.value, context.context_hash
            )
            bound_slice_ids: list[str] = []
            if node_id is CheckpointNode.CONTROL:
                active_slice_ids = [
                    str(row[0])
                    for row in connection.execute(
                        "SELECT slice_id FROM workflow_slices WHERE status='released' "
                        "UNION ALL SELECT slice_id FROM root_slices WHERE status='released' "
                        "ORDER BY slice_id"
                    )
                ]
                if slice_ids is None:
                    bound_slice_ids = active_slice_ids
                else:
                    if len(set(slice_ids)) != len(slice_ids) or not set(slice_ids) <= set(
                        active_slice_ids
                    ):
                        raise InvalidStateTransitionError(
                            "Control may bind only unique currently released Slice IDs"
                        )
                    bound_slice_ids = sorted(slice_ids)
            elif slice_ids is not None:
                raise InvalidStateTransitionError("Slice IDs apply only to Control evaluations")
            epochs = _epoch_snapshot(connection)
            hard = _validate_checkpoint_state(connection, node_id, branch)
            hard.extend(_validate_fact_state(connection, facts))
            if node_id is CheckpointNode.ACCEPTANCE:
                hard.extend(_validate_acceptance_history(connection, self._rule_loader))
            missing_facts, missing_evidence = _missing_requirements(context, facts, refs)
            if hard:
                outcome, final_branch = "blocked", branch
            elif missing_facts or missing_evidence:
                outcome, final_branch = "incomplete", branch
            else:
                outcome, final_branch = "ready", branch
            if node_id is CheckpointNode.CONTROL and branch in {
                "continue",
                "amend",
                "stop",
                "evidence-on-demand",
            }:
                signal = next(
                    (fact for fact in facts if fact["fact_key"] == "Progress Signal"), None
                )
                signal_value = None
                if signal is not None:
                    judgment = signal["judgment"]
                    if isinstance(judgment, dict):
                        value = judgment.get("value")
                        if isinstance(value, dict):
                            signal_value = value.get("value")
                if signal is not None and signal_value != branch:
                    outcome, final_branch = "blocked", branch
            if node_id is CheckpointNode.CONTROL and branch == "evidence-on-demand":
                outcome, final_branch = "evidence_on_demand", "evidence-on-demand"
            evidence_request_id: str | None = None
            if node_id is CheckpointNode.CONTROL and branch == "evidence-on-demand":
                evidence_request_id = str(uuid.uuid4())
            elif node_id is CheckpointNode.CONTROL and branch == "continue":
                requested = _one(
                    connection,
                    "SELECT request_id,status FROM control_evidence_requests "
                    "WHERE status IN ('pending','returned') ORDER BY created_revision DESC LIMIT 1",
                )
                if requested is not None:
                    if requested[1] != "returned":
                        outcome = "incomplete"
                        missing_evidence.append("evidence returned for the pending Control request")
                    else:
                        evidence_request_id = str(requested[0])
            if input_hash is not None and stored_input and input_hash != stored_input:
                outcome, final_branch = "incomplete", branch
                missing_evidence.append("current evaluation input hash")
            if node_id is CheckpointNode.SLICE and branch != "released":
                outcome, final_branch = "blocked", branch
            if node_id is not CheckpointNode.CONTROL and branch in {
                "blocked",
                "failure",
                "inconclusive",
                "incomplete",
                "amend",
                "stop",
                "evidence-on-demand",
                "request evidence",
            }:
                outcome, final_branch = "blocked", branch
            evaluation_id = str(uuid.uuid4())
            result_revision = current + 1
            record_hash = _hash_json(
                {"facts": facts, "branch": final_branch, "epochs": epochs.model_dump(mode="json")}
            )
            connection.execute(
                "INSERT INTO checkpoint_evaluations "
                "(evaluation_id,node_id,outcome,branch,facts_hash,input_hash,rule_hash,"
                "implementation_epoch,documentation_epoch,git_metadata_epoch,basis_revision,"
                "result_revision,missing_facts_json,missing_evidence_json,slice_ids_json,"
                "evidence_request_id,created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    evaluation_id,
                    node_id.value,
                    outcome,
                    final_branch,
                    record_hash,
                    stored_input or "0" * 64,
                    context.context_hash,
                    epochs.implementation_content,
                    epochs.documentation,
                    epochs.git_metadata,
                    current,
                    result_revision,
                    _json(missing_facts),
                    _json(missing_evidence),
                    _json(bound_slice_ids),
                    evidence_request_id,
                    _now(),
                ),
            )
            if node_id is CheckpointNode.CONTROL and branch == "evidence-on-demand":
                connection.execute(
                    "INSERT INTO control_evidence_requests "
                    "(request_id,source_evaluation_id,created_revision,status,created_at) "
                    "VALUES (?, ?, ?, 'pending', ?)",
                    (evidence_request_id, evaluation_id, result_revision, _now()),
                )
            connection.execute(
                "UPDATE workflow_control SET revision=? WHERE singleton=1", (result_revision,)
            )
            evaluation = CheckpointEvaluation(
                evaluation_id=evaluation_id,
                node_id=node_id,
                outcome=outcome,
                branch=LegalBranch(final_branch) if final_branch is not None else None,
                rule_hash=context.context_hash,
                input_hash=stored_input or "0" * 64,
                epochs=epochs,
                basis_revision=current,
                result_revision=result_revision,
                missing_facts=missing_facts,
                missing_evidence=missing_evidence,
                slice_ids=bound_slice_ids,
                evidence_request_id=evidence_request_id,
            )
            self._store_receipt(
                connection,
                "operation_receipts",
                key,
                "workflow_evaluate",
                payload_hash,
                evaluation.model_dump(mode="json"),
                result_revision,
            )
            return evaluation

    def evaluate_control_checkpoint(
        self,
        *,
        expected_revision: int,
        idempotency_key: str,
        branch: str | None = None,
        input_hash: str | None = None,
        slice_ids: list[str] | None = None,
    ) -> CheckpointEvaluation:
        return self.workflow_evaluate(
            CheckpointNode.CONTROL,
            expected_revision=expected_revision,
            idempotency_key=idempotency_key,
            branch=branch,
            input_hash=input_hash,
            slice_ids=slice_ids,
        )

    def workflow_advance_epoch(
        self,
        dimension: EpochDimension,
        *,
        expected_revision: int,
        idempotency_key: str,
    ) -> MutationReceipt:
        """Advance exactly one independent epoch after an authorized host observes change."""
        dimension = EpochDimension(dimension)
        binding = self._parent_binding({HostCapability.WORKFLOW_WRITE}, {HostGuard.PATH_BOUNDARY})
        column = {
            EpochDimension.IMPLEMENTATION_CONTENT: "implementation_content",
            EpochDimension.DOCUMENTATION: "documentation",
            EpochDimension.GIT_METADATA: "git_metadata",
        }[dimension]

        def mutate(connection: sqlite3.Connection, _revision: int) -> dict[str, object]:
            connection.execute(f"UPDATE workflow_epochs SET {column}={column}+1 WHERE singleton=1")
            row = _one(connection, f"SELECT {column} FROM workflow_epochs WHERE singleton=1")
            if row is None:
                raise WorkflowNotOpenError("workflow epoch record is missing")
            return {"dimension": dimension.value, "epoch": row[0]}

        return self._mutate_root(
            binding,
            "workflow_advance_epoch",
            {"dimension": dimension.value},
            expected_revision,
            idempotency_key,
            mutate,
        )

    def workflow_transition(self, request: WorkflowTransitionRequest) -> MutationReceipt:
        request = TypeAdapter(WorkflowTransitionRequest).validate_python(request)
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
                    "SELECT status FROM control_evidence_requests WHERE request_id=?",
                    (ev[8],),
                )
                if returned is None or returned[0] != "returned":
                    raise InvalidStateTransitionError(
                        "Continue requires returned evidence for its Control request"
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
                "(transition_id,evaluation_id,outcome,slice_ids_json,from_revision,to_revision,created_at) "
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

    def _confirm_checkpoint(self, request: CheckpointConfirmationTransition) -> MutationReceipt:
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
            if tuple(evaluation[4:7]) != tuple(_epoch_snapshot(connection).model_dump().values()):
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
                if _one(
                    connection, "SELECT 1 FROM workflow_slices WHERE status='released'"
                ) or _one(connection, "SELECT 1 FROM root_slices WHERE status='released'"):
                    raise InvalidStateTransitionError(
                        "Acceptance cannot complete with an active Slice"
                    )
                connection.execute(
                    "UPDATE workflow_slices SET status='closed' WHERE status='released'"
                )
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
            return self._store_receipt(
                connection,
                "operation_receipts",
                request.idempotency_key,
                "workflow_transition",
                payload_hash,
                {"confirmation_id": confirmation_id, "node_id": evaluation[0]},
                new_revision,
            )

    def workflow_reconcile(
        self,
        snapshot: NativeWorkflowSnapshot,
        *,
        confirm: bool = False,
        expected_revision: int,
        idempotency_key: str,
    ) -> ReconcileResult:
        snapshot = NativeWorkflowSnapshot.model_validate(snapshot)
        binding = self._parent_binding({HostCapability.WORKFLOW_WRITE}, {HostGuard.PATH_BOUNDARY})
        if (snapshot.project_id, snapshot.root_session_id) != (
            binding.project_id,
            binding.root_session_id,
        ):
            raise BindingError("Native snapshot belongs to another bound project or Root")
        path, root = self._root_database(binding, create=True)
        key = _nonempty(idempotency_key, "idempotency_key")
        payload = {
            "snapshot": snapshot.model_dump(mode="json"),
            "confirm": confirm,
            "expected_revision": expected_revision,
        }
        payload_hash = _hash_json({"operation": "workflow_reconcile", "payload": payload})
        with self._write_transaction(
            path,
            DatabaseKind.WORKFLOW,
            root,
            logical_identity=(binding.project_id, binding.root_session_id, None),
        ) as connection:
            control = _one(connection, "SELECT * FROM workflow_control WHERE singleton=1")
            if control is None:
                row = _one(
                    connection,
                    "SELECT MAX(result_revision) FROM native_reconciliations "
                    "WHERE project_id=? AND root_session_id=?",
                    (binding.project_id, binding.root_session_id),
                )
                current = int(row[0] or 0) if row else 0
            else:
                current = int(control[11])
            replay = self._find_receipt(
                connection,
                "operation_receipts",
                key,
                "workflow_reconcile",
                payload_hash,
                current,
            )
            if replay is not None:
                return ReconcileResult.model_validate_json(_json(replay.result)).model_copy(
                    update={"replayed": True, "current_revision": replay.current_revision}
                )
            if type(expected_revision) is not int or expected_revision < 0:
                raise ValueError("expected_revision must be a non-negative integer")
            if expected_revision != current:
                raise RevisionConflictError(
                    f"expected Revision {expected_revision}, current Revision is {current}"
                )
            snapshot_hash = _hash_json(snapshot.model_dump(mode="json"))
            approved_comparison = None
            if confirm:
                approved_comparison = _one(
                    connection,
                    "SELECT observed_revision,result_revision FROM native_reconciliations "
                    "WHERE snapshot_hash=? AND project_id=? AND root_session_id=? "
                    "AND status='awaiting_confirmation' ORDER BY result_revision DESC LIMIT 1",
                    (snapshot_hash, snapshot.project_id, snapshot.root_session_id),
                )
                if approved_comparison is None:
                    raise InvalidStateTransitionError(
                        "explicit reconciliation requires a prior matching comparison"
                    )
                if (
                    int(approved_comparison[0]) != snapshot.revision
                    or int(approved_comparison[1]) != current
                ):
                    raise RevisionConflictError(
                        "Root changed after Native comparison; compare again before confirmation"
                    )
            differences = []
            if snapshot.mode_source == "timeout-default":
                differences.append("legacy timeout-default is read-only")
            if control:
                if (
                    control[4] != snapshot.mode_count.mode.value
                    or control[5] != snapshot.mode_count.child_count
                ):
                    differences.append("mode/count")
                if control[6] != snapshot.mode_source:
                    differences.append("mode source")
                if (control[7], control[8]) != (
                    snapshot.source.uri,
                    snapshot.source.content_hash,
                ):
                    differences.append("Contract source")
                if json.loads(control[9]) != [
                    ref.model_dump(mode="json") for ref in snapshot.semantic_references
                ]:
                    differences.append("semantic references")
                if control[3] != snapshot.run_id:
                    differences.append("Run identity")
                if control[10] != snapshot.lifecycle:
                    differences.append("lifecycle")
                if not confirm and current != snapshot.revision:
                    differences.append("Revision")
                actual_allocs = [
                    (a.allocation_id, a.role, a.worker_session_id, a.status)
                    for a in _workflow_state(connection).allocations
                ]
                native_allocs = [
                    (
                        a.allocation_id,
                        a.role.value if a.role else None,
                        a.worker_session_id,
                        a.status,
                    )
                    for a in snapshot.allocations
                ]
                if actual_allocs != native_allocs:
                    differences.append("Allocation identities")
                if _epoch_snapshot(connection) != snapshot.epochs:
                    differences.append("Epochs")
            else:
                if not confirm and snapshot.revision != current:
                    differences.append("Revision")
                if snapshot.lifecycle == "running" or any(
                    item.status in {AllocationStatus.BOUND, AllocationStatus.INITIALIZED}
                    for item in snapshot.allocations
                ):
                    differences.append("snapshot lacks active Slice or confirmed dispatch history")
                if len(snapshot.allocations) != snapshot.mode_count.child_count:
                    differences.append("Allocation count differs from locked child budget")
            status = (
                "conflict"
                if differences
                else ("awaiting_confirmation" if not confirm else "matched")
            )
            if confirm and differences:
                status = "conflict"
            rid = str(uuid.uuid4())
            result_rev = current + 1
            if status == "matched" and confirm and control is None:
                now = _now()
                run_id = snapshot.run_id or str(uuid.uuid4())
                connection.execute(
                    "INSERT INTO workflow_control VALUES (1,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        binding.project_id,
                        binding.root_session_id,
                        run_id,
                        snapshot.mode_count.mode.value,
                        snapshot.mode_count.child_count,
                        snapshot.mode_source,
                        snapshot.source.uri,
                        snapshot.source.content_hash,
                        _json(
                            [ref.model_dump(mode="json") for ref in snapshot.semantic_references]
                        ),
                        snapshot.lifecycle,
                        result_rev,
                        now,
                    ),
                )
                connection.execute(
                    "UPDATE workflow_epochs SET implementation_content=?,documentation=?,"
                    "git_metadata=? WHERE singleton=1",
                    (
                        snapshot.epochs.implementation_content,
                        snapshot.epochs.documentation,
                        snapshot.epochs.git_metadata,
                    ),
                )
                for slot, item in enumerate(snapshot.allocations):
                    if item.status in {AllocationStatus.BOUND, AllocationStatus.INITIALIZED}:
                        raise InvalidStateTransitionError(
                            "Native Worker recovery requires dispatch history"
                        )
                    connection.execute(
                        "INSERT INTO allocations(allocation_id,slot,role,status,"
                        "worker_session_id,output_class,worker_event_id,created_at) "
                        "VALUES (?,?,?,?,NULL,NULL,NULL,?)",
                        (
                            item.allocation_id,
                            slot,
                            item.role.value if item.role else None,
                            item.status.value,
                            now,
                        ),
                    )
            native_refs = [ref.model_dump(mode="json") for ref in snapshot.evidence_refs]
            connection.execute(
                "INSERT INTO native_reconciliations VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    rid,
                    _hash_json(snapshot.model_dump(mode="json")),
                    _json(native_refs),
                    _json(differences),
                    status,
                    current,
                    result_rev,
                    _now(),
                    snapshot.project_id,
                    snapshot.root_session_id,
                    _json(snapshot.model_dump(mode="json")),
                ),
            )
            if control:
                connection.execute(
                    "UPDATE workflow_control SET revision=? WHERE singleton=1", (result_rev,)
                )
            result = ReconcileResult(
                reconcile_id=rid,
                status=status,
                observed_revision=current,
                result_revision=result_rev,
                current_revision=result_rev,
                differences=differences,
                native_refs=snapshot.evidence_refs,
            )
            self._store_receipt(
                connection,
                "operation_receipts",
                key,
                "workflow_reconcile",
                payload_hash,
                result.model_dump(mode="json"),
                result_rev,
            )
            return result

    def workflow_open(self, request: WorkflowOpenRequest) -> MutationReceipt:
        """Initialize the locked route once or read it back without resetting identity."""
        request = WorkflowOpenRequest.model_validate(request)
        if request.mode_source == "default" and (
            request.mode_count.mode is not CodingMode.MULTI_AGENT
            or request.mode_count.child_count != 1
        ):
            raise InvalidStateTransitionError(
                "default mode is fixed to Multi-Agent Coding with one slot"
            )
        binding = self._parent_binding({HostCapability.WORKFLOW_WRITE}, {HostGuard.PATH_BOUNDARY})
        path, root = self._root_database(binding, create=True)
        payload = request.model_dump(mode="json")
        payload_hash = _hash_json({"operation": "workflow_open", "payload": payload})
        with self._write_transaction(
            path,
            DatabaseKind.WORKFLOW,
            root,
            logical_identity=(binding.project_id, binding.root_session_id, None),
        ) as connection:
            existing = _one(connection, "SELECT * FROM workflow_control WHERE singleton=1")
            _ensure_native_resolution(connection)
            if existing is not None:
                receipt = self._find_receipt(
                    connection,
                    "operation_receipts",
                    request.idempotency_key,
                    "workflow_open",
                    payload_hash,
                    int(existing[11]),
                )
                if receipt is not None:
                    return receipt
                _assert_workflow_identity(existing, binding, request)
                current_revision = int(existing[11])
                if request.expected_revision != current_revision:
                    raise RevisionConflictError(
                        f"expected Revision {request.expected_revision}, "
                        f"current Revision is {current_revision}"
                    )
                state = _workflow_state(connection)
                return self._store_receipt(
                    connection,
                    "operation_receipts",
                    request.idempotency_key,
                    "workflow_open",
                    payload_hash,
                    state.model_dump(mode="json"),
                    current_revision,
                )

            if request.expected_revision != 0:
                raise RevisionConflictError("new workflow must start at Revision 0")
            run_id = str(uuid.uuid4())
            now = _now()
            connection.execute(
                """
                INSERT INTO workflow_control (
                    singleton, project_id, root_session_id, run_id, mode, child_count,
                    mode_source, source_uri, source_hash, semantic_references_json,
                    lifecycle, revision, created_at
                ) VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', 0, ?)
                """,
                (
                    binding.project_id,
                    binding.root_session_id,
                    run_id,
                    request.mode_count.mode.value,
                    request.mode_count.child_count,
                    request.mode_source,
                    request.source.uri,
                    request.source.content_hash,
                    _json([ref.model_dump(mode="json") for ref in request.semantic_references]),
                    now,
                ),
            )
            for slot in range(request.mode_count.child_count):
                connection.execute(
                    "INSERT INTO allocations(allocation_id, slot, role, status, created_at) "
                    "VALUES (?, ?, NULL, 'unassigned', ?)",
                    (str(uuid.uuid4()), slot, now),
                )
            state = _workflow_state(connection)
            return self._store_receipt(
                connection,
                "operation_receipts",
                request.idempotency_key,
                "workflow_open",
                payload_hash,
                state.model_dump(mode="json"),
                0,
            )

    def workflow_get_state(self) -> WorkflowState:
        binding = self._parent_binding({HostCapability.WORKFLOW_READ}, {HostGuard.PATH_BOUNDARY})
        path, root = self._root_database(binding, create=False)
        with self._read_transaction(path, DatabaseKind.WORKFLOW, root) as connection:
            return _workflow_state(connection)

    def delegation_reserve(
        self, role: str, *, expected_revision: int, idempotency_key: str
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
                raise InvalidStateTransitionError(
                    "a single Worker slot is reserved for Primary Output"
                )
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

    def slice_check(self, spec: SliceSpec) -> SliceCheckResult:
        spec = SliceSpec.model_validate(spec)
        if any(category not in set(ChangeCategory) for category in spec.change_categories):
            raise InvalidStateTransitionError("unknown change category")
        binding = self._parent_binding({HostCapability.WORKFLOW_READ}, {HostGuard.PATH_BOUNDARY})
        path, root = self._root_database(binding, create=False)
        with self._read_transaction(path, DatabaseKind.WORKFLOW, root) as connection:
            context = self._rule_loader.load_context(CheckpointNode.SLICE.value)
            checked = _check_slice(connection, spec, context.context_hash)
            return checked.model_copy(update={"input_hash": _slice_spec_hash(spec)})

    def slice_release(
        self,
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
            checked = _check_slice(connection, spec, context.context_hash)
            if not checked.eligible:
                raise InvalidStateTransitionError(checked.reason or "slice is not eligible")
            slice_id = str(uuid.uuid4())
            control = _required_control(connection)
            if control[4] == "Single-Agent Coding":
                connection.execute(
                    "INSERT INTO root_slices VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'released', ?, ?)",
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
                    ),
                )
                connection.execute(
                    "UPDATE workflow_control SET lifecycle='running' WHERE singleton=1"
                )
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
        self,
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

    def worker_get_assignment(self) -> dict[str, object]:
        binding = self._worker_binding({HostCapability.WORKER_READ})
        path, root = self._worker_database(binding.current_session_id, binding, create=False)
        with self._read_transaction(path, DatabaseKind.WORKER, root) as connection:
            identity = _worker_identity(connection, binding)
            _require_confirmed_worker_event(connection, identity[7])
            row = _one(
                connection, "SELECT snapshot_json FROM assignment_snapshot WHERE singleton=1"
            )
            if row is None:
                raise WorkflowNotOpenError("Worker assignment snapshot is missing")
            snapshot = json.loads(row[0])
            if _hash_json(snapshot) != identity[8]:
                raise BindingError(
                    "Worker assignment snapshot hash differs from its bound identity"
                )
            return snapshot

    def worker_get_dispatch(self, event_id: str) -> dict[str, object]:
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

    def worker_get_state(self) -> WorkerState:
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

    def worker_get_recovery_context(self) -> dict[str, object]:
        return {
            "assignment": self.worker_get_assignment(),
            "state": self.worker_get_state().model_dump(mode="json"),
        }

    def worker_record_progress(
        self,
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
                "INSERT INTO worker_progress(progress_key, progress_json, updated_at) "
                "VALUES (?, ?, ?)",
                (key, _json(payload), _now()),
            )
            return {"progress_id": key, "status": record.status}

        return self._mutate_worker(
            binding, "worker_record_progress", payload, expected_revision, idempotency_key, mutate
        )

    def worker_report_blocker(
        self,
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

    def parent_get_worker_summary(self, allocation_id: str) -> WorkerState:
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

    def _mutate_root(
        self,
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
            next_revision = current + 1
            result = mutation(connection, next_revision)
            connection.execute(
                "UPDATE workflow_control SET revision=? WHERE singleton=1", (next_revision,)
            )
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
        self,
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
            raise WorkflowNotOpenError(
                "Worker store is initialized only after Root identity binding"
            )
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
        self,
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
        self,
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

    def _complete_worker_dispatch(
        self,
        parent: BindingIdentity,
        child: VerifiedChildBinding,
        event_id: str,
    ) -> None:
        root_path, root = self._root_database(parent, create=False)
        with self._read_transaction(root_path, DatabaseKind.WORKFLOW, root) as connection:
            row = _one(
                connection,
                "SELECT allocation_id,payload_json,payload_hash,status,sequence "
                "FROM workflow_dispatch_events WHERE event_id=?",
                (event_id,),
            )
        if row is None:
            raise WorkerInitializationError("committed Root dispatch event is missing")
        allocation_id, payload_json, payload_hash, event_status, sequence = row
        payload = json.loads(payload_json)
        if payload["worker_session_id"] != child.child_session_id:
            raise WorkerInitializationError("outbox Worker identity differs from trusted child")
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
            logical_identity=(parent.project_id, parent.root_session_id, child.child_session_id),
        ) as connection:
            identity = _one(connection, "SELECT * FROM worker_identity WHERE singleton=1")
            snapshot = _json(payload)
            assignment_hash = _hash_json(payload)
            if assignment_hash != payload_hash:
                raise WorkerInitializationError("Root outbox payload hash does not match")
            history = _one(
                connection,
                "SELECT status,sequence,snapshot_json,assignment_hash "
                "FROM worker_dispatch_history WHERE event_id=?",
                (event_id,),
            )
            active = _one(
                connection, "SELECT sequence FROM worker_active_dispatch WHERE singleton=1"
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
                    # A replayed old event is queryable but may never rewind the active pointer.
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
                    connection, "SELECT snapshot_json FROM assignment_snapshot WHERE singleton=1"
                )
                if current_snapshot is not None and current_snapshot[0] != snapshot:
                    raise WorkerInitializationError(
                        "unbound Worker store already contains another assignment"
                    )
                connection.execute(
                    "INSERT OR IGNORE INTO assignment_snapshot "
                    "(singleton, snapshot_json, source_revision) "
                    "VALUES (1, ?, ?)",
                    (snapshot, payload["source_revision"]),
                )
                connection.execute(
                    """INSERT INTO worker_identity
                       (singleton, project_id, root_session_id, worker_session_id, allocation_id,
                        role, output_class, event_id, assignment_hash, revision, created_at)
                       VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?)""",
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
                connection.execute(
                    "INSERT INTO worker_inbox(event_id, payload_hash, status, received_at) "
                    "VALUES (?, ?, 'pending', ?)",
                    (event_id, payload_hash, _now()),
                )
                connection.execute(
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
                connection.execute(
                    "UPDATE assignment_snapshot SET snapshot_json=?,source_revision=? "
                    "WHERE singleton=1",
                    (snapshot, payload["source_revision"]),
                )
                connection.execute(
                    "UPDATE worker_identity SET output_class=?,event_id=?,assignment_hash=? "
                    "WHERE singleton=1",
                    (payload["output_class"], event_id, assignment_hash),
                )
                connection.execute(
                    "INSERT INTO worker_inbox(event_id,payload_hash,status,received_at) "
                    "VALUES (?,?,'pending',?)",
                    (event_id, payload_hash, _now()),
                )
                connection.execute(
                    "INSERT INTO worker_dispatch_history "
                    "(event_id,sequence,snapshot_json,assignment_hash,status,received_at) "
                    "VALUES (?,?,?,?,'pending',?)",
                    (event_id, sequence, snapshot, assignment_hash, _now()),
                )

        with self._write_transaction(
            root_path,
            DatabaseKind.WORKFLOW,
            root,
            logical_identity=(parent.project_id, parent.root_session_id, None),
        ) as connection:
            event = _one(
                connection,
                "SELECT status FROM workflow_dispatch_events WHERE event_id=?",
                (event_id,),
            )
            if event is None:
                raise WorkerInitializationError("Root outbox event disappeared during dispatch")
            if event[0] == "pending":
                next_revision = _required_control(connection)[11] + 1
                connection.execute(
                    "UPDATE root_outbox SET status='confirmed', confirmed_at=? WHERE event_id=?",
                    (_now(), event_id),
                )
                connection.execute(
                    "UPDATE workflow_dispatch_events SET status='confirmed',confirmed_at=? "
                    "WHERE event_id=?",
                    (_now(), event_id),
                )
                connection.execute(
                    "UPDATE allocations SET status='initialized' WHERE allocation_id=? "
                    "AND worker_event_id=?",
                    (allocation_id, event_id),
                )
                connection.execute(
                    "UPDATE workflow_control SET revision=? WHERE singleton=1", (next_revision,)
                )
        with self._write_transaction(
            worker_path,
            DatabaseKind.WORKER,
            worker_root,
            logical_identity=(parent.project_id, parent.root_session_id, child.child_session_id),
        ) as connection:
            row = _one(connection, "SELECT status FROM worker_inbox WHERE event_id=?", (event_id,))
            if row is None:
                raise WorkerInitializationError("Worker event receipt is missing")
            if row[0] == "pending":
                connection.execute(
                    "UPDATE worker_inbox SET status='confirmed', confirmed_at=? WHERE event_id=?",
                    (_now(), event_id),
                )
                connection.execute(
                    "UPDATE worker_dispatch_history SET status='confirmed',confirmed_at=? "
                    "WHERE event_id=?",
                    (_now(), event_id),
                )
                active = _one(
                    connection, "SELECT sequence FROM worker_active_dispatch WHERE singleton=1"
                )
                if active is None:
                    connection.execute(
                        "INSERT INTO worker_active_dispatch VALUES (1,?,?)", (event_id, sequence)
                    )
                elif sequence > int(active[0]):
                    connection.execute(
                        "UPDATE worker_active_dispatch SET event_id=?,sequence=? WHERE singleton=1",
                        (event_id, sequence),
                    )

    def _parent_binding(
        self,
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

    def _worker_binding(self, capabilities: set[HostCapability]) -> BindingIdentity:
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

    def _root_database(self, binding: BindingIdentity, *, create: bool) -> tuple[Path, Path]:
        anchor = self._state_root.resolve(strict=False)
        root = (
            anchor
            / _safe_component(binding.project_id, "project_id")
            / _safe_component(binding.root_session_id, "root_session_id")
        )
        _ensure_derived_directory_chain(anchor, root, create=create)
        return root / "workflow.sqlite3", root

    def _worker_database(
        self, worker_session_id: str, binding: BindingIdentity, *, create: bool
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

    @contextmanager
    def _write_transaction(
        self,
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
                        _validate_root_identity(
                            connection, self._binding_provider.current_binding()
                        )
                    yield connection
                    connection.commit()
                except Exception:
                    connection.rollback()
                    raise
            finally:
                connection.close()

    @contextmanager
    def _read_transaction(
        self,
        path: Path,
        kind: DatabaseKind,
        trusted_root: Path,
    ) -> Generator[sqlite3.Connection, None, None]:
        if not path.is_file():
            raise WorkflowNotOpenError(
                "database does not exist; read access cannot initialize state"
            )
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

    @contextmanager
    def _existing_write_transaction(
        self,
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
                        _validate_root_identity(
                            connection, self._binding_provider.current_binding()
                        )
                    yield connection
                    connection.commit()
                except Exception:
                    connection.rollback()
                    raise
            finally:
                connection.close()


def _check_slice(
    connection: sqlite3.Connection, spec: SliceSpec, current_rule_hash: str
) -> SliceCheckResult:
    expected_input_hash = _slice_spec_hash(spec)
    output_class = spec.output_class
    control = _required_control(connection)
    native_status = _one(
        connection,
        "SELECT status FROM native_reconciliations ORDER BY result_revision DESC LIMIT 1",
    )
    if native_status is not None and native_status[0] in {
        "awaiting_confirmation",
        "conflict",
    }:
        return SliceCheckResult(
            eligible=False,
            reason="Native reconciliation must be explicitly resolved before Slice release",
            allocation_id=spec.allocation_id,
            output_class=output_class,
            input_hash=expected_input_hash,
        )
    root_owned = control[4] == "Single-Agent Coding" and spec.allocation_id == "root"
    if output_class not in _WORKER_OUTPUT_CLASSES and not root_owned:
        return SliceCheckResult(
            eligible=False,
            reason="Worker Slice output must be code/configuration or Skill instructions",
            allocation_id=spec.allocation_id,
            output_class=output_class,
        )
    if control[10] in {"completed", "interrupted"}:
        return SliceCheckResult(
            eligible=False,
            reason="workflow lifecycle does not permit a new Slice",
            allocation_id=spec.allocation_id,
            output_class=output_class,
        )
    last_control = _one(
        connection, "SELECT outcome FROM control_transitions ORDER BY to_revision DESC LIMIT 1"
    )
    has_prior_slices = (
        _one(connection, "SELECT 1 FROM workflow_slices LIMIT 1") is not None
        or _one(connection, "SELECT 1 FROM root_slices LIMIT 1") is not None
    )
    if has_prior_slices and (last_control is None or last_control[0] != "continue"):
        return SliceCheckResult(
            eligible=False,
            reason="a current Control Continue is required before another Slice",
            allocation_id=spec.allocation_id,
            output_class=output_class,
        )
    latest_transition = _one(
        connection,
        "SELECT outcome,to_revision FROM control_transitions ORDER BY to_revision DESC LIMIT 1",
    )
    if latest_transition is not None and latest_transition[0] == "amend":
        epochs = _epoch_snapshot(connection)
        for required_node in ("contract", "decision"):
            evaluation = _one(
                connection,
                "SELECT outcome,result_revision,implementation_epoch,documentation_epoch,"
                "git_metadata_epoch "
                "FROM checkpoint_evaluations WHERE node_id=? ORDER BY result_revision DESC LIMIT 1",
                (required_node,),
            )
            if (
                evaluation is None
                or evaluation[0] != "ready"
                or evaluation[1] <= latest_transition[1]
                or tuple(evaluation[2:])
                != (epochs.implementation_content, epochs.documentation, epochs.git_metadata)
            ):
                return SliceCheckResult(
                    eligible=False,
                    reason="Amend requires current Contract and Decision reevaluation",
                    allocation_id=spec.allocation_id,
                    output_class=output_class,
                )
    if control[4] == "Single-Agent Coding":
        if spec.allocation_id != "root":
            return SliceCheckResult(
                eligible=False,
                reason="Single-Agent Slice is owned by Root",
                allocation_id=spec.allocation_id,
                output_class=output_class,
            )
        if _one(connection, "SELECT 1 FROM root_slices WHERE status='released'") is not None:
            return SliceCheckResult(
                eligible=False,
                reason="Root already has an active Slice",
                allocation_id=spec.allocation_id,
                output_class=output_class,
            )
    elif control[4] != "Multi-Agent Coding":
        return SliceCheckResult(
            eligible=False,
            reason="Single-Agent workflow cannot release a Worker Slice",
            allocation_id=spec.allocation_id,
            output_class=output_class,
        )
    allocation = _one(
        connection,
        "SELECT role, status FROM allocations WHERE allocation_id=?",
        (spec.allocation_id,),
    )
    if control[4] == "Multi-Agent Coding" and (
        allocation is None
        or allocation[0] is None
        or allocation[1] not in {"reserved", "initialized"}
    ):
        return SliceCheckResult(
            eligible=False,
            reason="Slice requires an allocation with a reserved role",
            allocation_id=spec.allocation_id,
            output_class=output_class,
        )
    active = _one(
        connection,
        "SELECT slice_id FROM workflow_slices WHERE allocation_id=? AND status='released'",
        (spec.allocation_id,),
    )
    if control[4] == "Multi-Agent Coding" and active is not None:
        return SliceCheckResult(
            eligible=False,
            reason="allocation already has an active Slice",
            allocation_id=spec.allocation_id,
            output_class=output_class,
        )
    for candidate in spec.authorized_paths:
        path = PurePosixPath(candidate)
        if path.is_absolute() or ".." in path.parts or not path.parts:
            return SliceCheckResult(
                eligible=False,
                reason="authorized paths must be relative and remain in the project boundary",
                allocation_id=spec.allocation_id,
                output_class=output_class,
            )
    if len(set(spec.authorized_paths)) != len(spec.authorized_paths):
        return SliceCheckResult(
            eligible=False,
            reason="authorized paths must be unique",
            allocation_id=spec.allocation_id,
            output_class=output_class,
        )
    prerequisite = _one(
        connection,
        "SELECT result_revision,implementation_epoch,documentation_epoch,git_metadata_epoch,"
        "branch,input_hash,rule_hash "
        "FROM checkpoint_evaluations "
        "WHERE node_id='slice' AND outcome='ready' ORDER BY result_revision DESC LIMIT 1",
    )
    current_epochs = _epoch_snapshot(connection)
    if (
        prerequisite is None
        or prerequisite[0] != control[11]
        or tuple(prerequisite[1:])
        [:3]
        != (
            current_epochs.implementation_content,
            current_epochs.documentation,
            current_epochs.git_metadata,
        )
        or prerequisite[4] != "released"
        or prerequisite[5] != expected_input_hash
        or prerequisite[6] != current_rule_hash
    ):
        return SliceCheckResult(
            eligible=False,
            reason="a current Slice prerequisite evaluation is required",
            allocation_id=spec.allocation_id,
            output_class=output_class,
        )
    return SliceCheckResult(
        eligible=True,
        reason=None,
        allocation_id=spec.allocation_id,
        output_class=output_class,
        input_hash=expected_input_hash,
    )


def _slice_spec_hash(spec: SliceSpec) -> str:
    return _hash_json(spec.model_dump(mode="json"))


def _ensure_native_resolution(connection: sqlite3.Connection) -> None:
    row = _one(
        connection,
        "SELECT status FROM native_reconciliations ORDER BY result_revision DESC LIMIT 1",
    )
    if row is not None and row[0] in {"awaiting_confirmation", "conflict"}:
        raise InvalidStateTransitionError(
            "Native reconciliation must be explicitly resolved before new Root mutations"
        )


def _epoch_snapshot(connection: sqlite3.Connection) -> EpochSnapshot:
    row = _one(
        connection,
        "SELECT implementation_content,documentation,git_metadata "
        "FROM workflow_epochs WHERE singleton=1",
    )
    if row is None:
        raise WorkflowNotOpenError("workflow epoch record is missing")
    return EpochSnapshot(implementation_content=row[0], documentation=row[1], git_metadata=row[2])


def _validate_coverage_dimensions(node_id: CheckpointNode, coverage: list[EpochDimension]) -> None:
    if len(coverage) != len(set(coverage)):
        raise InvalidStateTransitionError("coverage dimensions must be unique")
    required = {
        CheckpointNode.IMPLEMENTATION: {EpochDimension.IMPLEMENTATION_CONTENT},
        CheckpointNode.VERIFICATION: {EpochDimension.IMPLEMENTATION_CONTENT},
        CheckpointNode.REPAIR: {EpochDimension.IMPLEMENTATION_CONTENT},
        CheckpointNode.DOCUMENTATION: {EpochDimension.DOCUMENTATION},
        CheckpointNode.GIT: {EpochDimension.GIT_METADATA},
        CheckpointNode.ACCEPTANCE: set(EpochDimension),
        CheckpointNode.CONTROL: set(EpochDimension),
    }.get(node_id, set())
    if not required <= set(coverage):
        missing = sorted(item.value for item in required - set(coverage))
        raise InvalidStateTransitionError(
            f"checkpoint {node_id.value} must cover these Epoch dimensions: {missing}"
        )


def _latest_evidence(
    connection: sqlite3.Connection, node_id: str, current_rule_hash: str
) -> tuple[list[dict[str, object]], list[dict[str, object]], int, str]:
    rows = connection.execute(
        "SELECT facts_json,evidence_refs_json,basis_revision,input_hash,rule_hash,coverage_json,"
        "implementation_epoch,documentation_epoch,git_metadata_epoch,recorded_revision "
        "FROM checkpoint_evidence WHERE node_id=? ORDER BY recorded_revision DESC",
        (node_id,),
    ).fetchall()
    if not rows:
        return [], [], -1, ""
    epochs = _epoch_snapshot(connection)
    latest = rows[0]
    for row in rows:
        if row[4] == current_rule_hash and not _epochs_cover_changed_dimensions(
            json.loads(row[5]),
            (row[6], row[7], row[8]),
            epochs.model_dump(mode="json"),
        ):
            return json.loads(row[0]), json.loads(row[1]), row[2], row[3]
    return [], [], latest[2], latest[3]


def _epochs_cover_changed_dimensions(
    coverage: list[str], saved: tuple[int, int, int], current: Mapping[str, int]
) -> bool:
    saved_by_dimension = {
        "implementation_content": saved[0],
        "documentation": saved[1],
        "git_metadata": saved[2],
    }
    return any(saved_by_dimension[dimension] != current[dimension] for dimension in coverage)


def _missing_requirements(
    context: RuleContext, facts: list[dict[str, object]], refs: list[dict[str, object]]
) -> tuple[list[FactKey], list[str]]:
    by_key = {item["fact_key"]: item["judgment"] for item in facts}
    missing_facts: list[FactKey] = []
    for key in context.required_facts:
        judgment = by_key.get(key)
        if not isinstance(judgment, dict) or judgment.get("status") in {
            "unknown",
            "missing_evidence",
        }:
            try:
                missing_facts.append(FactKey(key))
            except ValueError:
                continue
    found = {item["kind"] for item in refs}
    missing_evidence = [kind for kind in context.required_evidence if kind not in found]
    return missing_facts, missing_evidence


def _validate_checkpoint_state(
    connection: sqlite3.Connection, node_id: CheckpointNode, branch: str | None
) -> list[str]:
    control = _required_control(connection)
    failures: list[str] = []
    allocations = connection.execute(
        "SELECT status,role,worker_session_id FROM allocations ORDER BY slot"
    ).fetchall()
    if control[4] == "Single-Agent Coding" and allocations:
        failures.append("single-agent workflow contains Worker allocations")
    if control[4] == "Multi-Agent Coding" and len(allocations) != control[5]:
        failures.append("allocation count differs from the locked child budget")
    if node_id is CheckpointNode.MODE and branch:
        expected = "single-agent" if control[4] == "Single-Agent Coding" else "multi-agent"
        if branch != expected:
            failures.append("mode branch differs from the persisted mode/count")
    if node_id is CheckpointNode.DELEGATION:
        bound = sum(row[0] in {"bound", "initialized"} for row in allocations)
        if bound > control[5]:
            failures.append("bound allocations exceed the locked child budget")
    if node_id is CheckpointNode.SLICE:
        active_worker = _one(connection, "SELECT 1 FROM workflow_slices WHERE status='released'")
        active_root = _one(connection, "SELECT 1 FROM root_slices WHERE status='released'")
        if active_worker is not None and active_root is not None:
            failures.append("multiple Root/Worker slices are active")
        if control[10] in {"completed", "interrupted"}:
            failures.append("workflow lifecycle is terminal")
    if node_id is CheckpointNode.CONTROL:
        if control[10] not in {"running", "pending"}:
            failures.append("workflow is not in a controllable lifecycle")
        if branch == "continue" and _one(
            connection, "SELECT 1 FROM control_transitions WHERE outcome='stop'"
        ):
            failures.append("Stop is terminal")
    if node_id is CheckpointNode.ACCEPTANCE and control[10] != "running":
        failures.append("Acceptance requires a running non-terminal workflow")
    return failures


def _validate_acceptance_history(connection: sqlite3.Connection, rule_loader: RuleLoader) -> list[str]:
    epochs = _epoch_snapshot(connection)
    expected_branches = {
        "contract": {"ready", "sufficient"},
        "mode": {"single-agent", "multi-agent"},
        "decision": {"decided"},
        "implementation": {"complete", "return for control"},
        "verification": {"pass"},
        "control": {"continue"},
    }
    optional_nodes = {"repair", "documentation", "git"}
    errors: list[str] = []
    for node_id, branches in expected_branches.items():
        row = _one(
            connection,
            "SELECT outcome,branch,rule_hash,implementation_epoch,documentation_epoch,"
            "git_metadata_epoch FROM checkpoint_evaluations WHERE node_id=? "
            "ORDER BY result_revision DESC LIMIT 1",
            (node_id,),
        )
        if row is None:
            errors.append(f"{node_id} checkpoint is missing")
            continue
        if (
            row[0] != "ready"
            or row[1] not in branches
            or row[2] != rule_loader.load_context(node_id).context_hash
            or tuple(row[3:])
            != (
                epochs.implementation_content,
                epochs.documentation,
                epochs.git_metadata,
            )
        ):
            errors.append(f"{node_id} checkpoint is stale or unsuccessful")
    for node_id in optional_nodes:
        row = _one(
            connection,
            "SELECT outcome,branch,rule_hash,implementation_epoch,documentation_epoch,"
            "git_metadata_epoch FROM checkpoint_evaluations WHERE node_id=? "
            "ORDER BY result_revision DESC LIMIT 1",
            (node_id,),
        )
        if row is None:
            continue
        if (
            row[0] != "ready"
            or row[1] in {"failure", "inconclusive", "blocked", "incomplete"}
            or row[2] != rule_loader.load_context(node_id).context_hash
            or tuple(row[3:])
            != (
                epochs.implementation_content,
                epochs.documentation,
                epochs.git_metadata,
            )
        ):
            errors.append(f"{node_id} checkpoint is stale or unsuccessful")
    return errors


def _validate_fact_state(
    connection: sqlite3.Connection, facts: list[dict[str, object]]
) -> list[str]:
    control = _required_control(connection)
    epochs = _epoch_snapshot(connection)
    actual = {
        FactKey.VALID_MODE_DECISION.value: "single-agent"
        if control[4] == "Single-Agent Coding"
        else "multi-agent",
        FactKey.LOCKED_CHILD_COUNT.value: int(control[5]),
        FactKey.CURRENT_IMPLEMENTATION_EPOCH.value: epochs.implementation_content,
        FactKey.AFFECTED_VERIFICATION_EPOCH.value: epochs.implementation_content,
        FactKey.AFFECTED_DOCUMENTATION_EPOCH.value: epochs.documentation,
        FactKey.CURRENT_GIT_EPOCH.value: epochs.git_metadata,
    }
    failures: list[str] = []
    for fact in facts:
        key = fact.get("fact_key")
        judgment = fact.get("judgment")
        if not isinstance(judgment, dict):
            continue
        if judgment.get("status") == "not_applicable":
            if key == FactKey.LOCKED_CHILD_COUNT.value and control[4] != "Single-Agent Coding":
                failures.append("locked child count cannot be not-applicable in Multi-Agent mode")
            continue
        if judgment.get("status") != "determined":
            continue
        value = judgment.get("value")
        if not isinstance(value, dict):
            continue
        if key in actual:
            expected = actual[key]
            if value.get("value") != expected:
                failures.append(f"{key} does not match persisted Root state")
        if key == FactKey.CAPABILITY_GATE_RESULT.value and value.get("value") is not True:
            failures.append("capability gate is not satisfied")
    return failures


def _workflow_state(connection: sqlite3.Connection) -> WorkflowState:
    control = _required_control(connection)
    allocations = [
        AllocationState(
            allocation_id=row[0],
            slot=row[1],
            role=row[2],
            status=AllocationStatus(row[3]),
            worker_session_id=row[4],
            output_class=OutputClass(row[5]) if row[5] else None,
        )
        for row in connection.execute(
            "SELECT allocation_id, slot, role, status, worker_session_id, output_class "
            "FROM allocations ORDER BY slot"
        )
    ]
    return WorkflowState(
        project_id=control[1],
        root_session_id=control[2],
        run_id=control[3],
        mode_count=ModeCount(mode=CodingMode(control[4]), child_count=control[5]),
        mode_source=control[6],
        source=SemanticRef(uri=control[7], content_hash=control[8]),
        semantic_references=json.loads(control[9]),
        lifecycle=control[10],
        revision=control[11],
        allocations=allocations,
    )


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


def _nonempty(value: str, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value.strip()


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _hash_json(value: object) -> str:
    return hashlib.sha256(_json(value).encode("utf-8")).hexdigest()


def _one(
    connection: sqlite3.Connection,
    sql: str,
    parameters: tuple[object, ...] = (),
) -> sqlite3.Row | None:
    connection.row_factory = sqlite3.Row
    return connection.execute(sql, parameters).fetchone()
