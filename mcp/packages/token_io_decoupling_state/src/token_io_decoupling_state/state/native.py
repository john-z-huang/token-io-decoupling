"""Native helpers for the state service."""

from __future__ import annotations

import json
import sqlite3
from typing import Literal, cast

from token_io_decoupling_core.models import (
    EvidenceRef,
)
from token_io_decoupling_core.state_models import (
    NativeReconcileIndex,
    NativeResolutionIndex,
    NativeResolutionTargetIndex,
    NativeWorkflowSnapshot,
    RecoveryIndexPageInfo,
    RecoveryIndexPageRequest,
)

from .common import _hash_json, _one
from .errors import InvalidStateTransitionError
from .paging import _recovery_page_bounds, _recovery_page_info


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
