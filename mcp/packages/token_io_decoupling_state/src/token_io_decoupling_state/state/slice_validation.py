"""Slice validation helpers for the state service."""

from __future__ import annotations

import sqlite3
from pathlib import PurePosixPath

from token_io_decoupling_core.state_models import (
    SliceCheckResult,
    SliceSpec,
)

from .common import _WORKER_OUTPUT_CLASSES, _hash_json, _one
from .identity import _required_control
from .native import _unresolved_native_rows
from .validation import _epoch_snapshot


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
