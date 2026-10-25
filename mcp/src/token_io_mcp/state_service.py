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
from typing import Literal, cast
from urllib.parse import quote

from pydantic import TypeAdapter

from token_io_mcp.binding import BindingError, BindingProvider
from token_io_mcp.migrations.runner import (
    DEFAULT_LOCK_TIMEOUT_SECONDS,
    DatabaseIdentityMismatchError,
    _migration_lock,
    _package_migrations,
    open_database_for_authorized_write,
    read_schema_status,
    validate_connection_identity,
    validate_existing_connection,
)
from token_io_mcp.models import (
    CodingMode,
    DatabaseKind,
    EvidenceRef,
    RuleContext,
    SchemaStatus,
    SemanticRef,
)
from token_io_mcp.rules import RuleLoader, RuleLoadError, UnknownRuleNodeError
from token_io_mcp.state_models import (
    ActiveSliceIndex,
    AllocationRole,
    AllocationState,
    AllocationStatus,
    BindingIdentity,
    BlockerRecord,
    ChangeCategory,
    CheckpointConfirmationTransition,
    CheckpointEvaluation,
    CheckpointNode,
    ControlEvidenceRequestIndex,
    ControlTransitionRequest,
    EpochAdvanceTransition,
    EpochDimension,
    EpochSnapshot,
    EvidenceKind,
    EvidenceRecord,
    EvidenceSubmission,
    FactKey,
    GateIndex,
    HostCapability,
    HostGuard,
    LegalBranch,
    ModeCount,
    MutationReceipt,
    NativeReconcileIndex,
    NativeReconcileResolutionTransition,
    NativeReconcileTransition,
    NativeResolutionIndex,
    NativeResolutionTargetIndex,
    NativeWorkflowSnapshot,
    OutputClass,
    ProgressRecord,
    ReconcileResult,
    RecoveryIndexCollection,
    RecoveryIndexCursor,
    RecoveryIndexPageInfo,
    RecoveryIndexPageRequest,
    SessionAudit,
    SessionAuditTransition,
    SessionRole,
    SliceCheckResult,
    SliceSpec,
    TrustedCapabilitySnapshot,
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


class StaleRecoveryCursorError(StateServiceError):
    """A recovery-index cursor refers to an older Root Revision."""


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
            _ensure_native_resolution(connection)
            request_id = submission.evidence_request_id
            if request_id is not None:
                request = _one(
                    connection,
                    "SELECT status,returned_revision FROM control_evidence_requests "
                    "WHERE request_id=?",
                    (request_id,),
                )
                if request is None or request[0] not in {"pending", "returned"}:
                    raise InvalidStateTransitionError(
                        "returned evidence must match a pending Control request or an "
                        "unresolved Control request eligible for recovery"
                    )
                if request[0] == "returned" and (
                    int(control[13]) <= 0
                    or request[1] is None
                    or int(request[1]) >= int(control[13])
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
        evaluation, _replayed = self.workflow_evaluate_with_replay(
            node_id,
            expected_revision=expected_revision,
            idempotency_key=idempotency_key,
            branch=branch,
            input_hash=input_hash,
            slice_ids=slice_ids,
        )
        return evaluation

    def workflow_evaluate_with_replay(
        self,
        node_id: CheckpointNode,
        *,
        expected_revision: int,
        idempotency_key: str,
        branch: str | None = None,
        input_hash: str | None = None,
        slice_ids: list[str] | None = None,
    ) -> tuple[CheckpointEvaluation, bool]:
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
                return CheckpointEvaluation.model_validate_json(_json(replay.result)), True
            if type(expected_revision) is not int or expected_revision < 0:
                raise ValueError("expected_revision must be a non-negative integer")
            if expected_revision != current:
                raise RevisionConflictError(
                    f"expected Revision {expected_revision}, current Revision is {current}"
                )
            _ensure_native_resolution(connection)
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
                # EOD is a request to collect more evidence, not a shortcut around
                # the Control checkpoint's own facts and evidence requirements.
                if outcome == "ready" and final_branch == branch:
                    outcome, final_branch = "evidence_on_demand", "evidence-on-demand"
            evidence_request_id: str | None = None
            if (
                node_id is CheckpointNode.CONTROL
                and branch == "evidence-on-demand"
                and outcome == "evidence_on_demand"
            ):
                evidence_request_id = str(uuid.uuid4())
            elif node_id is CheckpointNode.CONTROL and branch == "continue":
                requests = connection.execute(
                    "SELECT request_id,status,returned_revision FROM control_evidence_requests "
                    "WHERE status IN ('pending','returned') "
                    "ORDER BY created_revision DESC,request_id"
                ).fetchall()
                pending_requests = [item for item in requests if item[1] == "pending"]
                fresh_returned = [
                    item
                    for item in requests
                    if item[1] == "returned"
                    and item[2] is not None
                    and int(item[2]) > int(control[13])
                ]
                if pending_requests:
                    outcome = "incomplete"
                    missing_evidence.append("returned evidence for every pending Control request")
                elif requests and not fresh_returned:
                    outcome = "incomplete"
                    missing_evidence.append(
                        "new returned evidence after Native recovery for the Control request"
                    )
                elif fresh_returned:
                    evidence_request_id = str(fresh_returned[0][0])
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
            if (
                node_id is CheckpointNode.CONTROL
                and branch == "evidence-on-demand"
                and outcome == "evidence_on_demand"
            ):
                connection.execute(
                    "INSERT INTO control_evidence_requests "
                    "(request_id,source_evaluation_id,created_revision,status,created_at) "
                    "VALUES (?, ?, ?, 'pending', ?)",
                    (evidence_request_id, evaluation_id, result_revision, _now()),
                )
            connection.execute(
                "UPDATE workflow_control SET revision=? WHERE singleton=1", (result_revision,)
            )
            self._record_binding_snapshot(connection, binding, result_revision)
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
            return evaluation, False

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

    def evaluate_control_checkpoint_with_replay(
        self,
        *,
        expected_revision: int,
        idempotency_key: str,
        branch: str | None = None,
        input_hash: str | None = None,
        slice_ids: list[str] | None = None,
    ) -> tuple[CheckpointEvaluation, bool]:
        return self.workflow_evaluate_with_replay(
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
                    "SELECT status,returned_revision FROM control_evidence_requests "
                    "WHERE request_id=?",
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

    def _update_session_audit(self, request: SessionAuditTransition) -> MutationReceipt:
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

    def workflow_reconcile(
        self,
        snapshot: NativeWorkflowSnapshot,
        *,
        confirm: bool = False,
        expected_revision: int,
        idempotency_key: str,
    ) -> ReconcileResult:
        snapshot = NativeWorkflowSnapshot.model_validate(snapshot)
        if (
            len(snapshot.semantic_references) > 256
            or len(snapshot.allocations) > 256
            or len(snapshot.evidence_refs) > 256
        ):
            raise InvalidStateTransitionError(
                "Native snapshot exceeds the supported bounded recovery index"
            )
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
                    "SELECT observed_revision,result_revision,reconcile_id "
                    "FROM native_reconciliations "
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
                if (
                    _one(
                        connection,
                        "SELECT 1 FROM native_reconcile_preimages WHERE reconcile_id=?",
                        (approved_comparison[2],),
                    )
                    is None
                ):
                    raise InvalidStateTransitionError(
                        "legacy Native comparison lacks a captured Root preimage; compare again"
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
            root_preimage = _json(_native_root_preimage(connection))
            root_preimage_hash = _hash_json(json.loads(root_preimage))
            if status == "matched" and confirm and control is None:
                now = _now()
                run_id = snapshot.run_id or str(uuid.uuid4())
                connection.execute(
                    "INSERT INTO workflow_control "
                    "(singleton,project_id,root_session_id,run_id,mode,child_count,mode_source,"
                    "source_uri,source_hash,semantic_references_json,lifecycle,revision,"
                    "created_at) "
                    "VALUES (1,?,?,?,?,?,?,?,?,?,?,?,?)",
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
                self._record_binding_snapshot(connection, binding, result_rev)
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
            if confirm and status == "matched" and approved_comparison is not None:
                connection.execute(
                    "INSERT INTO native_reconcile_confirmations VALUES (?,?,?,?,?)",
                    (
                        approved_comparison[2],
                        rid,
                        snapshot_hash,
                        result_rev,
                        _now(),
                    ),
                )
            connection.execute(
                "INSERT INTO native_reconcile_preimages VALUES (?, ?, ?, ?, ?, ?)",
                (
                    rid,
                    snapshot_hash,
                    root_preimage,
                    root_preimage_hash,
                    current,
                    _now(),
                ),
            )
            if control:
                connection.execute(
                    "UPDATE workflow_control SET revision=? WHERE singleton=1", (result_rev,)
                )
                self._record_binding_snapshot(connection, binding, result_rev)
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

    def _resolve_native_reconcile(
        self, request: NativeReconcileResolutionTransition
    ) -> MutationReceipt:
        """Resolve a reviewed complete conflict set without importing identity/history."""
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
                raise RevisionConflictError("workflow changed before Native resolution")

            unresolved = _unresolved_native_rows(connection)
            if not unresolved:
                raise InvalidStateTransitionError("there is no unresolved Native comparison set")
            canonical = _one(
                connection,
                "SELECT reconcile_id,snapshot_hash,status,snapshot_json,result_revision "
                "FROM native_reconciliations "
                "ORDER BY result_revision DESC,reconcile_id DESC LIMIT 1",
            )
            if canonical is None or canonical[0] != request.canonical_reconcile_id:
                raise RevisionConflictError(
                    "Native resolution must bind the latest reviewed comparison"
                )
            if canonical[1] != request.snapshot_hash:
                raise RevisionConflictError("Native snapshot hash changed after review")
            if (
                _one(
                    connection,
                    "SELECT 1 FROM native_reconcile_preimages WHERE reconcile_id=? "
                    "AND snapshot_hash=?",
                    (canonical[0], canonical[1]),
                )
                is None
            ):
                raise InvalidStateTransitionError(
                    "latest comparison has no v5 Root preimage; create a fresh comparison"
                )
            review_hash = _native_review_set_hash(connection, current, unresolved, canonical)
            if request.unresolved_set_hash != review_hash:
                raise RevisionConflictError("unresolved Native comparison set changed after review")

            reviewed_rows: dict[str, sqlite3.Row | tuple[object, ...]] = {
                str(row[0]): row for row in unresolved
            }
            canonical_row = (
                canonical[0],
                canonical[1],
                canonical[2],
                "[]",
                0,
                canonical[4],
                json.loads(canonical[3]),
            )
            if canonical[0] not in reviewed_rows:
                reviewed_rows[str(canonical[0])] = canonical_row
            if len(reviewed_rows) > 256:
                raise InvalidStateTransitionError(
                    "Native resolution set exceeds the supported bounded review index"
                )
            snapshots: list[tuple[sqlite3.Row | tuple[object, ...], NativeWorkflowSnapshot]] = []
            permitted_differences = {
                "Revision",
                "Epochs",
                "Contract source",
                "semantic references",
            }
            max_native_revision = 0
            max_native_epochs = {"implementation_content": 0, "documentation": 0, "git_metadata": 0}
            reviewed_native_refs: set[tuple[str, str]] = set()
            expected_allocations = [
                (item.allocation_id, item.role, item.worker_session_id, item.status.value)
                for item in _workflow_state(connection).allocations
            ]
            for row in reviewed_rows.values():
                row_id, snapshot_hash, status, differences_json, *_tail, snapshot_json = row
                differences = set(json.loads(cast(str, differences_json)))
                unsupported = differences - permitted_differences
                if unsupported:
                    raise InvalidStateTransitionError(
                        "Native set contains unsupported identity or lifecycle differences"
                    )
                snapshot = NativeWorkflowSnapshot.model_validate_json(
                    _json(snapshot_json) if isinstance(snapshot_json, dict) else str(snapshot_json)
                )
                if (
                    len(snapshot.semantic_references) > 256
                    or len(snapshot.allocations) > 256
                    or len(snapshot.evidence_refs) > 256
                ):
                    raise InvalidStateTransitionError(
                        "Native snapshot exceeds the supported adjudication bound"
                    )
                if _hash_json(snapshot.model_dump(mode="json")) != snapshot_hash:
                    raise InvalidStateTransitionError("stored Native snapshot hash is invalid")
                if (snapshot.project_id, snapshot.root_session_id) != (
                    binding.project_id,
                    binding.root_session_id,
                ):
                    raise InvalidStateTransitionError("Native set crosses project or Root identity")
                if (
                    snapshot.run_id != control[3]
                    or snapshot.mode_count.mode.value != control[4]
                    or snapshot.mode_count.child_count != control[5]
                    or snapshot.mode_source != control[6]
                    or snapshot.lifecycle != control[10]
                ):
                    raise InvalidStateTransitionError(
                        "Native set changes immutable Run, mode, count, source mode, or lifecycle"
                    )
                native_allocations = [
                    (
                        item.allocation_id,
                        item.role.value if item.role else None,
                        item.worker_session_id,
                        item.status.value,
                    )
                    for item in snapshot.allocations
                ]
                if native_allocations != expected_allocations:
                    raise InvalidStateTransitionError(
                        "Native set changes allocation identity or dispatch history"
                    )
                if any(
                    item.worker_session_id is not None
                    or item.status in {AllocationStatus.BOUND, AllocationStatus.INITIALIZED}
                    for item in snapshot.allocations
                ):
                    raise InvalidStateTransitionError(
                        "Native Worker identity or initialized dispatch cannot be imported"
                    )
                max_native_revision = max(max_native_revision, snapshot.revision)
                reviewed_native_refs.update(
                    (item.uri, item.content_hash) for item in snapshot.evidence_refs
                )
                for dimension in max_native_epochs:
                    max_native_epochs[dimension] = max(
                        max_native_epochs[dimension], int(getattr(snapshot.epochs, dimension))
                    )
                snapshots.append((row, snapshot))

            if request.reviewed_native_revision != max_native_revision:
                raise InvalidStateTransitionError(
                    "Native attestation revision must equal the maximum reviewed timeline revision"
                )
            if request.reviewed_native_epochs.model_dump(mode="json") != max_native_epochs:
                raise InvalidStateTransitionError(
                    "Native attestation Epochs must equal the maximum reviewed timeline Epochs"
                )
            provided_native_refs = [
                (item.uri, item.content_hash) for item in request.native_freshness_refs
            ]
            if (
                len(provided_native_refs) != len(set(provided_native_refs))
                or set(provided_native_refs) != reviewed_native_refs
            ):
                raise InvalidStateTransitionError(
                    "Native freshness references must exactly cover the reviewed snapshots"
                )
            if not request.root_quiescence_refs:
                raise InvalidStateTransitionError("Root quiescence evidence is required")

            if control[10] in {"completed", "interrupted"}:
                raise InvalidStateTransitionError(
                    "terminal workflow cannot be resumed by resolution"
                )
            if _one(
                connection,
                "SELECT 1 FROM allocations WHERE worker_session_id IS NOT NULL "
                "OR status IN ('bound','initialized') LIMIT 1",
            ):
                raise InvalidStateTransitionError(
                    "bound or initialized Worker identity requires its own verified recovery"
                )
            if _one(connection, "SELECT 1 FROM workflow_slices WHERE status='released' LIMIT 1"):
                raise InvalidStateTransitionError("active Worker Slice blocks Native resolution")
            if _one(
                connection,
                "SELECT 1 FROM root_outbox WHERE status='pending' LIMIT 1",
            ) or _one(
                connection,
                "SELECT 1 FROM workflow_dispatch_events WHERE status='pending' LIMIT 1",
            ):
                raise InvalidStateTransitionError(
                    "pending Worker dispatch blocks Native resolution"
                )
            if any(
                item.worker_session_id is not None
                or item.status in {AllocationStatus.BOUND, AllocationStatus.INITIALIZED}
                for _, snapshot in snapshots
                for item in snapshot.allocations
            ):
                raise InvalidStateTransitionError("reviewed Native set contains Worker history")

            canonical_snapshot = NativeWorkflowSnapshot.model_validate_json(canonical[3])
            selected_source = (
                canonical_snapshot.source
                if request.choice == "adopt_native_pair"
                else SemanticRef(uri=control[7], content_hash=control[8])
            )
            selected_refs = (
                canonical_snapshot.semantic_references
                if request.choice == "adopt_native_pair"
                else [SemanticRef.model_validate(item) for item in json.loads(control[9])]
            )
            db_epochs = _epoch_snapshot(connection)
            max_epochs = {
                dimension: max(int(getattr(db_epochs, dimension)), max_native_epochs[dimension])
                for dimension in max_native_epochs
            }
            sqlite_max = 2**63 - 1
            result_revision = max(current, max_native_revision) + 1
            next_epochs = {key: value + 1 for key, value in max_epochs.items()}
            if result_revision > sqlite_max or any(
                value > sqlite_max for value in next_epochs.values()
            ):
                raise InvalidStateTransitionError("Native recovery counters exceed SQLite int64")
            recovery_revision = result_revision
            resolution_id = str(uuid.uuid4())
            now = _now()
            native_epochs_json = _json(max_native_epochs)
            connection.execute(
                "INSERT INTO native_reconcile_resolutions "
                "(resolution_id,reconcile_id,reviewed_set_hash,snapshot_hash,choice,"
                "selected_source_uri,selected_source_hash,selected_semantic_references_json,"
                "native_revision,native_epochs_json,root_decision_ref_json,"
                "native_freshness_refs_json,root_quiescence_refs_json,"
                "observed_revision,result_revision,recovery_revision,created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    resolution_id,
                    request.canonical_reconcile_id,
                    review_hash,
                    request.snapshot_hash,
                    request.choice,
                    selected_source.uri,
                    selected_source.content_hash,
                    _json([item.model_dump(mode="json") for item in selected_refs]),
                    max_native_revision,
                    native_epochs_json,
                    _json(request.root_decision_ref.model_dump(mode="json")),
                    _json([item.model_dump(mode="json") for item in request.native_freshness_refs]),
                    _json([item.model_dump(mode="json") for item in request.root_quiescence_refs]),
                    current,
                    result_revision,
                    recovery_revision,
                    now,
                ),
            )
            for row in reviewed_rows.values():
                connection.execute(
                    "INSERT INTO native_reconcile_resolution_targets VALUES (?, ?, ?)",
                    (row[0], resolution_id, row[1]),
                )
            connection.execute(
                "UPDATE workflow_control SET source_uri=?,source_hash=?,"
                "semantic_references_json=?,revision=?,recovery_revision=? WHERE singleton=1",
                (
                    selected_source.uri,
                    selected_source.content_hash,
                    _json([item.model_dump(mode="json") for item in selected_refs]),
                    result_revision,
                    recovery_revision,
                ),
            )
            connection.execute(
                "UPDATE workflow_epochs SET implementation_content=?,documentation=?,"
                "git_metadata=? WHERE singleton=1",
                (
                    next_epochs["implementation_content"],
                    next_epochs["documentation"],
                    next_epochs["git_metadata"],
                ),
            )
            connection.execute("UPDATE root_slices SET status='closed' WHERE status='released'")
            self._record_binding_snapshot(connection, binding, result_revision)
            result = {
                "resolution_id": resolution_id,
                "canonical_reconcile_id": request.canonical_reconcile_id,
                "reviewed_set_hash": review_hash,
                "resolved_comparison_count": len(reviewed_rows),
                "choice": request.choice,
                "result_revision": result_revision,
                "recovery_revision": recovery_revision,
                "epochs": next_epochs,
                "source": selected_source.model_dump(mode="json"),
                "semantic_references": [item.model_dump(mode="json") for item in selected_refs],
            }
            return self._store_receipt(
                connection,
                "operation_receipts",
                request.idempotency_key,
                "workflow_transition",
                payload_hash,
                result,
                result_revision,
            )

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
                _ensure_native_resolution(connection)
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

            _ensure_native_resolution(connection)

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
            self._record_binding_snapshot(connection, binding, 0)
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

    def workflow_get_state(
        self, *, index_page: RecoveryIndexPageRequest | None = None
    ) -> WorkflowState:
        binding = self._parent_binding({HostCapability.WORKFLOW_READ}, {HostGuard.PATH_BOUNDARY})
        if index_page is not None:
            index_page = RecoveryIndexPageRequest.model_validate(index_page)
        path, root = self._root_database(binding, create=False)
        with self._read_transaction(path, DatabaseKind.WORKFLOW, root) as connection:
            return _workflow_state(connection, self._rule_loader, binding, index_page)

    def workflow_get_state_for_evaluation(
        self, evaluation: CheckpointEvaluation
    ) -> WorkflowState | None:
        """Return current state only when the evaluation belongs to this bound Root DB."""
        binding = self._parent_binding({HostCapability.WORKFLOW_READ}, {HostGuard.PATH_BOUNDARY})
        path, root = self._root_database(binding, create=False)
        with self._read_transaction(path, DatabaseKind.WORKFLOW, root) as connection:
            _validate_root_identity(connection, binding)
            row = _one(
                connection,
                "SELECT node_id,outcome,branch,input_hash,rule_hash,implementation_epoch,"
                "documentation_epoch,git_metadata_epoch,basis_revision,result_revision,"
                "missing_facts_json,missing_evidence_json,slice_ids_json,evidence_request_id "
                "FROM checkpoint_evaluations WHERE evaluation_id=?",
                (evaluation.evaluation_id,),
            )
            if row is None:
                return None
            expected = (
                evaluation.node_id.value,
                evaluation.outcome,
                evaluation.branch.value if evaluation.branch is not None else None,
                evaluation.input_hash,
                evaluation.rule_hash,
                evaluation.epochs.implementation_content,
                evaluation.epochs.documentation,
                evaluation.epochs.git_metadata,
                evaluation.basis_revision,
                evaluation.result_revision,
                _json([item.value for item in evaluation.missing_facts]),
                _json(evaluation.missing_evidence),
                _json(evaluation.slice_ids),
                evaluation.evidence_request_id,
            )
            if tuple(row) != expected:
                return None
            return _workflow_state(connection, self._rule_loader, binding)

    def database_schema_status(self) -> SchemaStatus:
        """Read only the current trusted session database schema without mutation."""
        current = self._binding_provider.current_binding()
        if current.role is SessionRole.PARENT:
            binding = self._parent_binding(
                {HostCapability.WORKFLOW_READ}, {HostGuard.PATH_BOUNDARY}
            )
            kind = DatabaseKind.WORKFLOW
            path, root = self._root_database(binding, create=False)
        elif current.role is SessionRole.WORKER:
            binding = self._worker_binding({HostCapability.WORKER_READ})
            kind = DatabaseKind.WORKER
            path, root = self._worker_database(binding.current_session_id, binding, create=False)
        else:
            raise BindingError("a trusted Root or Worker binding is required")
        if not root.exists():
            migrations = _package_migrations(kind)
            return SchemaStatus(
                exists=False,
                database_kind=None,
                current_version=0,
                target_version=migrations[-1].version,
                pending_versions=[migration.version for migration in migrations],
                compatible=False,
                reason="database does not exist",
            )
        return read_schema_status(path, kind, trusted_root=root)

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
            control_context = self._rule_loader.load_context(CheckpointNode.CONTROL.value)
            checked = _check_slice(
                connection,
                spec,
                context.context_hash,
                control_context.context_hash,
            )
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
                allocation_id, payload_json, payload_hash, event_status, sequence, outbox_status = (
                    event
                )
                payload = json.loads(payload_json)
                if payload["worker_session_id"] != child.child_session_id:
                    raise WorkerInitializationError(
                        "outbox Worker identity differs from trusted child"
                    )
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
                identity = _one(
                    worker_connection, "SELECT * FROM worker_identity WHERE singleton=1"
                )
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
                        raise WorkerInitializationError(
                            "Worker identity differs from dispatch history"
                        )
                    if history[0] == "confirmed":
                        if history[3] != assignment_hash:
                            raise WorkerInitializationError(
                                "confirmed dispatch snapshot hash changed"
                            )
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
                            "missing dispatch history cannot be reconstructed behind "
                            "the active pointer"
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
                        "UPDATE worker_inbox SET status='confirmed',confirmed_at=? "
                        "WHERE event_id=?",
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
                            "UPDATE worker_active_dispatch SET event_id=?,sequence=? "
                            "WHERE singleton=1",
                            (event_id, sequence),
                        )

    def _worker_dispatch_is_confirmed(
        self,
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
            active = _one(
                connection, "SELECT sequence FROM worker_active_dispatch WHERE singleton=1"
            )
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

    def _record_binding_snapshot(
        self,
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
            with self._locked_write_connection(
                path, kind, trusted_root, logical_identity=logical_identity
            ) as connection:
                yield connection

    @contextmanager
    def _locked_write_connection(
        self,
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
    connection: sqlite3.Connection,
    spec: SliceSpec,
    current_rule_hash: str,
    current_control_rule_hash: str,
) -> SliceCheckResult:
    expected_input_hash = _slice_spec_hash(spec)
    output_class = spec.output_class
    control = _required_control(connection)
    if _unresolved_native_rows(connection):
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
    recovery_revision = int(control[13])
    has_prior_slices = (
        _one(connection, "SELECT 1 FROM workflow_slices LIMIT 1") is not None
        or _one(connection, "SELECT 1 FROM root_slices LIMIT 1") is not None
    )
    if has_prior_slices or recovery_revision > 0:
        current_epochs = _epoch_snapshot(connection)
        last_control = _one(
            connection,
            "SELECT ct.outcome,ct.to_revision,ce.outcome,ce.branch,ce.rule_hash,"
            "ce.implementation_epoch,ce.documentation_epoch,ce.git_metadata_epoch "
            "FROM control_transitions AS ct "
            "JOIN checkpoint_evaluations AS ce ON ce.evaluation_id=ct.evaluation_id "
            "ORDER BY ct.to_revision DESC LIMIT 1",
        )
        control_is_current = recovery_revision == 0 or (
            last_control is not None
            and int(last_control[1]) > recovery_revision
            and last_control[2] == "ready"
            and last_control[3] == "continue"
            and last_control[4] == current_control_rule_hash
            and tuple(last_control[5:8])
            == (
                current_epochs.implementation_content,
                current_epochs.documentation,
                current_epochs.git_metadata,
            )
        )
        if (
            last_control is None
            or last_control[0] != "continue"
            or int(last_control[1]) <= recovery_revision
            or not control_is_current
        ):
            return SliceCheckResult(
                eligible=False,
                reason="a current Control Continue is required before another Slice",
                allocation_id=spec.allocation_id,
                output_class=output_class,
            )
    latest_amend = _one(
        connection,
        "SELECT to_revision FROM control_transitions WHERE outcome='amend' "
        "ORDER BY to_revision DESC LIMIT 1",
    )
    if latest_amend is not None:
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
                or evaluation[1] <= latest_amend[0]
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
        or tuple(prerequisite[1:])[:3]
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
    if _unresolved_native_rows(connection):
        raise InvalidStateTransitionError(
            "Native reconciliation must be explicitly resolved before new Root mutations"
        )


def _unresolved_native_rows(connection: sqlite3.Connection) -> list[sqlite3.Row]:
    return connection.execute(
        "SELECT n.reconcile_id,n.snapshot_hash,n.status,n.differences_json,"
        "n.observed_revision,n.result_revision,n.snapshot_json "
        "FROM native_reconciliations AS n "
        "WHERE n.status IN ('conflict','awaiting_confirmation') "
        "AND NOT EXISTS (SELECT 1 FROM native_reconcile_resolution_targets AS t "
        "WHERE t.reconcile_id=n.reconcile_id) "
        "AND (n.status!='awaiting_confirmation' OR NOT EXISTS ("
        "SELECT 1 FROM native_reconcile_confirmations AS c "
        "WHERE c.awaiting_reconcile_id=n.reconcile_id)) "
        "ORDER BY n.result_revision,n.reconcile_id LIMIT 257"
    ).fetchall()


def _native_review_set_hash(
    connection: sqlite3.Connection,
    current_revision: int,
    unresolved: list[sqlite3.Row],
    canonical: sqlite3.Row | tuple[object, ...] | None = None,
) -> str:
    if canonical is None:
        canonical = _one(
            connection,
            "SELECT reconcile_id,snapshot_hash,status,snapshot_json,result_revision "
            "FROM native_reconciliations ORDER BY result_revision DESC,reconcile_id DESC LIMIT 1",
        )
    return _hash_json(
        {
            "revision": current_revision,
            "unresolved": [
                {
                    "reconcile_id": row[0],
                    "snapshot_hash": row[1],
                    "status": row[2],
                    "differences": json.loads(row[3]),
                    "observed_revision": int(row[4]),
                    "result_revision": int(row[5]),
                }
                for row in unresolved
            ],
            "canonical": (
                {
                    "reconcile_id": canonical[0],
                    "snapshot_hash": canonical[1],
                    "status": canonical[2],
                    "result_revision": cast(int, canonical[4]),
                }
                if canonical is not None
                else None
            ),
        }
    )


def _native_root_preimage(connection: sqlite3.Connection) -> dict[str, object]:
    """Capture the bounded Root control state changed by reconciliation, not a DB backup."""
    tables = (
        ("workflow_control", "SELECT * FROM workflow_control WHERE singleton=1"),
        ("allocations", "SELECT * FROM allocations ORDER BY slot,allocation_id"),
        ("workflow_epochs", "SELECT * FROM workflow_epochs WHERE singleton=1"),
        ("root_slices", "SELECT * FROM root_slices ORDER BY created_revision,slice_id"),
        ("workflow_slices", "SELECT * FROM workflow_slices ORDER BY created_revision,slice_id"),
        (
            "control_transitions",
            "SELECT * FROM control_transitions ORDER BY to_revision,transition_id",
        ),
        (
            "control_evidence_requests",
            "SELECT * FROM control_evidence_requests ORDER BY created_revision,request_id",
        ),
        ("workflow_session_metadata", "SELECT * FROM workflow_session_metadata WHERE singleton=1"),
    )
    return {
        table: [dict(row) for row in connection.execute(query).fetchall()]
        for table, query in tables
    }


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
    control = _required_control(connection)
    recovery_revision = int(control[13])
    eligible_rows = [row for row in rows if int(row[9]) > recovery_revision]
    if not eligible_rows:
        return [], [], int(rows[0][2]), str(rows[0][3])
    latest = eligible_rows[0]
    for row in eligible_rows:
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


def _validate_acceptance_history(
    connection: sqlite3.Connection, rule_loader: RuleLoader
) -> list[str]:
    epochs = _epoch_snapshot(connection)
    recovery_revision = int(_required_control(connection)[13])
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
            "git_metadata_epoch,result_revision FROM checkpoint_evaluations WHERE node_id=? "
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
            or int(row[6]) <= recovery_revision
            or not _evaluation_epochs_are_current(node_id, tuple(row[3:6]), epochs)
        ):
            errors.append(f"{node_id} checkpoint is stale or unsuccessful")
    for node_id in optional_nodes:
        row = _one(
            connection,
            "SELECT outcome,branch,rule_hash,implementation_epoch,documentation_epoch,"
            "git_metadata_epoch,result_revision FROM checkpoint_evaluations WHERE node_id=? "
            "ORDER BY result_revision DESC LIMIT 1",
            (node_id,),
        )
        if row is None:
            continue
        if (
            row[0] != "ready"
            or row[1] in {"failure", "inconclusive", "blocked", "incomplete"}
            or row[2] != rule_loader.load_context(node_id).context_hash
            or int(row[6]) <= recovery_revision
            or not _evaluation_epochs_are_current(node_id, tuple(row[3:6]), epochs)
        ):
            errors.append(f"{node_id} checkpoint is stale or unsuccessful")
    return errors


def _evaluation_epochs_are_current(
    node_id: str, saved: tuple[int, int, int], current: EpochSnapshot
) -> bool:
    """Compare a result only with the state dimensions its owner covers."""
    dimensions = {
        "implementation": (0,),
        "verification": (0,),
        "repair": (0,),
        "documentation": (1,),
        "git": (2,),
    }.get(node_id, (0, 1, 2))
    values = (
        current.implementation_content,
        current.documentation,
        current.git_metadata,
    )
    return all(saved[index] == values[index] for index in dimensions)


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
        if isinstance(key, str) and key in actual:
            expected = actual[key]
            if value.get("value") != expected:
                failures.append(f"{key} does not match persisted Root state")
        if key == FactKey.CAPABILITY_GATE_RESULT.value and value.get("value") is not True:
            failures.append("capability gate is not satisfied")
    return failures


def _workflow_state(
    connection: sqlite3.Connection,
    rule_loader: RuleLoader | None = None,
    binding: BindingIdentity | None = None,
    index_page: RecoveryIndexPageRequest | None = None,
) -> WorkflowState:
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
    revision = int(control[11])
    epochs = _epoch_snapshot(connection)
    metadata_exists = (
        connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='workflow_session_metadata'"
        ).fetchone()
        is not None
    )
    session_audit = None
    capability_snapshot = None
    capability_snapshot_current = None
    if metadata_exists:
        metadata = _one(
            connection,
            "SELECT session_audit_json,capability_snapshot_json,capability_snapshot_hash,"
            "capability_observed_revision FROM workflow_session_metadata WHERE singleton=1",
        )
        if metadata is not None:
            if metadata[0] is not None:
                session_audit = SessionAudit.model_validate_json(metadata[0])
            if metadata[1] is not None:
                capability_snapshot = TrustedCapabilitySnapshot.model_validate_json(metadata[1])
                stored_hash = str(metadata[2])
                payload = _binding_payload_from_snapshot(capability_snapshot)
                capability_snapshot_current = (
                    _hash_json(payload) == stored_hash == capability_snapshot.snapshot_hash
                    and capability_snapshot.observed_revision == int(metadata[3]) == revision
                    and (binding is None or _binding_payload(binding) == payload)
                )
    active_slices, active_total, active_page = _active_slice_indexes(
        connection, revision, index_page
    )
    latest_gates, gate_total, gate_page = _latest_gate_indexes(
        connection, rule_loader, epochs, revision, int(control[13]), index_page
    )
    native_indexes, native_total, native_page = _native_reconcile_indexes(
        connection, revision, index_page
    )
    native_resolutions, resolution_total, resolution_page = _native_resolution_indexes(
        connection, revision, index_page
    )
    control_requests, control_request_total, control_request_page = (
        _control_evidence_request_indexes(connection, revision, int(control[13]), index_page)
    )
    unresolved_native = _unresolved_native_rows(connection)
    canonical_native = _one(
        connection,
        "SELECT reconcile_id,snapshot_hash,status,snapshot_json,result_revision "
        "FROM native_reconciliations ORDER BY result_revision DESC,reconcile_id DESC LIMIT 1",
    )
    latest_native_row = _one(
        connection,
        "SELECT n.reconcile_id,n.status,n.snapshot_hash,n.native_refs_json,n.differences_json,"
        "n.observed_revision,n.result_revision,n.snapshot_json,"
        "EXISTS(SELECT 1 FROM native_reconcile_preimages p "
        "WHERE p.reconcile_id=n.reconcile_id) "
        "FROM native_reconciliations n "
        "ORDER BY n.result_revision DESC,n.reconcile_id DESC LIMIT 1",
    )
    canonical_unresolved = (
        canonical_native is not None
        and _one(
            connection,
            "SELECT 1 FROM native_reconciliations AS n "
            "WHERE n.reconcile_id=? AND n.status IN ('conflict','awaiting_confirmation') "
            "AND NOT EXISTS (SELECT 1 FROM native_reconcile_resolution_targets AS t "
            "WHERE t.reconcile_id=n.reconcile_id) "
            "AND (n.status!='awaiting_confirmation' OR NOT EXISTS ("
            "SELECT 1 FROM native_reconcile_confirmations AS c "
            "WHERE c.awaiting_reconcile_id=n.reconcile_id))",
            (canonical_native[0],),
        )
        is not None
    )
    reviewed_comparison_count = native_total + int(
        canonical_native is not None and not canonical_unresolved
    )
    resolution_unavailable_reason = (
        "reviewed_comparison_set_exceeds_supported_bound"
        if reviewed_comparison_count > 256 or len(unresolved_native) > 256
        else next(
            (
                item.resolution_unavailable_reason
                for item in native_indexes
                if item.resolution_unavailable_reason is not None
            ),
            None,
        )
    )
    unresolved_hash = (
        _native_review_set_hash(connection, revision, unresolved_native, canonical_native)
        if unresolved_native and resolution_unavailable_reason is None
        else None
    )
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
        epochs=epochs,
        active_slices=active_slices,
        omitted_active_slice_count=max(0, active_total - len(active_slices)),
        latest_gates=latest_gates,
        omitted_gate_count=max(0, gate_total - len(latest_gates)),
        unresolved_native_reconciliations=native_indexes,
        omitted_native_reconciliation_count=max(0, native_total - len(native_indexes)),
        latest_native_reconciliation=(
            _native_reconcile_index(latest_native_row, revision)
            if latest_native_row is not None
            else None
        ),
        unresolved_native_set_hash=unresolved_hash,
        native_resolution_unavailable_reason=resolution_unavailable_reason,
        recovery_revision=int(control[13]),
        native_resolution_history=native_resolutions,
        omitted_native_resolution_count=max(0, resolution_total - len(native_resolutions)),
        control_evidence_requests=control_requests,
        omitted_control_evidence_request_count=max(
            0, control_request_total - len(control_requests)
        ),
        recovery_pages=[
            active_page,
            gate_page,
            native_page,
            resolution_page,
            control_request_page,
        ],
        session_audit=session_audit,
        capability_snapshot=capability_snapshot,
        capability_snapshot_current=capability_snapshot_current,
    )


def _binding_payload(binding: BindingIdentity) -> dict[str, object]:
    return {
        "project_id": binding.project_id,
        "root_session_id": binding.root_session_id,
        "current_session_id": binding.current_session_id,
        "role": binding.role.value,
        "parent_session_id": binding.parent_session_id,
        "capabilities": sorted(item.value for item in binding.capabilities),
        "guards": sorted(item.value for item in binding.guards),
    }


def _binding_payload_from_snapshot(
    snapshot: TrustedCapabilitySnapshot,
) -> dict[str, object]:
    return {
        "project_id": snapshot.project_id,
        "root_session_id": snapshot.root_session_id,
        "current_session_id": snapshot.current_session_id,
        "role": snapshot.role.value,
        "parent_session_id": snapshot.parent_session_id,
        "capabilities": sorted(item.value for item in snapshot.capabilities),
        "guards": sorted(item.value for item in snapshot.guards),
    }


def _active_slice_indexes(
    connection: sqlite3.Connection,
    current_revision: int,
    page_request: RecoveryIndexPageRequest | None,
    default_page_size: int = 32,
) -> tuple[list[ActiveSliceIndex], int, RecoveryIndexPageInfo]:
    source = (
        "SELECT slice_id,allocation_id,output_class,write_content_memo,objective_uri,"
        "objective_hash,return_conditions_uri,return_conditions_hash,unreleased_boundary_uri,"
        "unreleased_boundary_hash,authorized_paths_json,change_categories_json "
        ", 'worker' AS source_kind FROM workflow_slices WHERE status='released' UNION ALL "
        "SELECT slice_id,'root',output_class,write_content_memo,objective_uri,objective_hash,"
        "return_uri,return_hash,boundary_uri,boundary_hash,authorized_paths_json,"
        "change_categories_json,'root' AS source_kind FROM root_slices WHERE status='released'"
    )
    total = int(connection.execute(f"SELECT COUNT(*) FROM ({source})").fetchone()[0])
    offset, page_size = _recovery_page_bounds(
        "active_slices", current_revision, total, page_request, default_page_size
    )
    rows = connection.execute(
        f"SELECT * FROM ({source}) ORDER BY slice_id,source_kind LIMIT ? OFFSET ?",
        (page_size, offset),
    ).fetchall()
    result: list[ActiveSliceIndex] = []
    for row in rows:
        objective = SemanticRef(uri=row[4], content_hash=row[5])
        return_conditions = SemanticRef(uri=row[6], content_hash=row[7])
        unreleased_boundary = SemanticRef(uri=row[8], content_hash=row[9])
        authorized_paths = json.loads(row[10])
        change_categories = [ChangeCategory(item) for item in json.loads(row[11])]
        output_class = OutputClass(row[2]) if row[2] else None
        memo_value = bool(row[3]) if row[3] is not None else None
        spec_hash = None
        unknown_reason = None
        if output_class is not None and memo_value is not None:
            spec_hash = _slice_spec_hash(
                SliceSpec(
                    allocation_id=row[1],
                    output_class=output_class,
                    objective=objective,
                    return_conditions=return_conditions,
                    unreleased_boundary=unreleased_boundary,
                    authorized_paths=authorized_paths,
                    change_categories=change_categories,
                    write_content_memo=memo_value,
                )
            )
        else:
            missing = []
            if output_class is None:
                missing.append("output_class")
            if memo_value is None:
                missing.append("write_content_memo")
            unknown_reason = f"legacy Root Slice lacks persisted {' and '.join(missing)}"
        result.append(
            ActiveSliceIndex(
                slice_id=row[0],
                allocation_id=row[1],
                output_class=output_class,
                objective=objective,
                return_conditions=return_conditions,
                unreleased_boundary=unreleased_boundary,
                authorized_paths=authorized_paths,
                change_categories=change_categories,
                write_content_memo=memo_value,
                spec_hash=spec_hash,
                spec_hash_unknown_reason=unknown_reason,
            )
        )
    return (
        result,
        total,
        _recovery_page_info(
            "active_slices", current_revision, offset, page_size, total, len(result)
        ),
    )


def _latest_gate_indexes(
    connection: sqlite3.Connection,
    rule_loader: RuleLoader | None,
    current_epochs: EpochSnapshot,
    current_revision: int,
    recovery_revision: int,
    page_request: RecoveryIndexPageRequest | None,
    default_page_size: int = 64,
) -> tuple[list[GateIndex], int, RecoveryIndexPageInfo]:
    total = int(
        connection.execute("SELECT COUNT(DISTINCT node_id) FROM checkpoint_evaluations").fetchone()[
            0
        ]
    )
    offset, page_size = _recovery_page_bounds(
        "latest_gates", current_revision, total, page_request, default_page_size
    )
    rows = connection.execute(
        "WITH ranked AS (SELECT e.node_id,e.outcome,e.branch,e.rule_hash,e.input_hash,"
        "e.implementation_epoch,e.documentation_epoch,e.git_metadata_epoch,"
        "e.basis_revision,e.result_revision,ROW_NUMBER() OVER (PARTITION BY e.node_id "
        "ORDER BY e.result_revision DESC,e.evaluation_id DESC) AS rank "
        "FROM checkpoint_evaluations e) SELECT node_id,outcome,branch,rule_hash,input_hash,"
        "implementation_epoch,documentation_epoch,git_metadata_epoch,basis_revision,"
        "result_revision FROM ranked WHERE rank=1 ORDER BY node_id LIMIT ? OFFSET ?",
        (page_size, offset),
    ).fetchall()
    indexes = []
    for row in rows:
        epochs = EpochSnapshot(
            implementation_content=row[5], documentation=row[6], git_metadata=row[7]
        )
        if rule_loader is None:
            rule_status = "unavailable"
        else:
            try:
                context = rule_loader.load_context(row[0])
                rule_status = "current" if context.context_hash == row[3] else "stale"
            except UnknownRuleNodeError:
                rule_status = "unknown_node"
            except (KeyError, OSError, RuleLoadError, ValueError):
                rule_status = "unavailable"
        indexes.append(
            GateIndex(
                node_id=row[0],
                outcome=row[1],
                branch=row[2],
                rule_hash=row[3],
                input_hash=row[4],
                epochs=epochs,
                basis_revision=row[8],
                result_revision=row[9],
                rule_status=rule_status,
                rule_current=rule_status == "current",
                epochs_current=_evaluation_epochs_are_current(
                    row[0], (row[5], row[6], row[7]), current_epochs
                )
                and int(row[9]) > recovery_revision,
                revision_current=int(row[9]) == current_revision,
            )
        )
    return (
        indexes,
        total,
        _recovery_page_info(
            "latest_gates", current_revision, offset, page_size, total, len(indexes)
        ),
    )


def _native_reconcile_indexes(
    connection: sqlite3.Connection,
    current_revision: int,
    page_request: RecoveryIndexPageRequest | None,
    default_page_size: int = 8,
) -> tuple[list[NativeReconcileIndex], int, RecoveryIndexPageInfo]:
    total = int(
        connection.execute(
            "SELECT COUNT(*) FROM native_reconciliations AS n "
            "WHERE n.status IN ('conflict','awaiting_confirmation') "
            "AND NOT EXISTS (SELECT 1 FROM native_reconcile_resolution_targets AS t "
            "WHERE t.reconcile_id=n.reconcile_id) "
            "AND (n.status!='awaiting_confirmation' OR NOT EXISTS ("
            "SELECT 1 FROM native_reconcile_confirmations AS c "
            "WHERE c.awaiting_reconcile_id=n.reconcile_id))"
        ).fetchone()[0]
    )
    offset, page_size = _recovery_page_bounds(
        "unresolved_native_reconciliations",
        current_revision,
        total,
        page_request,
        default_page_size,
    )
    rows = connection.execute(
        "SELECT n.reconcile_id,n.status,n.snapshot_hash,n.native_refs_json,n.differences_json,"
        "n.observed_revision,n.result_revision,n.snapshot_json,"
        "EXISTS(SELECT 1 FROM native_reconcile_preimages p "
        "WHERE p.reconcile_id=n.reconcile_id) FROM native_reconciliations AS n "
        "WHERE n.status IN ('conflict','awaiting_confirmation') "
        "AND NOT EXISTS (SELECT 1 FROM native_reconcile_resolution_targets AS t "
        "WHERE t.reconcile_id=n.reconcile_id) "
        "AND (n.status!='awaiting_confirmation' OR NOT EXISTS ("
        "SELECT 1 FROM native_reconcile_confirmations AS c "
        "WHERE c.awaiting_reconcile_id=n.reconcile_id)) "
        "ORDER BY n.result_revision DESC,n.reconcile_id LIMIT ? OFFSET ?",
        (page_size, offset),
    ).fetchall()
    indexes = []
    for row in rows:
        indexes.append(_native_reconcile_index(row, current_revision))
    return (
        indexes,
        total,
        _recovery_page_info(
            "unresolved_native_reconciliations",
            current_revision,
            offset,
            page_size,
            total,
            len(indexes),
        ),
    )


def _native_reconcile_index(
    row: sqlite3.Row | tuple[object, ...], current_revision: int
) -> NativeReconcileIndex:
    snapshot = NativeWorkflowSnapshot.model_validate_json(str(row[7]))
    return NativeReconcileIndex(
        reconcile_id=cast(str, row[0]),
        status=cast(Literal["matched", "conflict", "awaiting_confirmation"], row[1]),
        snapshot_hash=cast(str, row[2]),
        native_refs=[
            EvidenceRef.model_validate(item) for item in json.loads(cast(str, row[3]))[:256]
        ],
        native_reference_count=len(json.loads(cast(str, row[3]))),
        native_references_omitted=max(0, len(json.loads(cast(str, row[3]))) - 256),
        differences=json.loads(cast(str, row[4])),
        observed_revision=cast(int, row[5]),
        result_revision=cast(int, row[6]),
        native_revision=snapshot.revision,
        native_run_id=snapshot.run_id,
        native_mode_count=snapshot.mode_count,
        native_mode_source=snapshot.mode_source,
        native_lifecycle=snapshot.lifecycle,
        native_allocations=snapshot.allocations[:256],
        native_allocation_count=len(snapshot.allocations),
        native_allocations_omitted=max(0, len(snapshot.allocations) - 256),
        native_source=snapshot.source,
        native_semantic_references=snapshot.semantic_references[:256],
        native_semantic_reference_count=len(snapshot.semantic_references),
        native_semantic_references_omitted=max(0, len(snapshot.semantic_references) - 256),
        resolution_unavailable_reason=(
            "native_semantic_references_exceed_supported_bound"
            if len(snapshot.semantic_references) > 256
            else "native_allocations_exceed_supported_bound"
            if len(snapshot.allocations) > 256
            else "native_evidence_references_exceed_supported_bound"
            if len(snapshot.evidence_refs) > 256
            else None
        ),
        native_epochs=snapshot.epochs,
        preimage_known=bool(row[8]),
        current=cast(int, row[6]) == current_revision,
    )


def _native_resolution_indexes(
    connection: sqlite3.Connection,
    current_revision: int,
    page_request: RecoveryIndexPageRequest | None,
    default_page_size: int = 8,
) -> tuple[list[NativeResolutionIndex], int, RecoveryIndexPageInfo]:
    total = int(
        connection.execute("SELECT COUNT(*) FROM native_reconcile_resolutions").fetchone()[0]
    )
    offset, page_size = _recovery_page_bounds(
        "native_resolution_history", current_revision, total, page_request, default_page_size
    )
    rows = connection.execute(
        "SELECT resolution_id,reconcile_id,choice,reviewed_set_hash,snapshot_hash,"
        "root_decision_ref_json,native_freshness_refs_json,root_quiescence_refs_json,"
        "result_revision,recovery_revision "
        "FROM native_reconcile_resolutions "
        "ORDER BY result_revision DESC,resolution_id LIMIT ? OFFSET ?",
        (page_size, offset),
    ).fetchall()
    indexes: list[NativeResolutionIndex] = []
    for row in rows:
        target_rows = connection.execute(
            "SELECT reconcile_id,snapshot_hash FROM native_reconcile_resolution_targets "
            "WHERE resolution_id=? ORDER BY reconcile_id LIMIT 257",
            (row[0],),
        ).fetchall()
        if len(target_rows) > 256:
            raise InvalidStateTransitionError(
                "native resolution target index exceeds the supported bounded page"
            )
        indexes.append(
            NativeResolutionIndex(
                resolution_id=row[0],
                reconcile_id=row[1],
                choice=row[2],
                reviewed_set_hash=row[3],
                snapshot_hash=row[4],
                resolved_comparisons=[
                    NativeResolutionTargetIndex(reconcile_id=target[0], snapshot_hash=target[1])
                    for target in target_rows
                ],
                root_decision_ref=EvidenceRef.model_validate_json(row[5]),
                native_freshness_refs=[
                    EvidenceRef.model_validate(item) for item in json.loads(row[6])
                ],
                root_quiescence_refs=[
                    EvidenceRef.model_validate(item) for item in json.loads(row[7])
                ],
                result_revision=row[8],
                recovery_revision=row[9],
                current=int(row[9]) == current_revision,
            )
        )
    return (
        indexes,
        total,
        _recovery_page_info(
            "native_resolution_history", current_revision, offset, page_size, total, len(indexes)
        ),
    )


def _control_evidence_request_indexes(
    connection: sqlite3.Connection,
    current_revision: int,
    recovery_revision: int,
    page_request: RecoveryIndexPageRequest | None,
    default_page_size: int = 8,
) -> tuple[list[ControlEvidenceRequestIndex], int, RecoveryIndexPageInfo]:
    total = int(connection.execute("SELECT COUNT(*) FROM control_evidence_requests").fetchone()[0])
    offset, page_size = _recovery_page_bounds(
        "control_evidence_requests", current_revision, total, page_request, default_page_size
    )
    rows = connection.execute(
        "SELECT request_id,status,created_revision,returned_revision "
        "FROM control_evidence_requests ORDER BY created_revision,request_id LIMIT ? OFFSET ?",
        (page_size, offset),
    ).fetchall()
    indexes = [
        ControlEvidenceRequestIndex(
            request_id=row[0],
            status=row[1],
            created_revision=row[2],
            returned_revision=row[3],
            recovery_fresh=row[3] is not None and int(row[3]) > recovery_revision,
        )
        for row in rows
    ]
    return (
        indexes,
        total,
        _recovery_page_info(
            "control_evidence_requests", current_revision, offset, page_size, total, len(indexes)
        ),
    )


def _recovery_page_bounds(
    collection: str,
    current_revision: int,
    total_count: int,
    request: RecoveryIndexPageRequest | None,
    default_page_size: int,
) -> tuple[int, int]:
    if request is None or request.collection != collection:
        return 0, default_page_size
    if request.cursor is None:
        return 0, request.page_size or default_page_size
    if request.cursor.revision != current_revision:
        raise StaleRecoveryCursorError(
            f"recovery cursor Revision {request.cursor.revision} is stale; current Revision is "
            f"{current_revision}"
        )
    if request.cursor.offset > total_count:
        raise ValueError("recovery cursor offset exceeds the index total_count")
    return request.cursor.offset, request.cursor.page_size


def _recovery_page_info(
    collection: RecoveryIndexCollection,
    revision: int,
    offset: int,
    page_size: int,
    total: int,
    returned: int,
) -> RecoveryIndexPageInfo:
    next_offset = offset + returned
    next_cursor = (
        RecoveryIndexCursor(
            collection=collection,
            revision=revision,
            offset=next_offset,
            page_size=page_size,
        )
        if next_offset < total
        else None
    )
    return RecoveryIndexPageInfo(
        collection=collection,
        revision=revision,
        offset=offset,
        page_size=page_size,
        total_count=total,
        returned_count=returned,
        next_cursor=next_cursor,
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
