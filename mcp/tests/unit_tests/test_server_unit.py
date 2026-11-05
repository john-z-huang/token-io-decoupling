from __future__ import annotations

import asyncio
import hashlib
import json
import sysconfig
from pathlib import Path
from typing import Any, cast

from mcp import Client, StdioServerParameters
from mcp.server import MCPServer
from mcp.types import TextContent
from token_io_decoupling_core.project_identity import (
    ProjectIdentityError,
    project_id_from_git_common_dir,
)
from token_io_decoupling_core.server_tools import (
    DEV_WORKFLOW_TOOLS,
    TOOLS_SERVER_NAME,
    TOOLS_SERVER_TOOLS,
    WORKFLOW_SERVER_NAME,
    WORKFLOW_TOOLS,
)

from token_io_decoupling.server import create_tools_server, create_workflow_server


def _tool_names(server: MCPServer[Any]) -> set[str]:
    return {tool.name for tool in server._tool_manager.list_tools()}


def _result_text(result: Any) -> str:
    return cast(TextContent, result.content[0]).text


def test_two_fixed_servers_have_exact_inventories_and_fail_closed() -> None:
    workflow = create_workflow_server()
    tools = create_tools_server()
    assert _tool_names(workflow) == WORKFLOW_TOOLS
    assert _tool_names(tools) == TOOLS_SERVER_TOOLS
    assert len(WORKFLOW_TOOLS) == 17
    assert len(TOOLS_SERVER_TOOLS) == 51
    assert WORKFLOW_TOOLS.isdisjoint(TOOLS_SERVER_TOOLS)
    assert DEV_WORKFLOW_TOOLS <= TOOLS_SERVER_TOOLS

    async def inspect() -> None:
        async with Client(workflow, mode="auto") as client:
            capabilities = await client.call_tool("workflow_capabilities", {})
            assert not capabilities.is_error
            rules = await client.call_tool(
                "rules_get_context", {"payload": {"node_id": "contract", "language": "en"}}
            )
            assert not rules.is_error
            bundle = await client.call_tool(
                "rules_get_context",
                {"payload": {"node_id": "contract", "context_version": 1}},
            )
            assert not bundle.is_error
            parsed_bundle = json.loads(_result_text(bundle))
            assert parsed_bundle["schema_version"] == 1
            assert parsed_bundle["complete"] is True
            assert "owner_text" not in parsed_bundle["node_metadata"]

        async with Client(tools, mode="auto") as client:
            for tool, payload in (
                ("workflow_open", {"payload": {"request": {}}}),
                ("worker_get_assignment", {}),
                ("state_get", {"payload": {}}),
            ):
                result = await client.call_tool(tool, payload)
                assert result.is_error
            diagnostics = await client.call_tool("database_schema_status", {})
            assert not diagnostics.is_error
            assert '"available": false' in _result_text(diagnostics)
            assert "no state path was inspected" in _result_text(diagnostics)

    asyncio.run(inspect())


def test_aggregate_tools_matches_all_pinned_upstream_tool_metadata() -> None:
    from dev_workflow_standards_tools import server as upstream

    async def read_tool_metadata() -> tuple[dict[str, Any], dict[str, Any]]:
        expected_tools = await upstream.mcp.list_tools()
        actual_tools = await create_tools_server().list_tools()
        expected = {
            tool.name: tool.model_dump(mode="json", by_alias=True) for tool in expected_tools
        }
        actual = {
            tool.name: tool.model_dump(mode="json", by_alias=True)
            for tool in actual_tools
            if tool.name in DEV_WORKFLOW_TOOLS
        }
        return expected, actual

    expected, actual = asyncio.run(read_tool_metadata())
    assert len(expected) == 33
    assert set(expected) == DEV_WORKFLOW_TOOLS
    assert actual == expected


def test_server_discovery_and_tool_metadata_for_fixed_servers() -> None:
    from token_io_decoupling_transport.tool_metadata import (
        tools_server_instructions,
        workflow_server_instructions,
    )

    expected = {"workflow": WORKFLOW_TOOLS, "tools": TOOLS_SERVER_TOOLS}
    assert "workflow_capabilities" in workflow_server_instructions()
    assert "Root starts with workflow_open" in tools_server_instructions()
    assert "role checks on every call" in tools_server_instructions()

    async def check_server(server_kind: str, mode: str) -> None:
        server = create_workflow_server() if server_kind == "workflow" else create_tools_server()
        async with Client(server, mode=mode) as client:
            assert client.protocol_version == ("2026-07-28" if mode == "auto" else "2025-11-25")
            assert client.server_info is not None
            assert client.server_info.description
            assert client.instructions
            expected_name = WORKFLOW_SERVER_NAME if server_kind == "workflow" else TOOLS_SERVER_NAME
            assert client.server_info.name == expected_name
            assert "profile" not in client.instructions.casefold()
            if server_kind == "tools":
                from dev_workflow_standards_tools.server import (
                    SERVER_INSTRUCTIONS as development_instructions,
                )

                assert development_instructions in client.instructions
            listed = await client.list_tools()
            by_name = {tool.name: tool for tool in listed.tools}
            assert set(by_name) == expected[server_kind]
            assert all(tool.description for tool in by_name.values())
            if "materialize_decoupled_output" in by_name:
                description = by_name["materialize_decoupled_output"].description or ""
                for required in (
                    "verified MCP Worker binding",
                    "Primary Output assignment",
                    "separate active operator grant",
                    "pinned roots",
                    "project-file write permission",
                ):
                    assert required in description
            # Check the public wire schema itself, not the SDK's internal tool model.
            if "workflow_capabilities" in by_name:
                assert by_name["workflow_capabilities"].input_schema["properties"] == {}
            if "rules_get_context" in by_name:
                schema = by_name["rules_get_context"].input_schema
                payload_schema = schema["properties"]["payload"]
                properties = payload_schema["properties"]
                assert {"node_id", "language"} <= set(properties)
                assert {"context_version", "fragment_ids", "max_chars"} <= set(properties)
                assert properties["context_version"]["anyOf"][0]["const"] == 1
                assert properties["max_chars"]["anyOf"][0]["minimum"] == 256
                assert properties["max_chars"]["anyOf"][0]["maximum"] == 60_000
                description = by_name["rules_get_context"].description or ""
                assert "unchanged legacy" in description
                assert "Unicode characters" in description
                assert "remaining_owner_refs" in description
                assert "does not mean the task's other direct owners" in description
            if "workflow_select_child_effort" in by_name:
                schema = by_name["workflow_select_child_effort"].input_schema
                selector_schema = schema["properties"]["payload"]["properties"]
                assert "request" in selector_schema
                assert "outbound_data_permitted" in selector_schema["request"]["properties"]
                request_schema = selector_schema["request"]
                assert "decision_question" in request_schema["required"]
                assert request_schema["properties"]["decision_question"]["minLength"] == 1
                assert request_schema["properties"]["decision_question"]["maxLength"] == 1200
                description = by_name["workflow_select_child_effort"].description
                assert description is not None
                assert "grants no creation authority" in description
            if "workflow_generate_decision_context" in by_name:
                schema = by_name["workflow_generate_decision_context"].input_schema
                request_schema = schema["properties"]["payload"]["properties"]["request"]
                assert set(request_schema["required"]) == {
                    "raw_content",
                    "decision_goal",
                    "output_kind",
                    "outbound_data_permitted",
                }
                request_properties = request_schema["properties"]
                assert request_properties["raw_content"]["maxLength"] == 60_000
                assert request_properties["decision_goal"]["maxLength"] == 1200
                assert request_properties["output_kind"]["enum"] == [
                    "decision_question",
                    "decision_context",
                ]
                description = by_name["workflow_generate_decision_context"].description
                assert description is not None
                assert "does not inspect repositories" in description
                assert "automatic downstream Decisions call" in description
            if "decide_decoupling_workflow" in by_name:
                route_schema = by_name["decide_decoupling_workflow"].input_schema["properties"][
                    "payload"
                ]["properties"]["request"]
                request_schema = route_schema["properties"]
                assert {
                    "task_id",
                    "task_summary",
                    "stage",
                    "mode_locked",
                    "mode_count",
                    "capabilities",
                    "hard_constraints",
                    "source_facts",
                    "source_facts_hash",
                    "outbound_data_permitted",
                } <= set(request_schema)
                assert request_schema["stage"]["enum"] == [
                    "auto",
                    "entry_readiness",
                    "session_readiness",
                    "work_definition",
                    "execution",
                    "verification_repair",
                    "documentation",
                    "delivery_acceptance",
                ]
                assert "outbound_data_permitted" in route_schema["required"]
                description = by_name["decide_decoupling_workflow"].description or ""
                assert "not a second policy source" in description
                assert "max_retries=0" in description
                assert "Single-Agent or Multi-Agent" in description
            if "workflow_select_child_role" in by_name:
                request_schema = by_name["workflow_select_child_role"].input_schema["properties"][
                    "payload"
                ]["properties"]["request"]
                assert {
                    "created_roles",
                    "reserved_roles",
                    "available_slots",
                    "forked_session",
                    "mode_reselected_after_fork",
                    "outbound_data_permitted",
                } <= set(request_schema["properties"])
                description = by_name["workflow_select_child_role"].description or ""
                assert "never reserves or creates" in description
                assert "gpt-6-luna" in description
            if "workflow_select_child" in by_name:
                request_schema = by_name["workflow_select_child"].input_schema["properties"][
                    "payload"
                ]["properties"]["request"]
                assert "candidates" in request_schema["properties"]
                assert "explicit_user_candidate_ref" in request_schema["properties"]
            if "workflow_assess_output_tokens" in by_name:
                description = by_name["workflow_assess_output_tokens"].description or ""
                assert "forbids Root immediate execution" in description
                assert "waiting" in description
            if "delegation_reserve" in by_name:
                reserve_schema = by_name["delegation_reserve"].input_schema["properties"]["payload"]
                properties = reserve_schema["properties"]
                assert "budget_approval" in properties
                assert "budget_approval" not in reserve_schema.get("required", [])
                description = by_name["delegation_reserve"].description or ""
                assert "not cryptographic host proof" in description
            if "delegation_unreserve" in by_name:
                payload_schema = by_name["delegation_unreserve"].input_schema["properties"][
                    "payload"
                ]
                assert set(payload_schema["required"]) == {
                    "allocation_id",
                    "creation_not_started",
                    "creation_not_started_reference",
                    "expected_revision",
                    "idempotency_key",
                }
                assert payload_schema["properties"]["creation_not_started"]["type"] == "boolean"
                description = by_name["delegation_unreserve"].description or ""
                assert "not host proof" in description
                assert "does not create, bind, or dispatch" in description
            if "state_get" in by_name:
                assert "payload" in by_name["state_get"].input_schema["properties"]

    async def run() -> None:
        for server_kind in expected:
            await check_server(server_kind, "auto")
            await check_server(server_kind, "legacy")

    asyncio.run(run())


def test_real_workflow_stdio_discovery_and_public_wire_calls_are_fail_closed(
    tmp_path: Path,
) -> None:
    async def run() -> None:
        workflow_cli = Path(sysconfig.get_path("scripts")) / "token-io-decoupling-workflow"
        tools_cli = Path(sysconfig.get_path("scripts")) / "token-io-decoupling-tools"
        assert workflow_cli.is_file()
        assert tools_cli.is_file()
        parameters = StdioServerParameters(
            command=str(workflow_cli),
            args=[],
            cwd=Path(__file__).parents[2],
            env={"PYTHONDONTWRITEBYTECODE": "1"},
        )
        async with Client(parameters, mode="auto") as client:
            assert client.protocol_version == "2026-07-28"
            result = await client.list_tools()
            assert {tool.name for tool in result.tools} == WORKFLOW_TOOLS
            context = await client.call_tool(
                "rules_get_context",
                {"payload": {"node_id": "contract", "language": "zh_cn"}},
            )
            assert not context.is_error
            assert '"language": "zh_cn"' in _result_text(context)
            route = await client.call_tool(
                "decide_decoupling_workflow",
                {
                    "payload": {
                        "request": {
                            "task_id": "stdio-route",
                            "task_summary": "Inspect the current execution stage.",
                            "stage": "execution",
                            "language": "en",
                            "mode_locked": True,
                            "mode_count": {"mode": "Single-Agent Coding", "child_count": 0},
                            "capabilities": [],
                            "hard_constraints": [],
                            "source_facts": [],
                            "source_facts_hash": hashlib.sha256(b"[]").hexdigest(),
                            "outbound_data_permitted": False,
                        }
                    }
                },
            )
            assert not route.is_error
            route_result = json.loads(_result_text(route))
            assert route_result["status"] == "available"
            assert route_result["module_id"] == "SM04"
            assert route_result["advisory_only"] is True
            for payload in (
                {"node_id": "contract", "context_version": True},
                {"node_id": "contract", "context_version": 1.0},
                {
                    "node_id": "contract",
                    "context_version": 1,
                    "fragment_ids": [f"fragment-{index}" for index in range(129)],
                },
                {
                    "node_id": "contract",
                    "context_version": 1,
                    "fragment_ids": ["x" * 129],
                },
            ):
                invalid_context = await client.call_tool("rules_get_context", {"payload": payload})
                assert invalid_context.is_error
            extra = await client.call_tool(
                "rules_get_context",
                {"payload": {"node_id": "contract", "language": "en", "path": "/tmp"}},
            )
            assert extra.is_error

            compliance = await client.call_tool(
                "validate_decoupling_compliance",
                {
                    "payload": {
                        "request": {
                            "policy_scope": "skill_maintenance",
                            "candidates": [
                                {
                                    "path": "docs/skill/example.md",
                                    "operation": "create",
                                    "baseline": {"state": "absent"},
                                    "content": "# candidate\n",
                                }
                            ],
                        }
                    }
                },
            )
            assert not compliance.is_error
            compliance_result = json.loads(_result_text(compliance))
            assert compliance_result["status"] == "unknown"
            assert any(
                check["reason_code"] == "compliance_backend_unavailable"
                for check in compliance_result["checks"]
                if check["rule_id"] == "candidate_baseline"
            )

        tools_parameters = StdioServerParameters(
            command=str(tools_cli),
            args=[],
            cwd=Path(__file__).parents[2],
            env={"PYTHONDONTWRITEBYTECODE": "1"},
        )
        async with Client(tools_parameters, mode="auto") as tools_client:
            listed = await tools_client.list_tools()
            assert {tool.name for tool in listed.tools} == TOOLS_SERVER_TOOLS
            diagnostics = await tools_client.call_tool("database_schema_status", {})
            assert not diagnostics.is_error
            assert '"available": false' in _result_text(diagnostics)
            assert "no state path was inspected" in _result_text(diagnostics)

    asyncio.run(run())


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
