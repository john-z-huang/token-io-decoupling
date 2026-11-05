"""Real local request scoping and state lifecycle, without a host/provider fixture."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from mcp import Client
from token_io_decoupling_core.binding import BindingError
from token_io_decoupling_core.models import CodingMode, EvidenceRef, ModeCount, SemanticRef
from token_io_decoupling_core.rules import RuleLoader
from token_io_decoupling_core.state_models import (
    ChangeCategory,
    CheckpointFact,
    CheckpointNode,
    EvidenceKind,
    EvidenceSubmission,
    FactDetermined,
    FactKey,
    OutputClass,
    ReferenceFactValue,
    SessionRole,
    SliceSpec,
    TypedEvidenceReference,
    WorkflowOpenRequest,
)
from token_io_decoupling_state.local_context import LocalSessionContext
from token_io_decoupling_state.service import StateService
from token_io_decoupling_state.state.errors import WorkflowNotOpenError

from token_io_decoupling.server import create_server


def prepared(tmp_path):
    state_root = tmp_path / "state"
    provider = LocalSessionContext(tmp_path / "project", state_root)
    service = StateService(
        provider,
        state_root=state_root,
        rule_loader=RuleLoader(repository_root=Path(__file__).parents[3]),
    )
    with provider.request_scope(meta("root-session")):
        service.workflow_open(
            WorkflowOpenRequest(
                mode_count=ModeCount(mode=CodingMode.MULTI_AGENT, child_count=1),
                mode_source="explicit",
                source=SemanticRef(uri="memory://stdio-contract", content_hash="a" * 64),
                idempotency_key="stdio-setup-open",
            )
        )
        allocation = service.workflow_get_state().allocations[0].allocation_id
        service.delegation_reserve(
            "Primary Output", expected_revision=0, idempotency_key="stdio-setup-reserve"
        )
        objective = SemanticRef(uri="memory://stdio-objective", content_hash="b" * 64)
        return_conditions = SemanticRef(uri="memory://stdio-return", content_hash="c" * 64)
        boundary = SemanticRef(uri="memory://stdio-boundary", content_hash="d" * 64)
        spec = SliceSpec(
            allocation_id=allocation,
            output_class=OutputClass.CODE_CONFIGURATION,
            objective=objective,
            return_conditions=return_conditions,
            unreleased_boundary=boundary,
            authorized_paths=["src/"],
            change_categories=[ChangeCategory.SOURCE_CODE],
            write_content_memo=False,
        )
        input_hash = service.slice_check(spec).input_hash

        def fact(key: FactKey, value: SemanticRef) -> CheckpointFact:
            return CheckpointFact(
                fact_key=key,
                judgment=FactDetermined(
                    status="determined",
                    value=ReferenceFactValue(kind="semantic_ref", value=value),
                ),
            )

        service.workflow_record_evidence(
            EvidenceSubmission(
                node_id=CheckpointNode.SLICE,
                facts=[
                    fact(FactKey.SLICE_OBJECTIVE, objective),
                    fact(
                        FactKey.SLICE_AUTHORIZED_SCOPE,
                        SemanticRef(uri=f"slice://{input_hash}", content_hash="e" * 64),
                    ),
                    fact(FactKey.RETURN_CONDITIONS, return_conditions),
                    fact(FactKey.UNRELEASED_BOUNDARY, boundary),
                ],
                evidence_refs=[
                    TypedEvidenceReference(
                        kind=EvidenceKind.PARENT_SLICE_RELEASE,
                        reference=EvidenceRef(uri="test://stdio-slice", content_hash="f" * 64),
                    )
                ],
                input_hash=input_hash,
            ),
            expected_revision=1,
            idempotency_key="stdio-setup-evidence",
        )
        service.workflow_evaluate(
            CheckpointNode.SLICE,
            branch="released",
            input_hash=input_hash,
            expected_revision=2,
            idempotency_key="stdio-setup-evaluate",
        )
        service.slice_release(spec, expected_revision=3, idempotency_key="stdio-setup-release")
        service.delegation_bind(
            allocation,
            "stdio-test-worker",
            expected_revision=4,
            idempotency_key="stdio-setup-bind",
        )

    return provider, service


def meta(thread, session="opaque-session"):
    return {"threadId": thread, "sessionId": session}


def test_real_local_root_worker_lifecycle_and_role_boundaries(tmp_path):
    provider, service = prepared(tmp_path)
    with pytest.raises(BindingError):
        provider.current_binding()
    with provider.request_scope(meta("stdio-test-worker")):
        assert provider.current_binding().role is SessionRole.WORKER
        assignment = service.worker_get_assignment()
        assert assignment is not None
        with pytest.raises(BindingError):
            service.workflow_get_state()
    with provider.request_scope(meta("root-session", "changed-opaque-session")):
        assert service.workflow_get_state().root_session_id == "root-session"
        assert service.parent_get_worker_summary(
            service.workflow_get_state().allocations[0].allocation_id
        )
        with pytest.raises(BindingError):
            service.worker_get_assignment()
        with pytest.raises(BindingError):
            provider.verify_child_binding(provider.current_binding(), "root-session")
    with provider.request_scope(meta("other-root")):
        with pytest.raises(WorkflowNotOpenError):
            service.workflow_get_state()
        with pytest.raises(BindingError):
            provider.verify_child_binding(provider.current_binding(), "stdio-test-worker")
    other = LocalSessionContext(tmp_path / "another-project", tmp_path / "state")
    with other.request_scope(meta("stdio-test-worker")):
        assert other.current_binding().role is SessionRole.PARENT
        assert other.project_id != provider.project_id


@pytest.mark.parametrize(
    "metadata",
    [
        None,
        {},
        {"threadId": "../escape", "sessionId": "s"},
        {"threadId": "root"},
        {"threadId": "root", "sessionId": "\x00"},
    ],
)
def test_missing_and_unsafe_context_has_no_filesystem_effect(tmp_path, metadata):
    provider = LocalSessionContext(tmp_path, tmp_path / "untouched")
    with pytest.raises(BindingError), provider.request_scope(metadata):
        provider.current_binding()
    assert not (tmp_path / "untouched").exists()


def test_worker_mapping_rechecks_symlinks_and_current_allocation(tmp_path):
    provider, service = prepared(tmp_path)
    worker = (
        tmp_path
        / "state"
        / provider.project_id
        / "root-session"
        / "subagents"
        / "stdio-test-worker"
    )
    original = worker.with_name("saved-worker")
    worker.rename(original)
    worker.symlink_to(original, target_is_directory=True)
    with provider.request_scope(meta("stdio-test-worker")), pytest.raises(BindingError):
        service.worker_get_assignment()


def test_standard_named_server_opens_state_using_only_mcp_metadata(tmp_path):
    server = create_server(profile="root", state_root=tmp_path / "state")
    payload = {
        "payload": {
            "mode_count": {"mode": "Single-Agent Coding", "child_count": 0},
            "mode_source": "explicit",
            "source": {"uri": "test://local", "content_hash": "a" * 64},
            "expected_revision": 0,
            "idempotency_key": "open",
        }
    }

    async def run():
        async with Client(server, mode="auto") as client:
            denied = await client.call_tool("workflow_open", payload)
            assert denied.is_error
            assert not (tmp_path / "state").exists()
            opened = await client.call_tool("workflow_open", payload, meta=meta("real-local-root"))
            assert not opened.is_error

    asyncio.run(run())


def test_missing_worker_database_does_not_promote_worker_to_root(tmp_path):
    provider, _service = prepared(tmp_path)
    worker = (
        tmp_path
        / "state"
        / provider.project_id
        / "root-session"
        / "subagents"
        / "stdio-test-worker"
        / "worker.sqlite3"
    )
    worker.unlink()
    with provider.request_scope(meta("stdio-test-worker")), pytest.raises(BindingError):
        provider.current_binding()


def test_concurrent_request_scopes_do_not_leak(tmp_path):
    provider = LocalSessionContext(tmp_path, tmp_path / "state")

    async def read(thread):
        with provider.request_scope(meta(thread)):
            await asyncio.sleep(0)
            return provider.current_binding().current_session_id

    async def run():
        assert await asyncio.gather(read("first"), read("second")) == ["first", "second"]

    asyncio.run(run())
