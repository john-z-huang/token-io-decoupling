from __future__ import annotations

import asyncio

import pytest
from mcp.types import RequestParamsMeta
from token_io_decoupling_core.binding import BindingError
from token_io_decoupling_core.codex_context import (
    CodexCallerBoundProvider,
    parse_codex_request_context,
)
from token_io_decoupling_core.state_models import (
    BindingIdentity,
    HostCapability,
    HostGuard,
    SessionRole,
    VerifiedChildBinding,
)

from token_io_decoupling.server import create_server


def _meta(thread_id: object, session_id: object = "opaque-session") -> RequestParamsMeta:
    return {"threadId": thread_id, "sessionId": session_id, "unrelated": {"ignored": True}}


def test_parser_reads_only_required_bounded_caller_fields() -> None:
    parsed = parse_codex_request_context(
        {
            "threadId": "thread-1",
            "sessionId": "session-1",
            "clientInfo": {"name": "untrusted", "threadId": "forged"},
            "other": ["ignored"],
        }
    )
    assert parsed.thread_id == "thread-1"
    assert parsed.session_id == "session-1"


@pytest.mark.parametrize(
    "meta",
    [
        None,
        [],
        {},
        {"sessionId": "s"},
        {"threadId": "t"},
        {"threadId": 4, "sessionId": "s"},
        {"threadId": "t", "sessionId": False},
        {"threadId": "  \t", "sessionId": "s"},
        {"threadId": "t", "sessionId": "\n"},
        {"threadId": "x" * 257, "sessionId": "s"},
        {"threadId": "t", "sessionId": "s\x00"},
    ],
)
def test_parser_rejects_missing_malformed_and_unbounded_context(meta: object) -> None:
    with pytest.raises(BindingError):
        parse_codex_request_context(meta)


def test_request_scope_is_task_local_nested_and_reset_on_exit() -> None:
    class TaskLocalProvider:
        def __init__(self) -> None:
            self.bindings: dict[int, BindingIdentity] = {}

        def current_binding(self) -> BindingIdentity:
            task = asyncio.current_task()
            if task is None or id(task) not in self.bindings:
                raise BindingError("no synthetic task identity")
            return self.bindings[id(task)]

        def verify_child_binding(
            self, parent: BindingIdentity, child_session_id: str
        ) -> VerifiedChildBinding:
            del parent, child_session_id
            raise BindingError("synthetic test provider has no child")

    async def run() -> None:
        base = TaskLocalProvider()
        bound = CodexCallerBoundProvider(base)
        other_bound = CodexCallerBoundProvider(base)
        ready = 0
        both_ready = asyncio.Event()

        async def observe(thread_id: str) -> str:
            nonlocal ready
            task = asyncio.current_task()
            assert task is not None
            identity = BindingIdentity(
                project_id=f"project-{thread_id}",
                root_session_id=thread_id,
                current_session_id=thread_id,
                role=SessionRole.PARENT,
                capabilities=frozenset(HostCapability),
                guards=frozenset(HostGuard),
            )
            base.bindings[id(task)] = identity
            with bound.request_scope(_meta(thread_id)):
                ready += 1
                if ready == 2:
                    both_ready.set()
                await both_ready.wait()
                assert bound.current_binding() == identity
                with pytest.raises(BindingError, match="unavailable or mismatched"):
                    other_bound.current_binding()
                return bound.current_binding().current_session_id

        observed = await asyncio.gather(observe("task-a"), observe("task-b"))
        assert set(observed) == {"task-a", "task-b"}

        task = asyncio.current_task()
        assert task is not None
        base.bindings[id(task)] = BindingIdentity(
            project_id="project-normal",
            root_session_id="normal",
            current_session_id="normal",
            role=SessionRole.PARENT,
            capabilities=frozenset(HostCapability),
            guards=frozenset(HostGuard),
        )
        with pytest.raises(BindingError, match="unavailable or mismatched"):
            bound.current_binding()
        with pytest.raises(RuntimeError, match="scope failure"):
            with bound.request_scope(_meta("normal")):
                raise RuntimeError("scope failure")
        with pytest.raises(BindingError, match="unavailable or mismatched"):
            bound.current_binding()

    asyncio.run(run())


def test_unbound_server_cannot_enable_codex_context() -> None:
    with pytest.raises(BindingError, match="usable bound identity"):
        create_server(require_codex_context=True)
