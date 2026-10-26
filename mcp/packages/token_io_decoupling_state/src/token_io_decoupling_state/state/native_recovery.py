"""Native recovery operations for the state service."""

from __future__ import annotations

import json
import sqlite3
import uuid
from typing import TYPE_CHECKING, cast

from token_io_decoupling_core.binding import BindingError
from token_io_decoupling_core.models import (
    DatabaseKind,
    SemanticRef,
)
from token_io_decoupling_core.state_models import (
    AllocationStatus,
    HostCapability,
    HostGuard,
    MutationReceipt,
    NativeReconcileResolutionTransition,
    NativeWorkflowSnapshot,
    ReconcileResult,
)

if TYPE_CHECKING:
    from ..service import StateService

from .common import _hash_json, _json, _nonempty, _now, _one
from .errors import InvalidStateTransitionError, RevisionConflictError
from .identity import _required_control
from .native import _native_review_set_hash, _native_root_preimage, _unresolved_native_rows
from .projection import _workflow_state
from .validation import _epoch_snapshot


def workflow_reconcile(
    self: StateService,
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
            "conflict" if differences else ("awaiting_confirmation" if not confirm else "matched")
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
                    _json([ref.model_dump(mode="json") for ref in snapshot.semantic_references]),
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
    self: StateService, request: NativeReconcileResolutionTransition
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
                "SELECT 1 FROM native_reconcile_preimages WHERE reconcile_id=? AND snapshot_hash=?",
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
            raise InvalidStateTransitionError("terminal workflow cannot be resumed by resolution")
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
            raise InvalidStateTransitionError("pending Worker dispatch blocks Native resolution")
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
