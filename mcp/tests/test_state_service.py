from __future__ import annotations

import hashlib
import json
import shutil
import sqlite3
import threading
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal, cast

import pytest
from token_io_decoupling_core.binding import BindingError, DenyingBindingProvider
from token_io_decoupling_core.models import (
    CodingMode,
    DatabaseKind,
    EvidenceRef,
    ModeCount,
    SemanticRef,
)
from token_io_decoupling_core.rules import RuleLoader
from token_io_decoupling_core.state_models import (
    BindingIdentity,
    BooleanFactValue,
    ChangeCategory,
    CheckpointConfirmationTransition,
    CheckpointEvaluation,
    CheckpointFact,
    CheckpointNode,
    ControlTransitionRequest,
    CountFactValue,
    EnumFactValue,
    EpochDimension,
    EvidenceKind,
    EvidenceSubmission,
    FactDetermined,
    FactKey,
    LegalBranch,
    OutputClass,
    ProgressRecord,
    ReferenceFactValue,
    SessionAudit,
    SessionAuditPrompt,
    SessionAuditSources,
    SessionAuditTransition,
    SessionRole,
    SliceSpec,
    TypedEvidenceReference,
    VerifiedChildBinding,
    WorkflowOpenRequest,
)
from token_io_decoupling_core.state_models import (
    HostCapability as Cap,
)
from token_io_decoupling_core.state_models import (
    HostGuard as Guard,
)
from token_io_decoupling_state.migrations.runner import (
    _migration_lock,
    _open_with_migrations,
    _package_migrations,
)
from token_io_decoupling_state.service import (
    IdempotencyConflictError,
    InvalidStateTransitionError,
    RevisionConflictError,
    StaleRecoveryCursorError,
    StateService,
    WorkflowNotOpenError,
    _epochs_cover_changed_dimensions,
    _slice_spec_hash,
)

PARENT_CAPS = frozenset(
    {
        Cap.WORKFLOW_READ,
        Cap.WORKFLOW_WRITE,
        Cap.CHILD_IDENTITY_CHECK,
        Cap.WORKER_STORE_CREATE,
        Cap.PARENT_SUMMARY_READ,
    }
)
PARENT_GUARDS = frozenset({Guard.IDENTITY_BOUND, Guard.SESSION_BOUND, Guard.PATH_BOUNDARY})
CHILD_CAPS = frozenset(
    {Cap.WORKER_READ, Cap.WORKER_WRITE, Cap.WORKER_STORE_CREATE, Cap.PARENT_SUMMARY_READ}
)
CHILD_GUARDS = frozenset(
    {
        Guard.IDENTITY_BOUND,
        Guard.SESSION_BOUND,
        Guard.PATH_BOUNDARY,
        Guard.PARENT_CHILD_RELATION,
        Guard.WORKER_STORE_ISOLATION,
    }
)


class FakeBindings:
    """Test-only identities; this does not assert operating-system isolation."""

    def __init__(self, project: str = "project-a", root: str = "root-a") -> None:
        self.parent = BindingIdentity(
            project_id=project,
            root_session_id=root,
            current_session_id=root,
            role=SessionRole.PARENT,
            capabilities=PARENT_CAPS,
            guards=PARENT_GUARDS,
        )
        self.current = self.parent
        self.children: dict[str, VerifiedChildBinding] = {}

    def current_binding(self) -> BindingIdentity:
        return self.current

    def verify_child_binding(
        self, parent: BindingIdentity, child_session_id: str
    ) -> VerifiedChildBinding:
        child = self.children.get(child_session_id)
        if child is None or parent != self.parent:
            raise BindingError("fake child is not registered")
        return child

    def add_child(self, session_id: str) -> None:
        self.children[session_id] = VerifiedChildBinding(
            project_id=self.parent.project_id,
            root_session_id=self.parent.root_session_id,
            parent_session_id=self.parent.current_session_id,
            child_session_id=session_id,
            capabilities=CHILD_CAPS,
            guards=CHILD_GUARDS,
        )

    def become_worker(self, session_id: str) -> None:
        self.current = BindingIdentity(
            project_id=self.parent.project_id,
            root_session_id=self.parent.root_session_id,
            current_session_id=session_id,
            parent_session_id=self.parent.root_session_id,
            role=SessionRole.WORKER,
            capabilities=CHILD_CAPS,
            guards=CHILD_GUARDS,
        )


def ref(name: str) -> SemanticRef:
    return SemanticRef(uri=f"test://{name}", content_hash="a" * 64)


def source_rule_loader() -> RuleLoader:
    return RuleLoader(repository_root=Path(__file__).parents[2])


def request(
    *,
    children: int = 1,
    mode: CodingMode = CodingMode.MULTI_AGENT,
    mode_source: Literal["explicit", "default"] = "explicit",
    key: str = "open",
) -> WorkflowOpenRequest:
    return WorkflowOpenRequest(
        mode_count=ModeCount(mode=mode, child_count=children),
        mode_source=mode_source,
        source=ref("plan"),
        semantic_references=[],
        idempotency_key=key,
    )


def setup(tmp_path: Path, children: int = 1):
    provider = FakeBindings()
    service = StateService(
        provider, state_root=tmp_path / "state", rule_loader=source_rule_loader()
    )
    service.workflow_open(request(children=children))
    return service, provider


def native_resolution_request(
    service: StateService,
    reconcile_id: str,
    *,
    native_revision: int,
    native_epochs: dict[str, int],
    native_freshness_refs: list[EvidenceRef],
    unresolved_set_hash: str | None = None,
    choice: Literal["adopt_native_pair", "retain_sqlite_pair"] = "adopt_native_pair",
):
    from token_io_decoupling_core.state_models import (
        EpochSnapshot,
        NativeReconcileResolutionTransition,
    )

    state = service.workflow_get_state()
    comparison = state.latest_native_reconciliation
    assert comparison is not None and comparison.reconcile_id == reconcile_id
    decision_ref = EvidenceRef(uri="test://root/native-decision", content_hash="e" * 64)
    quiescence_ref = EvidenceRef(uri="test://root/quiescence", content_hash="f" * 64)
    set_hash = unresolved_set_hash or state.unresolved_native_set_hash
    assert set_hash
    return NativeReconcileResolutionTransition(
        kind="resolve_native_reconcile",
        canonical_reconcile_id=reconcile_id,
        snapshot_hash=comparison.snapshot_hash,
        unresolved_set_hash=set_hash,
        choice=choice,
        reviewed_native_revision=native_revision,
        reviewed_native_epochs=EpochSnapshot(**native_epochs),
        root_decision_ref=decision_ref,
        native_freshness_refs=native_freshness_refs,
        root_quiescence_refs=[quiescence_ref],
        expected_revision=state.revision,
        idempotency_key="resolve-native-test",
    )


def session_audit(
    *,
    visibility: Literal["available", "unverified", "unavailable", "Not applicable"] = "unverified",
) -> SessionAudit:
    return SessionAudit(
        audit_mode="balanced",
        root_reasoning_cadence="milestone_only",
        worker_reasoning_cadence="full",
        source=SessionAuditSources(
            audit_mode="explicit",
            root_reasoning_cadence="explicit",
            worker_reasoning_cadence="default",
        ),
        worker_log_visibility=visibility,
        worker_log_evidence=(
            EvidenceRef(uri="test://worker-log-audit", content_hash="e" * 64)
            if visibility != "unverified"
            else None
        ),
        audit_config_prompt=SessionAuditPrompt(
            status="unasked",
            prompted_at=None,
            deadline_at=None,
            response_at=None,
            resolution="unavailable",
        ),
        revision="session-audit/v2",
    )


def prime_slice(service: StateService, spec: SliceSpec | None = None) -> SliceSpec:
    if spec is None:
        allocation = service.workflow_get_state().allocations[0].allocation_id
        spec = SliceSpec(
            allocation_id=allocation,
            output_class=OutputClass.CODE_CONFIGURATION,
            objective=ref("default-objective"),
            return_conditions=ref("default-return"),
            unreleased_boundary=ref("default-boundary"),
            authorized_paths=["mcp/"],
            change_categories=[ChangeCategory.SOURCE_CODE],
            write_content_memo=False,
        )
    input_hash = service.slice_check(spec).input_hash
    values = {
        FactKey.SLICE_OBJECTIVE: spec.objective,
        FactKey.SLICE_AUTHORIZED_SCOPE: ref(f"slice-spec://{input_hash}"),
        FactKey.RETURN_CONDITIONS: spec.return_conditions,
        FactKey.UNRELEASED_BOUNDARY: spec.unreleased_boundary,
    }
    record = EvidenceSubmission(
        node_id=CheckpointNode.SLICE,
        facts=[
            CheckpointFact(
                fact_key=key,
                judgment=FactDetermined(
                    status="determined",
                    value=ReferenceFactValue(kind="semantic_ref", value=value),
                ),
            )
            for key, value in values.items()
        ],
        evidence_refs=[
            TypedEvidenceReference(
                kind=EvidenceKind.PARENT_SLICE_RELEASE,
                reference=EvidenceRef(uri="test://slice-release", content_hash="a" * 64),
            )
        ],
        input_hash=input_hash,
    )
    revision = service.workflow_get_state().revision
    service.workflow_record_evidence(
        record, expected_revision=revision, idempotency_key=f"slice-evidence-{revision}"
    )
    revision = service.workflow_get_state().revision
    service.workflow_evaluate(
        CheckpointNode.SLICE,
        branch="released",
        input_hash=input_hash,
        expected_revision=revision,
        idempotency_key=f"slice-evaluation-{revision}",
    )
    return spec


def prime_control_continue(
    service: StateService,
    signal: LegalBranch = LegalBranch.CONTINUE,
    *,
    slice_ids: list[str] | None = None,
    amended_contract: SemanticRef | None = None,
) -> CheckpointEvaluation:
    binding = service._parent_binding({Cap.WORKFLOW_READ}, {Guard.PATH_BOUNDARY})
    database, trusted_root = service._root_database(binding, create=False)
    with service._read_transaction(database, DatabaseKind.WORKFLOW, trusted_root) as connection:
        pending = connection.execute(
            "SELECT request_id FROM control_evidence_requests WHERE status='pending' "
            "ORDER BY created_revision DESC LIMIT 1"
        ).fetchone()
    evidence_request_id = pending[0] if pending else None
    record = EvidenceSubmission(
        node_id=CheckpointNode.CONTROL,
        facts=[
            CheckpointFact(
                fact_key=FactKey.PROGRESS_SIGNAL,
                judgment=FactDetermined(
                    status="determined",
                    value=EnumFactValue(kind="enum", value=signal),
                ),
            ),
            CheckpointFact(
                fact_key=FactKey.CURRENT_UNRELEASED_BOUNDARY,
                judgment=FactDetermined(
                    status="determined",
                    value=ReferenceFactValue(kind="semantic_ref", value=ref("control-boundary")),
                ),
            ),
            CheckpointFact(
                fact_key=FactKey.EVIDENCE_REQUEST_STATUS,
                judgment=FactDetermined(
                    status="determined",
                    value=ReferenceFactValue(kind="semantic_ref", value=ref("no-evidence-request")),
                ),
            ),
        ],
        evidence_refs=[
            TypedEvidenceReference(
                kind=EvidenceKind.CURRENT_SLICE_OUTCOME,
                reference=EvidenceRef(uri="test://current-slice", content_hash="c" * 64),
            ),
            TypedEvidenceReference(
                kind=EvidenceKind.RETURNED_EVIDENCE,
                reference=EvidenceRef(uri="test://returned", content_hash="d" * 64),
            ),
        ],
        input_hash="e" * 64,
        coverage_dimensions=list(EpochDimension),
        evidence_request_id=evidence_request_id,
    )
    revision = service.workflow_get_state().revision
    service.workflow_record_evidence(
        record, expected_revision=revision, idempotency_key=f"control-evidence-{revision}"
    )
    branch = signal.value
    evaluation = service.evaluate_control_checkpoint(
        branch=branch,
        expected_revision=service.workflow_get_state().revision,
        idempotency_key=f"control-evaluation-{service.workflow_get_state().revision}",
        slice_ids=slice_ids,
    )
    if branch == "evidence-on-demand":
        assert evaluation.outcome == "evidence_on_demand"
        return evaluation
    service.workflow_transition(
        ControlTransitionRequest(
            kind="control",
            evaluation_id=evaluation.evaluation_id,
            outcome=cast(Literal["continue", "amend", "stop"], branch),
            expected_revision=evaluation.result_revision,
            idempotency_key=f"control-{branch}-{evaluation.result_revision}",
            slice_ids=evaluation.slice_ids,
            amended_contract=amended_contract,
        )
    )
    return evaluation


def test_default_provider_denies_without_creating_state(tmp_path: Path) -> None:
    service = StateService(
        DenyingBindingProvider(),
        state_root=tmp_path / "state",
        rule_loader=source_rule_loader(),
    )
    with pytest.raises(BindingError):
        service.workflow_open(request())
    assert not (tmp_path / "state").exists()


def test_uninitialized_root_and_worker_reads_do_not_create_paths(tmp_path: Path) -> None:
    provider = FakeBindings()
    service = StateService(
        provider, state_root=tmp_path / "state", rule_loader=source_rule_loader()
    )
    with pytest.raises(WorkflowNotOpenError, match="does not exist"):
        service.workflow_get_state()
    assert not (tmp_path / "state").exists()
    provider.become_worker("worker-unbound")
    with pytest.raises(WorkflowNotOpenError, match="does not exist"):
        service.worker_get_assignment()
    assert not (tmp_path / "state").exists()


def test_configured_state_root_alias_is_normalized_but_derived_symlinks_are_rejected(
    tmp_path: Path,
) -> None:
    actual = tmp_path / "actual-state"
    actual.mkdir()
    alias = tmp_path / "state-alias"
    alias.symlink_to(actual, target_is_directory=True)
    provider = FakeBindings()
    service = StateService(provider, state_root=alias, rule_loader=source_rule_loader())
    service.workflow_open(request())
    assert service.workflow_get_state().project_id == "project-a"

    project_dir = actual / "project-a"
    moved = tmp_path / "moved-project"
    project_dir.rename(moved)
    project_dir.symlink_to(moved, target_is_directory=True)
    with pytest.raises(BindingError, match="symlink"):
        service.workflow_get_state()


def test_mode_slot_lock_cas_and_idempotent_replay(tmp_path: Path) -> None:
    service, _ = setup(tmp_path)
    first = service.workflow_get_state()
    assert len(first.allocations) == 1
    with pytest.raises(InvalidStateTransitionError):
        service.workflow_open(request(children=2, key="reopen"))
    reserved = service.delegation_reserve(
        "Primary Output", expected_revision=0, idempotency_key="reserve"
    )
    replay = service.delegation_reserve(
        "Primary Output", expected_revision=0, idempotency_key="reserve"
    )
    assert replay.replayed and replay.receipt_revision == 1 and replay.current_revision == 1
    assert reserved.result == replay.result
    with pytest.raises(IdempotencyConflictError):
        service.workflow_open(request(key="reserve"))
    with pytest.raises(RevisionConflictError):
        service.delegation_reserve("Primary Output", expected_revision=0, idempotency_key="stale")
    with pytest.raises(InvalidStateTransitionError):
        service.delegation_reserve(
            "Change Verification", expected_revision=1, idempotency_key="second"
        )
    assert service.workflow_get_state().revision == 1


def test_single_agent_and_default_mode_invariants(tmp_path: Path) -> None:
    provider = FakeBindings()
    single = StateService(
        provider, state_root=tmp_path / "single", rule_loader=source_rule_loader()
    )
    single.workflow_open(request(children=0, mode=CodingMode.SINGLE_AGENT))
    assert single.workflow_get_state().allocations == []
    with pytest.raises(InvalidStateTransitionError):
        single.delegation_reserve("Primary Output", expected_revision=0, idempotency_key="reserve")

    default_provider = FakeBindings(project="default-project", root="default-root")
    default = StateService(
        default_provider, state_root=tmp_path / "default", rule_loader=source_rule_loader()
    )
    with pytest.raises(InvalidStateTransitionError):
        default.workflow_open(request(children=2, mode_source="default"))
    default.workflow_open(request(mode_source="default"))
    assert len(default.workflow_get_state().allocations) == 1


def test_slice_gate_role_and_category_are_enforced(tmp_path: Path) -> None:
    service, _ = setup(tmp_path)
    with pytest.raises(InvalidStateTransitionError):
        service.delegation_reserve("invented-role", expected_revision=0, idempotency_key="role")
    with pytest.raises(InvalidStateTransitionError):
        service.delegation_reserve(
            "Change Verification", expected_revision=0, idempotency_key="role2"
        )
    allocation = service.workflow_get_state().allocations[0].allocation_id
    service.delegation_reserve("Primary Output", expected_revision=0, idempotency_key="reserve")
    invalid = SliceSpec(
        allocation_id=allocation,
        output_class=OutputClass.ORDINARY_DOCUMENTATION,
        objective=ref("objective"),
        return_conditions=ref("return"),
        unreleased_boundary=ref("boundary"),
        authorized_paths=["mcp/"],
        change_categories=[ChangeCategory.SOURCE_CODE],
        write_content_memo=False,
    )
    check = service.slice_check(invalid)
    assert not check.eligible and service.workflow_get_state().revision == 1
    with pytest.raises(InvalidStateTransitionError):
        service.slice_release(invalid, expected_revision=1, idempotency_key="bad-slice")


def test_binding_requires_released_slice_and_replay_recovers_dispatch(tmp_path: Path) -> None:
    service, provider = setup(tmp_path)
    allocation = service.workflow_get_state().allocations[0].allocation_id
    provider.add_child("worker-a")
    service.delegation_reserve("Primary Output", expected_revision=0, idempotency_key="reserve")
    objective = SliceSpec(
        allocation_id=allocation,
        output_class=OutputClass.SKILL_INSTRUCTIONS,
        objective=ref("objective"),
        return_conditions=ref("return"),
        unreleased_boundary=ref("boundary"),
        authorized_paths=["references/"],
        change_categories=[ChangeCategory.SKILL_INSTRUCTIONS],
        write_content_memo=False,
    )
    with pytest.raises(InvalidStateTransitionError):
        service.delegation_bind(allocation, "worker-a", expected_revision=1, idempotency_key="bind")
    worker_dir = tmp_path / "state" / "project-a" / "root-a" / "subagents" / "worker-a"
    assert not worker_dir.exists()
    prime_slice(service, objective)
    service.slice_release(
        objective, expected_revision=service.workflow_get_state().revision, idempotency_key="slice"
    )

    class FailOnce(StateService):
        failed = False

        def _complete_worker_dispatch(self, *args, **kwargs):
            if not self.failed:
                self.failed = True
                raise RuntimeError("simulated interruption after Root commit")
            return super()._complete_worker_dispatch(*args, **kwargs)

    interrupted = FailOnce(provider, state_root=tmp_path / "state")
    with pytest.raises(RuntimeError):
        interrupted.delegation_bind(
            allocation,
            "worker-a",
            expected_revision=service.workflow_get_state().revision,
            idempotency_key="bind",
        )
    assert not (worker_dir / "worker.sqlite3").exists()
    receipt = interrupted.delegation_bind(
        allocation,
        "worker-a",
        expected_revision=service.workflow_get_state().revision,
        idempotency_key="bind",
    )
    assert receipt.replayed and (worker_dir / "worker.sqlite3").is_file()
    assert interrupted.workflow_get_state().allocations[0].status.value == "initialized"
    provider.become_worker("worker-a")
    assignment = interrupted.worker_get_assignment()
    assert assignment["allocation_id"] == allocation
    assert "session_audit" not in assignment
    worker_path = worker_dir / "worker.sqlite3"
    with sqlite3.connect(worker_path) as connection:
        connection.execute(
            "UPDATE assignment_snapshot SET snapshot_json=? WHERE singleton=1",
            ('{"forged":true}',),
        )
    with pytest.raises(BindingError, match="snapshot hash"):
        interrupted.worker_get_assignment()
    with sqlite3.connect(worker_path) as connection:
        connection.execute(
            "UPDATE assignment_snapshot SET snapshot_json=? WHERE singleton=1",
            (json.dumps(assignment, sort_keys=True, separators=(",", ":")),),
        )
    progress = ProgressRecord(status="reported_complete", milestone=ref("done"))
    worker_receipt = interrupted.worker_record_progress(
        progress, expected_revision=0, idempotency_key="progress"
    )
    assert worker_receipt.receipt_revision == 1
    moved_worker = worker_dir.with_name("worker-a-moved")
    worker_dir.rename(moved_worker)
    worker_dir.symlink_to(moved_worker, target_is_directory=True)
    with pytest.raises(BindingError, match="symlink"):
        interrupted.worker_get_state()


@pytest.mark.parametrize("boundary", ["root_confirm", "worker_confirm"])
def test_dispatch_recovers_after_each_cross_database_commit_boundary(
    tmp_path: Path, boundary: str
) -> None:
    service, provider = setup(tmp_path)
    allocation = service.workflow_get_state().allocations[0].allocation_id
    provider.add_child("worker-a")
    service.delegation_reserve("Primary Output", expected_revision=0, idempotency_key="reserve")
    spec = SliceSpec(
        allocation_id=allocation,
        output_class=OutputClass.CODE_CONFIGURATION,
        objective=ref("dispatch-objective"),
        return_conditions=ref("dispatch-return"),
        unreleased_boundary=ref("dispatch-boundary"),
        authorized_paths=["mcp/"],
        change_categories=[ChangeCategory.SOURCE_CODE],
        write_content_memo=False,
    )
    prime_slice(service, spec)
    service.slice_release(
        spec,
        expected_revision=service.workflow_get_state().revision,
        idempotency_key="slice",
    )

    class InterruptBoundary(StateService):
        inside_dispatch = False
        workflow_writes = 0
        worker_writes = 0
        interrupted = False

        def _complete_worker_dispatch(self, *args, **kwargs):
            self.inside_dispatch = True
            try:
                return super()._complete_worker_dispatch(*args, **kwargs)
            finally:
                self.inside_dispatch = False

        @contextmanager
        def _locked_write_connection(self, path, kind, trusted_root, **kwargs):
            if self.inside_dispatch and kind is DatabaseKind.WORKFLOW:
                self.workflow_writes += 1
            if self.inside_dispatch and kind is DatabaseKind.WORKER:
                self.worker_writes += 1
            with super()._locked_write_connection(path, kind, trusted_root, **kwargs) as connection:
                yield connection
            if not self.interrupted and (
                boundary == "root_confirm"
                and self.inside_dispatch
                and kind is DatabaseKind.WORKFLOW
                and self.workflow_writes == 2
            ):
                self.interrupted = True
                raise RuntimeError("interrupt after Root confirmation commit")
            if not self.interrupted and (
                boundary == "worker_confirm"
                and self.inside_dispatch
                and kind is DatabaseKind.WORKER
                and self.worker_writes == 2
            ):
                self.interrupted = True
                raise RuntimeError("interrupt after Worker confirmation commit")

    service = InterruptBoundary(provider, state_root=tmp_path / "state")
    with pytest.raises(RuntimeError, match="interrupt after"):
        service.delegation_bind(
            allocation,
            "worker-a",
            expected_revision=service.workflow_get_state().revision,
            idempotency_key="dispatch-bind",
        )
    receipt = service.delegation_bind(
        allocation,
        "worker-a",
        expected_revision=service.workflow_get_state().revision,
        idempotency_key="dispatch-bind",
    )
    assert receipt.replayed
    assert service.workflow_get_state().allocations[0].status.value == "initialized"
    provider.become_worker("worker-a")
    assert service.worker_get_assignment()["allocation_id"] == allocation


def test_foreign_root_database_cannot_be_read_or_mutated_even_on_receipt_replay(
    tmp_path: Path,
) -> None:
    service, provider = setup(tmp_path)
    old = service.delegation_reserve(
        "Primary Output", expected_revision=0, idempotency_key="reserve"
    )
    correct_path = tmp_path / "state" / "project-a" / "root-a" / "workflow.sqlite3"
    other_provider = FakeBindings(project="project-b", root="root-b")
    other = StateService(
        other_provider, state_root=tmp_path / "other", rule_loader=source_rule_loader()
    )
    other.workflow_open(request())
    other_path = tmp_path / "other" / "project-b" / "root-b" / "workflow.sqlite3"
    shutil.copyfile(other_path, correct_path)
    with pytest.raises(BindingError):
        service.workflow_get_state()
    with pytest.raises(BindingError):
        service.slice_check(
            SliceSpec(
                allocation_id=old.result["allocation_id"],
                output_class=OutputClass.CODE_CONFIGURATION,
                objective=ref("objective"),
                return_conditions=ref("return"),
                unreleased_boundary=ref("boundary"),
                authorized_paths=["mcp/"],
                change_categories=[ChangeCategory.SOURCE_CODE],
                write_content_memo=False,
            )
        )
    with pytest.raises(BindingError):
        service.delegation_reserve("Primary Output", expected_revision=1, idempotency_key="next")
    provider.add_child("worker-a")
    with pytest.raises(BindingError):
        service.delegation_bind(
            str(old.result["allocation_id"]),
            "worker-a",
            expected_revision=1,
            idempotency_key="bind-foreign",
        )
    with pytest.raises(BindingError):
        service.delegation_reserve("Primary Output", expected_revision=0, idempotency_key="reserve")
    assert old.receipt_revision == 1


def test_worker_b_database_cannot_be_used_for_worker_a_parent_summary(tmp_path: Path) -> None:
    provider = FakeBindings()
    provider.add_child("worker-a")
    provider.add_child("worker-b")
    service = StateService(
        provider, state_root=tmp_path / "state", rule_loader=source_rule_loader()
    )
    service.workflow_open(request(children=2))
    allocations = service.workflow_get_state().allocations

    def assign(slot: int, worker: str, role: str, offset: int) -> None:
        allocation = allocations[slot].allocation_id
        revision = service.workflow_get_state().revision
        service.delegation_reserve(
            role, expected_revision=revision, idempotency_key=f"reserve-{worker}"
        )
        if slot > 0:
            prime_control_continue(service)
        spec = SliceSpec(
            allocation_id=allocation,
            output_class=OutputClass.CODE_CONFIGURATION,
            objective=ref(f"objective-{worker}"),
            return_conditions=ref(f"return-{worker}"),
            unreleased_boundary=ref(f"boundary-{worker}"),
            authorized_paths=["mcp/"],
            change_categories=[ChangeCategory.SOURCE_CODE],
            write_content_memo=False,
        )
        prime_slice(service, spec)
        service.slice_release(
            spec,
            expected_revision=service.workflow_get_state().revision,
            idempotency_key=f"slice-{worker}",
        )
        service.delegation_bind(
            allocation,
            worker,
            expected_revision=service.workflow_get_state().revision,
            idempotency_key=f"bind-{worker}",
        )

    assign(0, "worker-a", "Primary Output", 0)
    assign(1, "worker-b", "Change Verification", 4)
    root = tmp_path / "state" / "project-a" / "root-a" / "subagents"
    shutil.copyfile(root / "worker-b" / "worker.sqlite3", root / "worker-a" / "worker.sqlite3")
    with pytest.raises(BindingError):
        service.parent_get_worker_summary(allocations[0].allocation_id)


def test_read_snapshot_and_business_write_share_migration_lock(tmp_path: Path) -> None:
    service, _ = setup(tmp_path)
    binding = service._parent_binding({Cap.WORKFLOW_READ}, {Guard.PATH_BOUNDARY})
    path, root = service._root_database(binding, create=False)
    started = threading.Event()

    def write() -> None:
        started.set()
        service.delegation_reserve(
            "Primary Output", expected_revision=0, idempotency_key="concurrent-reserve"
        )

    with ThreadPoolExecutor(max_workers=1) as pool:
        with service._read_transaction(path, DatabaseKind.WORKFLOW, root) as connection:
            first_revision = connection.execute(
                "SELECT revision FROM workflow_control WHERE singleton=1"
            ).fetchone()[0]
            future = pool.submit(write)
            assert started.wait(timeout=1)
            assert not future.done()
            allocation_count = connection.execute("SELECT COUNT(*) FROM allocations").fetchone()[0]
            assert (
                connection.execute(
                    "SELECT revision FROM workflow_control WHERE singleton=1"
                ).fetchone()[0]
                == first_revision
            )
            assert allocation_count == 1
        future.result(timeout=3)
    assert service.workflow_get_state().revision == 1


def test_business_write_waits_for_migration_restore_exclusion_lock(tmp_path: Path) -> None:
    service, _ = setup(tmp_path)
    binding = service._parent_binding({Cap.WORKFLOW_READ}, {Guard.PATH_BOUNDARY})
    path, root = service._root_database(binding, create=False)
    started = threading.Event()

    def write() -> None:
        started.set()
        service.delegation_reserve(
            "Primary Output", expected_revision=0, idempotency_key="after-recovery-lock"
        )

    with ThreadPoolExecutor(max_workers=1) as pool:
        with _migration_lock(path, root, 2):
            future = pool.submit(write)
            assert started.wait(timeout=1)
            assert not future.done()
        future.result(timeout=3)


def test_evidence_revision_epoch_freshness_and_evidence_on_demand_return_to_control(
    tmp_path: Path,
) -> None:
    service, _ = setup(tmp_path)
    evaluation = prime_control_continue(service, LegalBranch.EVIDENCE_ON_DEMAND)
    assert evaluation.outcome == "evidence_on_demand"
    with pytest.raises(InvalidStateTransitionError):
        service.workflow_transition(
            ControlTransitionRequest(
                kind="control",
                evaluation_id=evaluation.evaluation_id,
                outcome="continue",
                expected_revision=evaluation.result_revision,
                idempotency_key="cannot-transition-eod",
            )
        )
    continued = prime_control_continue(service)
    assert continued.outcome == "ready"
    state = service.workflow_get_state()
    service.workflow_advance_epoch(
        "documentation", expected_revision=state.revision, idempotency_key="doc-epoch"
    )
    revision = service.workflow_get_state().revision
    stale = service.workflow_evaluate(
        CheckpointNode.CONTROL,
        branch="continue",
        expected_revision=revision,
        idempotency_key=f"stale-control-evaluation-{revision}",
    )
    assert stale.outcome == "incomplete"
    assert stale.missing_facts


def test_evidence_staleness_tracks_only_covered_epoch_dimensions() -> None:
    saved = (2, 3, 4)
    current = {
        "implementation_content": 2,
        "documentation": 4,
        "git_metadata": 5,
    }
    assert not _epochs_cover_changed_dimensions(
        [EpochDimension.IMPLEMENTATION_CONTENT.value], saved, current
    )
    assert _epochs_cover_changed_dimensions([EpochDimension.DOCUMENTATION.value], saved, current)
    assert _epochs_cover_changed_dimensions(
        [
            EpochDimension.IMPLEMENTATION_CONTENT.value,
            EpochDimension.DOCUMENTATION.value,
        ],
        saved,
        current,
    )
    content_change = {
        "implementation_content": 3,
        "documentation": 3,
        "git_metadata": 4,
    }
    assert _epochs_cover_changed_dimensions(
        [
            EpochDimension.IMPLEMENTATION_CONTENT.value,
            EpochDimension.DOCUMENTATION.value,
        ],
        saved,
        content_change,
    )
    assert _epochs_cover_changed_dimensions([EpochDimension.GIT_METADATA.value], saved, current)


def test_state_service_evidence_freshness_tracks_actual_owner_dimensions(tmp_path: Path) -> None:
    service, _ = setup(tmp_path)

    def submit_verification() -> None:
        state = service.workflow_get_state()
        binding = service._parent_binding({Cap.WORKFLOW_READ}, {Guard.PATH_BOUNDARY})
        database, trusted_root = service._root_database(binding, create=False)
        with service._read_transaction(database, DatabaseKind.WORKFLOW, trusted_root) as connection:
            implementation_epoch = connection.execute(
                "SELECT implementation_content FROM workflow_epochs WHERE singleton=1"
            ).fetchone()[0]
        evidence = EvidenceSubmission(
            node_id=CheckpointNode.VERIFICATION,
            facts=[
                CheckpointFact(
                    fact_key=FactKey.CURRENT_IMPLEMENTATION_EPOCH,
                    judgment=FactDetermined(
                        status="determined",
                        value=CountFactValue(kind="count", value=implementation_epoch),
                    ),
                ),
                CheckpointFact(
                    fact_key=FactKey.VERIFICATION_SCOPE,
                    judgment=FactDetermined(
                        status="determined",
                        value=ReferenceFactValue(
                            kind="semantic_ref", value=ref("verification-scope")
                        ),
                    ),
                ),
            ],
            evidence_refs=[
                TypedEvidenceReference(
                    kind=EvidenceKind.VERIFICATION_RESULTS,
                    reference=EvidenceRef(uri="test://verification", content_hash="f" * 64),
                )
            ],
            coverage_dimensions=[EpochDimension.IMPLEMENTATION_CONTENT],
            input_hash="9" * 64,
        )
        service.workflow_record_evidence(
            evidence,
            expected_revision=state.revision,
            idempotency_key=f"verification-{state.revision}",
        )

    submit_verification()
    state = service.workflow_get_state()
    git_change = service.workflow_advance_epoch(
        EpochDimension.GIT_METADATA,
        expected_revision=state.revision,
        idempotency_key="git-only-for-verification",
    )
    evaluation = service.workflow_evaluate(
        CheckpointNode.VERIFICATION,
        branch="pass",
        expected_revision=git_change.receipt_revision,
        idempotency_key="verify-after-git-only",
    )
    assert evaluation.outcome == "ready"

    changed = service.workflow_advance_epoch(
        EpochDimension.IMPLEMENTATION_CONTENT,
        expected_revision=service.workflow_get_state().revision,
        idempotency_key="content-invalidates-verification",
    )
    stale = service.workflow_evaluate(
        CheckpointNode.VERIFICATION,
        branch="pass",
        expected_revision=changed.receipt_revision,
        idempotency_key="verify-after-content-change",
    )
    assert stale.outcome == "incomplete"
    assert "current implementation/content epoch" in stale.missing_facts


def test_documentation_evidence_stales_on_docs_and_explicit_content_epoch_changes(
    tmp_path: Path,
) -> None:
    service, _ = setup(tmp_path)

    def submit(coverage: list[EpochDimension]) -> int:
        state = service.workflow_get_state()
        binding = service._parent_binding({Cap.WORKFLOW_READ}, {Guard.PATH_BOUNDARY})
        database, trusted_root = service._root_database(binding, create=False)
        with service._read_transaction(database, DatabaseKind.WORKFLOW, trusted_root) as connection:
            docs_epoch = connection.execute(
                "SELECT documentation FROM workflow_epochs WHERE singleton=1"
            ).fetchone()[0]
        evidence = EvidenceSubmission(
            node_id=CheckpointNode.DOCUMENTATION,
            facts=[
                CheckpointFact(
                    fact_key=FactKey.DOCUMENTATION_SCOPE,
                    judgment=FactDetermined(
                        status="determined",
                        value=ReferenceFactValue(kind="semantic_ref", value=ref("docs-scope")),
                    ),
                ),
                CheckpointFact(
                    fact_key=FactKey.AFFECTED_DOCUMENTATION_EPOCH,
                    judgment=FactDetermined(
                        status="determined", value=CountFactValue(kind="count", value=docs_epoch)
                    ),
                ),
            ],
            evidence_refs=[
                TypedEvidenceReference(
                    kind=EvidenceKind.DOCUMENTATION_CHECKS,
                    reference=EvidenceRef(uri="test://docs", content_hash="d" * 64),
                ),
                TypedEvidenceReference(
                    kind=EvidenceKind.UPDATED_EPOCH,
                    reference=EvidenceRef(uri="test://epoch", content_hash="e" * 64),
                ),
            ],
            coverage_dimensions=coverage,
            input_hash="f" * 64,
        )
        receipt = service.workflow_record_evidence(
            evidence,
            expected_revision=state.revision,
            idempotency_key=f"docs-evidence-{state.revision}",
        )
        return receipt.receipt_revision

    revision = submit([EpochDimension.DOCUMENTATION])
    git = service.workflow_advance_epoch(
        EpochDimension.GIT_METADATA,
        expected_revision=revision,
        idempotency_key="git-only-does-not-stale-docs-evidence",
    )
    fresh = service.workflow_evaluate(
        CheckpointNode.DOCUMENTATION,
        branch="complete",
        expected_revision=git.receipt_revision,
        idempotency_key="documentation-after-git-change",
    )
    assert fresh.outcome == "ready"

    docs = service.workflow_advance_epoch(
        EpochDimension.DOCUMENTATION,
        expected_revision=fresh.result_revision,
        idempotency_key="documentation-epoch-change",
    )
    stale_docs = service.workflow_evaluate(
        CheckpointNode.DOCUMENTATION,
        branch="complete",
        expected_revision=docs.receipt_revision,
        idempotency_key="documentation-after-doc-change",
    )
    assert stale_docs.outcome == "incomplete"

    content = service.workflow_advance_epoch(
        EpochDimension.IMPLEMENTATION_CONTENT,
        expected_revision=stale_docs.result_revision,
        idempotency_key="docs-change-affects-content",
    )
    stale_content = service.workflow_evaluate(
        CheckpointNode.DOCUMENTATION,
        branch="complete",
        expected_revision=content.receipt_revision,
        idempotency_key="documentation-after-cross-dimension-change",
    )
    assert stale_content.outcome == "incomplete"


def test_slice_branch_and_spec_are_bound_to_release_authorization(tmp_path: Path) -> None:
    service, _ = setup(tmp_path)
    spec = prime_slice(service)
    altered = spec.model_copy(update={"objective": ref("different-objective")})
    mismatched = service.slice_check(altered)
    assert not mismatched.eligible
    assert mismatched.input_hash != service.slice_check(spec).input_hash

    revision = service.workflow_get_state().revision
    rejected = service.workflow_evaluate(
        CheckpointNode.SLICE,
        branch="stop",
        input_hash=service.slice_check(spec).input_hash,
        expected_revision=revision,
        idempotency_key="slice-stop-is-not-release",
    )
    assert rejected.outcome == "blocked"
    with pytest.raises(InvalidStateTransitionError):
        service.slice_release(
            spec,
            expected_revision=rejected.result_revision,
            idempotency_key="slice-stop-cannot-release",
        )


def test_incomplete_evidence_on_demand_does_not_become_a_control_request(tmp_path: Path) -> None:
    service, _ = setup(tmp_path)
    revision = service.workflow_get_state().revision
    evaluation = service.workflow_evaluate(
        CheckpointNode.CONTROL,
        branch="evidence-on-demand",
        expected_revision=revision,
        idempotency_key="incomplete-eod",
    )
    assert evaluation.outcome == "incomplete"
    binding = service._parent_binding({Cap.WORKFLOW_READ}, {Guard.PATH_BOUNDARY})
    database, trusted_root = service._root_database(binding, create=False)
    with service._read_transaction(database, DatabaseKind.WORKFLOW, trusted_root) as connection:
        assert (
            connection.execute(
                "SELECT 1 FROM control_evidence_requests WHERE source_evaluation_id=?",
                (evaluation.evaluation_id,),
            ).fetchone()
            is None
        )


def test_evidence_on_demand_rejects_unrelated_returned_evidence(tmp_path: Path) -> None:
    service, _ = setup(tmp_path)
    request_eval = prime_control_continue(service, LegalBranch.EVIDENCE_ON_DEMAND)
    assert request_eval.evidence_request_id

    def returned_submission(request_id: str) -> EvidenceSubmission:
        return EvidenceSubmission(
            node_id=CheckpointNode.CONTROL,
            facts=[
                CheckpointFact(
                    fact_key=FactKey.PROGRESS_SIGNAL,
                    judgment=FactDetermined(
                        status="determined",
                        value=EnumFactValue(kind="enum", value=LegalBranch.CONTINUE),
                    ),
                ),
                CheckpointFact(
                    fact_key=FactKey.CURRENT_UNRELEASED_BOUNDARY,
                    judgment=FactDetermined(
                        status="determined",
                        value=ReferenceFactValue(kind="semantic_ref", value=ref("boundary")),
                    ),
                ),
                CheckpointFact(
                    fact_key=FactKey.EVIDENCE_REQUEST_STATUS,
                    judgment=FactDetermined(
                        status="determined",
                        value=ReferenceFactValue(
                            kind="semantic_ref", value=ref("request-returned")
                        ),
                    ),
                ),
            ],
            evidence_refs=[
                TypedEvidenceReference(
                    kind=EvidenceKind.CURRENT_SLICE_OUTCOME,
                    reference=EvidenceRef(uri="test://slice-outcome", content_hash="a" * 64),
                ),
                TypedEvidenceReference(
                    kind=EvidenceKind.RETURNED_EVIDENCE,
                    reference=EvidenceRef(uri="test://unrelated-return", content_hash="b" * 64),
                ),
            ],
            coverage_dimensions=list(EpochDimension),
            input_hash="c" * 64,
            evidence_request_id=request_id,
        )

    with pytest.raises(InvalidStateTransitionError, match="pending Control request"):
        service.workflow_record_evidence(
            returned_submission("unrelated-request"),
            expected_revision=service.workflow_get_state().revision,
            idempotency_key="wrong-eod-request",
        )
    record = service.workflow_record_evidence(
        returned_submission(request_eval.evidence_request_id),
        expected_revision=service.workflow_get_state().revision,
        idempotency_key="right-eod-request",
    )
    assert record.result["evidence_id"]
    continued = prime_control_continue(service)
    assert continued.outcome == "ready"


def test_stop_control_is_terminal_and_never_acceptance(tmp_path: Path) -> None:
    service, _ = setup(tmp_path)
    stopped = prime_control_continue(service, LegalBranch.STOP)
    assert stopped.outcome == "ready"
    assert service.workflow_get_state().lifecycle == "interrupted"
    after_stop = service.slice_check(
        SliceSpec(
            allocation_id=service.workflow_get_state().allocations[0].allocation_id,
            output_class=OutputClass.CODE_CONFIGURATION,
            objective=ref("after-stop"),
            return_conditions=ref("return"),
            unreleased_boundary=ref("boundary"),
            authorized_paths=["mcp/"],
            change_categories=[ChangeCategory.SOURCE_CODE],
            write_content_memo=False,
        )
    )
    assert not after_stop.eligible
    revision = service.workflow_get_state().revision
    acceptance = service.workflow_evaluate(
        CheckpointNode.ACCEPTANCE,
        branch="complete",
        expected_revision=revision,
        idempotency_key="acceptance-after-stop",
    )
    assert acceptance.outcome == "blocked"


def test_amend_invalidates_authorization_until_contract_and_decision_recheck(
    tmp_path: Path,
) -> None:
    service, _ = setup(tmp_path)
    service.delegation_reserve(
        "Primary Output",
        expected_revision=service.workflow_get_state().revision,
        idempotency_key="amend-reserve",
    )
    spec = prime_slice(service)
    service.slice_release(
        spec,
        expected_revision=service.workflow_get_state().revision,
        idempotency_key="before-amend",
    )
    amended = ref("amended-contract")
    control = prime_control_continue(service, LegalBranch.AMEND, amended_contract=amended)
    assert control.outcome == "ready"
    assert service.workflow_get_state().source == amended

    next_spec = spec.model_copy(update={"objective": ref("post-amend-objective")})
    check = service.slice_check(next_spec)
    assert not check.eligible
    prime_control_continue(service)
    check = service.slice_check(next_spec)
    assert not check.eligible
    assert "Contract and Decision reevaluation" in (check.reason or "")

    def reevaluate(node: CheckpointNode, branch: str, facts: list[FactKey]) -> None:
        current = service.workflow_get_state()
        evidence = EvidenceSubmission(
            node_id=node,
            facts=[
                CheckpointFact(
                    fact_key=key,
                    judgment=FactDetermined(
                        status="determined",
                        value=ReferenceFactValue(
                            kind="semantic_ref", value=ref(f"post-amend-{key.value}")
                        ),
                    ),
                )
                for key in facts
            ],
            evidence_refs=[
                TypedEvidenceReference(
                    kind=(
                        EvidenceKind.USER_DIRECTIVE
                        if node is CheckpointNode.CONTRACT
                        else EvidenceKind.DECISION_BRIEF
                    ),
                    reference=EvidenceRef(
                        uri=f"test://post-amend-{node.value}", content_hash="a" * 64
                    ),
                ),
                *(
                    [
                        TypedEvidenceReference(
                            kind=EvidenceKind.EXPLICIT_TASK_CONSTRAINTS,
                            reference=EvidenceRef(
                                uri="test://post-amend-constraints", content_hash="b" * 64
                            ),
                        )
                    ]
                    if node is CheckpointNode.CONTRACT
                    else []
                ),
            ],
            input_hash="c" * 64,
        )
        receipt = service.workflow_record_evidence(
            evidence,
            expected_revision=current.revision,
            idempotency_key=f"post-amend-evidence-{node.value}",
        )
        result = service.workflow_evaluate(
            node,
            branch=branch,
            input_hash=evidence.input_hash,
            expected_revision=receipt.receipt_revision,
            idempotency_key=f"post-amend-evaluation-{node.value}",
        )
        assert result.outcome == "ready"

    reevaluate(
        CheckpointNode.CONTRACT,
        "ready",
        [
            FactKey.TASK_OBJECTIVE,
            FactKey.AUTHORIZED_SCOPE,
            FactKey.CONSTRAINTS,
            FactKey.ACCEPTANCE_CONDITIONS,
        ],
    )
    reevaluate(
        CheckpointNode.DECISION,
        "decided",
        [
            FactKey.DECISION_QUESTION,
            FactKey.AVAILABLE_OPTIONS,
            FactKey.DECISION_CONSEQUENCES,
        ],
    )
    prime_control_continue(service)
    prime_slice(service, next_spec)
    released = service.slice_release(
        next_spec,
        expected_revision=service.workflow_get_state().revision,
        idempotency_key="post-amend-slice-release",
    )
    assert released.result["status"] == "released"
    assert released.result["allocation_id"] == next_spec.allocation_id


def test_state_service_contract_slice_control_verification_acceptance_flow(tmp_path: Path) -> None:
    service, _ = setup(tmp_path)

    def submit_and_evaluate(
        node: CheckpointNode,
        branch: str,
        facts: list[tuple[FactKey, object]],
        evidence_kinds: list[EvidenceKind],
        *,
        coverage: list[EpochDimension] | None = None,
        key_prefix: str = "flow",
    ) -> CheckpointEvaluation:
        state = service.workflow_get_state()
        typed_facts: list[CheckpointFact] = []
        for key, value in facts:
            if isinstance(value, LegalBranch):
                typed = EnumFactValue(kind="enum", value=value)
            elif isinstance(value, bool):
                typed = BooleanFactValue(kind="boolean", value=value)
            elif isinstance(value, int):
                typed = CountFactValue(kind="count", value=value)
            else:
                assert isinstance(value, SemanticRef)
                typed = ReferenceFactValue(kind="semantic_ref", value=value)
            typed_facts.append(
                CheckpointFact(
                    fact_key=key,
                    judgment=FactDetermined(status="determined", value=typed),
                )
            )
        submission = EvidenceSubmission(
            node_id=node,
            facts=typed_facts,
            evidence_refs=[
                TypedEvidenceReference(
                    kind=kind,
                    reference=EvidenceRef(
                        uri=f"test://{node.value}/{index}",
                        content_hash=hex(index + 1)[2:].zfill(64),
                    ),
                )
                for index, kind in enumerate(evidence_kinds)
            ],
            coverage_dimensions=coverage or [],
            input_hash=hex(len(node.value) + 100)[2:].zfill(64),
        )
        recorded = service.workflow_record_evidence(
            submission,
            expected_revision=state.revision,
            idempotency_key=f"{key_prefix}-evidence-{node.value}",
        )
        return service.workflow_evaluate(
            node,
            branch=branch,
            input_hash=submission.input_hash,
            expected_revision=recorded.receipt_revision,
            idempotency_key=f"{key_prefix}-evaluate-{node.value}",
        )

    contract = submit_and_evaluate(
        CheckpointNode.CONTRACT,
        "ready",
        [
            (FactKey.TASK_OBJECTIVE, ref("objective")),
            (FactKey.AUTHORIZED_SCOPE, ref("scope")),
            (FactKey.CONSTRAINTS, ref("constraints")),
            (FactKey.ACCEPTANCE_CONDITIONS, ref("acceptance-conditions")),
        ],
        [EvidenceKind.USER_DIRECTIVE, EvidenceKind.EXPLICIT_TASK_CONSTRAINTS],
    )
    assert contract.outcome == "ready"

    mode = submit_and_evaluate(
        CheckpointNode.MODE,
        "multi-agent",
        [
            (FactKey.VALID_MODE_DECISION, LegalBranch.MULTI_AGENT),
            (FactKey.LOCKED_CHILD_COUNT, 1),
            (FactKey.CAPABILITY_GATE_RESULT, True),
        ],
        [EvidenceKind.PARENT_MODE_RECORD],
    )
    assert mode.outcome == "ready"
    service.delegation_reserve(
        "Primary Output",
        expected_revision=service.workflow_get_state().revision,
        idempotency_key="flow-reserve",
    )

    decision = submit_and_evaluate(
        CheckpointNode.DECISION,
        "decided",
        [
            (FactKey.DECISION_QUESTION, ref("decision-question")),
            (FactKey.AVAILABLE_OPTIONS, ref("decision-options")),
            (FactKey.DECISION_CONSEQUENCES, ref("decision-consequences")),
        ],
        [EvidenceKind.DECISION_BRIEF],
    )
    assert decision.outcome == "ready"

    spec = SliceSpec(
        allocation_id=service.workflow_get_state().allocations[0].allocation_id,
        output_class=OutputClass.CODE_CONFIGURATION,
        objective=ref("flow-objective"),
        return_conditions=ref("flow-return"),
        unreleased_boundary=ref("flow-boundary"),
        authorized_paths=["mcp/"],
        change_categories=[ChangeCategory.TESTS],
        write_content_memo=False,
    )
    prime_slice(service, spec)
    released = service.slice_release(
        spec,
        expected_revision=service.workflow_get_state().revision,
        idempotency_key="flow-release",
    )
    implementation = submit_and_evaluate(
        CheckpointNode.IMPLEMENTATION,
        "complete",
        [
            (FactKey.RELEASED_OBJECTIVE, spec.objective),
            (FactKey.AUTHORIZED_MUTATION_SCOPE, ref("flow-authorized-mutations")),
            (FactKey.CURRENT_UNRELEASED_BOUNDARY, spec.unreleased_boundary),
        ],
        [EvidenceKind.SLICE_RELEASE, EvidenceKind.IMPLEMENTATION_RESULT],
        coverage=[EpochDimension.IMPLEMENTATION_CONTENT],
    )
    assert implementation.outcome == "ready"
    assert released.result["status"] == "released"

    control = prime_control_continue(service)
    assert control.outcome == "ready"
    binding = service._parent_binding({Cap.WORKFLOW_READ}, {Guard.PATH_BOUNDARY})
    database, trusted_root = service._root_database(binding, create=False)
    with service._read_transaction(database, DatabaseKind.WORKFLOW, trusted_root) as connection:
        current_impl_epoch = connection.execute(
            "SELECT implementation_content FROM workflow_epochs WHERE singleton=1"
        ).fetchone()[0]
    verification = submit_and_evaluate(
        CheckpointNode.VERIFICATION,
        "pass",
        [
            (FactKey.CURRENT_IMPLEMENTATION_EPOCH, current_impl_epoch),
            (FactKey.VERIFICATION_SCOPE, ref("flow-verification-scope")),
        ],
        [EvidenceKind.VERIFICATION_RESULTS],
        coverage=[EpochDimension.IMPLEMENTATION_CONTENT],
    )
    assert verification.outcome == "ready"

    acceptance = submit_and_evaluate(
        CheckpointNode.ACCEPTANCE,
        "complete",
        [
            (FactKey.CHECKPOINT_OUTCOMES, ref("flow-checkpoint-outcomes")),
            (FactKey.CURRENT_AFFECTED_EPOCHS, ref("flow-epochs")),
            (FactKey.REMAINING_LIMITATIONS, ref("flow-limitations")),
        ],
        [EvidenceKind.REQUIRED_COMPLETION],
        coverage=list(EpochDimension),
    )
    assert acceptance.outcome == "ready"
    service.workflow_transition(
        CheckpointConfirmationTransition(
            kind="confirm_checkpoint",
            evaluation_id=acceptance.evaluation_id,
            expected_revision=acceptance.result_revision,
            idempotency_key="flow-confirm-acceptance",
        )
    )
    assert service.workflow_get_state().lifecycle == "completed"


def test_acceptance_rechecks_git_documentation_and_content_epochs(tmp_path: Path) -> None:
    service, _ = setup(tmp_path)

    def submit_eval(
        node: CheckpointNode,
        branch: str,
        facts: list[tuple[FactKey, object]],
        kinds: list[EvidenceKind],
        *,
        coverage: list[EpochDimension] | None = None,
        prefix: str,
    ) -> CheckpointEvaluation:
        typed_facts: list[CheckpointFact] = []
        for key, value in facts:
            if isinstance(value, LegalBranch):
                item = EnumFactValue(kind="enum", value=value)
            elif isinstance(value, bool):
                item = BooleanFactValue(kind="boolean", value=value)
            elif isinstance(value, int):
                item = CountFactValue(kind="count", value=value)
            else:
                assert isinstance(value, SemanticRef)
                item = ReferenceFactValue(kind="semantic_ref", value=value)
            typed_facts.append(
                CheckpointFact(
                    fact_key=key, judgment=FactDetermined(status="determined", value=item)
                )
            )
        evidence = EvidenceSubmission(
            node_id=node,
            facts=typed_facts,
            evidence_refs=[
                TypedEvidenceReference(
                    kind=kind,
                    reference=EvidenceRef(
                        uri=f"test://{prefix}/{node.value}/{index}",
                        content_hash=hex(index + 10)[2:].zfill(64),
                    ),
                )
                for index, kind in enumerate(kinds)
            ],
            coverage_dimensions=coverage or [],
            input_hash=hex(len(prefix) + len(node.value) + 200)[2:].zfill(64),
        )
        recorded = service.workflow_record_evidence(
            evidence,
            expected_revision=service.workflow_get_state().revision,
            idempotency_key=f"{prefix}-evidence-{node.value}",
        )
        return service.workflow_evaluate(
            node,
            branch=branch,
            input_hash=evidence.input_hash,
            expected_revision=recorded.receipt_revision,
            idempotency_key=f"{prefix}-evaluate-{node.value}",
        )

    def refresh_gates(prefix: str) -> None:
        assert (
            submit_eval(
                CheckpointNode.CONTRACT,
                "ready",
                [
                    (FactKey.TASK_OBJECTIVE, ref("objective")),
                    (FactKey.AUTHORIZED_SCOPE, ref("scope")),
                    (FactKey.CONSTRAINTS, ref("constraints")),
                    (FactKey.ACCEPTANCE_CONDITIONS, ref("acceptance-conditions")),
                ],
                [EvidenceKind.USER_DIRECTIVE, EvidenceKind.EXPLICIT_TASK_CONSTRAINTS],
                prefix=f"{prefix}-contract",
            ).outcome
            == "ready"
        )
        assert (
            submit_eval(
                CheckpointNode.MODE,
                "multi-agent",
                [
                    (FactKey.VALID_MODE_DECISION, LegalBranch.MULTI_AGENT),
                    (FactKey.LOCKED_CHILD_COUNT, 1),
                    (FactKey.CAPABILITY_GATE_RESULT, True),
                ],
                [EvidenceKind.PARENT_MODE_RECORD],
                prefix=f"{prefix}-mode",
            ).outcome
            == "ready"
        )
        assert (
            submit_eval(
                CheckpointNode.DECISION,
                "decided",
                [
                    (FactKey.DECISION_QUESTION, ref("decision-question")),
                    (FactKey.AVAILABLE_OPTIONS, ref("decision-options")),
                    (FactKey.DECISION_CONSEQUENCES, ref("decision-consequences")),
                ],
                [EvidenceKind.DECISION_BRIEF],
                prefix=f"{prefix}-decision",
            ).outcome
            == "ready"
        )

    mode = submit_eval(
        CheckpointNode.MODE,
        "multi-agent",
        [
            (FactKey.VALID_MODE_DECISION, LegalBranch.MULTI_AGENT),
            (FactKey.LOCKED_CHILD_COUNT, 1),
            (FactKey.CAPABILITY_GATE_RESULT, True),
        ],
        [EvidenceKind.PARENT_MODE_RECORD],
        prefix="acceptance-initial-mode",
    )
    assert mode.outcome == "ready"
    service.delegation_reserve(
        "Primary Output",
        expected_revision=service.workflow_get_state().revision,
        idempotency_key="acceptance-reserve",
    )
    assert (
        submit_eval(
            CheckpointNode.CONTRACT,
            "ready",
            [
                (FactKey.TASK_OBJECTIVE, ref("objective")),
                (FactKey.AUTHORIZED_SCOPE, ref("scope")),
                (FactKey.CONSTRAINTS, ref("constraints")),
                (FactKey.ACCEPTANCE_CONDITIONS, ref("acceptance-conditions")),
            ],
            [EvidenceKind.USER_DIRECTIVE, EvidenceKind.EXPLICIT_TASK_CONSTRAINTS],
            prefix="acceptance-initial-contract",
        ).outcome
        == "ready"
    )
    assert (
        submit_eval(
            CheckpointNode.DECISION,
            "decided",
            [
                (FactKey.DECISION_QUESTION, ref("decision-question")),
                (FactKey.AVAILABLE_OPTIONS, ref("decision-options")),
                (FactKey.DECISION_CONSEQUENCES, ref("decision-consequences")),
            ],
            [EvidenceKind.DECISION_BRIEF],
            prefix="acceptance-initial-decision",
        ).outcome
        == "ready"
    )

    slice_spec = SliceSpec(
        allocation_id=service.workflow_get_state().allocations[0].allocation_id,
        output_class=OutputClass.CODE_CONFIGURATION,
        objective=ref("acceptance-objective"),
        return_conditions=ref("acceptance-return"),
        unreleased_boundary=ref("acceptance-boundary"),
        authorized_paths=["mcp/"],
        change_categories=[ChangeCategory.TESTS],
        write_content_memo=False,
    )
    prime_slice(service, slice_spec)
    service.slice_release(
        slice_spec,
        expected_revision=service.workflow_get_state().revision,
        idempotency_key="acceptance-release",
    )
    assert (
        submit_eval(
            CheckpointNode.IMPLEMENTATION,
            "complete",
            [
                (FactKey.RELEASED_OBJECTIVE, slice_spec.objective),
                (FactKey.AUTHORIZED_MUTATION_SCOPE, ref("acceptance-mutations")),
                (FactKey.CURRENT_UNRELEASED_BOUNDARY, slice_spec.unreleased_boundary),
            ],
            [EvidenceKind.SLICE_RELEASE, EvidenceKind.IMPLEMENTATION_RESULT],
            coverage=[EpochDimension.IMPLEMENTATION_CONTENT],
            prefix="acceptance-implementation",
        ).outcome
        == "ready"
    )
    prime_control_continue(service)

    binding = service._parent_binding({Cap.WORKFLOW_READ}, {Guard.PATH_BOUNDARY})
    database, trusted_root = service._root_database(binding, create=False)
    with service._read_transaction(database, DatabaseKind.WORKFLOW, trusted_root) as connection:
        impl_epoch = connection.execute(
            "SELECT implementation_content FROM workflow_epochs WHERE singleton=1"
        ).fetchone()[0]
    assert (
        submit_eval(
            CheckpointNode.VERIFICATION,
            "pass",
            [
                (FactKey.CURRENT_IMPLEMENTATION_EPOCH, impl_epoch),
                (FactKey.VERIFICATION_SCOPE, ref("acceptance-verification")),
            ],
            [EvidenceKind.VERIFICATION_RESULTS],
            coverage=[EpochDimension.IMPLEMENTATION_CONTENT],
            prefix="acceptance-verification",
        ).outcome
        == "ready"
    )

    def submit_acceptance(prefix: str) -> CheckpointEvaluation:
        return submit_eval(
            CheckpointNode.ACCEPTANCE,
            "complete",
            [
                (FactKey.CHECKPOINT_OUTCOMES, ref("acceptance-outcomes")),
                (FactKey.CURRENT_AFFECTED_EPOCHS, ref("acceptance-epochs")),
                (FactKey.REMAINING_LIMITATIONS, ref("acceptance-limitations")),
            ],
            [EvidenceKind.REQUIRED_COMPLETION],
            coverage=list(EpochDimension),
            prefix=prefix,
        )

    # Git-only changes preserve Product implementation/verification evidence;
    # the wider workflow checkpoints are explicitly reevaluated at the new snapshot.
    service.workflow_advance_epoch(
        EpochDimension.GIT_METADATA,
        expected_revision=service.workflow_get_state().revision,
        idempotency_key="acceptance-git-epoch",
    )
    refresh_gates("after-git")
    prime_control_continue(service)
    assert submit_acceptance("after-git").outcome == "ready"

    with service._read_transaction(database, DatabaseKind.WORKFLOW, trusted_root) as connection:
        docs_epoch = connection.execute(
            "SELECT documentation FROM workflow_epochs WHERE singleton=1"
        ).fetchone()[0]
    docs_facts = [
        (FactKey.DOCUMENTATION_SCOPE, ref("acceptance-docs")),
        (FactKey.AFFECTED_DOCUMENTATION_EPOCH, docs_epoch),
    ]
    docs_kinds = [EvidenceKind.DOCUMENTATION_CHECKS, EvidenceKind.UPDATED_EPOCH]
    assert (
        submit_eval(
            CheckpointNode.DOCUMENTATION,
            "complete",
            docs_facts,
            docs_kinds,
            coverage=[EpochDimension.DOCUMENTATION],
            prefix="acceptance-documentation",
        ).outcome
        == "ready"
    )
    assert submit_acceptance("with-documentation").outcome == "ready"

    service.workflow_advance_epoch(
        EpochDimension.DOCUMENTATION,
        expected_revision=service.workflow_get_state().revision,
        idempotency_key="acceptance-docs-epoch",
    )
    refresh_gates("after-docs")
    prime_control_continue(service)
    assert submit_acceptance("stale-documentation").outcome == "blocked"

    with service._read_transaction(database, DatabaseKind.WORKFLOW, trusted_root) as connection:
        docs_epoch = connection.execute(
            "SELECT documentation FROM workflow_epochs WHERE singleton=1"
        ).fetchone()[0]
    docs_facts = [
        (FactKey.DOCUMENTATION_SCOPE, ref("acceptance-docs")),
        (FactKey.AFFECTED_DOCUMENTATION_EPOCH, docs_epoch),
    ]
    assert (
        submit_eval(
            CheckpointNode.DOCUMENTATION,
            "complete",
            docs_facts,
            docs_kinds,
            coverage=[EpochDimension.DOCUMENTATION],
            prefix="refreshed-acceptance-documentation",
        ).outcome
        == "ready"
    )
    refresh_gates("after-docs-refresh")
    prime_control_continue(service)
    assert submit_acceptance("fresh-documentation").outcome == "ready"

    service.workflow_advance_epoch(
        EpochDimension.IMPLEMENTATION_CONTENT,
        expected_revision=service.workflow_get_state().revision,
        idempotency_key="acceptance-content-epoch",
    )
    refresh_gates("after-content")
    prime_control_continue(service)
    assert submit_acceptance("stale-content").outcome == "blocked"


def test_required_mode_and_objective_facts_cannot_be_marked_not_applicable() -> None:
    from pydantic import ValidationError
    from token_io_decoupling_core.state_models import FactNotApplicable

    for key in (FactKey.VALID_MODE_DECISION, FactKey.TASK_OBJECTIVE):
        with pytest.raises(ValidationError):
            CheckpointFact(
                fact_key=key,
                judgment=FactNotApplicable(
                    status="not_applicable", reason=ref("not-applicable-reason")
                ),
            )


def test_checkpoint_confirmation_requires_and_records_current_evaluation(tmp_path: Path) -> None:
    service, _ = setup(tmp_path)
    spec = prime_slice(service)
    revision = service.workflow_get_state().revision
    evaluation = service.workflow_evaluate(
        CheckpointNode.SLICE,
        branch="released",
        input_hash=service.slice_check(spec).input_hash,
        expected_revision=revision,
        idempotency_key=f"confirmed-slice-evaluation-{revision}",
    )
    receipt = service.workflow_transition(
        CheckpointConfirmationTransition(
            kind="confirm_checkpoint",
            evaluation_id=evaluation.evaluation_id,
            expected_revision=evaluation.result_revision,
            idempotency_key="confirm-slice-checkpoint",
        )
    )
    assert receipt.receipt_revision == evaluation.result_revision + 1
    assert receipt.result["node_id"] == CheckpointNode.SLICE.value
    replay = service.workflow_transition(
        CheckpointConfirmationTransition(
            kind="confirm_checkpoint",
            evaluation_id=evaluation.evaluation_id,
            expected_revision=evaluation.result_revision,
            idempotency_key="confirm-slice-checkpoint",
        )
    )
    assert replay.replayed and replay.receipt_revision == receipt.receipt_revision


def test_evaluation_cas_replay_and_idempotency_key_conflict(tmp_path: Path) -> None:
    service, _ = setup(tmp_path)
    spec = prime_slice(service)
    revision = service.workflow_get_state().revision
    args = {
        "branch": "released",
        "input_hash": service.slice_check(spec).input_hash,
        "expected_revision": revision,
        "idempotency_key": "slice-evaluation-once",
    }
    first = service.workflow_evaluate(CheckpointNode.SLICE, **args)
    replay = service.workflow_evaluate(CheckpointNode.SLICE, **args)
    assert replay.evaluation_id == first.evaluation_id
    assert replay.result_revision == first.result_revision
    assert service.workflow_get_state().revision == first.result_revision
    with pytest.raises(IdempotencyConflictError):
        service.workflow_evaluate(
            CheckpointNode.SLICE,
            branch="blocked",
            expected_revision=revision,
            idempotency_key="slice-evaluation-once",
        )
    with pytest.raises(RevisionConflictError):
        service.workflow_evaluate(
            CheckpointNode.SLICE,
            branch="released",
            expected_revision=revision,
            idempotency_key="slice-evaluation-stale-cas",
        )


def test_control_transition_replay_precedes_revision_check(tmp_path: Path) -> None:
    service, _ = setup(tmp_path)
    evaluation = prime_control_continue(service)
    request = ControlTransitionRequest(
        kind="control",
        evaluation_id=evaluation.evaluation_id,
        outcome="continue",
        expected_revision=evaluation.result_revision,
        idempotency_key=f"control-continue-{evaluation.result_revision}",
    )
    replay = service.workflow_transition(request)
    assert replay.replayed
    with pytest.raises(IdempotencyConflictError):
        service.workflow_transition(request.model_copy(update={"outcome": "stop"}))


def test_control_continue_closes_only_the_bound_parallel_slice(tmp_path: Path) -> None:
    service, _ = setup(tmp_path, children=2)
    state = service.workflow_get_state()
    service.delegation_reserve(
        "Primary Output", expected_revision=state.revision, idempotency_key="reserve-a"
    )
    state = service.workflow_get_state()
    service.delegation_reserve(
        "Change Verification", expected_revision=state.revision, idempotency_key="reserve-b"
    )
    allocations = service.workflow_get_state().allocations

    spec_a = SliceSpec(
        allocation_id=allocations[0].allocation_id,
        output_class=OutputClass.CODE_CONFIGURATION,
        objective=ref("parallel-a"),
        return_conditions=ref("return-a"),
        unreleased_boundary=ref("boundary-a"),
        authorized_paths=["mcp/"],
        change_categories=[ChangeCategory.SOURCE_CODE],
        write_content_memo=False,
    )
    prime_slice(service, spec_a)
    receipt_a = service.slice_release(
        spec_a, expected_revision=service.workflow_get_state().revision, idempotency_key="release-a"
    )
    # An explicit empty set preserves the unrelated active Slice while recording
    # the Control decision needed to release the next allocation's Slice.
    prime_control_continue(service, slice_ids=[])

    spec_b = SliceSpec(
        allocation_id=allocations[1].allocation_id,
        output_class=OutputClass.CODE_CONFIGURATION,
        objective=ref("parallel-b"),
        return_conditions=ref("return-b"),
        unreleased_boundary=ref("boundary-b"),
        authorized_paths=["mcp/"],
        change_categories=[ChangeCategory.TESTS],
        write_content_memo=False,
    )
    prime_slice(service, spec_b)
    receipt_b = service.slice_release(
        spec_b, expected_revision=service.workflow_get_state().revision, idempotency_key="release-b"
    )
    prime_control_continue(service, slice_ids=[str(receipt_b.result["slice_id"])])

    binding = service._parent_binding({Cap.WORKFLOW_READ}, {Guard.PATH_BOUNDARY})
    database, trusted_root = service._root_database(binding, create=False)
    with service._read_transaction(database, DatabaseKind.WORKFLOW, trusted_root) as connection:
        statuses = dict(
            connection.execute("SELECT slice_id,status FROM workflow_slices").fetchall()
        )
    assert statuses[str(receipt_a.result["slice_id"])] == "released"
    assert statuses[str(receipt_b.result["slice_id"])] == "closed"


def test_native_reconcile_requires_confirmation_and_preserves_conflicts(tmp_path: Path) -> None:
    from token_io_decoupling_core.state_models import (
        EpochSnapshot,
        NativeReconcileTransition,
        NativeWorkflowSnapshot,
    )

    provider = FakeBindings()
    service = StateService(
        provider, state_root=tmp_path / "state", rule_loader=source_rule_loader()
    )
    native = NativeWorkflowSnapshot(
        project_id="project-a",
        root_session_id="root-a",
        run_id="native-run",
        mode_count=ModeCount(mode=CodingMode.SINGLE_AGENT, child_count=0),
        mode_source="explicit",
        lifecycle="pending",
        source=ref("native-plan"),
        semantic_references=[],
        revision=0,
        allocations=[],
        epochs=EpochSnapshot(implementation_content=0, documentation=0, git_metadata=0),
        evidence_refs=[EvidenceRef(uri="test://native", content_hash="f" * 64)],
    )
    pending = service.workflow_reconcile(
        native, expected_revision=0, idempotency_key="native-compare"
    )
    assert pending.status == "awaiting_confirmation"
    pending_replay = service.workflow_reconcile(
        native, expected_revision=0, idempotency_key="native-compare"
    )
    assert pending_replay.replayed and pending_replay.reconcile_id == pending.reconcile_id
    with pytest.raises(InvalidStateTransitionError, match="explicitly resolved"):
        service.workflow_open(request())
    with pytest.raises(IdempotencyConflictError):
        service.workflow_reconcile(
            native.model_copy(update={"run_id": "different-run"}),
            expected_revision=0,
            idempotency_key="native-compare",
        )
    confirmation = NativeReconcileTransition(
        kind="confirm_native_reconcile",
        snapshot=native,
        expected_revision=pending.result_revision,
        idempotency_key="native-confirm",
    )
    confirmed = service.workflow_transition(confirmation)
    assert confirmed.result["status"] == "matched"
    replay = service.workflow_transition(confirmation)
    assert replay.replayed and replay.result["status"] == "matched"
    assert service.workflow_get_state().revision == confirmed.receipt_revision
    before = service.workflow_get_state()
    assert before.mode_count.mode is CodingMode.SINGLE_AGENT
    conflicting = native.model_copy(
        update={
            "mode_count": ModeCount(mode=CodingMode.MULTI_AGENT, child_count=1),
            "revision": before.revision,
        }
    )
    result = service.workflow_reconcile(
        conflicting,
        confirm=False,
        expected_revision=before.revision,
        idempotency_key="native-conflict",
    )
    assert result.status == "conflict"
    assert result.native_refs == native.evidence_refs
    after = service.workflow_get_state()
    assert after.mode_count == before.mode_count
    assert after.run_id == before.run_id
    assert any(
        item.reconcile_id == result.reconcile_id and item.status == "conflict"
        for item in after.unresolved_native_reconciliations
    )


def test_native_two_phase_reconcile_on_existing_root_is_revision_safe(tmp_path: Path) -> None:
    from token_io_decoupling_core.state_models import (
        EpochSnapshot,
        NativeAllocation,
        NativeWorkflowSnapshot,
    )

    service, _ = setup(tmp_path)
    state = service.workflow_get_state()
    snapshot = NativeWorkflowSnapshot(
        project_id=state.project_id,
        root_session_id=state.root_session_id,
        run_id=state.run_id,
        mode_count=state.mode_count,
        mode_source=state.mode_source,
        lifecycle=state.lifecycle,
        source=state.source,
        semantic_references=state.semantic_references,
        revision=state.revision,
        allocations=[
            NativeAllocation(
                allocation_id=item.allocation_id,
                role=item.role,
                worker_session_id=item.worker_session_id,
                status=item.status,
            )
            for item in state.allocations
        ],
        epochs=EpochSnapshot(implementation_content=0, documentation=0, git_metadata=0),
        evidence_refs=[EvidenceRef(uri="test://same-root", content_hash="a" * 64)],
    )
    compared = service.workflow_reconcile(
        snapshot, expected_revision=state.revision, idempotency_key="same-root-compare"
    )
    assert compared.status == "awaiting_confirmation"
    assert compared.result_revision == state.revision + 1
    confirmed = service.workflow_reconcile(
        snapshot,
        confirm=True,
        expected_revision=compared.result_revision,
        idempotency_key="same-root-confirm",
    )
    assert confirmed.status == "matched"
    assert service.workflow_get_state().revision == confirmed.result_revision

    after_confirmation = service.workflow_get_state()
    assert after_confirmation.unresolved_native_reconciliations == []
    service.workflow_advance_epoch(
        "documentation",
        expected_revision=after_confirmation.revision,
        idempotency_key="native-confirmation-follow-up-mutation",
    )
    assert service.workflow_get_state().epochs.documentation == 1

    actual = service.workflow_get_state()
    altered = snapshot.model_copy(
        update={
            "revision": actual.revision,
            "mode_count": ModeCount(mode=CodingMode.MULTI_AGENT, child_count=2),
        }
    )
    conflict = service.workflow_reconcile(
        altered, expected_revision=actual.revision, idempotency_key="same-root-conflict"
    )
    assert conflict.status == "conflict"
    assert conflict.result_revision == actual.revision + 1
    conflict_state = service.workflow_get_state()
    assert conflict_state.mode_count == actual.mode_count
    assert any(
        item.reconcile_id == conflict.reconcile_id and item.status == "conflict" and item.current
        for item in conflict_state.unresolved_native_reconciliations
    )

    huge = altered.model_copy(update={"revision": 10_000_000})
    huge_conflict = service.workflow_reconcile(
        huge,
        expected_revision=conflict.result_revision,
        idempotency_key="huge-native-revision",
    )
    assert huge_conflict.status == "conflict"
    assert huge_conflict.result_revision == conflict.result_revision + 1


def test_native_full_set_resolution_adjudicates_stale_awaiting_and_exposes_basis_refs(
    tmp_path: Path,
) -> None:
    from token_io_decoupling_core.state_models import (
        EpochSnapshot,
        NativeAllocation,
        NativeReconcileResolutionTransition,
        NativeWorkflowSnapshot,
    )

    service, _ = setup(tmp_path)

    def snapshot_from(state, *, source_name: str, revision: int, evidence_name: str):
        return NativeWorkflowSnapshot(
            project_id=state.project_id,
            root_session_id=state.root_session_id,
            run_id=state.run_id,
            mode_count=state.mode_count,
            mode_source=state.mode_source,
            lifecycle=state.lifecycle,
            source=ref(source_name),
            semantic_references=state.semantic_references,
            revision=revision,
            allocations=[
                NativeAllocation(
                    allocation_id=item.allocation_id,
                    role=item.role,
                    worker_session_id=item.worker_session_id,
                    status=item.status,
                )
                for item in state.allocations
            ],
            epochs=EpochSnapshot(
                implementation_content=state.epochs.implementation_content,
                documentation=state.epochs.documentation,
                git_metadata=state.epochs.git_metadata,
            ),
            evidence_refs=[
                EvidenceRef(uri=f"test://native/{evidence_name}", content_hash="d" * 64)
            ],
        )

    initial = service.workflow_get_state()
    matching = snapshot_from(
        initial,
        source_name="plan",
        revision=initial.revision,
        evidence_name="first",
    )
    first = service.workflow_reconcile(
        matching,
        expected_revision=initial.revision,
        idempotency_key="native-match-awaiting",
    )
    assert first.status == "awaiting_confirmation"

    after_first = service.workflow_get_state()
    changed = snapshot_from(
        after_first,
        source_name="native-plan",
        revision=after_first.revision,
        evidence_name="second",
    )
    second = service.workflow_reconcile(
        changed,
        expected_revision=after_first.revision,
        idempotency_key="native-material-conflict",
    )
    assert second.status == "conflict"

    reviewed = service.workflow_get_state()
    assert reviewed.unresolved_native_set_hash
    assert {item.status for item in reviewed.unresolved_native_reconciliations} == {
        "awaiting_confirmation",
        "conflict",
    }
    canonical = next(
        item
        for item in reviewed.unresolved_native_reconciliations
        if item.reconcile_id == second.reconcile_id
    )
    assert canonical.native_source == changed.source
    assert canonical.native_semantic_references == changed.semantic_references
    assert canonical.native_epochs == changed.epochs
    refs = [
        evidence_ref
        for comparison in reviewed.unresolved_native_reconciliations
        for evidence_ref in comparison.native_refs
    ]
    decision_ref = EvidenceRef(uri="test://root/native-decision", content_hash="e" * 64)
    quiescence_ref = EvidenceRef(uri="test://root/quiescence", content_hash="f" * 64)
    native_revision = max(
        item.native_revision for item in reviewed.unresolved_native_reconciliations
    )
    native_epochs = {
        dimension: max(
            int(getattr(item.native_epochs, dimension))
            for item in reviewed.unresolved_native_reconciliations
        )
        for dimension in ("implementation_content", "documentation", "git_metadata")
    }
    transition = NativeReconcileResolutionTransition(
        kind="resolve_native_reconcile",
        canonical_reconcile_id=second.reconcile_id,
        snapshot_hash=canonical.snapshot_hash,
        unresolved_set_hash=reviewed.unresolved_native_set_hash,
        choice="adopt_native_pair",
        reviewed_native_revision=native_revision,
        reviewed_native_epochs=EpochSnapshot(**native_epochs),
        root_decision_ref=decision_ref,
        native_freshness_refs=refs,
        root_quiescence_refs=[quiescence_ref],
        expected_revision=reviewed.revision,
        idempotency_key="resolve-native-full-set",
    )

    resolved = service.workflow_transition(transition)
    assert resolved.result["resolved_comparison_count"] == 2
    assert resolved.result["source"] == ref("native-plan").model_dump(mode="json")
    assert (
        resolved.receipt_revision == max(reviewed.revision, matching.revision, changed.revision) + 1
    )
    recovered = service.workflow_get_state()
    assert recovered.recovery_revision == resolved.receipt_revision
    assert not recovered.unresolved_native_reconciliations
    assert recovered.epochs.implementation_content == 1
    assert recovered.epochs.documentation == 1
    assert recovered.epochs.git_metadata == 1
    history = recovered.native_resolution_history[0]
    assert [item.reconcile_id for item in history.resolved_comparisons] == sorted(
        [first.reconcile_id, second.reconcile_id]
    )
    assert {item.snapshot_hash for item in history.resolved_comparisons} == {
        item.snapshot_hash for item in reviewed.unresolved_native_reconciliations
    }
    assert history.root_decision_ref == decision_ref
    assert set((item.uri, item.content_hash) for item in history.native_freshness_refs) == {
        (item.uri, item.content_hash) for item in refs
    }
    assert history.root_quiescence_refs == [quiescence_ref]

    replay = service.workflow_transition(transition)
    assert replay.replayed and replay.receipt_revision == resolved.receipt_revision
    assert service.workflow_get_state().revision == resolved.receipt_revision

    binding = service._parent_binding({Cap.WORKFLOW_READ}, {Guard.PATH_BOUNDARY})
    database, trusted_root = service._root_database(binding, create=False)
    with service._read_transaction(database, DatabaseKind.WORKFLOW, trusted_root) as connection:
        old_statuses = dict(
            connection.execute("SELECT reconcile_id,status FROM native_reconciliations").fetchall()
        )
        linked_targets = connection.execute(
            "SELECT COUNT(*) FROM native_reconcile_resolution_targets"
        ).fetchone()[0]
    assert old_statuses[first.reconcile_id] == "awaiting_confirmation"
    assert old_statuses[second.reconcile_id] == "conflict"
    assert linked_targets == 2


def test_native_resolution_rejects_stale_set_and_unbound_freshness_refs(tmp_path: Path) -> None:
    from pydantic import ValidationError
    from token_io_decoupling_core.state_models import (
        EpochSnapshot,
        NativeAllocation,
        NativeWorkflowSnapshot,
    )

    service, _ = setup(tmp_path)
    state = service.workflow_get_state()
    freshness = EvidenceRef(uri="test://native/current", content_hash="d" * 64)
    native = NativeWorkflowSnapshot(
        project_id=state.project_id,
        root_session_id=state.root_session_id,
        run_id=state.run_id,
        mode_count=state.mode_count,
        mode_source=state.mode_source,
        lifecycle=state.lifecycle,
        source=ref("native-plan"),
        semantic_references=state.semantic_references,
        revision=state.revision,
        allocations=[
            NativeAllocation(
                allocation_id=item.allocation_id,
                role=item.role,
                worker_session_id=item.worker_session_id,
                status=item.status,
            )
            for item in state.allocations
        ],
        epochs=EpochSnapshot(
            implementation_content=state.epochs.implementation_content,
            documentation=state.epochs.documentation,
            git_metadata=state.epochs.git_metadata,
        ),
        evidence_refs=[freshness],
    )
    compared = service.workflow_reconcile(
        native, expected_revision=state.revision, idempotency_key="native-ref-check"
    )
    assert compared.status == "conflict"
    valid = native_resolution_request(
        service,
        compared.reconcile_id,
        native_revision=native.revision,
        native_epochs={
            "implementation_content": native.epochs.implementation_content,
            "documentation": native.epochs.documentation,
            "git_metadata": native.epochs.git_metadata,
        },
        native_freshness_refs=[freshness],
    )
    for required_field in ("root_decision_ref", "native_freshness_refs", "root_quiescence_refs"):
        incomplete_payload = valid.model_dump(mode="python")
        incomplete_payload.pop(required_field)
        with pytest.raises(ValidationError):
            type(valid).model_validate(incomplete_payload)
    wrong_set = valid.model_copy(update={"unresolved_set_hash": "0" * 64})
    before = service.workflow_get_state()
    with pytest.raises(RevisionConflictError, match="comparison set changed"):
        service.workflow_transition(wrong_set)

    unrelated_freshness = EvidenceRef(uri="test://native/not-reviewed", content_hash="c" * 64)
    wrong_refs = native_resolution_request(
        service,
        compared.reconcile_id,
        native_revision=native.revision,
        native_epochs={
            "implementation_content": native.epochs.implementation_content,
            "documentation": native.epochs.documentation,
            "git_metadata": native.epochs.git_metadata,
        },
        native_freshness_refs=[unrelated_freshness],
    )
    with pytest.raises(InvalidStateTransitionError, match="exactly cover"):
        service.workflow_transition(wrong_refs)
    after = service.workflow_get_state()
    assert after.revision == before.revision
    assert after.unresolved_native_set_hash == before.unresolved_native_set_hash
    assert after.native_resolution_history == []


def test_native_conflict_guard_precedes_worker_dispatch_side_effects(tmp_path: Path) -> None:
    from token_io_decoupling_core.state_models import (
        AllocationRole,
        EpochSnapshot,
        NativeAllocation,
        NativeWorkflowSnapshot,
    )

    service, provider = setup(tmp_path)
    before = service.workflow_get_state()
    allocation_id = before.allocations[0].allocation_id
    service.delegation_reserve(
        "Primary Output",
        expected_revision=before.revision,
        idempotency_key="reserve-before-native-conflict",
    )
    spec = prime_slice(service)
    state = service.workflow_get_state()
    released = service.slice_release(
        spec,
        expected_revision=state.revision,
        idempotency_key="release-before-native-conflict",
    )
    provider.add_child("worker-native-guard")
    state = service.workflow_get_state()
    native = NativeWorkflowSnapshot(
        project_id=state.project_id,
        root_session_id=state.root_session_id,
        run_id=state.run_id,
        mode_count=state.mode_count,
        mode_source=state.mode_source,
        lifecycle=state.lifecycle,
        source=ref("foreign-plan-reference"),
        semantic_references=state.semantic_references,
        revision=state.revision,
        allocations=[
            NativeAllocation(
                allocation_id=item.allocation_id,
                role=AllocationRole(item.role) if item.role else None,
                worker_session_id=item.worker_session_id,
                status=item.status,
            )
            for item in state.allocations
        ],
        epochs=EpochSnapshot(
            implementation_content=state.epochs.implementation_content,
            documentation=state.epochs.documentation,
            git_metadata=state.epochs.git_metadata,
        ),
        evidence_refs=[EvidenceRef(uri="test://native/guard", content_hash="c" * 64)],
    )
    conflict = service.workflow_reconcile(
        native, expected_revision=state.revision, idempotency_key="conflict-before-bind"
    )
    assert conflict.status == "conflict"

    binding = service._parent_binding({Cap.WORKFLOW_READ}, {Guard.PATH_BOUNDARY})
    worker_database, _ = service._worker_database("worker-native-guard", binding, create=False)
    assert not worker_database.exists()
    state_before_bind = service.workflow_get_state()
    with pytest.raises(InvalidStateTransitionError, match="explicitly resolved"):
        service.delegation_bind(
            allocation_id,
            "worker-native-guard",
            expected_revision=state_before_bind.revision,
            idempotency_key="blocked-bind-native-conflict",
        )
    assert not worker_database.exists()
    after_bind = service.workflow_get_state()
    assert after_bind.revision == state_before_bind.revision
    assert after_bind.allocations[0].worker_session_id is None
    assert released.result["slice_id"] == after_bind.active_slices[0].slice_id


def test_native_conflict_blocks_partial_bind_replay_before_worker_initialization(
    tmp_path: Path,
) -> None:
    from token_io_decoupling_core.state_models import (
        AllocationRole,
        EpochSnapshot,
        NativeAllocation,
        NativeWorkflowSnapshot,
    )

    service, provider = setup(tmp_path)
    before = service.workflow_get_state()
    allocation_id = before.allocations[0].allocation_id
    service.delegation_reserve(
        "Primary Output", expected_revision=before.revision, idempotency_key="reserve-partial-bind"
    )
    spec = prime_slice(service)
    state = service.workflow_get_state()
    service.slice_release(
        spec, expected_revision=state.revision, idempotency_key="release-partial-bind"
    )
    provider.add_child("worker-partial-native-guard")
    bind_revision = service.workflow_get_state().revision

    class InterruptBeforeDispatch(StateService):
        interrupted = False

        def _complete_worker_dispatch(self, *_args, **_kwargs):
            if not self.interrupted:
                self.interrupted = True
                raise RuntimeError("simulated interruption after Root outbox commit")
            return super()._complete_worker_dispatch(*_args, **_kwargs)

    interrupted = InterruptBeforeDispatch(provider, state_root=tmp_path / "state")
    with pytest.raises(RuntimeError, match="interruption"):
        interrupted.delegation_bind(
            allocation_id,
            "worker-partial-native-guard",
            expected_revision=bind_revision,
            idempotency_key="partial-bind-native-conflict",
        )

    state = interrupted.workflow_get_state()
    native = NativeWorkflowSnapshot(
        project_id=state.project_id,
        root_session_id=state.root_session_id,
        run_id=state.run_id,
        mode_count=state.mode_count,
        mode_source=state.mode_source,
        lifecycle=state.lifecycle,
        source=ref("different-plan-after-partial-bind"),
        semantic_references=state.semantic_references,
        revision=state.revision,
        allocations=[
            NativeAllocation(
                allocation_id=item.allocation_id,
                role=AllocationRole(item.role) if item.role else None,
                worker_session_id=item.worker_session_id,
                status=item.status,
            )
            for item in state.allocations
        ],
        epochs=EpochSnapshot(
            implementation_content=state.epochs.implementation_content,
            documentation=state.epochs.documentation,
            git_metadata=state.epochs.git_metadata,
        ),
        evidence_refs=[EvidenceRef(uri="test://native/partial-bind", content_hash="b" * 64)],
    )
    conflict = interrupted.workflow_reconcile(
        native, expected_revision=state.revision, idempotency_key="compare-after-partial-bind"
    )
    assert conflict.status == "conflict"
    state_before_replay = interrupted.workflow_get_state()
    worker_path, _ = interrupted._worker_database(
        "worker-partial-native-guard",
        interrupted._parent_binding({Cap.WORKFLOW_READ}, {Guard.PATH_BOUNDARY}),
        create=False,
    )
    assert not worker_path.exists()

    with pytest.raises(InvalidStateTransitionError, match="Native reconciliation"):
        interrupted.delegation_bind(
            allocation_id,
            "worker-partial-native-guard",
            expected_revision=bind_revision,
            idempotency_key="partial-bind-native-conflict",
        )
    state_after_replay = interrupted.workflow_get_state()
    assert state_after_replay.revision == state_before_replay.revision
    assert not worker_path.exists()
    binding = interrupted._parent_binding({Cap.WORKFLOW_READ}, {Guard.PATH_BOUNDARY})
    database, trusted_root = interrupted._root_database(binding, create=False)
    with interrupted._read_transaction(database, DatabaseKind.WORKFLOW, trusted_root) as connection:
        assert tuple(
            connection.execute(
                "SELECT e.status,o.status FROM workflow_dispatch_events AS e "
                "JOIN root_outbox AS o ON o.event_id=e.event_id WHERE e.allocation_id=?",
                (allocation_id,),
            ).fetchone()
        ) == ("pending", "pending")


def test_confirmed_bind_replay_is_read_only_during_native_conflict(tmp_path: Path) -> None:
    from token_io_decoupling_core.state_models import (
        AllocationRole,
        EpochSnapshot,
        NativeAllocation,
        NativeWorkflowSnapshot,
    )

    service, provider = setup(tmp_path)
    initial = service.workflow_get_state()
    allocation_id = initial.allocations[0].allocation_id
    service.delegation_reserve(
        "Primary Output",
        expected_revision=initial.revision,
        idempotency_key="reserve-confirmed-replay",
    )
    spec = prime_slice(service)
    current = service.workflow_get_state()
    service.slice_release(
        spec, expected_revision=current.revision, idempotency_key="release-confirmed-replay"
    )
    provider.add_child("worker-confirmed-native-guard")
    bind_revision = service.workflow_get_state().revision
    first = service.delegation_bind(
        allocation_id,
        "worker-confirmed-native-guard",
        expected_revision=bind_revision,
        idempotency_key="confirmed-bind-native-conflict",
    )
    assert not first.replayed

    state = service.workflow_get_state()
    native = NativeWorkflowSnapshot(
        project_id=state.project_id,
        root_session_id=state.root_session_id,
        run_id=state.run_id,
        mode_count=state.mode_count,
        mode_source=state.mode_source,
        lifecycle=state.lifecycle,
        source=ref("different-plan-after-confirmed-bind"),
        semantic_references=state.semantic_references,
        revision=state.revision,
        allocations=[
            NativeAllocation(
                allocation_id=item.allocation_id,
                role=AllocationRole(item.role) if item.role else None,
                worker_session_id=item.worker_session_id,
                status=item.status,
            )
            for item in state.allocations
        ],
        epochs=EpochSnapshot(
            implementation_content=state.epochs.implementation_content,
            documentation=state.epochs.documentation,
            git_metadata=state.epochs.git_metadata,
        ),
        evidence_refs=[EvidenceRef(uri="test://native/confirmed-bind", content_hash="c" * 64)],
    )
    conflict = service.workflow_reconcile(
        native, expected_revision=state.revision, idempotency_key="compare-after-confirmed-bind"
    )
    assert conflict.status == "conflict"
    before_replay = service.workflow_get_state()

    replay = service.delegation_bind(
        allocation_id,
        "worker-confirmed-native-guard",
        expected_revision=bind_revision,
        idempotency_key="confirmed-bind-native-conflict",
    )
    after_replay = service.workflow_get_state()
    assert replay.replayed
    assert replay.receipt_revision == first.receipt_revision
    assert after_replay.revision == before_replay.revision
    assert after_replay.unresolved_native_reconciliations


@pytest.mark.parametrize("case", ["unsupported_mode", "counter_overflow"])
def test_native_resolution_rejects_unsupported_or_overflow_without_mutation(
    tmp_path: Path, case: str
) -> None:
    from token_io_decoupling_core.state_models import (
        EpochSnapshot,
        NativeAllocation,
        NativeWorkflowSnapshot,
    )

    service, _ = setup(tmp_path)
    state = service.workflow_get_state()
    maximum = 2**63 - 1
    native_revision = maximum if case == "counter_overflow" else state.revision
    native_epochs = EpochSnapshot(
        implementation_content=maximum if case == "counter_overflow" else 0,
        documentation=0,
        git_metadata=0,
    )
    native = NativeWorkflowSnapshot(
        project_id=state.project_id,
        root_session_id=state.root_session_id,
        run_id=state.run_id,
        mode_count=(
            ModeCount(mode=CodingMode.MULTI_AGENT, child_count=2)
            if case == "unsupported_mode"
            else state.mode_count
        ),
        mode_source=state.mode_source,
        lifecycle=state.lifecycle,
        source=ref("native-plan"),
        semantic_references=state.semantic_references,
        revision=native_revision,
        allocations=[
            NativeAllocation(
                allocation_id=item.allocation_id,
                role=item.role,
                worker_session_id=item.worker_session_id,
                status=item.status,
            )
            for item in state.allocations
        ],
        epochs=native_epochs,
        evidence_refs=[EvidenceRef(uri=f"test://native/{case}", content_hash="d" * 64)],
    )
    conflict = service.workflow_reconcile(
        native, expected_revision=state.revision, idempotency_key=f"conflict-{case}"
    )
    assert conflict.status == "conflict"
    transition = native_resolution_request(
        service,
        conflict.reconcile_id,
        native_revision=native_revision,
        native_epochs={
            "implementation_content": native_epochs.implementation_content,
            "documentation": native_epochs.documentation,
            "git_metadata": native_epochs.git_metadata,
        },
        native_freshness_refs=native.evidence_refs,
    )
    before = service.workflow_get_state()
    message = (
        "unsupported identity or lifecycle differences"
        if case == "unsupported_mode"
        else "exceed SQLite int64"
    )
    with pytest.raises(InvalidStateTransitionError, match=message):
        service.workflow_transition(transition)
    after = service.workflow_get_state()
    assert after.revision == before.revision
    assert after.unresolved_native_set_hash == before.unresolved_native_set_hash
    assert after.native_resolution_history == []


def test_oversized_legacy_native_snapshot_has_bounded_readback_and_new_write_is_rejected(
    tmp_path: Path,
) -> None:
    from token_io_decoupling_core.state_models import (
        AllocationStatus,
        EpochSnapshot,
        NativeAllocation,
        NativeWorkflowSnapshot,
    )

    service, _ = setup(tmp_path)
    state = service.workflow_get_state()
    native_ref = EvidenceRef(uri="test://native/oversized", content_hash="e" * 64)
    base = NativeWorkflowSnapshot(
        project_id=state.project_id,
        root_session_id=state.root_session_id,
        run_id=state.run_id,
        mode_count=state.mode_count,
        mode_source=state.mode_source,
        lifecycle=state.lifecycle,
        source=state.source,
        semantic_references=state.semantic_references,
        revision=state.revision,
        allocations=[
            NativeAllocation(
                allocation_id=item.allocation_id,
                role=item.role,
                worker_session_id=item.worker_session_id,
                status=item.status,
            )
            for item in state.allocations
        ],
        epochs=EpochSnapshot(
            implementation_content=state.epochs.implementation_content,
            documentation=state.epochs.documentation,
            git_metadata=state.epochs.git_metadata,
        ),
        evidence_refs=[native_ref],
    )
    oversized_refs = [
        EvidenceRef(uri=f"test://native/oversized/{index}", content_hash="e" * 64)
        for index in range(257)
    ]
    oversized_allocations = [
        NativeAllocation(
            allocation_id=f"legacy-allocation-{index}",
            role=None,
            worker_session_id=None,
            status=AllocationStatus.RESERVED,
        )
        for index in range(257)
    ]
    oversized = base.model_copy(
        update={"evidence_refs": oversized_refs, "allocations": oversized_allocations}
    )
    with pytest.raises(InvalidStateTransitionError, match="supported bounded recovery index"):
        service.workflow_reconcile(
            oversized,
            expected_revision=state.revision,
            idempotency_key="reject-new-oversized-native",
        )
    assert service.workflow_get_state().revision == state.revision

    payload = oversized.model_dump(mode="json")
    snapshot_json = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    snapshot_hash = hashlib.sha256(snapshot_json.encode("utf-8")).hexdigest()
    refs_json = json.dumps(
        [item.model_dump(mode="json") for item in oversized_refs],
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    binding = service._parent_binding({Cap.WORKFLOW_READ}, {Guard.PATH_BOUNDARY})
    database, _trusted_root = service._root_database(binding, create=False)
    with sqlite3.connect(database) as connection:
        connection.execute(
            "INSERT INTO native_reconciliations VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (
                "legacy-oversized-native",
                snapshot_hash,
                refs_json,
                '["Revision"]',
                "conflict",
                state.revision,
                state.revision + 1,
                "2026-10-25T00:00:00+00:00",
                state.project_id,
                state.root_session_id,
                snapshot_json,
            ),
        )
    readback = service.workflow_get_state()
    index = readback.unresolved_native_reconciliations[0]
    assert index.reconcile_id == "legacy-oversized-native"
    assert index.native_reference_count == 257
    assert index.native_references_omitted == 1
    assert len(index.native_refs) == 256
    assert index.native_allocation_count == 257
    assert index.native_allocations_omitted == 1
    assert len(index.native_allocations) == 256
    assert index.resolution_unavailable_reason == "native_allocations_exceed_supported_bound"
    assert readback.native_resolution_unavailable_reason == (
        "native_allocations_exceed_supported_bound"
    )
    assert readback.revision == state.revision


def test_single_root_slice_is_quiesced_by_explicit_native_resolution(tmp_path: Path) -> None:
    from token_io_decoupling_core.state_models import EpochSnapshot, NativeWorkflowSnapshot

    provider = FakeBindings()
    service = StateService(
        provider, state_root=tmp_path / "state", rule_loader=source_rule_loader()
    )
    service.workflow_open(request(children=0, mode=CodingMode.SINGLE_AGENT))
    spec = SliceSpec(
        allocation_id="root",
        output_class=OutputClass.OTHER,
        objective=ref("root-recovery-objective"),
        return_conditions=ref("root-recovery-return"),
        unreleased_boundary=ref("root-recovery-boundary"),
        authorized_paths=["mcp/"],
        change_categories=[ChangeCategory.SOURCE_CODE],
        write_content_memo=False,
    )
    prime_slice(service, spec)
    state = service.workflow_get_state()
    service.slice_release(
        spec, expected_revision=state.revision, idempotency_key="root-recovery-release"
    )
    state = service.workflow_get_state()
    native_ref = EvidenceRef(uri="test://native/root-current", content_hash="d" * 64)
    native = NativeWorkflowSnapshot(
        project_id=state.project_id,
        root_session_id=state.root_session_id,
        run_id=state.run_id,
        mode_count=state.mode_count,
        mode_source=state.mode_source,
        lifecycle=state.lifecycle,
        source=ref("native-root-plan"),
        semantic_references=state.semantic_references,
        revision=state.revision,
        allocations=[],
        epochs=EpochSnapshot(
            implementation_content=state.epochs.implementation_content,
            documentation=state.epochs.documentation,
            git_metadata=state.epochs.git_metadata,
        ),
        evidence_refs=[native_ref],
    )
    conflict = service.workflow_reconcile(
        native, expected_revision=state.revision, idempotency_key="native-root-conflict"
    )
    assert conflict.status == "conflict"
    request_to_resolve = native_resolution_request(
        service,
        conflict.reconcile_id,
        native_revision=native.revision,
        native_epochs={
            "implementation_content": native.epochs.implementation_content,
            "documentation": native.epochs.documentation,
            "git_metadata": native.epochs.git_metadata,
        },
        native_freshness_refs=[native_ref],
    )
    service.workflow_transition(request_to_resolve)
    recovered = service.workflow_get_state()
    assert recovered.active_slices == []
    binding = service._parent_binding({Cap.WORKFLOW_READ}, {Guard.PATH_BOUNDARY})
    database, trusted_root = service._root_database(binding, create=False)
    with service._read_transaction(database, DatabaseKind.WORKFLOW, trusted_root) as connection:
        assert connection.execute("SELECT status FROM root_slices").fetchone()[0] == "closed"
    assert recovered.recovery_revision > 0


def test_native_recovery_invalidates_old_slice_evidence_and_requires_fresh_eod_return(
    tmp_path: Path,
) -> None:
    from token_io_decoupling_core.state_models import (
        EpochSnapshot,
        NativeAllocation,
        NativeWorkflowSnapshot,
    )

    service, _ = setup(tmp_path)
    spec = prime_slice(service)
    old_slice_gate = service.workflow_get_state().latest_gates
    eod = prime_control_continue(service, LegalBranch.EVIDENCE_ON_DEMAND)
    assert eod.evidence_request_id

    state = service.workflow_get_state()
    native_ref = EvidenceRef(uri="test://native/recovery-freshness", content_hash="d" * 64)
    native = NativeWorkflowSnapshot(
        project_id=state.project_id,
        root_session_id=state.root_session_id,
        run_id=state.run_id,
        mode_count=state.mode_count,
        mode_source=state.mode_source,
        lifecycle=state.lifecycle,
        source=ref("native-recovery-plan"),
        semantic_references=state.semantic_references,
        revision=state.revision,
        allocations=[
            NativeAllocation(
                allocation_id=item.allocation_id,
                role=item.role,
                worker_session_id=item.worker_session_id,
                status=item.status,
            )
            for item in state.allocations
        ],
        epochs=EpochSnapshot(
            implementation_content=state.epochs.implementation_content,
            documentation=state.epochs.documentation,
            git_metadata=state.epochs.git_metadata,
        ),
        evidence_refs=[native_ref],
    )
    conflict = service.workflow_reconcile(
        native, expected_revision=state.revision, idempotency_key="native-eod-conflict"
    )
    assert conflict.status == "conflict"
    resolution = native_resolution_request(
        service,
        conflict.reconcile_id,
        native_revision=native.revision,
        native_epochs={
            "implementation_content": native.epochs.implementation_content,
            "documentation": native.epochs.documentation,
            "git_metadata": native.epochs.git_metadata,
        },
        native_freshness_refs=[native_ref],
    )
    service.workflow_transition(resolution)
    recovered = service.workflow_get_state()
    assert any(
        item.request_id == eod.evidence_request_id for item in recovered.control_evidence_requests
    )
    slice_gate = next(
        (item for item in recovered.latest_gates if item.node_id == CheckpointNode.SLICE.value),
        None,
    )
    assert slice_gate is not None
    assert not slice_gate.epochs_current, slice_gate
    assert old_slice_gate

    old_hash = service.slice_check(spec).input_hash
    assert old_hash
    reevaluation = service.workflow_evaluate(
        CheckpointNode.SLICE,
        branch="released",
        input_hash=old_hash,
        expected_revision=recovered.revision,
        idempotency_key="old-slice-evidence-after-native-recovery",
    )
    assert reevaluation.outcome == "incomplete"
    assert not service.slice_check(spec).eligible

    continue_result = prime_control_continue(service)
    assert continue_result.outcome == "ready"
    after_continue = service.workflow_get_state()
    returned = next(
        item
        for item in after_continue.control_evidence_requests
        if item.request_id == eod.evidence_request_id
    )
    assert returned.status == "resolved"
    assert returned.recovery_fresh

    current = service.workflow_get_state()
    service.workflow_advance_epoch(
        EpochDimension.IMPLEMENTATION_CONTENT,
        expected_revision=current.revision,
        idempotency_key="epoch-change-after-recovery-control",
    )
    assert not service.slice_check(spec).eligible
    prime_control_continue(service)

    state = service.workflow_get_state()
    service.delegation_reserve(
        "Primary Output",
        expected_revision=state.revision,
        idempotency_key="reserve-after-native-recovery",
    )
    fresh_spec = prime_slice(service, spec)
    state = service.workflow_get_state()
    released = service.slice_release(
        fresh_spec,
        expected_revision=state.revision,
        idempotency_key="release-after-native-recovery-and-control",
    )
    assert released.result["status"] == "released"


def test_native_recovery_before_first_slice_requires_fresh_control(tmp_path: Path) -> None:
    from token_io_decoupling_core.state_models import (
        EpochSnapshot,
        NativeAllocation,
        NativeWorkflowSnapshot,
    )

    service, _ = setup(tmp_path)
    state = service.workflow_get_state()
    native_ref = EvidenceRef(uri="test://native/first-slice", content_hash="e" * 64)
    native = NativeWorkflowSnapshot(
        project_id=state.project_id,
        root_session_id=state.root_session_id,
        run_id=state.run_id,
        mode_count=state.mode_count,
        mode_source=state.mode_source,
        lifecycle=state.lifecycle,
        source=ref("native-first-slice-plan"),
        semantic_references=state.semantic_references,
        revision=state.revision,
        allocations=[
            NativeAllocation(
                allocation_id=item.allocation_id,
                role=item.role,
                worker_session_id=item.worker_session_id,
                status=item.status,
            )
            for item in state.allocations
        ],
        epochs=EpochSnapshot(
            implementation_content=state.epochs.implementation_content,
            documentation=state.epochs.documentation,
            git_metadata=state.epochs.git_metadata,
        ),
        evidence_refs=[native_ref],
    )
    conflict = service.workflow_reconcile(
        native, expected_revision=state.revision, idempotency_key="first-slice-native-conflict"
    )
    resolution = native_resolution_request(
        service,
        conflict.reconcile_id,
        native_revision=native.revision,
        native_epochs={
            "implementation_content": native.epochs.implementation_content,
            "documentation": native.epochs.documentation,
            "git_metadata": native.epochs.git_metadata,
        },
        native_freshness_refs=[native_ref],
    )
    service.workflow_transition(resolution)
    current = service.workflow_get_state()
    spec = SliceSpec(
        allocation_id=current.allocations[0].allocation_id,
        output_class=OutputClass.CODE_CONFIGURATION,
        objective=ref("first-slice-objective"),
        return_conditions=ref("first-slice-return"),
        unreleased_boundary=ref("first-slice-boundary"),
        authorized_paths=["mcp/"],
        change_categories=[ChangeCategory.SOURCE_CODE],
        write_content_memo=False,
    )
    blocked = service.slice_check(spec)
    assert not blocked.eligible
    assert "Control Continue" in (blocked.reason or "")

    prime_control_continue(service)
    current = service.workflow_get_state()
    service.delegation_reserve(
        "Primary Output",
        expected_revision=current.revision,
        idempotency_key="reserve-after-first-slice-recovery",
    )
    fresh = prime_slice(service, spec)
    assert service.slice_check(fresh).eligible


def test_native_resolution_can_retain_sqlite_contract_pair(tmp_path: Path) -> None:
    from token_io_decoupling_core.state_models import (
        AllocationRole,
        AllocationStatus,
        EpochSnapshot,
        NativeAllocation,
        NativeWorkflowSnapshot,
    )

    service, _ = setup(tmp_path)
    before = service.workflow_get_state()
    native_ref = EvidenceRef(uri="test://native/unselected-plan", content_hash="d" * 64)
    native = NativeWorkflowSnapshot(
        project_id=before.project_id,
        root_session_id=before.root_session_id,
        run_id=before.run_id,
        mode_count=before.mode_count,
        mode_source=before.mode_source,
        lifecycle=before.lifecycle,
        source=ref("unselected-native-plan"),
        semantic_references=[ref("unselected-native-semantic")],
        revision=before.revision,
        allocations=[
            NativeAllocation(
                allocation_id=item.allocation_id,
                role=AllocationRole(item.role) if item.role else None,
                worker_session_id=item.worker_session_id,
                status=AllocationStatus(item.status),
            )
            for item in before.allocations
        ],
        epochs=EpochSnapshot(
            implementation_content=before.epochs.implementation_content,
            documentation=before.epochs.documentation,
            git_metadata=before.epochs.git_metadata,
        ),
        evidence_refs=[native_ref],
    )
    comparison = service.workflow_reconcile(
        native, expected_revision=before.revision, idempotency_key="native-retain-compare"
    )
    assert comparison.status == "conflict"
    transition = native_resolution_request(
        service,
        comparison.reconcile_id,
        choice="retain_sqlite_pair",
        native_revision=native.revision,
        native_epochs={
            "implementation_content": native.epochs.implementation_content,
            "documentation": native.epochs.documentation,
            "git_metadata": native.epochs.git_metadata,
        },
        native_freshness_refs=[native_ref],
    )
    service.workflow_transition(transition)
    after = service.workflow_get_state()
    assert after.source == before.source
    assert after.semantic_references == before.semantic_references
    assert after.native_resolution_history[0].choice == "retain_sqlite_pair"
    assert after.native_resolution_history[0].native_freshness_refs == [native_ref]


def test_legacy_native_comparison_requires_fresh_v5_preimage_before_resolution(
    tmp_path: Path,
) -> None:
    from token_io_decoupling_core.state_models import (
        EpochSnapshot,
        NativeAllocation,
        NativeWorkflowSnapshot,
    )

    service, _ = setup(tmp_path)
    initial = service.workflow_get_state()
    old_ref = EvidenceRef(uri="test://native/legacy", content_hash="b" * 64)
    legacy_snapshot = NativeWorkflowSnapshot(
        project_id=initial.project_id,
        root_session_id=initial.root_session_id,
        run_id=initial.run_id,
        mode_count=initial.mode_count,
        mode_source=initial.mode_source,
        lifecycle=initial.lifecycle,
        source=ref("legacy-native-plan"),
        semantic_references=initial.semantic_references,
        revision=initial.revision,
        allocations=[
            NativeAllocation(
                allocation_id=item.allocation_id,
                role=item.role,
                worker_session_id=item.worker_session_id,
                status=item.status,
            )
            for item in initial.allocations
        ],
        epochs=EpochSnapshot(
            implementation_content=initial.epochs.implementation_content,
            documentation=initial.epochs.documentation,
            git_metadata=initial.epochs.git_metadata,
        ),
        evidence_refs=[old_ref],
    )
    conflict = service.workflow_reconcile(
        legacy_snapshot,
        expected_revision=initial.revision,
        idempotency_key="legacy-native-conflict-before-v5",
    )
    assert conflict.status == "conflict"

    binding = service._parent_binding({Cap.WORKFLOW_READ}, {Guard.PATH_BOUNDARY})
    database, trusted_root = service._root_database(binding, create=False)
    connection = sqlite3.connect(database)
    try:
        connection.execute("DROP TABLE native_reconcile_resolution_targets")
        connection.execute("DROP TABLE native_reconcile_resolutions")
        connection.execute("DROP TABLE native_reconcile_preimages")
        connection.execute("DROP TABLE native_reconcile_confirmations")
        connection.execute("ALTER TABLE workflow_control DROP COLUMN recovery_revision")
        connection.execute("DELETE FROM schema_migrations WHERE version=5")
        connection.commit()
    finally:
        connection.close()

    from token_io_decoupling_state.storage import open_database_for_authorized_write

    migrated = open_database_for_authorized_write(
        database,
        DatabaseKind.WORKFLOW,
        trusted_root=trusted_root,
        expected_identity=(binding.project_id, binding.root_session_id, None),
    )
    migrated.close()

    upgraded = service.workflow_get_state()
    old_entry = next(
        item
        for item in upgraded.unresolved_native_reconciliations
        if item.reconcile_id == conflict.reconcile_id
    )
    assert not old_entry.preimage_known
    old_transition = native_resolution_request(
        service,
        conflict.reconcile_id,
        native_revision=old_entry.native_revision,
        native_epochs={
            "implementation_content": old_entry.native_epochs.implementation_content,
            "documentation": old_entry.native_epochs.documentation,
            "git_metadata": old_entry.native_epochs.git_metadata,
        },
        native_freshness_refs=old_entry.native_refs,
    )
    before_fresh = service.workflow_get_state()
    with pytest.raises(InvalidStateTransitionError, match="no v5 Root preimage"):
        service.workflow_transition(old_transition)
    assert service.workflow_get_state().revision == before_fresh.revision

    state = service.workflow_get_state()
    fresh_ref = EvidenceRef(uri="test://native/fresh-v5", content_hash="c" * 64)
    fresh_snapshot = NativeWorkflowSnapshot(
        project_id=state.project_id,
        root_session_id=state.root_session_id,
        run_id=state.run_id,
        mode_count=state.mode_count,
        mode_source=state.mode_source,
        lifecycle=state.lifecycle,
        source=state.source,
        semantic_references=state.semantic_references,
        revision=state.revision,
        allocations=[
            NativeAllocation(
                allocation_id=item.allocation_id,
                role=item.role,
                worker_session_id=item.worker_session_id,
                status=item.status,
            )
            for item in state.allocations
        ],
        epochs=EpochSnapshot(
            implementation_content=state.epochs.implementation_content,
            documentation=state.epochs.documentation,
            git_metadata=state.epochs.git_metadata,
        ),
        evidence_refs=[fresh_ref],
    )
    fresh = service.workflow_reconcile(
        fresh_snapshot,
        expected_revision=state.revision,
        idempotency_key="fresh-v5-native-comparison",
    )
    assert fresh.status == "awaiting_confirmation"
    reviewed = service.workflow_get_state()
    assert any(
        item.reconcile_id == conflict.reconcile_id and not item.preimage_known
        for item in reviewed.unresolved_native_reconciliations
    )
    assert any(
        item.reconcile_id == fresh.reconcile_id and item.preimage_known
        for item in reviewed.unresolved_native_reconciliations
    )
    refs = [
        evidence_ref
        for item in reviewed.unresolved_native_reconciliations
        for evidence_ref in item.native_refs
    ]
    resolution = native_resolution_request(
        service,
        fresh.reconcile_id,
        native_revision=max(
            item.native_revision for item in reviewed.unresolved_native_reconciliations
        ),
        native_epochs={
            dimension: max(
                int(getattr(item.native_epochs, dimension))
                for item in reviewed.unresolved_native_reconciliations
            )
            for dimension in ("implementation_content", "documentation", "git_metadata")
        },
        native_freshness_refs=refs,
        choice="retain_sqlite_pair",
    )
    receipt = service.workflow_transition(resolution)
    assert receipt.result["resolved_comparison_count"] == 2
    assert service.workflow_get_state().native_resolution_history[0].native_freshness_refs == refs


def test_later_matching_native_snapshot_does_not_hide_older_conflict(tmp_path: Path) -> None:
    from token_io_decoupling_core.state_models import (
        EpochSnapshot,
        NativeAllocation,
        NativeReconcileTransition,
        NativeWorkflowSnapshot,
    )

    service, _ = setup(tmp_path)
    initial = service.workflow_get_state()

    def snapshot_from(state, *, source: SemanticRef, evidence_uri: str):
        return NativeWorkflowSnapshot(
            project_id=state.project_id,
            root_session_id=state.root_session_id,
            run_id=state.run_id,
            mode_count=state.mode_count,
            mode_source=state.mode_source,
            lifecycle=state.lifecycle,
            source=source,
            semantic_references=state.semantic_references,
            revision=state.revision,
            allocations=[
                NativeAllocation(
                    allocation_id=item.allocation_id,
                    role=item.role,
                    worker_session_id=item.worker_session_id,
                    status=item.status,
                )
                for item in state.allocations
            ],
            epochs=EpochSnapshot(
                implementation_content=state.epochs.implementation_content,
                documentation=state.epochs.documentation,
                git_metadata=state.epochs.git_metadata,
            ),
            evidence_refs=[EvidenceRef(uri=evidence_uri, content_hash="d" * 64)],
        )

    conflict = service.workflow_reconcile(
        snapshot_from(initial, source=ref("older-native-plan"), evidence_uri="test://older"),
        expected_revision=initial.revision,
        idempotency_key="older-native-conflict",
    )
    assert conflict.status == "conflict"
    state = service.workflow_get_state()
    canonical = snapshot_from(state, source=state.source, evidence_uri="test://current-match")
    comparison = service.workflow_reconcile(
        canonical,
        expected_revision=state.revision,
        idempotency_key="newer-matching-comparison",
    )
    assert comparison.status == "awaiting_confirmation"
    confirmed = service.workflow_transition(
        NativeReconcileTransition(
            kind="confirm_native_reconcile",
            snapshot=canonical,
            expected_revision=comparison.result_revision,
            idempotency_key="confirm-newer-matching-comparison",
        )
    )
    assert confirmed.result["status"] == "matched"

    after_match = service.workflow_get_state()
    assert after_match.latest_native_reconciliation is not None
    assert after_match.latest_native_reconciliation.status == "matched"
    canonical_id = after_match.latest_native_reconciliation.reconcile_id
    assert canonical_id != comparison.reconcile_id
    assert {item.reconcile_id for item in after_match.unresolved_native_reconciliations} == {
        conflict.reconcile_id,
    }
    assert after_match.unresolved_native_set_hash
    with pytest.raises(InvalidStateTransitionError, match="explicitly resolved"):
        service.workflow_open(request(key="cannot-open-over-conflict"))
    still_unresolved = service.workflow_get_state()
    refs_by_identity = {
        (item.uri, item.content_hash): item
        for comparison_index in [
            *still_unresolved.unresolved_native_reconciliations,
            still_unresolved.latest_native_reconciliation,
        ]
        for item in comparison_index.native_refs
    }
    refs = list(refs_by_identity.values())
    reviewed_comparisons = [
        *still_unresolved.unresolved_native_reconciliations,
        still_unresolved.latest_native_reconciliation,
    ]
    reviewed_revision = max(item.native_revision for item in reviewed_comparisons)
    native_epochs = {
        dimension: max(int(getattr(item.native_epochs, dimension)) for item in reviewed_comparisons)
        for dimension in ("implementation_content", "documentation", "git_metadata")
    }
    resolution = native_resolution_request(
        service,
        canonical_id,
        native_revision=reviewed_revision,
        native_epochs=native_epochs,
        native_freshness_refs=refs,
        choice="retain_sqlite_pair",
    )
    receipt = service.workflow_transition(resolution)
    assert receipt.result["resolved_comparison_count"] == 2
    after_resolution = service.workflow_get_state()
    assert after_resolution.unresolved_native_reconciliations == []
    assert {
        item.reconcile_id
        for item in after_resolution.native_resolution_history[0].resolved_comparisons
    } == {item.reconcile_id for item in reviewed_comparisons}


def test_native_confirmation_rejects_concurrent_root_change(tmp_path: Path) -> None:
    from token_io_decoupling_core.state_models import (
        EpochSnapshot,
        NativeAllocation,
        NativeWorkflowSnapshot,
    )

    service, _ = setup(tmp_path)
    state = service.workflow_get_state()
    snapshot = NativeWorkflowSnapshot(
        project_id=state.project_id,
        root_session_id=state.root_session_id,
        run_id=state.run_id,
        mode_count=state.mode_count,
        mode_source=state.mode_source,
        lifecycle=state.lifecycle,
        source=state.source,
        semantic_references=state.semantic_references,
        revision=state.revision,
        allocations=[
            NativeAllocation(
                allocation_id=item.allocation_id,
                role=item.role,
                worker_session_id=item.worker_session_id,
                status=item.status,
            )
            for item in state.allocations
        ],
        epochs=EpochSnapshot(implementation_content=0, documentation=0, git_metadata=0),
        evidence_refs=[EvidenceRef(uri="test://concurrent", content_hash="b" * 64)],
    )
    service.workflow_reconcile(
        snapshot, expected_revision=state.revision, idempotency_key="concurrent-compare"
    )
    changed_state = service.workflow_get_state()
    second_snapshot = snapshot.model_copy(update={"revision": changed_state.revision})
    changed = service.workflow_reconcile(
        second_snapshot,
        expected_revision=changed_state.revision,
        idempotency_key="concurrent-second-compare",
    )
    with pytest.raises(RevisionConflictError, match="Root changed"):
        service.workflow_reconcile(
            snapshot,
            confirm=True,
            expected_revision=changed.result_revision,
            idempotency_key="concurrent-confirm",
        )


def test_native_conflicts_include_source_mode_source_and_semantic_refs(tmp_path: Path) -> None:
    from token_io_decoupling_core.state_models import (
        EpochSnapshot,
        NativeAllocation,
        NativeWorkflowSnapshot,
    )

    service, _ = setup(tmp_path)
    state = service.workflow_get_state()
    snapshot = NativeWorkflowSnapshot(
        project_id=state.project_id,
        root_session_id=state.root_session_id,
        run_id=state.run_id,
        mode_count=state.mode_count,
        mode_source=state.mode_source,
        lifecycle=state.lifecycle,
        source=state.source,
        semantic_references=state.semantic_references,
        revision=state.revision,
        allocations=[
            NativeAllocation(
                allocation_id=item.allocation_id,
                role=item.role,
                worker_session_id=item.worker_session_id,
                status=item.status,
            )
            for item in state.allocations
        ],
        epochs=EpochSnapshot(implementation_content=0, documentation=0, git_metadata=0),
        evidence_refs=[EvidenceRef(uri="test://native-conflict", content_hash="a" * 64)],
    )
    variants = [
        snapshot.model_copy(update={"source": ref("different-contract")}),
        snapshot.model_copy(update={"mode_source": "default"}),
        snapshot.model_copy(update={"semantic_references": [ref("different-semantic-ref")]}),
    ]
    for index, variant in enumerate(variants):
        current = service.workflow_get_state()
        variant = variant.model_copy(update={"revision": current.revision})
        result = service.workflow_reconcile(
            variant,
            expected_revision=current.revision,
            idempotency_key=f"native-field-conflict-{index}",
        )
        assert result.status == "conflict"
        assert result.native_refs == variant.evidence_refs
        after = service.workflow_get_state()
        assert after.source == state.source
        assert after.mode_source == state.mode_source
        assert after.semantic_references == state.semantic_references


def test_single_agent_slice_is_root_owned(tmp_path: Path) -> None:
    provider = FakeBindings()
    service = StateService(
        provider, state_root=tmp_path / "state", rule_loader=source_rule_loader()
    )
    service.workflow_open(request(children=0, mode=CodingMode.SINGLE_AGENT))
    spec = SliceSpec(
        allocation_id="root",
        output_class=OutputClass.OTHER,
        objective=ref("root-objective"),
        return_conditions=ref("root-return"),
        unreleased_boundary=ref("root-boundary"),
        authorized_paths=["mcp/"],
        change_categories=[ChangeCategory.SOURCE_CODE],
        write_content_memo=False,
    )
    prime_slice(service, spec)
    receipt = service.slice_release(
        spec, expected_revision=service.workflow_get_state().revision, idempotency_key="root-slice"
    )
    assert receipt.result["allocation_id"] == "root"
    binding = service._parent_binding({Cap.WORKFLOW_READ}, {Guard.PATH_BOUNDARY})
    db, root = service._root_database(binding, create=False)
    with service._read_transaction(db, DatabaseKind.WORKFLOW, root) as connection:
        assert connection.execute("SELECT status FROM root_slices").fetchone()[0] == "released"
    active = service.workflow_get_state().active_slices[0]
    assert active.spec_hash == _slice_spec_hash(spec)
    assert active.output_class is spec.output_class
    assert active.write_content_memo is spec.write_content_memo


def test_reused_worker_dispatch_history_does_not_rewind_on_old_receipt_replay(
    tmp_path: Path,
) -> None:
    from token_io_decoupling_core.state_models import (
        AllocationRole,
        AllocationStatus,
        EpochSnapshot,
        NativeAllocation,
        NativeWorkflowSnapshot,
    )

    provider = FakeBindings()
    provider.add_child("worker-a")
    service = StateService(
        provider, state_root=tmp_path / "state", rule_loader=source_rule_loader()
    )
    service.workflow_open(request())
    allocation = service.workflow_get_state().allocations[0].allocation_id
    service.delegation_reserve("Primary Output", expected_revision=0, idempotency_key="reserve")
    spec1 = SliceSpec(
        allocation_id=allocation,
        output_class=OutputClass.CODE_CONFIGURATION,
        objective=ref("first-objective"),
        return_conditions=ref("first-return"),
        unreleased_boundary=ref("first-boundary"),
        authorized_paths=["mcp/"],
        change_categories=[ChangeCategory.SOURCE_CODE],
        write_content_memo=False,
    )
    prime_slice(service, spec1)
    service.slice_release(
        spec1,
        expected_revision=service.workflow_get_state().revision,
        idempotency_key="first-slice",
    )
    first_revision = service.workflow_get_state().revision
    first = service.delegation_bind(
        allocation, "worker-a", expected_revision=first_revision, idempotency_key="first-bind"
    )
    first_event = str(first.result["event_id"])

    provider.current = provider.parent
    prime_control_continue(service)
    spec2 = spec1.model_copy(update={"objective": ref("second-objective")})
    prime_slice(service, spec2)
    service.slice_release(
        spec2,
        expected_revision=service.workflow_get_state().revision,
        idempotency_key="second-slice",
    )
    second_revision = service.workflow_get_state().revision
    second = service.delegation_bind(
        allocation, "worker-a", expected_revision=second_revision, idempotency_key="second-bind"
    )
    second_event = str(second.result["event_id"])
    assert second_event != first_event

    current = service.workflow_get_state()
    native = NativeWorkflowSnapshot(
        project_id=current.project_id,
        root_session_id=current.root_session_id,
        run_id=current.run_id,
        mode_count=current.mode_count,
        mode_source=current.mode_source,
        lifecycle=current.lifecycle,
        source=ref("different-plan-during-reused-dispatch"),
        semantic_references=current.semantic_references,
        revision=current.revision,
        allocations=[
            NativeAllocation(
                allocation_id=item.allocation_id,
                role=AllocationRole(item.role) if item.role else None,
                worker_session_id=item.worker_session_id,
                status=AllocationStatus(item.status),
            )
            for item in current.allocations
        ],
        epochs=EpochSnapshot(
            implementation_content=current.epochs.implementation_content,
            documentation=current.epochs.documentation,
            git_metadata=current.epochs.git_metadata,
        ),
        evidence_refs=[EvidenceRef(uri="test://native/reused-dispatch", content_hash="c" * 64)],
    )
    conflict = service.workflow_reconcile(
        native, expected_revision=current.revision, idempotency_key="conflict-after-reused-dispatch"
    )
    assert conflict.status == "conflict"
    before_replay = service.workflow_get_state()
    binding = service._parent_binding({Cap.WORKFLOW_READ}, {Guard.PATH_BOUNDARY})
    root_path, trusted_root = service._root_database(binding, create=False)
    with service._read_transaction(root_path, DatabaseKind.WORKFLOW, trusted_root) as connection:
        assert (
            connection.execute(
                "SELECT 1 FROM root_outbox WHERE event_id=?", (second_event,)
            ).fetchone()
            is None
        )
    replayed = service.delegation_bind(
        allocation,
        "worker-a",
        expected_revision=second_revision,
        idempotency_key="second-bind",
    )
    assert replayed.replayed
    assert service.workflow_get_state().revision == before_replay.revision

    provider.become_worker("worker-a")
    assert service.worker_get_assignment()["event_id"] == second_event
    older = cast(dict[str, Any], service.worker_get_dispatch(first_event))
    assert older["snapshot"]["objective"]["uri"] == "test://first-objective"
    provider.current = provider.parent
    service.delegation_bind(
        allocation, "worker-a", expected_revision=first_revision, idempotency_key="first-bind"
    )
    provider.become_worker("worker-a")
    assert service.worker_get_assignment()["event_id"] == second_event


def test_service_upgrades_empty_v1_and_preserves_valid_v2_root_state(tmp_path: Path) -> None:
    provider = FakeBindings()
    service = StateService(
        provider, state_root=tmp_path / "state", rule_loader=source_rule_loader()
    )
    binding = service._parent_binding({Cap.WORKFLOW_WRITE}, {Guard.PATH_BOUNDARY})
    database, trusted_root = service._root_database(binding, create=True)
    workflow_migrations = _package_migrations(DatabaseKind.WORKFLOW)

    empty_v1 = _open_with_migrations(
        database,
        DatabaseKind.WORKFLOW,
        trusted_root=trusted_root,
        migrations=workflow_migrations[:1],
    )
    empty_v1.close()
    service.workflow_open(request())
    assert service.workflow_get_state().revision == 0

    database.unlink()
    legacy_v2 = _open_with_migrations(
        database,
        DatabaseKind.WORKFLOW,
        trusted_root=trusted_root,
        migrations=workflow_migrations[:2],
    )
    allocation_id = "legacy-allocation"
    legacy_v2.execute(
        "INSERT INTO workflow_control VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            provider.parent.project_id,
            provider.parent.root_session_id,
            "legacy-run",
            CodingMode.MULTI_AGENT.value,
            1,
            "explicit",
            "test://plan",
            "a" * 64,
            "[]",
            "running",
            10,
            "2026-10-01T00:00:00+00:00",
        ),
    )
    legacy_v2.execute(
        "INSERT INTO allocations(allocation_id,slot,role,status,created_at) "
        "VALUES (?,0,'Primary Output','reserved','2026-10-01T00:00:00+00:00')",
        (allocation_id,),
    )
    legacy_v2.execute(
        "INSERT INTO workflow_slices VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            "legacy-slice",
            allocation_id,
            OutputClass.CODE_CONFIGURATION.value,
            "test://objective",
            "b" * 64,
            "test://return",
            "c" * 64,
            "test://boundary",
            "d" * 64,
            '["mcp/"]',
            '["source_code"]',
            0,
            "released",
            9,
            "2026-10-01T00:00:00+00:00",
        ),
    )
    legacy_v2.close()

    opened = service.workflow_open(
        request().model_copy(update={"expected_revision": 10, "idempotency_key": "open-v2"})
    )
    state = service.workflow_get_state()
    assert opened.result["run_id"] == "legacy-run"
    assert state.revision == 10
    assert state.session_audit is None
    assert state.allocations[0].allocation_id == allocation_id
    assert state.allocations[0].role == "Primary Output"
    with sqlite3.connect(database) as connection:
        assert connection.execute(
            "SELECT status,created_revision FROM workflow_slices WHERE slice_id='legacy-slice'"
        ).fetchone() == ("released", 9)
        assert connection.execute("SELECT MAX(version) FROM schema_migrations").fetchone()[0] == 5


def test_service_rejects_unverifiable_and_foreign_v2_before_upgrade(tmp_path: Path) -> None:
    provider = FakeBindings()
    service = StateService(
        provider, state_root=tmp_path / "state", rule_loader=source_rule_loader()
    )
    binding = service._parent_binding({Cap.WORKFLOW_WRITE}, {Guard.PATH_BOUNDARY})
    database, trusted_root = service._root_database(binding, create=True)
    workflow_migrations = _package_migrations(DatabaseKind.WORKFLOW)

    unverifiable = _open_with_migrations(
        database,
        DatabaseKind.WORKFLOW,
        trusted_root=trusted_root,
        migrations=workflow_migrations[:2],
    )
    unverifiable.execute("INSERT INTO workflow_state VALUES ('legacy-business', '{}', 1)")
    unverifiable.close()
    with pytest.raises(BindingError, match="no verifiable logical identity"):
        service.workflow_open(request())
    with sqlite3.connect(database) as connection:
        assert connection.execute("SELECT MAX(version) FROM schema_migrations").fetchone()[0] == 2
        assert (
            connection.execute("SELECT state_key FROM workflow_state").fetchone()[0]
            == "legacy-business"
        )

    database.unlink()
    foreign = _open_with_migrations(
        database,
        DatabaseKind.WORKFLOW,
        trusted_root=trusted_root,
        migrations=workflow_migrations[:2],
    )
    foreign.execute(
        "INSERT INTO workflow_control VALUES (1, 'foreign-project', 'foreign-root', "
        "'foreign-run', ?, 1, "
        "'explicit', 'test://plan', ?, '[]', 'running', 4, '2026-10-01T00:00:00+00:00')",
        (CodingMode.MULTI_AGENT.value, "a" * 64),
    )
    foreign.execute(
        "INSERT INTO allocations(allocation_id,slot,role,status,created_at) "
        "VALUES ('foreign-allocation',0,'Primary Output','reserved','2026-10-01T00:00:00+00:00')"
    )
    foreign.close()
    with pytest.raises(BindingError, match="logical identity"):
        service.workflow_open(request())
    with sqlite3.connect(database) as connection:
        assert connection.execute("SELECT MAX(version) FROM schema_migrations").fetchone()[0] == 2
        assert connection.execute(
            "SELECT project_id,root_session_id FROM workflow_control"
        ).fetchone() == ("foreign-project", "foreign-root")


def test_service_upgrades_frozen_v2_worker_during_confirmed_dispatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    provider = FakeBindings()
    provider.add_child("worker-a")
    service = StateService(
        provider, state_root=tmp_path / "state", rule_loader=source_rule_loader()
    )
    service.workflow_open(request())
    allocation_id = service.workflow_get_state().allocations[0].allocation_id
    service.delegation_reserve(
        "Primary Output", expected_revision=0, idempotency_key="worker-v2-reserve"
    )
    spec = SliceSpec(
        allocation_id=allocation_id,
        output_class=OutputClass.CODE_CONFIGURATION,
        objective=ref("worker-v2-objective"),
        return_conditions=ref("worker-v2-return"),
        unreleased_boundary=ref("worker-v2-boundary"),
        authorized_paths=["mcp/"],
        change_categories=[ChangeCategory.SOURCE_CODE],
        write_content_memo=False,
    )
    prime_slice(service, spec)
    service.slice_release(
        spec,
        expected_revision=service.workflow_get_state().revision,
        idempotency_key="worker-v2-slice",
    )
    complete_dispatch = service._complete_worker_dispatch
    monkeypatch.setattr(service, "_complete_worker_dispatch", lambda *_args: None)
    bound = service.delegation_bind(
        allocation_id,
        "worker-a",
        expected_revision=service.workflow_get_state().revision,
        idempotency_key="worker-v2-bind",
    )
    event_id = str(bound.result["event_id"])

    root_path, trusted_root = service._root_database(provider.parent, create=False)
    with service._read_transaction(root_path, DatabaseKind.WORKFLOW, trusted_root) as connection:
        event = connection.execute(
            "SELECT payload_json,payload_hash FROM workflow_dispatch_events WHERE event_id=?",
            (event_id,),
        ).fetchone()
    payload = json.loads(event[0])
    worker_path, worker_root = service._worker_database("worker-a", provider.parent, create=True)
    worker_migrations = _package_migrations(DatabaseKind.WORKER)
    legacy = _open_with_migrations(
        worker_path,
        DatabaseKind.WORKER,
        trusted_root=worker_root,
        migrations=worker_migrations[:2],
    )
    snapshot_json = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    legacy.execute(
        "INSERT INTO assignment_snapshot VALUES (1, ?, ?)",
        (snapshot_json, payload["source_revision"]),
    )
    legacy.execute(
        "INSERT INTO worker_identity VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            payload["project_id"],
            payload["root_session_id"],
            payload["worker_session_id"],
            payload["allocation_id"],
            payload["role"],
            payload["output_class"],
            event_id,
            event[1],
            5,
            "2026-10-01T00:00:00+00:00",
        ),
    )
    legacy.execute(
        "INSERT INTO worker_inbox VALUES (?, ?, 'pending', ?, NULL)",
        (event_id, event[1], "2026-10-01T00:00:00+00:00"),
    )
    legacy.execute(
        "INSERT INTO worker_progress VALUES (?, ?, ?)",
        (
            "legacy-progress",
            json.dumps(
                {
                    "status": "in_progress",
                    "milestone": ref("legacy-milestone").model_dump(mode="json"),
                    "references": [],
                },
                sort_keys=True,
            ),
            "2026-10-01T00:00:00+00:00",
        ),
    )
    legacy.close()

    child = provider.verify_child_binding(provider.parent, "worker-a")
    complete_dispatch(provider.parent, child, event_id)
    provider.become_worker("worker-a")
    before = service.worker_get_state()
    assert before.revision == 5
    assert before.progress[0].milestone.uri == "test://legacy-milestone"
    receipt = service.worker_record_progress(
        ProgressRecord(status="reported_complete", milestone=ref("new-milestone")),
        expected_revision=before.revision,
        idempotency_key="worker-v2-progress",
    )
    after = service.worker_get_state()
    assert receipt.receipt_revision == 6
    assert after.revision == 6
    assert [item.milestone.uri for item in after.progress] == [
        "test://legacy-milestone",
        "test://new-milestone",
    ]
    with sqlite3.connect(worker_path) as connection:
        assert connection.execute("SELECT MAX(version) FROM schema_migrations").fetchone()[0] == 3
        assert connection.execute(
            "SELECT sequence,status FROM worker_dispatch_history WHERE event_id=?", (event_id,)
        ).fetchone() == (1, "confirmed")


def test_session_audit_v2_is_root_only_strict_cas_and_idempotent(tmp_path: Path) -> None:
    from pydantic import ValidationError

    provider = FakeBindings()
    service = StateService(
        provider, state_root=tmp_path / "state", rule_loader=source_rule_loader()
    )
    service.workflow_open(request(children=0, mode=CodingMode.SINGLE_AGENT))
    initial = service.workflow_get_state()
    assert initial.session_audit is None
    prompted_at = datetime(2026, 10, 24, 12, tzinfo=UTC)
    prompt = SessionAuditPrompt(
        status="pending",
        prompted_at=prompted_at,
        deadline_at=datetime(2026, 10, 24, 13, tzinfo=UTC),
        response_at=None,
        resolution="awaiting_input",
    )
    assert SessionAuditPrompt.model_validate_json(prompt.model_dump_json()) == prompt
    audit = session_audit().model_copy(update={"audit_config_prompt": prompt})
    transition = SessionAuditTransition(
        kind="session_audit",
        session_audit=audit,
        expected_revision=initial.revision,
        idempotency_key="audit-save",
    )
    receipt = service.workflow_transition(transition)
    assert receipt.receipt_revision == 1
    assert service.workflow_get_state().session_audit == audit
    replay = service.workflow_transition(transition)
    assert replay.replayed and replay.receipt_revision == receipt.receipt_revision
    assert service.workflow_get_state().revision == 1
    with pytest.raises(IdempotencyConflictError):
        service.workflow_transition(
            transition.model_copy(
                update={"session_audit": audit.model_copy(update={"audit_mode": "full"})}
            )
        )
    with pytest.raises(RevisionConflictError):
        service.workflow_transition(
            transition.model_copy(update={"idempotency_key": "audit-stale", "expected_revision": 0})
        )

    provider.become_worker("unbound-worker")
    with pytest.raises(BindingError):
        service.workflow_transition(
            transition.model_copy(
                update={"idempotency_key": "worker-audit", "expected_revision": 1}
            )
        )
    with pytest.raises(ValidationError):
        SessionAudit.model_validate({**audit.model_dump(mode="python"), "audit_mode": "unknown"})
    with pytest.raises(ValidationError):
        SessionAuditPrompt(
            status="pending",
            prompted_at=datetime(2026, 10, 24, 12),
            deadline_at=datetime(2026, 10, 24, 13),
            response_at=None,
            resolution="awaiting_input",
        )
    with pytest.raises(ValidationError):
        SessionAuditPrompt(
            status="pending",
            prompted_at=datetime(2026, 10, 24, 12, tzinfo=UTC),
            deadline_at=datetime(2026, 10, 24, 13),
            response_at=None,
            resolution="awaiting_input",
        )
    with pytest.raises(ValidationError):
        SessionAuditPrompt(
            status="answered",
            prompted_at=datetime(2026, 10, 24, 12, tzinfo=UTC),
            deadline_at=datetime(2026, 10, 24, 13, tzinfo=UTC),
            response_at=datetime(2026, 10, 24, 11, tzinfo=UTC),
            resolution="question_reply",
        )


def test_capability_snapshot_freshness_reads_and_replays_are_read_only(tmp_path: Path) -> None:
    service, provider = setup(tmp_path)
    initial = service.workflow_get_state()
    assert initial.capability_snapshot is not None
    assert initial.capability_snapshot_current is True
    binding = service._parent_binding({Cap.WORKFLOW_READ}, {Guard.PATH_BOUNDARY})
    database, _ = service._root_database(binding, create=False)

    def stored_snapshot() -> tuple[str, int, int]:
        with sqlite3.connect(database) as connection:
            row = connection.execute(
                "SELECT capability_snapshot_hash,capability_observed_revision "
                "FROM workflow_session_metadata WHERE singleton=1"
            ).fetchone()
            assert row is not None
            revision = connection.execute(
                "SELECT revision FROM workflow_control WHERE singleton=1"
            ).fetchone()[0]
            return str(row[0]), int(row[1]), int(revision)

    before = stored_snapshot()
    for _ in range(3):
        service.workflow_get_state()
    assert stored_snapshot() == before
    receipt = service.delegation_reserve(
        "Primary Output", expected_revision=0, idempotency_key="snapshot-reserve"
    )
    updated = service.workflow_get_state()
    assert updated.capability_snapshot_current is True
    assert updated.capability_snapshot is not None
    after_mutation = stored_snapshot()
    assert after_mutation[1:] == (receipt.receipt_revision, receipt.receipt_revision)

    changed = provider.parent.model_copy(
        update={"capabilities": provider.parent.capabilities | {Cap.WORKER_READ}}
    )
    provider.parent = changed
    provider.current = changed
    stale = service.workflow_get_state()
    assert stale.capability_snapshot_current is False
    replay = service.delegation_reserve(
        "Primary Output", expected_revision=0, idempotency_key="snapshot-reserve"
    )
    assert replay.replayed and replay.receipt_revision == receipt.receipt_revision
    assert stored_snapshot() == after_mutation


def test_workflow_get_state_returns_reference_only_recovery_indexes(tmp_path: Path) -> None:
    service, _ = setup(tmp_path)
    service.delegation_reserve(
        "Primary Output", expected_revision=0, idempotency_key="index-reserve"
    )
    spec = prime_slice(service)
    released = service.slice_release(
        spec,
        expected_revision=service.workflow_get_state().revision,
        idempotency_key="index-slice-release",
    )
    binding = service._parent_binding({Cap.WORKFLOW_WRITE}, {Guard.PATH_BOUNDARY})
    database, _ = service._root_database(binding, create=False)
    current_revision = service.workflow_get_state().revision
    with sqlite3.connect(database) as connection:
        connection.execute(
            "INSERT INTO checkpoint_evaluations (evaluation_id,node_id,outcome,branch,"
            "facts_hash,input_hash,rule_hash,implementation_epoch,documentation_epoch,"
            "git_metadata_epoch,basis_revision,result_revision,missing_facts_json,"
            "missing_evidence_json,slice_ids_json,evidence_request_id,created_at) "
            "VALUES ('legacy-unknown-gate','unknown_node_from_legacy','ready','done',?,?,?,"
            "0,0,0,0,?, '[]','[]','[]',NULL,'2026-10-24T00:00:00+00:00')",
            ("a" * 64, "b" * 64, "c" * 64, current_revision),
        )
    state = service.workflow_get_state()
    assert len(state.active_slices) == 1
    active = state.active_slices[0]
    assert active.slice_id == released.result["slice_id"]
    assert active.objective == spec.objective
    assert active.spec_hash == _slice_spec_hash(spec)
    assert active.write_content_memo is spec.write_content_memo
    gate = next(item for item in state.latest_gates if item.node_id == "slice")
    assert gate.rule_status == "current" and gate.epochs_current
    unknown = next(
        item for item in state.latest_gates if item.node_id == "unknown_node_from_legacy"
    )
    assert unknown.rule_status == "unknown_node" and not unknown.rule_current
    assert state.omitted_active_slice_count == 0
    assert state.omitted_gate_count == 0


def test_populated_v3_upgrade_preserves_state_indexes(tmp_path: Path) -> None:
    provider = FakeBindings()
    service = StateService(
        provider, state_root=tmp_path / "state", rule_loader=source_rule_loader()
    )
    binding = service._parent_binding({Cap.WORKFLOW_WRITE}, {Guard.PATH_BOUNDARY})
    database, trusted_root = service._root_database(binding, create=True)
    legacy = _open_with_migrations(
        database,
        DatabaseKind.WORKFLOW,
        trusted_root=trusted_root,
        migrations=_package_migrations(DatabaseKind.WORKFLOW)[:3],
    )
    legacy.execute(
        "INSERT INTO workflow_control VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            provider.parent.project_id,
            provider.parent.root_session_id,
            "v3-run",
            CodingMode.MULTI_AGENT.value,
            1,
            "explicit",
            "test://plan",
            "a" * 64,
            "[]",
            "running",
            7,
            "2026-10-01T00:00:00+00:00",
        ),
    )
    legacy.execute(
        "INSERT INTO allocations(allocation_id,slot,role,status,created_at) "
        "VALUES ('v3-allocation',0,'Primary Output','reserved','2026-10-01T00:00:00+00:00')"
    )
    legacy.execute(
        "INSERT INTO checkpoint_evidence VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            "v3-evidence",
            "contract",
            "[]",
            "[]",
            "b" * 64,
            "c" * 64,
            "[]",
            None,
            0,
            0,
            0,
            6,
            7,
            "2026-10-01T00:00:00+00:00",
        ),
    )
    legacy.execute(
        "INSERT INTO operation_receipts VALUES (?,?,?,?,?,?)",
        (
            "v3-receipt",
            "prior_operation",
            "d" * 64,
            '{"kept":true}',
            6,
            "2026-10-01T00:00:00+00:00",
        ),
    )
    legacy.close()

    service.workflow_open(
        request().model_copy(update={"expected_revision": 7, "idempotency_key": "upgrade-v3"})
    )
    state = service.workflow_get_state()
    assert state.run_id == "v3-run"
    assert state.revision == 7
    assert state.allocations[0].allocation_id == "v3-allocation"
    assert state.session_audit is None
    with sqlite3.connect(database) as connection:
        assert connection.execute(
            "SELECT evidence_id,recorded_revision FROM checkpoint_evidence"
        ).fetchall() == [("v3-evidence", 7)]
        assert connection.execute(
            "SELECT idempotency_key,result_json FROM operation_receipts "
            "WHERE idempotency_key='v3-receipt'"
        ).fetchone() == ("v3-receipt", '{"kept":true}')
        assert connection.execute("SELECT MAX(version) FROM schema_migrations").fetchone()[0] == 5


def test_v3_root_slice_hash_remains_explicitly_unknown_after_v4_upgrade(tmp_path: Path) -> None:
    provider = FakeBindings()
    service = StateService(
        provider, state_root=tmp_path / "state", rule_loader=source_rule_loader()
    )
    binding = service._parent_binding({Cap.WORKFLOW_WRITE}, {Guard.PATH_BOUNDARY})
    database, trusted_root = service._root_database(binding, create=True)
    legacy = _open_with_migrations(
        database,
        DatabaseKind.WORKFLOW,
        trusted_root=trusted_root,
        migrations=_package_migrations(DatabaseKind.WORKFLOW)[:3],
    )
    legacy.execute(
        "INSERT INTO workflow_control VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            provider.parent.project_id,
            provider.parent.root_session_id,
            "legacy-single-run",
            CodingMode.SINGLE_AGENT.value,
            0,
            "explicit",
            "test://plan",
            "a" * 64,
            "[]",
            "running",
            4,
            "2026-10-01T00:00:00+00:00",
        ),
    )
    legacy.execute(
        "INSERT INTO root_slices VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            "legacy-root-slice",
            "test://legacy-objective",
            "b" * 64,
            "test://legacy-return",
            "c" * 64,
            "test://legacy-boundary",
            "d" * 64,
            '["mcp/"]',
            '["source_code"]',
            "released",
            3,
            "2026-10-01T00:00:00+00:00",
        ),
    )
    legacy.close()

    service.workflow_open(
        request(children=0, mode=CodingMode.SINGLE_AGENT).model_copy(
            update={"expected_revision": 4, "idempotency_key": "upgrade-root-slice"}
        )
    )
    active = service.workflow_get_state().active_slices[0]
    assert active.slice_id == "legacy-root-slice"
    assert active.allocation_id == "root"
    assert active.output_class is None
    assert active.write_content_memo is None
    assert active.spec_hash is None
    assert active.spec_hash_unknown_reason == (
        "legacy Root Slice lacks persisted output_class and write_content_memo"
    )


def test_recovery_index_cursors_page_slices_and_reject_stale_native_cursor(
    tmp_path: Path,
) -> None:
    from token_io_decoupling_core.state_models import (
        EpochSnapshot,
        NativeAllocation,
        NativeWorkflowSnapshot,
        RecoveryIndexPageRequest,
    )

    service, _ = setup(tmp_path, children=33)
    allocations = service.workflow_get_state().allocations
    for index, _allocation in enumerate(allocations):
        role = "Primary Output" if index == 0 else "Change Verification"
        state = service.workflow_get_state()
        service.delegation_reserve(
            role,
            expected_revision=state.revision,
            idempotency_key=f"page-reserve-{index}",
        )

    for index, allocation in enumerate(allocations):
        spec = SliceSpec(
            allocation_id=allocation.allocation_id,
            output_class=OutputClass.CODE_CONFIGURATION,
            objective=ref(f"page-objective-{index}"),
            return_conditions=ref(f"page-return-{index}"),
            unreleased_boundary=ref(f"page-boundary-{index}"),
            authorized_paths=["mcp/"],
            change_categories=[ChangeCategory.SOURCE_CODE],
            write_content_memo=False,
        )
        prime_slice(service, spec)
        if index == 1:
            prime_control_continue(service, slice_ids=[])
            prime_slice(service, spec)
        service.slice_release(
            spec,
            expected_revision=service.workflow_get_state().revision,
            idempotency_key=f"page-slice-{index}",
        )

    first = service.workflow_get_state()
    first_ids = [item.slice_id for item in first.active_slices]
    slice_page = next(item for item in first.recovery_pages if item.collection == "active_slices")
    assert len(first_ids) == 32
    assert slice_page.total_count == 33 and slice_page.next_cursor is not None
    remainder = service.workflow_get_state(
        index_page=RecoveryIndexPageRequest(
            collection="active_slices", cursor=slice_page.next_cursor
        )
    )
    all_ids = first_ids + [item.slice_id for item in remainder.active_slices]
    assert len(all_ids) == 33 and len(set(all_ids)) == 33
    assert remainder.recovery_pages[0].next_cursor is None

    # Use a fresh Root because unresolved Native state intentionally blocks later work.
    native_service, _ = setup(tmp_path / "native")
    state = native_service.workflow_get_state()
    base = NativeWorkflowSnapshot(
        project_id=state.project_id,
        root_session_id=state.root_session_id,
        run_id=state.run_id,
        mode_count=state.mode_count,
        mode_source=state.mode_source,
        lifecycle=state.lifecycle,
        source=state.source,
        semantic_references=state.semantic_references,
        revision=state.revision,
        allocations=[
            NativeAllocation(
                allocation_id=item.allocation_id,
                role=None,
                worker_session_id=None,
                status=item.status,
            )
            for item in state.allocations
        ],
        epochs=EpochSnapshot(implementation_content=0, documentation=0, git_metadata=0),
        evidence_refs=[EvidenceRef(uri="test://native-page", content_hash="e" * 64)],
    )
    reconcile_ids = []
    for index in range(10):
        current = native_service.workflow_get_state()
        conflict = base.model_copy(
            update={
                "revision": current.revision,
                "source": ref(f"native-conflict-{index}"),
            }
        )
        result = native_service.workflow_reconcile(
            conflict,
            expected_revision=current.revision,
            idempotency_key=f"native-page-{index}",
        )
        assert result.status == "conflict"
        reconcile_ids.append(result.reconcile_id)
    native_first = native_service.workflow_get_state()
    native_page = next(
        item
        for item in native_first.recovery_pages
        if item.collection == "unresolved_native_reconciliations"
    )
    first_native_ids = [
        item.reconcile_id for item in native_first.unresolved_native_reconciliations
    ]
    assert len(first_native_ids) == 8 and native_page.next_cursor is not None
    native_rest = native_service.workflow_get_state(
        index_page=RecoveryIndexPageRequest(
            collection="unresolved_native_reconciliations",
            cursor=native_page.next_cursor,
        )
    )
    all_native_ids = first_native_ids + [
        item.reconcile_id for item in native_rest.unresolved_native_reconciliations
    ]
    assert set(all_native_ids) == set(reconcile_ids)
    assert len(all_native_ids) == len(set(all_native_ids))

    current = native_service.workflow_get_state()
    conflict = base.model_copy(
        update={"revision": current.revision, "source": ref("native-next-conflict")}
    )
    native_service.workflow_reconcile(
        conflict,
        expected_revision=current.revision,
        idempotency_key="native-page-after-cursor",
    )
    before_stale_read = native_service.workflow_get_state().revision
    with pytest.raises(StaleRecoveryCursorError, match="stale"):
        native_service.workflow_get_state(
            index_page=RecoveryIndexPageRequest(
                collection="unresolved_native_reconciliations",
                cursor=native_page.next_cursor,
            )
        )
    assert native_service.workflow_get_state().revision == before_stale_read
