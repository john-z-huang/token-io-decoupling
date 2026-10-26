"""Lifecycle operations for the state service."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from token_io_decoupling_core.binding import BindingError
from token_io_decoupling_core.models import (
    CodingMode,
    DatabaseKind,
    SchemaStatus,
)
from token_io_decoupling_core.state_models import (
    CheckpointEvaluation,
    HostCapability,
    HostGuard,
    MutationReceipt,
    RecoveryIndexPageRequest,
    SessionRole,
    WorkflowOpenRequest,
    WorkflowState,
)

from token_io_decoupling_state.migrations.runner import (
    _package_migrations,
    read_schema_status,
)

if TYPE_CHECKING:
    from ..service import StateService

from .common import _hash_json, _json, _now, _one
from .errors import InvalidStateTransitionError, RevisionConflictError
from .identity import _assert_workflow_identity, _validate_root_identity
from .native import _ensure_native_resolution
from .projection import _workflow_state


def workflow_open(self: StateService, request: WorkflowOpenRequest) -> MutationReceipt:
    """Initialize the locked route once or read it back without resetting identity."""
    request = WorkflowOpenRequest.model_validate(request)
    if request.mode_source == "default" and (
        request.mode_count.mode is not CodingMode.MULTI_AGENT or request.mode_count.child_count != 1
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
    self: StateService, *, index_page: RecoveryIndexPageRequest | None = None
) -> WorkflowState:
    binding = self._parent_binding({HostCapability.WORKFLOW_READ}, {HostGuard.PATH_BOUNDARY})
    if index_page is not None:
        index_page = RecoveryIndexPageRequest.model_validate(index_page)
    path, root = self._root_database(binding, create=False)
    with self._read_transaction(path, DatabaseKind.WORKFLOW, root) as connection:
        return _workflow_state(connection, self._rule_loader, binding, index_page)


def workflow_get_state_for_evaluation(
    self: StateService, evaluation: CheckpointEvaluation
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


def database_schema_status(self: StateService) -> SchemaStatus:
    """Read only the current trusted session database schema without mutation."""
    current = self._binding_provider.current_binding()
    if current.role is SessionRole.PARENT:
        binding = self._parent_binding({HostCapability.WORKFLOW_READ}, {HostGuard.PATH_BOUNDARY})
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
