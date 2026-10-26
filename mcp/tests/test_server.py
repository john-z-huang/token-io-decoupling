from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Any, cast

import pytest
from mcp import Client, StdioServerParameters
from mcp.server import MCPServer
from mcp.types import TextContent
from token_io_decoupling_core.binding import BindingError
from token_io_decoupling_core.models import CodingMode, EvidenceRef, ModeCount, SemanticRef
from token_io_decoupling_core.project_identity import (
    ProjectIdentityError,
    project_id_from_git_common_dir,
)
from token_io_decoupling_core.rules import RuleLoader
from token_io_decoupling_core.state_models import (
    BindingIdentity,
    ChangeCategory,
    CheckpointFact,
    CheckpointNode,
    EvidenceKind,
    EvidenceSubmission,
    FactDetermined,
    FactKey,
    HostCapability,
    HostGuard,
    OutputClass,
    ReferenceFactValue,
    SessionRole,
    SliceSpec,
    TypedEvidenceReference,
    VerifiedChildBinding,
    WorkflowOpenRequest,
)
from token_io_decoupling_state.service import StateService

from token_io_decoupling.server import create_server

PUBLIC_TOOLS = {
    "workflow_capabilities",
    "rules_get_context",
    "database_schema_status",
}
ROOT_TOOLS = {
    "workflow_open",
    "workflow_get_state",
    "delegation_reserve",
    "delegation_bind",
    "slice_check",
    "slice_release",
    "workflow_evaluate",
    "evaluate_control_checkpoint",
    "workflow_record_evidence",
    "workflow_transition",
    "parent_get_worker_summary",
    "workflow_reconcile",
}
WORKER_TOOLS = {
    "worker_get_assignment",
    "worker_get_state",
    "worker_record_progress",
    "worker_record_evidence",
    "worker_get_evidence",
    "worker_report_blocker",
    "worker_get_recovery_context",
}


class FakeBindingProvider:
    """Explicit test identity only; it is not an OS or real-host assertion."""

    def __init__(self, role: SessionRole = SessionRole.PARENT) -> None:
        self.revoked = False
        self.children: dict[str, VerifiedChildBinding] = {}
        self.binding = BindingIdentity(
            project_id="test-project",
            root_session_id="root-session",
            current_session_id=("worker-a" if role is SessionRole.WORKER else "root-session"),
            role=role,
            capabilities=frozenset(HostCapability),
            guards=frozenset(HostGuard),
            parent_session_id=("root-session" if role is SessionRole.WORKER else None),
        )

    def current_binding(self) -> BindingIdentity:
        if self.revoked:
            raise BindingError("test binding revoked")
        return self.binding

    def verify_child_binding(
        self, parent: BindingIdentity, child_session_id: str
    ) -> VerifiedChildBinding:
        child = self.children.get(child_session_id)
        if child is None:
            raise BindingError("test provider has no verified child")
        return child

    def add_child(self, child_session_id: str) -> None:
        self.children[child_session_id] = VerifiedChildBinding(
            project_id="test-project",
            root_session_id="root-session",
            parent_session_id="root-session",
            child_session_id=child_session_id,
            capabilities=frozenset(HostCapability),
            guards=frozenset(HostGuard),
        )

    def become_worker(self, child_session_id: str) -> None:
        self.binding = BindingIdentity(
            project_id="test-project",
            root_session_id="root-session",
            current_session_id=child_session_id,
            role=SessionRole.WORKER,
            parent_session_id="root-session",
            capabilities=frozenset(HostCapability),
            guards=frozenset(HostGuard),
        )


class RequestMetaClient:
    """Test SDK proxy that sends caller context in protocol `_meta`, not arguments."""

    def __init__(self, client: Any, thread_id: str) -> None:
        self._client = client
        self._thread_id = thread_id

    def __getattr__(self, name: str) -> Any:
        return getattr(self._client, name)

    async def call_tool(
        self,
        name: str,
        arguments: dict[str, Any] | None = None,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        kwargs["meta"] = {
            "threadId": self._thread_id,
            "sessionId": f"synthetic-session-{self._thread_id}",
        }
        return await self._client.call_tool(name, arguments, *args, **kwargs)


def _tool_names(server: MCPServer[Any]) -> set[str]:
    return {tool.name for tool in server._tool_manager.list_tools()}


def _result_text(result: Any) -> str:
    return cast(TextContent, result.content[0]).text


def test_tool_inventory_is_exact_and_default_server_is_public_only() -> None:
    unbound = create_server()
    listed_tools = unbound._tool_manager.list_tools()
    assert len(listed_tools) == len({tool.name for tool in listed_tools})
    assert _tool_names(unbound) == PUBLIC_TOOLS
    parameters: dict[str, Any] = {
        tool.name: tool.parameters for tool in unbound._tool_manager.list_tools()
    }
    assert parameters["database_schema_status"]["properties"] == {}
    assert "path" not in str(parameters)
    capabilities = asyncio.run(_call(unbound, "workflow_capabilities", {}))
    assert capabilities["host_adapters"]["Codex Desktop"]["identity_attestation"] == "unavailable"
    assert capabilities["host_adapters"]["ChatGPT Desktop"]["guard_binding"] == "unavailable"
    assert capabilities["mode_fallback"] == "Native"

    root_tools = _tool_names(
        create_server(FakeBindingProvider(), state_root=Path("/private/tmp/never-used"))
    )
    worker_tools = _tool_names(create_server(FakeBindingProvider(SessionRole.WORKER)))
    assert root_tools == PUBLIC_TOOLS | ROOT_TOOLS
    assert worker_tools == PUBLIC_TOOLS | WORKER_TOOLS
    assert len(root_tools) == 15
    assert len(worker_tools) == 10
    assert len(root_tools | worker_tools) == 22
    for tool in create_server(FakeBindingProvider())._tool_manager.list_tools():
        assert not any(
            forbidden in str(tool.parameters).casefold()
            for forbidden in ("database_path", "state_root", "sql_query", "shell")
        )
    worker_server = create_server(FakeBindingProvider(SessionRole.WORKER))
    worker_parameters = {
        tool.name: tool.parameters for tool in worker_server._tool_manager.list_tools()
    }
    assert worker_parameters["worker_get_assignment"]["properties"] == {}
    insufficient = FakeBindingProvider()
    insufficient.binding = insufficient.binding.model_copy(
        update={"guards": frozenset({HostGuard.IDENTITY_BOUND, HostGuard.SESSION_BOUND})}
    )
    assert _tool_names(create_server(insufficient)) == PUBLIC_TOOLS


def test_profiles_have_fixed_disjoint_inventories_and_fail_closed() -> None:
    expected = {
        "workflow": {
            "workflow_capabilities",
            "rules_get_context",
            "workflow_evaluate",
            "evaluate_control_checkpoint",
        },
        "root": {
            "workflow_open",
            "delegation_reserve",
            "delegation_bind",
            "slice_check",
            "slice_release",
            "workflow_transition",
            "parent_get_worker_summary",
            "workflow_reconcile",
        },
        "worker": {
            "worker_get_assignment",
            "worker_record_progress",
            "worker_get_evidence",
            "worker_report_blocker",
            "worker_get_recovery_context",
        },
        "share": {"database_schema_status", "state_get", "record_evidence"},
    }
    servers = {name: create_server(profile=name) for name in expected}
    inventories = {name: _tool_names(server) for name, server in servers.items()}
    assert inventories == expected
    assert all(
        inventories[left].isdisjoint(inventories[right])
        for left in expected
        for right in expected
        if left != right
    )

    async def denied() -> None:
        async with Client(servers["workflow"], mode="auto") as client:
            capabilities = await client.call_tool("workflow_capabilities", {})
            assert not capabilities.is_error
            rules = await client.call_tool(
                "rules_get_context", {"payload": {"node_id": "contract", "language": "en"}}
            )
            assert not rules.is_error
        for profile, tool, payload in (
            ("root", "workflow_transition", {"payload": {"request": {}}}),
            ("worker", "worker_get_assignment", {}),
            ("share", "state_get", {"payload": {}}),
        ):
            async with Client(servers[profile], mode="auto") as client:
                result = await client.call_tool(tool, payload)
                assert result.is_error
        async with Client(servers["share"], mode="auto") as client:
            diagnostics = await client.call_tool("database_schema_status", {})
            assert not diagnostics.is_error
            assert '"available": false' in _result_text(diagnostics)
            assert "no state path was inspected" in _result_text(diagnostics)

    asyncio.run(denied())


def test_server_discovery_and_tool_metadata_for_each_profile() -> None:
    expected = {
        "workflow": {
            "workflow_capabilities",
            "rules_get_context",
            "workflow_evaluate",
            "evaluate_control_checkpoint",
        },
        "root": {
            "workflow_open",
            "delegation_reserve",
            "delegation_bind",
            "slice_check",
            "slice_release",
            "workflow_transition",
            "parent_get_worker_summary",
            "workflow_reconcile",
        },
        "worker": {
            "worker_get_assignment",
            "worker_record_progress",
            "worker_get_evidence",
            "worker_report_blocker",
            "worker_get_recovery_context",
        },
        "share": {"database_schema_status", "state_get", "record_evidence"},
    }

    async def check_profile(profile: str, mode: str) -> None:
        server = create_server(profile=profile)
        async with Client(server, mode=mode) as client:
            assert client.protocol_version == ("2026-07-28" if mode == "auto" else "2025-11-25")
            assert client.server_info is not None
            assert client.server_info.description
            assert client.instructions
            assert profile in client.instructions
            listed = await client.list_tools()
            by_name = {tool.name: tool for tool in listed.tools}
            assert set(by_name) == expected[profile]
            assert all(tool.description for tool in by_name.values())
            # Check the public wire schema itself, not the SDK's internal tool model.
            if "workflow_capabilities" in by_name:
                assert by_name["workflow_capabilities"].input_schema["properties"] == {}
            if "state_get" in by_name:
                assert "payload" in by_name["state_get"].input_schema["properties"]

    async def run() -> None:
        for profile in expected:
            await check_profile(profile, "auto")
            await check_profile(profile, "legacy")

    asyncio.run(run())


def test_default_and_embedded_discovery_metadata_matches_bound_role() -> None:
    scenarios = {
        "public": (None, PUBLIC_TOOLS),
        "parent": (FakeBindingProvider(SessionRole.PARENT), PUBLIC_TOOLS | ROOT_TOOLS),
        "worker": (FakeBindingProvider(SessionRole.WORKER), PUBLIC_TOOLS | WORKER_TOOLS),
    }

    async def run() -> None:
        for role, (provider, expected_tools) in scenarios.items():
            async with Client(create_server(provider), mode="auto") as client:
                assert client.server_info is not None
                expected_role_label = "public-only" if role == "public" else role
                assert expected_role_label in (client.instructions or "").casefold()
                tool_list = await client.list_tools()
                assert {tool.name for tool in tool_list.tools} == expected_tools
                assert all(tool.description for tool in tool_list.tools)
                if role == "parent":
                    assert "No Worker operations" in (client.instructions or "")
                elif role == "worker":
                    assert "No parent operations" in (client.instructions or "")

    asyncio.run(run())


def test_profile_role_and_revocation_are_rechecked_per_call(tmp_path: Path) -> None:
    provider = FakeBindingProvider(SessionRole.PARENT)
    state_root = tmp_path / "profile-state"
    server = create_server(provider, profile="root", state_root=state_root)
    expected = {
        "workflow_open",
        "delegation_reserve",
        "delegation_bind",
        "slice_check",
        "slice_release",
        "workflow_transition",
        "parent_get_worker_summary",
        "workflow_reconcile",
    }
    assert _tool_names(server) == expected
    wrong_worker_profile = create_server(FakeBindingProvider(SessionRole.PARENT), profile="worker")

    open_payload = {
        "payload": {
            "mode_count": {"mode": CodingMode.MULTI_AGENT.value, "child_count": 1},
            "mode_source": "explicit",
            "source": {"uri": "memory://profile-contract", "content_hash": "a" * 64},
            "semantic_references": [],
            "expected_revision": 0,
            "idempotency_key": "profile-root-open",
        }
    }

    async def run() -> None:
        async with Client(wrong_worker_profile, mode="auto") as worker_client:
            denied_worker = await worker_client.call_tool("worker_get_assignment", {})
            assert denied_worker.is_error
            assert "binding" in _result_text(denied_worker).casefold()
        async with Client(server, mode="auto") as client:
            opened = await client.call_tool("workflow_open", open_payload)
            assert not opened.is_error
            share = create_server(provider, profile="share", state_root=state_root)
            async with Client(share, mode="auto") as share_client:
                current = await share_client.call_tool("state_get", {"payload": {}})
                assert not current.is_error
                assert '"revision": 0' in _result_text(current)
                recorded = await share_client.call_tool(
                    "record_evidence",
                    {
                        "payload": {
                            "submission": {
                                "node_id": "contract",
                                "facts": [
                                    {
                                        "fact_key": key,
                                        "judgment": {
                                            "status": "determined",
                                            "value": {
                                                "kind": "semantic_ref",
                                                "value": {
                                                    "uri": f"memory://{uri}",
                                                    "content_hash": "b" * 64,
                                                },
                                            },
                                        },
                                    }
                                    for key, uri in [
                                        ("task objective", "profile-objective"),
                                        ("authorized scope", "profile-scope"),
                                        ("constraints", "profile-constraints"),
                                        ("acceptance conditions", "profile-acceptance"),
                                    ]
                                ],
                                "evidence_refs": [],
                                "coverage_dimensions": [],
                                "input_hash": "c" * 64,
                            },
                            "expected_revision": 0,
                            "idempotency_key": "profile-root-evidence",
                        }
                    },
                )
                assert not recorded.is_error
                assert "evidence_id" in _result_text(recorded)
            provider.become_worker("worker-a")
            changed_role = await client.call_tool("workflow_open", open_payload)
            assert changed_role.is_error
            assert "binding" in _result_text(changed_role)
            provider.binding = provider.binding.model_copy(
                update={
                    "role": SessionRole.PARENT,
                    "current_session_id": "root-session",
                    "parent_session_id": None,
                }
            )
            before_revoked_call = {
                path.relative_to(state_root): (path.stat().st_size, path.stat().st_mtime_ns)
                for path in state_root.rglob("*")
                if path.is_file()
            }
            provider.revoked = True
            result = await client.call_tool("workflow_open", open_payload)
            assert result.is_error
            assert "binding" in _result_text(result)
            after_revoked_call = {
                path.relative_to(state_root): (path.stat().st_size, path.stat().st_mtime_ns)
                for path in state_root.rglob("*")
                if path.is_file()
            }
            assert after_revoked_call == before_revoked_call
            provider.revoked = False
            async with Client(share, mode="auto") as share_client:
                unchanged = await share_client.call_tool("state_get", {"payload": {}})
                assert not unchanged.is_error
                assert '"revision": 1' in _result_text(unchanged)

    asyncio.run(run())


async def _call(server: MCPServer[Any], name: str, arguments: dict[str, object]) -> dict[str, Any]:
    async with Client(server, mode="auto") as client:
        result = await client.call_tool(name, arguments)
        assert not result.is_error
        assert result.content
        return json.loads(cast(TextContent, result.content[0]).text or "{}")


def test_real_stdio_sdk_discovery_and_public_wire_calls_are_fail_closed(tmp_path: Path) -> None:
    async def run() -> None:
        parameters = StdioServerParameters(
            command=sys.executable,
            args=["-m", "token_io_decoupling.cli"],
            cwd=Path(__file__).parents[1],
            env={"PYTHONDONTWRITEBYTECODE": "1"},
        )
        async with Client(parameters, mode="auto") as client:
            assert client.protocol_version == "2026-07-28"
            result = await client.list_tools()
            assert {tool.name for tool in result.tools} == PUBLIC_TOOLS
            context = await client.call_tool(
                "rules_get_context",
                {"payload": {"node_id": "contract", "language": "zh_cn"}},
            )
            assert not context.is_error
            assert '"language": "zh_cn"' in _result_text(context)
            diagnostics = await client.call_tool("database_schema_status", {})
            assert not diagnostics.is_error
            assert '"available": false' in _result_text(diagnostics)
            assert "no state path was inspected" in _result_text(diagnostics)
            extra = await client.call_tool(
                "rules_get_context",
                {"payload": {"node_id": "contract", "language": "en", "path": "/tmp"}},
            )
            assert extra.is_error

    asyncio.run(run())


def test_bound_wire_parses_enum_json_and_revocation_is_checked_per_call(tmp_path: Path) -> None:
    async def run() -> None:
        provider = FakeBindingProvider()
        async with Client(create_server(provider, state_root=tmp_path), mode="auto") as client:
            assert client.protocol_version == "2026-07-28"
            opened = await client.call_tool(
                "workflow_open",
                {
                    "payload": {
                        "mode_count": {
                            "mode": CodingMode.MULTI_AGENT.value,
                            "child_count": 1,
                        },
                        "mode_source": "explicit",
                        "source": {"uri": "memory://contract", "content_hash": "a" * 64},
                        "semantic_references": [],
                        "expected_revision": 0,
                        "idempotency_key": "wire-open",
                    }
                },
            )
            assert not opened.is_error
            assert '"revision": 0' in _result_text(opened)
            audit = await client.call_tool(
                "workflow_transition",
                {
                    "payload": {
                        "request": {
                            "kind": "session_audit",
                            "session_audit": {
                                "audit_mode": "balanced",
                                "root_reasoning_cadence": "milestone_only",
                                "worker_reasoning_cadence": "full",
                                "source": {
                                    "audit_mode": "explicit",
                                    "root_reasoning_cadence": "explicit",
                                    "worker_reasoning_cadence": "default",
                                },
                                "worker_log_visibility": "unverified",
                                "worker_log_evidence": None,
                                "audit_config_prompt": {
                                    "status": "answered",
                                    "prompted_at": "2026-10-24T00:00:00Z",
                                    "deadline_at": "2026-10-24T00:01:00Z",
                                    "response_at": "2026-10-24T00:00:30Z",
                                    "resolution": "question_reply",
                                },
                                "revision": "session-audit/v2",
                            },
                            "expected_revision": 0,
                            "idempotency_key": "wire-audit",
                        }
                    }
                },
            )
            assert not audit.is_error
            assert '"receipt_revision": 1' in _result_text(audit)
            provider.revoked = True
            denied = await client.call_tool("workflow_get_state", {"payload": {}})
            assert denied.is_error
            assert "trusted host binding" in _result_text(denied)

    asyncio.run(run())


@pytest.mark.parametrize("bridge_mode", ["bridge", "bridge-codex"])
def test_bound_stdio_subprocess_root_and_worker_protocols(tmp_path: Path, bridge_mode: str) -> None:
    state_root = tmp_path / "state"
    provider = FakeBindingProvider()
    service = StateService(
        provider,
        state_root=state_root,
        rule_loader=RuleLoader(repository_root=Path(__file__).resolve().parents[2]),
    )
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
    provider.add_child("stdio-test-worker")
    service.delegation_bind(
        allocation,
        "stdio-test-worker",
        expected_revision=4,
        idempotency_key="stdio-setup-bind",
    )

    harness = Path(__file__).with_name("stdio_binding_harness.py")
    project_root = Path(__file__).parents[1]
    root_state = tmp_path / "root-stdio-state"

    def server_parameters(role: str) -> StdioServerParameters:
        return StdioServerParameters(
            command=sys.executable,
            args=[
                str(harness),
                bridge_mode,
                role,
                str(root_state if role == "root" else state_root),
            ],
            cwd=project_root,
            env={"PYTHONDONTWRITEBYTECODE": "1"},
        )

    async def run() -> None:
        async with Client(server_parameters("root"), mode="auto") as raw_root_client:
            root_client = RequestMetaClient(raw_root_client, "root-session")
            assert root_client.protocol_version == "2026-07-28"
            listed = await root_client.list_tools()
            assert {tool.name for tool in listed.tools} == PUBLIC_TOOLS | ROOT_TOOLS
            opened = await root_client.call_tool(
                "workflow_open",
                {
                    "payload": {
                        "mode_count": {"mode": "Multi-Agent Coding", "child_count": 1},
                        "mode_source": "explicit",
                        "source": {
                            "uri": "memory://root-stdio-contract",
                            "content_hash": "1" * 64,
                        },
                        "semantic_references": [],
                        "expected_revision": 0,
                        "idempotency_key": "root-stdio-open",
                    }
                },
            )
            assert not opened.is_error
            audit = await root_client.call_tool(
                "workflow_transition",
                {
                    "payload": {
                        "request": {
                            "kind": "session_audit",
                            "session_audit": {
                                "audit_mode": "balanced",
                                "root_reasoning_cadence": "milestone_only",
                                "worker_reasoning_cadence": "full",
                                "source": {
                                    "audit_mode": "explicit",
                                    "root_reasoning_cadence": "explicit",
                                    "worker_reasoning_cadence": "default",
                                },
                                "worker_log_visibility": "unverified",
                                "worker_log_evidence": None,
                                "audit_config_prompt": {
                                    "status": "answered",
                                    "prompted_at": "2026-10-24T00:00:00Z",
                                    "deadline_at": "2026-10-24T00:01:00Z",
                                    "response_at": "2026-10-24T00:00:30Z",
                                    "resolution": "question_reply",
                                },
                                "revision": "session-audit/v2",
                            },
                            "expected_revision": 0,
                            "idempotency_key": "root-stdio-audit",
                        }
                    }
                },
            )
            assert not audit.is_error
            assert '"receipt_revision": 1' in _result_text(audit)
            root_state_result = await root_client.call_tool("workflow_get_state", {"payload": {}})
            assert not root_state_result.is_error
            root_state = json.loads(_result_text(root_state_result))
            assert root_state["session_audit"]["audit_mode"] == "balanced"
            assert root_state["session_audit"]["root_reasoning_cadence"] == "milestone_only"
            assert root_state["session_audit"]["worker_reasoning_cadence"] == "full"
            root_revision = root_state["revision"]
            root_facts = [
                ("task objective", "stdio-root-objective"),
                ("authorized scope", "stdio-root-scope"),
                ("constraints", "stdio-root-constraints"),
                ("acceptance conditions", "stdio-root-acceptance"),
            ]
            root_evidence_arguments = {
                "payload": {
                    "submission": {
                        "node_id": "contract",
                        "facts": [
                            {
                                "fact_key": key,
                                "judgment": {
                                    "status": "determined",
                                    "value": {
                                        "kind": "semantic_ref",
                                        "value": {
                                            "uri": f"memory://{uri}",
                                            "content_hash": "3" * 64,
                                        },
                                    },
                                },
                            }
                            for key, uri in root_facts
                        ],
                        "evidence_refs": [],
                        "coverage_dimensions": [],
                        "input_hash": "4" * 64,
                    },
                    "expected_revision": root_revision,
                    "idempotency_key": "root-stdio-contract-evidence",
                }
            }
            evidence = await root_client.call_tool(
                "workflow_record_evidence", root_evidence_arguments
            )
            assert not evidence.is_error
            evidence_receipt = json.loads(_result_text(evidence))
            evidence_record = evidence_receipt["result"]
            assert evidence_record["node_id"] == "contract"
            assert len(evidence_record["facts"]) == 4
            assert evidence_receipt["current_revision"] == root_revision + 1
            root_after_write = await root_client.call_tool("workflow_get_state", {"payload": {}})
            assert not root_after_write.is_error
            assert json.loads(_result_text(root_after_write))["revision"] == root_revision + 1
            replay = await root_client.call_tool(
                "workflow_record_evidence", root_evidence_arguments
            )
            assert not replay.is_error
            replay_receipt = json.loads(_result_text(replay))
            assert replay_receipt["replayed"] is True
            stale_arguments = {
                "payload": {
                    **root_evidence_arguments["payload"],
                    "idempotency_key": "root-stdio-stale-cas",
                }
            }
            stale_write = await root_client.call_tool("workflow_record_evidence", stale_arguments)
            assert stale_write.is_error
            assert "expected Revision" in _result_text(stale_write)
            wrong_role = await root_client.call_tool("worker_get_assignment", {})
            assert wrong_role.is_error

        async with Client(server_parameters("worker"), mode="auto") as raw_worker_client:
            worker_client = RequestMetaClient(raw_worker_client, "stdio-test-worker")
            assert worker_client.protocol_version == "2026-07-28"
            listed = await worker_client.list_tools()
            assert {tool.name for tool in listed.tools} == PUBLIC_TOOLS | WORKER_TOOLS
            assignment = await worker_client.call_tool("worker_get_assignment", {})
            assert not assignment.is_error
            status = await worker_client.call_tool("database_schema_status", {})
            assert not status.is_error
            assert '"database_kind": "worker"' in _result_text(status)
            progress = await worker_client.call_tool(
                "worker_record_progress",
                {
                    "payload": {
                        "record": {
                            "status": "started",
                            "milestone": {
                                "uri": "memory://stdio-worker-started",
                                "content_hash": "2" * 64,
                            },
                            "references": [],
                        },
                        "expected_revision": 0,
                        "idempotency_key": "worker-stdio-progress",
                    }
                },
            )
            assert not progress.is_error
            progress_receipt = json.loads(_result_text(progress))
            assert progress_receipt["receipt_revision"] == 1
            worker_evidence = await worker_client.call_tool(
                "worker_record_evidence",
                {
                    "payload": {
                        "submission": {
                            "node_id": "implementation",
                            "facts": [
                                {
                                    "fact_key": key,
                                    "judgment": {
                                        "status": "determined",
                                        "value": {
                                            "kind": "semantic_ref",
                                            "value": {
                                                "uri": f"memory://{uri}",
                                                "content_hash": "5" * 64,
                                            },
                                        },
                                    },
                                }
                                for key, uri in [
                                    ("released objective", "worker-objective"),
                                    ("authorized mutation scope", "worker-scope"),
                                    ("current unreleased boundary", "worker-boundary"),
                                ]
                            ],
                            "evidence_refs": [
                                {
                                    "kind": "slice release",
                                    "reference": {
                                        "uri": "test://stdio-slice-release",
                                        "content_hash": "6" * 64,
                                    },
                                },
                                {
                                    "kind": "implementation result or blocker",
                                    "reference": {
                                        "uri": "test://stdio-implementation-result",
                                        "content_hash": "7" * 64,
                                    },
                                },
                            ],
                            "coverage_dimensions": ["implementation_content"],
                            "input_hash": "8" * 64,
                        },
                        "expected_revision": 1,
                        "idempotency_key": "worker-stdio-implementation-evidence",
                    }
                },
            )
            assert not worker_evidence.is_error
            worker_evidence_receipt = json.loads(_result_text(worker_evidence))
            worker_evidence_id = worker_evidence_receipt["result"]["evidence_id"]
            persisted_worker_evidence = await worker_client.call_tool(
                "worker_get_evidence", {"payload": {"evidence_id": worker_evidence_id}}
            )
            assert not persisted_worker_evidence.is_error
            worker_record = json.loads(_result_text(persisted_worker_evidence))
            assert worker_record["evidence_id"] == worker_evidence_id
            assert worker_record["node_id"] == "implementation"
            worker_state = await worker_client.call_tool("worker_get_state", {})
            assert not worker_state.is_error
            worker_state_value = json.loads(_result_text(worker_state))
            assert worker_state_value["revision"] == 2
            assert worker_state_value["progress"][0]["status"] == "started"
            if bridge_mode == "bridge-codex":
                rejected_progress = await raw_worker_client.call_tool(
                    "worker_record_progress",
                    {
                        "payload": {
                            "record": {
                                "status": "started",
                                "milestone": {
                                    "uri": "memory://stdio-worker-wrong-thread",
                                    "content_hash": "9" * 64,
                                },
                                "references": [],
                            },
                            "expected_revision": 2,
                            "idempotency_key": "worker-stdio-wrong-thread",
                        }
                    },
                    meta={"threadId": "another-thread", "sessionId": "opaque-session"},
                )
                assert rejected_progress.is_error
                assert "Codex caller context" in _result_text(rejected_progress)
                unchanged_worker_state = await worker_client.call_tool("worker_get_state", {})
                assert not unchanged_worker_state.is_error
                assert json.loads(_result_text(unchanged_worker_state))["revision"] == 2
            wrong_role = await worker_client.call_tool("workflow_get_state", {"payload": {}})
            assert wrong_role.is_error

    asyncio.run(run())


def test_root_worker_tool_isolation_and_per_operation_capability_checks(tmp_path: Path) -> None:
    async def run() -> None:
        fake_identity = FakeBindingProvider()
        async with Client(create_server(fake_identity, state_root=tmp_path), mode="auto") as client:
            forged = await client.call_tool(
                "delegation_bind",
                {
                    "payload": {
                        "allocation_id": "allocation-a",
                        "child_session_id": "forged-worker",
                        "expected_revision": 0,
                        "idempotency_key": "bind-forged-child",
                    }
                },
            )
            assert forged.is_error
            assert "trusted host binding" in _result_text(forged)
        assert list(tmp_path.iterdir()) == []

        worker = create_server(FakeBindingProvider(SessionRole.WORKER), state_root=tmp_path)
        async with Client(worker, mode="auto") as client:
            listed = await client.list_tools()
            assert {tool.name for tool in listed.tools} == PUBLIC_TOOLS | WORKER_TOOLS
            cross_role = await client.call_tool("workflow_get_state", {"payload": {}})
            assert cross_role.is_error

        root_provider = FakeBindingProvider()
        root_provider.binding = root_provider.binding.model_copy(
            update={
                "capabilities": frozenset(
                    capability
                    for capability in root_provider.binding.capabilities
                    if capability is not HostCapability.CHILD_IDENTITY_CHECK
                )
            }
        )
        async with Client(create_server(root_provider, state_root=tmp_path), mode="auto") as client:
            denied = await client.call_tool(
                "delegation_bind",
                {
                    "payload": {
                        "allocation_id": "allocation-a",
                        "child_session_id": "worker-b",
                        "expected_revision": 0,
                        "idempotency_key": "bind-no-capability",
                    }
                },
            )
            assert denied.is_error
            assert "trusted host binding" in _result_text(denied)
        assert list(tmp_path.iterdir()) == []

    asyncio.run(run())


def test_worker_protocol_reads_and_writes_its_confirmed_assignment(tmp_path: Path) -> None:
    provider = FakeBindingProvider()
    state_root = tmp_path / "state"
    service = StateService(
        provider,
        state_root=state_root,
        rule_loader=RuleLoader(repository_root=Path(__file__).resolve().parents[2]),
    )
    source = SemanticRef(uri="memory://contract", content_hash="a" * 64)
    service.workflow_open(
        WorkflowOpenRequest(
            mode_count=ModeCount(mode=CodingMode.MULTI_AGENT, child_count=1),
            mode_source="explicit",
            source=source,
            idempotency_key="open-for-worker-wire",
        )
    )
    allocation = service.workflow_get_state().allocations[0].allocation_id
    service.delegation_reserve(
        "Primary Output", expected_revision=0, idempotency_key="reserve-for-worker-wire"
    )
    objective = SemanticRef(uri="memory://objective", content_hash="b" * 64)
    returns = SemanticRef(uri="memory://return", content_hash="c" * 64)
    boundary = SemanticRef(uri="memory://boundary", content_hash="d" * 64)
    spec = SliceSpec(
        allocation_id=allocation,
        output_class=OutputClass.CODE_CONFIGURATION,
        objective=objective,
        return_conditions=returns,
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
                fact(FactKey.RETURN_CONDITIONS, returns),
                fact(FactKey.UNRELEASED_BOUNDARY, boundary),
            ],
            evidence_refs=[
                TypedEvidenceReference(
                    kind=EvidenceKind.PARENT_SLICE_RELEASE,
                    reference=EvidenceRef(uri="test://slice-authority", content_hash="f" * 64),
                )
            ],
            input_hash=input_hash,
        ),
        expected_revision=1,
        idempotency_key="slice-evidence-for-worker-wire",
    )
    service.workflow_evaluate(
        CheckpointNode.SLICE,
        branch="released",
        input_hash=input_hash,
        expected_revision=2,
        idempotency_key="slice-evaluation-for-worker-wire",
    )
    service.slice_release(spec, expected_revision=3, idempotency_key="release-for-worker-wire")
    provider.add_child("worker-a")
    service.delegation_bind(
        allocation,
        "worker-a",
        expected_revision=4,
        idempotency_key="bind-for-worker-wire",
    )
    provider.become_worker("worker-a")

    async def run() -> None:
        async with Client(create_server(provider, state_root=state_root), mode="auto") as client:
            listed = await client.list_tools()
            assert {tool.name for tool in listed.tools} == PUBLIC_TOOLS | WORKER_TOOLS
            assignment = await client.call_tool("worker_get_assignment", {})
            assert not assignment.is_error
            assert '"allocation_id"' in _result_text(assignment)
            progress = await client.call_tool(
                "worker_record_progress",
                {
                    "payload": {
                        "record": {
                            "status": "started",
                            "milestone": {
                                "uri": "memory://worker-started",
                                "content_hash": "1" * 64,
                            },
                            "references": [],
                        },
                        "expected_revision": 0,
                        "idempotency_key": "worker-progress-wire",
                    }
                },
            )
            assert not progress.is_error
            state = await client.call_tool("worker_get_state", {})
            assert not state.is_error
            assert '"revision": 1' in _result_text(state)
            assert '"status": "started"' in _result_text(state)
        share = create_server(provider, profile="share", state_root=state_root)
        async with Client(share, mode="auto") as share_client:
            shared_state = await share_client.call_tool("state_get", {"payload": {}})
            assert not shared_state.is_error
            assert '"revision": 1' in _result_text(shared_state)
            invalid_page = await share_client.call_tool(
                "state_get",
                {"payload": {"index_page": {"collection": "evidence", "page_size": 1}}},
            )
            assert invalid_page.is_error
            worker_evidence = await share_client.call_tool(
                "record_evidence",
                {
                    "payload": {
                        "submission": {
                            "node_id": "implementation",
                            "facts": [
                                {
                                    "fact_key": key,
                                    "judgment": {
                                        "status": "determined",
                                        "value": {
                                            "kind": "semantic_ref",
                                            "value": {
                                                "uri": f"memory://{key}",
                                                "content_hash": "a" * 64,
                                            },
                                        },
                                    },
                                }
                                for key in (
                                    "released objective",
                                    "authorized mutation scope",
                                    "current unreleased boundary",
                                )
                            ],
                            "evidence_refs": [],
                            "coverage_dimensions": ["implementation_content"],
                            "input_hash": "c" * 64,
                        },
                        "expected_revision": 1,
                        "idempotency_key": "share-worker-evidence",
                    }
                },
            )
            assert not worker_evidence.is_error
            assert "evidence_id" in _result_text(worker_evidence)
            shared_after_write = await share_client.call_tool("state_get", {"payload": {}})
            assert not shared_after_write.is_error
            assert '"revision": 2' in _result_text(shared_after_write)
            schema = await share_client.call_tool("database_schema_status", {})
            assert not schema.is_error
            assert '"database_kind": "worker"' in _result_text(schema)
            assert '"exists": true' in _result_text(schema)

    asyncio.run(run())


def test_schema_status_unbound_has_no_path_or_filesystem_side_effect(tmp_path: Path) -> None:
    server = create_server()
    result = asyncio.run(_call(server, "database_schema_status", {}))
    assert result["available"] is False
    assert list(tmp_path.iterdir()) == []

    bound_root = tmp_path / "bound-state"
    result2 = asyncio.run(
        _call(
            create_server(FakeBindingProvider(), state_root=bound_root),
            "database_schema_status",
            {},
        )
    )
    assert result2["exists"] is False
    assert not bound_root.exists()


def test_worker_schema_status_requires_isolation_guard_without_path_side_effect(
    tmp_path: Path,
) -> None:
    provider = FakeBindingProvider(SessionRole.WORKER)
    provider.binding = provider.binding.model_copy(
        update={"guards": provider.binding.guards - {HostGuard.WORKER_STORE_ISOLATION}}
    )
    bound_root = tmp_path / "guarded-state"
    server = create_server(provider, state_root=bound_root)
    assert _tool_names(server) == PUBLIC_TOOLS
    result = asyncio.run(_call(server, "database_schema_status", {}))
    assert result["available"] is False
    assert not bound_root.exists()


def test_git_common_directory_identity_matches_worktrees_and_rejects_symlinks(
    tmp_path: Path,
) -> None:
    main = tmp_path / "main"
    (main / ".git" / "worktrees" / "wt1").mkdir(parents=True)
    (main / ".git" / "config").write_text("", encoding="utf-8")
    wt = tmp_path / "worktree"
    wt.mkdir()
    (wt / ".git").write_text(f"gitdir: {main / '.git' / 'worktrees' / 'wt1'}\n", encoding="utf-8")
    (main / ".git" / "worktrees" / "wt1" / "commondir").write_text("../..\n", encoding="utf-8")
    assert project_id_from_git_common_dir(main) == project_id_from_git_common_dir(wt)

    separate_common = tmp_path / "separate-main"
    separate_common.mkdir()
    common_dir = tmp_path / "repo.git"
    (common_dir / "worktrees" / "linked").mkdir(parents=True)
    (separate_common / ".git").write_text(f"gitdir: {common_dir}\n", encoding="utf-8")
    linked = tmp_path / "separate-worktree"
    linked.mkdir()
    linked_git_dir = common_dir / "worktrees" / "linked"
    (linked / ".git").write_text(f"gitdir: {linked_git_dir}\n", encoding="utf-8")
    (linked_git_dir / "commondir").write_text("../..\n", encoding="utf-8")
    assert project_id_from_git_common_dir(separate_common) == project_id_from_git_common_dir(linked)

    clone = tmp_path / "clone"
    (clone / ".git").mkdir(parents=True)
    assert project_id_from_git_common_dir(clone) != project_id_from_git_common_dir(main)
    assert project_id_from_git_common_dir(
        clone, trusted_association="trusted-project-1"
    ) == project_id_from_git_common_dir(main, trusted_association="trusted-project-1")

    symlinked = tmp_path / "symlinked"
    symlinked.mkdir()
    (symlinked / ".git").symlink_to(main / ".git", target_is_directory=True)
    try:
        project_id_from_git_common_dir(symlinked)
    except ProjectIdentityError:
        pass
    else:
        raise AssertionError("symlinked .git metadata must be rejected")

    escaping = tmp_path / "escaping"
    escaping_gitdir = escaping / ".git" / "worktrees" / "wt2"
    escaping_gitdir.mkdir(parents=True)
    evil_worktree = tmp_path / "evil-worktree"
    evil_worktree.mkdir()
    (evil_worktree / ".git").write_text(f"gitdir: {escaping_gitdir}\n", encoding="utf-8")
    (escaping_gitdir / "commondir").write_text("../../../../\n", encoding="utf-8")
    try:
        project_id_from_git_common_dir(evil_worktree)
    except ProjectIdentityError:
        pass
    else:
        raise AssertionError("commondir outside the linked Git directory must be rejected")

    symlink_gitdir = tmp_path / "linked" / ".git" / "worktrees" / "wt3"
    symlink_gitdir.mkdir(parents=True)
    symlink_worktree = tmp_path / "symlink-worktree"
    symlink_worktree.mkdir()
    (symlink_worktree / ".git").write_text(f"gitdir: {symlink_gitdir}\n", encoding="utf-8")
    (symlink_gitdir / "commondir").symlink_to(main / ".git", target_is_directory=True)
    try:
        project_id_from_git_common_dir(symlink_worktree)
    except ProjectIdentityError:
        pass
    else:
        raise AssertionError("symlinked commondir metadata must be rejected")
