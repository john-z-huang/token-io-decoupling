"""Validation helpers for the state service."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Mapping

from token_io_decoupling_core.models import (
    RuleContext,
)
from token_io_decoupling_core.rules import RuleLoader
from token_io_decoupling_core.state_models import (
    CheckpointNode,
    EpochDimension,
    EpochSnapshot,
    FactKey,
)

from .common import _one
from .errors import InvalidStateTransitionError, WorkflowNotOpenError
from .identity import _required_control


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
