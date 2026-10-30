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
    "task_plan_update",
    "task_plan_complete",
    "task_plan_archive",
    "rules_get_context",
    "workflow_select_child_effort",
    "workflow_generate_decision_context",
    "workflow_select_child_role",
    "workflow_select_executor",
    "workflow_select_child",
    "workflow_assess_output_tokens",
    "database_schema_status",
}

ROOT_TOOLS = {
    "workflow_open",
    "workflow_get_state",
    "delegation_reserve",
    "delegation_unreserve",
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
    root_server = create_server(FakeBindingProvider())
    root_tool_specs = {tool.name: tool for tool in root_server._tool_manager.list_tools()}
    unreserve_parameters = root_tool_specs["delegation_unreserve"].parameters
    unreserve_payload = unreserve_parameters["properties"]["payload"]
    assert set(unreserve_payload["properties"]) == {
        "allocation_id",
        "creation_not_started",
        "creation_not_started_reference",
        "expected_revision",
        "idempotency_key",
    }
    assert set(unreserve_payload["required"]) == set(unreserve_payload["properties"])
    assert unreserve_payload["properties"]["allocation_id"]["type"] == "string"
    assert unreserve_payload["properties"]["creation_not_started"]["type"] == "boolean"
    assert unreserve_payload["properties"]["expected_revision"]["type"] == "integer"
    assert unreserve_payload["properties"]["idempotency_key"]["type"] == "string"
    proof_schema = unreserve_payload["properties"]["creation_not_started_reference"]
    assert proof_schema["anyOf"]
    assert all(
        {"uri", "content_hash"} <= set(variant["properties"]) for variant in proof_schema["anyOf"]
    )
    capabilities = asyncio.run(_call(unbound, "workflow_capabilities", {}))
    assert capabilities["host_adapters"]["Codex Desktop"]["identity_attestation"] == "unavailable"
    assert capabilities["host_adapters"]["ChatGPT Desktop"]["guard_binding"] == "unavailable"
    assert capabilities["mode_fallback"] == "Native"
    assert capabilities["api_decisions"] == "disabled"
    assert capabilities["child_effort_decisions"] == "available_per_invocation"
    assert capabilities["delegation_decisions"] == "available_per_invocation"
    assert capabilities["decision_context_generation"] == "available_per_invocation"
    denied_context = asyncio.run(
        _call(
            unbound,
            "workflow_generate_decision_context",
            {
                "payload": {
                    "request": {
                        "raw_content": "caller-composed material",
                        "decision_goal": "Create a short question.",
                        "output_kind": "decision_question",
                        "outbound_data_permitted": False,
                    }
                }
            },
        )
    )
    assert (denied_context["status"], denied_context["reason"]) == (
        "blocked",
        "outbound_data_not_permitted",
    )

    root_tools = _tool_names(
        create_server(FakeBindingProvider(), state_root=Path("/private/tmp/never-used"))
    )
    worker_tools = _tool_names(create_server(FakeBindingProvider(SessionRole.WORKER)))
    assert root_tools == PUBLIC_TOOLS | ROOT_TOOLS
    assert worker_tools == PUBLIC_TOOLS | WORKER_TOOLS
    assert len(root_tools) == 25
    assert len(worker_tools) == 19
    assert len(root_tools | worker_tools) == 32
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
                    descriptions = {tool.name: tool.description or "" for tool in tool_list.tools}
                    unreserve_description = descriptions["delegation_unreserve"]
                    for required in (
                        "literal JSON true",
                        "SemanticRef or EvidenceRef",
                        "verified Root binding",
                        "reserved state",
                        "unknown/corrupt/missing identity blocks",
                        "worker.sqlite3",
                        "fail closed",
                        "Success changes only role to null and status to unassigned",
                        "slot and child_count stay fixed",
                        "not host proof",
                        "makes no API request",
                    ):
                        assert required in unreserve_description
                    for name in (
                        "workflow_select_child_role",
                        "workflow_select_executor",
                        "workflow_select_child",
                        "workflow_assess_output_tokens",
                    ):
                        description = descriptions[name]
                        for required in (
                            "status is available, skipped, fallback, blocked, or stale",
                            "fact_revision",
                            "fact_fingerprint",
                            "context_input_hash",
                            "source_policy_hashes",
                            "authority=advisory_only",
                            "outbound_data_permitted=true",
                            "OPENAI_API_KEY",
                            "OPENAI_BASE_URL",
                            "gpt-6-luna",
                            "refresh current facts",
                        ):
                            assert required in description
                    assert (
                        "Documentation/Comments & Git Operations"
                        in descriptions["workflow_select_child_role"]
                    )
                    assert (
                        "suggested_value is root or sub_agent"
                        in descriptions["workflow_select_executor"]
                    )
                    assert "busy Primary requires waiting" in descriptions["workflow_select_child"]
                    assert (
                        "suggested_value yes or no" in descriptions["workflow_assess_output_tokens"]
                    )
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
        "delegation_unreserve",
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
            reserved = await client.call_tool(
                "delegation_reserve",
                {
                    "payload": {
                        "role": "Primary Output",
                        "expected_revision": 1,
                        "idempotency_key": "wire-reserve-for-unreserve",
                    }
                },
            )
            assert not reserved.is_error
            reservation = json.loads(_result_text(reserved))
            allocation_id = reservation["result"]["allocation_id"]
            unreserve_payload = {
                "payload": {
                    "allocation_id": allocation_id,
                    "creation_not_started": True,
                    "creation_not_started_reference": {
                        "uri": "evidence://wire-creation-not-started",
                        "content_hash": "f" * 64,
                    },
                    "expected_revision": reservation["receipt_revision"],
                    "idempotency_key": "wire-unreserve",
                }
            }
            unreserved = await client.call_tool("delegation_unreserve", unreserve_payload)
            assert not unreserved.is_error
            unreserve_receipt = json.loads(_result_text(unreserved))
            assert unreserve_receipt["result"]["allocation_id"] == allocation_id
            assert unreserve_receipt["result"]["status"] == "unassigned"
            assert unreserve_receipt["result"]["proof"]["uri"] == (
                "evidence://wire-creation-not-started"
            )
            assert unreserve_receipt["result"]["root_attestation"]["authority_limit"] == (
                "Root attestation with referenced evidence; not host proof"
            )
            replay = await client.call_tool("delegation_unreserve", unreserve_payload)
            assert not replay.is_error
            assert json.loads(_result_text(replay))["replayed"] is True
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
                assert '"revision": 3' in _result_text(unchanged)

    asyncio.run(run())


async def _call(server: MCPServer[Any], name: str, arguments: dict[str, object]) -> dict[str, Any]:
    async with Client(server, mode="auto") as client:
        result = await client.call_tool(name, arguments)
        assert not result.is_error
        assert result.content
        return json.loads(cast(TextContent, result.content[0]).text or "{}")


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
        rule_loader=RuleLoader(repository_root=Path(__file__).resolve().parents[3]),
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

    harness = Path(__file__).parents[1] / "support" / "stdio_binding_harness.py"
    project_root = Path(__file__).parents[2]
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
        rule_loader=RuleLoader(repository_root=Path(__file__).resolve().parents[3]),
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
