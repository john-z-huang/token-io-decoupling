from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import Any, cast

from mcp import Client, StdioServerParameters
from mcp.server import MCPServer
from mcp.types import TextContent
from token_io_decoupling_core.project_identity import (
    ProjectIdentityError,
    project_id_from_git_common_dir,
)

from token_io_decoupling.server import create_server

PUBLIC_TOOLS = {
    "workflow_capabilities",
    "rules_get_context",
    "workflow_select_child_effort",
    "workflow_generate_decision_context",
    "workflow_select_child_role",
    "workflow_select_executor",
    "workflow_select_child",
    "workflow_assess_output_tokens",
    "database_schema_status",
}


def _tool_names(server: MCPServer[Any]) -> set[str]:
    return {tool.name for tool in server._tool_manager.list_tools()}


def _result_text(result: Any) -> str:
    return cast(TextContent, result.content[0]).text


def test_profiles_have_fixed_disjoint_inventories_and_fail_closed() -> None:
    expected = {
        "workflow": {
            "workflow_capabilities",
            "rules_get_context",
            "workflow_select_child_effort",
            "workflow_generate_decision_context",
            "workflow_select_child_role",
            "workflow_select_executor",
            "workflow_select_child",
            "workflow_assess_output_tokens",
            "workflow_evaluate",
            "evaluate_control_checkpoint",
        },
        "root": {
            "workflow_open",
            "delegation_reserve",
            "delegation_unreserve",
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
            "workflow_select_child_effort",
            "workflow_generate_decision_context",
            "workflow_select_child_role",
            "workflow_select_executor",
            "workflow_select_child",
            "workflow_assess_output_tokens",
            "workflow_evaluate",
            "evaluate_control_checkpoint",
        },
        "root": {
            "workflow_open",
            "delegation_reserve",
            "delegation_unreserve",
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
        for profile in expected:
            await check_profile(profile, "auto")
            await check_profile(profile, "legacy")

    asyncio.run(run())


def test_real_stdio_sdk_discovery_and_public_wire_calls_are_fail_closed(tmp_path: Path) -> None:
    async def run() -> None:
        parameters = StdioServerParameters(
            command=sys.executable,
            args=["-m", "token_io_decoupling.cli"],
            cwd=Path(__file__).parents[2],
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
