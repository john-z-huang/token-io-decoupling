from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any, cast

import pytest
from mcp import Client
from mcp.types import RequestParamsMeta, TextContent

from token_io_mcp.binding import BindingError
from token_io_mcp.codex_context import CodexCallerBoundProvider, parse_codex_request_context
from token_io_mcp.server import create_server
from token_io_mcp.state_models import (
    BindingIdentity,
    HostCapability,
    HostGuard,
    SessionRole,
    VerifiedChildBinding,
)


class SyntheticContextProvider:
    """Synthetic identity for SDK metadata tests, not a production host assertion."""

    def __init__(self) -> None:
        self.binding = BindingIdentity(
            project_id="codex-context-test-project",
            root_session_id="codex-context-test-thread",
            current_session_id="codex-context-test-thread",
            role=SessionRole.PARENT,
            capabilities=frozenset(HostCapability),
            guards=frozenset(HostGuard),
        )

    def current_binding(self) -> BindingIdentity:
        return self.binding

    def verify_child_binding(
        self, parent: BindingIdentity, child_session_id: str
    ) -> VerifiedChildBinding:
        del parent, child_session_id
        raise BindingError("synthetic test provider has no child")


def _text(result: Any) -> str:
    return cast(TextContent, result.content[0]).text or ""


def _meta(thread_id: object, session_id: object = "opaque-session") -> RequestParamsMeta:
    return {"threadId": thread_id, "sessionId": session_id, "unrelated": {"ignored": True}}


def _open_arguments() -> dict[str, object]:
    return {
        "payload": {
            "mode_count": {"mode": "Multi-Agent Coding", "child_count": 1},
            "mode_source": "explicit",
            "source": {"uri": "memory://codex-contract", "content_hash": "a" * 64},
            "semantic_references": [],
            "expected_revision": 0,
            "idempotency_key": "codex-context-open",
        }
    }


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


def test_real_sdk_meta_guards_protected_tools_and_is_request_scoped(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    provider = SyntheticContextProvider()
    server = create_server(
        provider,
        require_codex_context=True,
        state_root=tmp_path / "state",
    )
    schemas = {tool.name: tool.parameters for tool in server._tool_manager.list_tools()}
    assert "context" not in str(schemas["workflow_open"])
    assert schemas["database_schema_status"]["properties"] == {}

    async def run() -> None:
        async with Client(server, mode="auto") as client:
            public = await client.call_tool("workflow_capabilities", {})
            assert not public.is_error
            assert json.loads(_text(public))["caller_match"] == "required"
            rules = await client.call_tool(
                "rules_get_context", {"payload": {"node_id": "contract", "language": "en"}}
            )
            assert not rules.is_error

            wrong_open = await client.call_tool(
                "workflow_open",
                _open_arguments(),
                meta=_meta("wrong-thread"),
            )
            assert wrong_open.is_error
            assert "Codex caller context" in _text(wrong_open)
            assert not (tmp_path / "state").exists()
            monkeypatch.setenv("CODEX_THREAD_ID", "codex-context-test-thread")
            forged_payload = _open_arguments()
            forged_payload["threadId"] = "codex-context-test-thread"
            forged = await client.call_tool(
                "workflow_open",
                forged_payload,
                meta=_meta("wrong-thread"),
            )
            assert forged.is_error
            assert not (tmp_path / "state").exists()

            opened = await client.call_tool(
                "workflow_open",
                _open_arguments(),
                meta=_meta("codex-context-test-thread", "opaque-session-a"),
            )
            assert not opened.is_error

            missing = await client.call_tool("workflow_get_state", {"payload": {}})
            assert missing.is_error
            malformed = await client.call_tool(
                "database_schema_status", {}, meta=_meta("codex-context-test-thread", 7)
            )
            assert malformed.is_error
            mismatched_status = await client.call_tool(
                "database_schema_status", {}, meta=_meta("wrong-thread")
            )
            assert mismatched_status.is_error
            assert "Codex caller context" in _text(mismatched_status)

            mismatched = await client.call_tool(
                "workflow_get_state",
                {"payload": {}},
                meta=_meta("wrong-thread", "opaque-session-b"),
            )
            assert mismatched.is_error

            ok_status = await client.call_tool(
                "database_schema_status",
                {},
                meta=_meta("codex-context-test-thread", "opaque-session-c"),
            )
            assert not ok_status.is_error

            async def read_with(meta: RequestParamsMeta):
                return await client.call_tool("workflow_get_state", {"payload": {}}, meta=meta)

            concurrent = await asyncio.gather(
                read_with(_meta("codex-context-test-thread", "opaque-session-e")),
                read_with(_meta("wrong-thread", "opaque-session-f")),
            )
            assert not concurrent[0].is_error
            assert concurrent[1].is_error
            final_state = await read_with(_meta("codex-context-test-thread", "opaque-session-g"))
            assert not final_state.is_error
            assert json.loads(_text(final_state))["revision"] == 0

    asyncio.run(run())


def test_request_scope_rechecks_provider_identity_before_state_access(tmp_path: Path) -> None:
    class ChangingProvider(SyntheticContextProvider):
        reads = 0

        def current_binding(self) -> BindingIdentity:
            self.reads += 1
            if self.reads >= 3:
                return self.binding.model_copy(
                    update={
                        "root_session_id": "other-thread",
                        "current_session_id": "other-thread",
                    }
                )
            return self.binding

    provider = ChangingProvider()
    state_root = tmp_path / "changing-provider-state"
    server = create_server(
        provider,
        require_codex_context=True,
        state_root=state_root,
    )

    async def run() -> None:
        async with Client(server, mode="auto") as client:
            result = await client.call_tool(
                "workflow_open",
                _open_arguments(),
                meta=_meta("codex-context-test-thread"),
            )
            assert result.is_error
            assert not state_root.exists()

    asyncio.run(run())


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
