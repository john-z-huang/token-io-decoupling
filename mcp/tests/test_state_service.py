from __future__ import annotations

import json
import shutil
import sqlite3
import threading
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Literal, cast

import pytest

from token_io_mcp.binding import BindingError, DenyingBindingProvider
from token_io_mcp.migrations.runner import _migration_lock
from token_io_mcp.models import CodingMode, DatabaseKind, EvidenceRef, ModeCount, SemanticRef
from token_io_mcp.rules import RuleLoader
from token_io_mcp.state_models import (
    BindingIdentity,
    ChangeCategory,
    CheckpointConfirmationTransition,
    CheckpointEvaluation,
    CheckpointFact,
    CheckpointNode,
    ControlTransitionRequest,
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
    SessionRole,
    SliceSpec,
    TypedEvidenceReference,
    VerifiedChildBinding,
    WorkflowOpenRequest,
)
from token_io_mcp.state_models import (
    HostCapability as Cap,
)
from token_io_mcp.state_models import (
    HostGuard as Guard,
)
from token_io_mcp.state_service import (
    IdempotencyConflictError,
    InvalidStateTransitionError,
    RevisionConflictError,
    StateService,
    WorkflowNotOpenError,
    _epochs_cover_changed_dimensions,
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
    service: StateService, signal: LegalBranch = LegalBranch.CONTINUE
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
    )
    if branch == "evidence-on-demand":
        assert evaluation.outcome == "evidence_on_demand"
        return evaluation
    service.workflow_transition(
        ControlTransitionRequest(
            kind="control",
            evaluation_id=evaluation.evaluation_id,
            outcome="continue",
            expected_revision=evaluation.result_revision,
            idempotency_key=f"control-continue-{evaluation.result_revision}",
            slice_ids=evaluation.slice_ids,
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
        def _write_transaction(self, path, kind, trusted_root, **kwargs):
            if self.inside_dispatch and kind is DatabaseKind.WORKFLOW:
                self.workflow_writes += 1
            if self.inside_dispatch and kind is DatabaseKind.WORKER:
                self.worker_writes += 1
            with super()._write_transaction(path, kind, trusted_root, **kwargs) as connection:
                yield connection
            if not self.interrupted and (
                boundary == "root_confirm"
                and self.inside_dispatch
                and kind is DatabaseKind.WORKFLOW
                and self.workflow_writes == 1
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


def test_required_mode_and_objective_facts_cannot_be_marked_not_applicable() -> None:
    from pydantic import ValidationError

    from token_io_mcp.state_models import FactNotApplicable

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


def test_native_reconcile_requires_confirmation_and_preserves_conflicts(tmp_path: Path) -> None:
    from token_io_mcp.state_models import (
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


def test_native_two_phase_reconcile_on_existing_root_is_revision_safe(tmp_path: Path) -> None:
    from token_io_mcp.state_models import (
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
    assert service.workflow_get_state().mode_count == actual.mode_count

    huge = altered.model_copy(update={"revision": 10_000_000})
    huge_conflict = service.workflow_reconcile(
        huge,
        expected_revision=conflict.result_revision,
        idempotency_key="huge-native-revision",
    )
    assert huge_conflict.status == "conflict"
    assert huge_conflict.result_revision == conflict.result_revision + 1


def test_native_confirmation_rejects_concurrent_root_change(tmp_path: Path) -> None:
    from token_io_mcp.state_models import (
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
    compared = service.workflow_reconcile(
        snapshot, expected_revision=state.revision, idempotency_key="concurrent-compare"
    )
    changed = service.workflow_advance_epoch(
        "git_metadata",
        expected_revision=compared.result_revision,
        idempotency_key="concurrent-epoch",
    )
    with pytest.raises(RevisionConflictError, match="Root changed"):
        service.workflow_reconcile(
            snapshot,
            confirm=True,
            expected_revision=changed.receipt_revision,
            idempotency_key="concurrent-confirm",
        )


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


def test_reused_worker_dispatch_history_does_not_rewind_on_old_receipt_replay(
    tmp_path: Path,
) -> None:
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
