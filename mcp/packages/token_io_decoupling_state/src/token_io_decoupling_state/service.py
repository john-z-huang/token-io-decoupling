"""Deterministic Root/Worker state services behind a fail-closed host binding."""

from __future__ import annotations

import sqlite3
from collections.abc import Callable, Generator
from contextlib import contextmanager
from pathlib import Path

from token_io_decoupling_core.binding import BindingError as BindingError
from token_io_decoupling_core.binding import BindingProvider
from token_io_decoupling_core.models import (
    DatabaseKind,
    SchemaStatus,
)
from token_io_decoupling_core.rules import RuleLoader
from token_io_decoupling_core.state_models import (
    BindingIdentity,
    BlockerRecord,
    CheckpointConfirmationTransition,
    CheckpointEvaluation,
    CheckpointNode,
    DelegationBudgetApproval,
    DelegationUnreserveRequest,
    EpochDimension,
    EvidenceSubmission,
    HostCapability,
    HostGuard,
    MutationReceipt,
    NativeReconcileResolutionTransition,
    NativeWorkflowSnapshot,
    ProgressRecord,
    ReconcileResult,
    RecoveryIndexPageRequest,
    SessionAuditTransition,
    SliceCheckResult,
    SliceSpec,
    VerifiedChildBinding,
    WorkerState,
    WorkflowOpenRequest,
    WorkflowState,
    WorkflowTransitionRequest,
)

from token_io_decoupling_state.migrations.runner import (
    DEFAULT_LOCK_TIMEOUT_SECONDS,
)

from .state import control as _control_ops
from .state import delegation as _delegation_ops
from .state import dispatch as _dispatch_ops
from .state import evaluation as _evaluation_ops
from .state import evidence as _evidence_ops
from .state import lifecycle as _lifecycle_ops
from .state import native_recovery as _native_recovery_ops
from .state import persistence as _persistence_ops
from .state import storage as _storage_ops
from .state import worker as _worker_ops
from .state.common import (
    _SAFE_COMPONENT as _SAFE_COMPONENT,
)
from .state.common import (
    _WORKER_OUTPUT_CLASSES as _WORKER_OUTPUT_CLASSES,
)
from .state.common import (
    DEFAULT_STATE_ROOT,
)
from .state.common import (
    _hash_json as _hash_json,
)
from .state.common import (
    _json as _json,
)
from .state.common import (
    _nonempty as _nonempty,
)
from .state.common import (
    _now as _now,
)
from .state.common import (
    _one as _one,
)
from .state.errors import (
    IdempotencyConflictError as IdempotencyConflictError,
)
from .state.errors import (
    InvalidStateTransitionError as InvalidStateTransitionError,
)
from .state.errors import (
    RevisionConflictError as RevisionConflictError,
)
from .state.errors import (
    StaleRecoveryCursorError as StaleRecoveryCursorError,
)
from .state.errors import (
    StateServiceError as StateServiceError,
)
from .state.errors import (
    WorkerInitializationError as WorkerInitializationError,
)
from .state.errors import (
    WorkflowNotOpenError as WorkflowNotOpenError,
)
from .state.identity import (
    _assert_workflow_identity as _assert_workflow_identity,
)
from .state.identity import (
    _ensure_derived_directory_chain as _ensure_derived_directory_chain,
)
from .state.identity import (
    _ensure_directory_chain as _ensure_directory_chain,
)
from .state.identity import (
    _require_capabilities as _require_capabilities,
)
from .state.identity import (
    _require_confirmed_worker_event as _require_confirmed_worker_event,
)
from .state.identity import (
    _require_guards as _require_guards,
)
from .state.identity import (
    _required_control as _required_control,
)
from .state.identity import (
    _safe_component as _safe_component,
)
from .state.identity import (
    _validate_child_binding as _validate_child_binding,
)
from .state.identity import (
    _validate_root_identity as _validate_root_identity,
)
from .state.identity import (
    _worker_identity as _worker_identity,
)
from .state.native import (
    _ensure_native_resolution as _ensure_native_resolution,
)
from .state.native import (
    _native_reconcile_index as _native_reconcile_index,
)
from .state.native import (
    _native_reconcile_indexes as _native_reconcile_indexes,
)
from .state.native import (
    _native_resolution_indexes as _native_resolution_indexes,
)
from .state.native import (
    _native_review_set_hash as _native_review_set_hash,
)
from .state.native import (
    _native_root_preimage as _native_root_preimage,
)
from .state.native import (
    _unresolved_native_rows as _unresolved_native_rows,
)
from .state.paging import (
    _recovery_page_bounds as _recovery_page_bounds,
)
from .state.paging import (
    _recovery_page_info as _recovery_page_info,
)
from .state.projection import (
    _active_slice_indexes as _active_slice_indexes,
)
from .state.projection import (
    _binding_payload as _binding_payload,
)
from .state.projection import (
    _binding_payload_from_snapshot as _binding_payload_from_snapshot,
)
from .state.projection import (
    _control_evidence_request_indexes as _control_evidence_request_indexes,
)
from .state.projection import (
    _latest_gate_indexes as _latest_gate_indexes,
)
from .state.projection import (
    _workflow_state as _workflow_state,
)
from .state.slice_validation import (
    _check_slice as _check_slice,
)
from .state.slice_validation import (
    _slice_spec_hash as _slice_spec_hash,
)
from .state.validation import (
    _epoch_snapshot as _epoch_snapshot,
)
from .state.validation import (
    _epochs_cover_changed_dimensions as _epochs_cover_changed_dimensions,
)
from .state.validation import (
    _evaluation_epochs_are_current as _evaluation_epochs_are_current,
)
from .state.validation import (
    _latest_evidence as _latest_evidence,
)
from .state.validation import (
    _missing_requirements as _missing_requirements,
)
from .state.validation import (
    _validate_acceptance_history as _validate_acceptance_history,
)
from .state.validation import (
    _validate_checkpoint_state as _validate_checkpoint_state,
)
from .state.validation import (
    _validate_coverage_dimensions as _validate_coverage_dimensions,
)
from .state.validation import (
    _validate_fact_state as _validate_fact_state,
)


class StateService:
    """Backward-compatible facade for Root and Worker state operations."""

    def __init__(
        self,
        binding_provider: BindingProvider | None = None,
        *,
        state_root: Path | str | None = None,
        lock_timeout_seconds: float = DEFAULT_LOCK_TIMEOUT_SECONDS,
        rule_loader: RuleLoader | None = None,
    ) -> None:
        if binding_provider is None:
            from token_io_decoupling_core.binding import DenyingBindingProvider

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
        "Persist typed evidence as references and indexes, never semantic bodies."
        return _evidence_ops.workflow_record_evidence(
            self, submission, expected_revision=expected_revision, idempotency_key=idempotency_key
        )

    def worker_record_evidence(
        self, submission: EvidenceSubmission, *, expected_revision: int, idempotency_key: str
    ) -> MutationReceipt:
        return _evidence_ops.worker_record_evidence(
            self, submission, expected_revision=expected_revision, idempotency_key=idempotency_key
        )

    def worker_get_evidence(self, evidence_id: str) -> dict[str, object]:
        return _evidence_ops.worker_get_evidence(self, evidence_id)

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
        return _evaluation_ops.workflow_evaluate(
            self,
            node_id,
            expected_revision=expected_revision,
            idempotency_key=idempotency_key,
            branch=branch,
            input_hash=input_hash,
            slice_ids=slice_ids,
        )

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
        return _evaluation_ops.workflow_evaluate_with_replay(
            self,
            node_id,
            expected_revision=expected_revision,
            idempotency_key=idempotency_key,
            branch=branch,
            input_hash=input_hash,
            slice_ids=slice_ids,
        )

    def evaluate_control_checkpoint(
        self,
        *,
        expected_revision: int,
        idempotency_key: str,
        branch: str | None = None,
        input_hash: str | None = None,
        slice_ids: list[str] | None = None,
    ) -> CheckpointEvaluation:
        return _evaluation_ops.evaluate_control_checkpoint(
            self,
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
        return _evaluation_ops.evaluate_control_checkpoint_with_replay(
            self,
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
        "Advance exactly one independent epoch after an authorized host observes change."
        return _evaluation_ops.workflow_advance_epoch(
            self, dimension, expected_revision=expected_revision, idempotency_key=idempotency_key
        )

    def workflow_transition(self, request: WorkflowTransitionRequest) -> MutationReceipt:
        return _control_ops.workflow_transition(self, request)

    def _update_session_audit(self, request: SessionAuditTransition) -> MutationReceipt:
        return _control_ops._update_session_audit(self, request)

    def _confirm_checkpoint(self, request: CheckpointConfirmationTransition) -> MutationReceipt:
        return _control_ops._confirm_checkpoint(self, request)

    def workflow_reconcile(
        self,
        snapshot: NativeWorkflowSnapshot,
        *,
        confirm: bool = False,
        expected_revision: int,
        idempotency_key: str,
    ) -> ReconcileResult:
        return _native_recovery_ops.workflow_reconcile(
            self,
            snapshot,
            confirm=confirm,
            expected_revision=expected_revision,
            idempotency_key=idempotency_key,
        )

    def _resolve_native_reconcile(
        self, request: NativeReconcileResolutionTransition
    ) -> MutationReceipt:
        "Resolve a reviewed complete conflict set without importing identity/history."
        return _native_recovery_ops._resolve_native_reconcile(self, request)

    def workflow_open(self, request: WorkflowOpenRequest) -> MutationReceipt:
        "Initialize the locked route once or read it back without resetting identity."
        return _lifecycle_ops.workflow_open(self, request)

    def workflow_get_state(
        self, *, index_page: RecoveryIndexPageRequest | None = None
    ) -> WorkflowState:
        return _lifecycle_ops.workflow_get_state(self, index_page=index_page)

    def workflow_get_state_for_evaluation(
        self, evaluation: CheckpointEvaluation
    ) -> WorkflowState | None:
        "Return current state only when the evaluation belongs to this bound Root DB."
        return _lifecycle_ops.workflow_get_state_for_evaluation(self, evaluation)

    def database_schema_status(self) -> SchemaStatus:
        "Read only the current trusted session database schema without mutation."
        return _lifecycle_ops.database_schema_status(self)

    def delegation_reserve(
        self,
        role: str,
        *,
        expected_revision: int,
        idempotency_key: str,
        budget_approval: DelegationBudgetApproval | None = None,
    ) -> MutationReceipt:
        return _delegation_ops.delegation_reserve(
            self,
            role,
            expected_revision=expected_revision,
            idempotency_key=idempotency_key,
            budget_approval=budget_approval,
        )

    def delegation_unreserve(
        self,
        request: DelegationUnreserveRequest,
    ) -> MutationReceipt:
        return _delegation_ops.delegation_unreserve(self, request)

    def slice_check(self, spec: SliceSpec) -> SliceCheckResult:
        return _delegation_ops.slice_check(self, spec)

    def slice_release(
        self,
        spec: SliceSpec,
        *,
        expected_revision: int,
        idempotency_key: str,
    ) -> MutationReceipt:
        return _delegation_ops.slice_release(
            self, spec, expected_revision=expected_revision, idempotency_key=idempotency_key
        )

    def delegation_bind(
        self,
        allocation_id: str,
        child_session_id: str,
        *,
        expected_revision: int,
        idempotency_key: str,
    ) -> MutationReceipt:
        return _delegation_ops.delegation_bind(
            self,
            allocation_id,
            child_session_id,
            expected_revision=expected_revision,
            idempotency_key=idempotency_key,
        )

    def worker_get_assignment(self) -> dict[str, object]:
        return _worker_ops.worker_get_assignment(self)

    def worker_get_dispatch(self, event_id: str) -> dict[str, object]:
        "Read this bound Worker's immutable dispatch history by event identity."
        return _worker_ops.worker_get_dispatch(self, event_id)

    def worker_get_state(self) -> WorkerState:
        return _worker_ops.worker_get_state(self)

    def worker_get_recovery_context(self) -> dict[str, object]:
        return _worker_ops.worker_get_recovery_context(self)

    def worker_record_progress(
        self,
        record: ProgressRecord,
        *,
        expected_revision: int,
        idempotency_key: str,
    ) -> MutationReceipt:
        return _worker_ops.worker_record_progress(
            self, record, expected_revision=expected_revision, idempotency_key=idempotency_key
        )

    def worker_report_blocker(
        self,
        blocker: BlockerRecord,
        *,
        expected_revision: int,
        idempotency_key: str,
    ) -> MutationReceipt:
        return _worker_ops.worker_report_blocker(
            self, blocker, expected_revision=expected_revision, idempotency_key=idempotency_key
        )

    def parent_get_worker_summary(self, allocation_id: str) -> WorkerState:
        return _worker_ops.parent_get_worker_summary(self, allocation_id)

    def _mutate_root(
        self,
        binding: BindingIdentity,
        operation: str,
        payload: dict[str, object],
        expected_revision: int,
        idempotency_key: str,
        mutation: Callable[[sqlite3.Connection, int], dict[str, object]],
    ) -> MutationReceipt:
        return _persistence_ops._mutate_root(
            self, binding, operation, payload, expected_revision, idempotency_key, mutation
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
        return _persistence_ops._mutate_worker(
            self, binding, operation, payload, expected_revision, idempotency_key, mutation
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
        return _persistence_ops._find_receipt(
            self, connection, table, key, operation, payload_hash, current_revision
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
        return _persistence_ops._store_receipt(
            self, connection, table, key, operation, payload_hash, result, revision
        )

    def _complete_worker_dispatch(
        self,
        parent: BindingIdentity,
        child: VerifiedChildBinding,
        event_id: str,
    ) -> None:
        return _dispatch_ops._complete_worker_dispatch(self, parent, child, event_id)

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
        return _dispatch_ops._worker_dispatch_is_confirmed(
            self,
            parent,
            worker_session_id,
            allocation_id,
            event_id,
            sequence,
            payload,
            payload_hash,
        )

    def _parent_binding(
        self,
        capabilities: set[HostCapability],
        guards: set[HostGuard],
    ) -> BindingIdentity:
        return _storage_ops._parent_binding(self, capabilities, guards)

    def _record_binding_snapshot(
        self,
        connection: sqlite3.Connection,
        binding: BindingIdentity,
        observed_revision: int,
    ) -> None:
        return _storage_ops._record_binding_snapshot(self, connection, binding, observed_revision)

    def _worker_binding(self, capabilities: set[HostCapability]) -> BindingIdentity:
        return _storage_ops._worker_binding(self, capabilities)

    def _root_database(self, binding: BindingIdentity, *, create: bool) -> tuple[Path, Path]:
        return _storage_ops._root_database(self, binding, create=create)

    def _worker_database(
        self, worker_session_id: str, binding: BindingIdentity, *, create: bool
    ) -> tuple[Path, Path]:
        return _storage_ops._worker_database(self, worker_session_id, binding, create=create)

    @contextmanager
    def _write_transaction(
        self,
        path: Path,
        kind: DatabaseKind,
        trusted_root: Path,
        *,
        logical_identity: tuple[str, str, str | None],
    ) -> Generator[sqlite3.Connection, None, None]:
        return _storage_ops._write_transaction(
            self, path, kind, trusted_root, logical_identity=logical_identity
        )

    @contextmanager
    def _locked_write_connection(
        self,
        path: Path,
        kind: DatabaseKind,
        trusted_root: Path,
        *,
        logical_identity: tuple[str, str, str | None],
    ) -> Generator[sqlite3.Connection, None, None]:
        "Open one write transaction while the caller holds this database's migration lock."
        return _storage_ops._locked_write_connection(
            self, path, kind, trusted_root, logical_identity=logical_identity
        )

    @contextmanager
    def _read_transaction(
        self,
        path: Path,
        kind: DatabaseKind,
        trusted_root: Path,
    ) -> Generator[sqlite3.Connection, None, None]:
        return _storage_ops._read_transaction(self, path, kind, trusted_root)

    @contextmanager
    def _existing_write_transaction(
        self,
        path: Path,
        kind: DatabaseKind,
        trusted_root: Path,
    ) -> Generator[sqlite3.Connection, None, None]:
        return _storage_ops._existing_write_transaction(self, path, kind, trusted_root)
