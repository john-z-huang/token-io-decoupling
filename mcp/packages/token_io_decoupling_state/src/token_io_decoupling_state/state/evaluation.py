"""Evaluation operations for the state service."""

from __future__ import annotations

import sqlite3
import uuid
from typing import TYPE_CHECKING

from token_io_decoupling_core.models import (
    DatabaseKind,
)
from token_io_decoupling_core.state_models import (
    CheckpointEvaluation,
    CheckpointNode,
    EpochDimension,
    HostCapability,
    HostGuard,
    LegalBranch,
    MutationReceipt,
)

if TYPE_CHECKING:
    from ..service import StateService

from .common import _hash_json, _json, _nonempty, _now, _one
from .errors import InvalidStateTransitionError, RevisionConflictError, WorkflowNotOpenError
from .identity import _required_control
from .native import _ensure_native_resolution
from .validation import (
    _epoch_snapshot,
    _latest_evidence,
    _missing_requirements,
    _validate_acceptance_history,
    _validate_checkpoint_state,
    _validate_fact_state,
)


def workflow_evaluate(
    self: StateService,
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
    self: StateService,
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
            raise InvalidStateTransitionError("evaluation branch is not legal for this checkpoint")
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
            signal = next((fact for fact in facts if fact["fact_key"] == "Progress Signal"), None)
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
                if item[1] == "returned" and item[2] is not None and int(item[2]) > int(control[13])
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
    self: StateService,
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
    self: StateService,
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
    self: StateService,
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
