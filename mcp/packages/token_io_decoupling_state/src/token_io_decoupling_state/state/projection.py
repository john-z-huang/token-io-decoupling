"""Projection helpers for the state service."""

from __future__ import annotations

import json
import sqlite3

from token_io_decoupling_core.models import (
    CodingMode,
    SemanticRef,
)
from token_io_decoupling_core.rules import RuleLoader, RuleLoadError, UnknownRuleNodeError
from token_io_decoupling_core.state_models import (
    ActiveSliceIndex,
    AllocationState,
    AllocationStatus,
    BindingIdentity,
    ChangeCategory,
    ControlEvidenceRequestIndex,
    EpochSnapshot,
    GateIndex,
    ModeCount,
    OutputClass,
    RecoveryIndexPageInfo,
    RecoveryIndexPageRequest,
    SessionAudit,
    SliceSpec,
    TrustedCapabilitySnapshot,
    WorkflowState,
)

from .common import _hash_json, _one
from .identity import _required_control
from .native import (
    _native_reconcile_index,
    _native_reconcile_indexes,
    _native_resolution_indexes,
    _native_review_set_hash,
    _unresolved_native_rows,
)
from .paging import _recovery_page_bounds, _recovery_page_info
from .slice_validation import _slice_spec_hash
from .validation import _epoch_snapshot, _evaluation_epochs_are_current


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
