"""Smoke-test the unified installed launcher through real stdio subprocesses."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path

from mcp import Client, StdioServerParameters

EXPECTED_TOOLS = {
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
SERVER_NAMES = {
    "workflow": "token-io-decoupling-workflow",
    "root": "token-io-decoupling-root-agent-tools",
    "worker": "token-io-decoupling-worker-agent-tools",
    "share": "token-io-decoupling-share-tools",
}


def _text(result: object) -> str:
    content = getattr(result, "content", None)
    if not content:
        raise AssertionError("stdio call returned no content")
    return "\n".join(getattr(item, "text", "") for item in content)


async def _exercise(cli_path: Path, profile: str, repo_root: Path) -> None:
    if not cli_path.is_absolute():
        raise AssertionError("installed CLI path must be absolute")
    cli_path = cli_path.resolve(strict=True)
    if cli_path.is_relative_to(repo_root):
        raise AssertionError("installed CLI must be an absolute path outside the checkout")

    with tempfile.TemporaryDirectory(prefix="token-io-installed-stdio-") as temporary:
        cwd = Path(temporary).resolve()
        if cwd.is_relative_to(repo_root):
            raise AssertionError("stdio subprocess working directory must be outside the checkout")
        parameters = StdioServerParameters(
            command=str(cli_path),
            args=["start-mcp-server", "--profile", profile],
            cwd=str(cwd),
            env={"PATH": os.defpath, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONPATH": ""},
        )
        async with Client(parameters, mode="auto") as client:
            if client.protocol_version != "2026-07-28":
                raise AssertionError(
                    f"unexpected negotiated MCP protocol: {client.protocol_version}"
                )
            if (
                client.server_info is None
                or not client.server_info.description
                or not client.instructions
                or profile not in client.instructions
            ):
                raise AssertionError(f"installed {profile} profile omitted discovery metadata")
            tools = await client.list_tools()
            names = {tool.name for tool in tools.tools}
            if names != EXPECTED_TOOLS[profile]:
                raise AssertionError(f"unbound {profile} profile exposed unexpected tools: {names}")
            if any(not tool.description for tool in tools.tools):
                raise AssertionError(f"installed {profile} profile has an undescribed tool")
            if profile == "workflow":
                capabilities = await client.call_tool("workflow_capabilities", {})
                capability_data = json.loads(_text(capabilities))
                if capabilities.is_error or capability_data.get("mode_fallback") != "Native":
                    raise AssertionError("installed unbound CLI did not report Native fallback")
                denied_context = await client.call_tool(
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
                if denied_context.is_error:
                    raise AssertionError("public decision-context denial returned a tool error")
                denied_data = json.loads(_text(denied_context))
                if (
                    denied_data.get("status") != "blocked"
                    or denied_data.get("reason") != "outbound_data_not_permitted"
                ):
                    raise AssertionError("unbound installed workflow called without permission")
                common_decision_facts = {
                    "task_id": "installed-stdio-delegation-smoke",
                    "task_summary": "Synthetic smoke check for delegation advice.",
                    "reviewed_context": (
                        "Synthetic bounded facts only; no user data or repository content."
                    ),
                    "context_input_hash": "a" * 64,
                    "fact_revision": 0,
                    "fact_fingerprint": "b" * 64,
                    "forked_session": False,
                    "mode_reselected_after_fork": True,
                    "outbound_data_permitted": False,
                    "mode": "Multi-Agent Coding",
                }
                delegation_calls = (
                    (
                        "workflow_select_child_role",
                        "child_role",
                        {
                            "created_roles": [],
                            "reserved_roles": [],
                            "available_slots": 1,
                            "user_explicit_create_instruction": False,
                        },
                    ),
                    (
                        "workflow_select_executor",
                        "executor",
                        {"current_session_child_count": 1, "available_slots": 0},
                    ),
                    (
                        "workflow_select_child",
                        "child_candidate",
                        {
                            "candidates": [
                                {
                                    "candidate_ref": "primary-output-1",
                                    "role": "Primary Output",
                                    "responsibility_match": True,
                                    "capability_match": True,
                                    "permission_allows": True,
                                    "same_current_session": True,
                                    "availability": "idle",
                                    "responsibility_summary": "Owns the released slice.",
                                    "capability_summary": "Implementation tools are available.",
                                    "permission_summary": "Slice permits the listed paths.",
                                    "task_relevant_context": "Has the current task facts.",
                                },
                                {
                                    "candidate_ref": "context-refresh-1",
                                    "role": "Context Bootstrap/Refresh",
                                    "responsibility_match": True,
                                    "capability_match": True,
                                    "permission_allows": True,
                                    "same_current_session": True,
                                    "availability": "idle",
                                    "responsibility_summary": "Owns bounded context refresh.",
                                    "capability_summary": "Context lookup tools are available.",
                                    "permission_summary": "Slice permits the lookup paths.",
                                    "task_relevant_context": "Has current source notes.",
                                },
                            ]
                        },
                    ),
                    (
                        "workflow_assess_output_tokens",
                        "output_tokens",
                        {
                            "requested_output_shape": "A concise installed-launcher smoke result.",
                            "expected_output_volume": "One short status summary.",
                            "idle_suitable_child_count": 1,
                            "busy_suitable_child_count": 0,
                        },
                    ),
                )
                for tool_name, expected_decision, specific_facts in delegation_calls:
                    result = await client.call_tool(
                        tool_name,
                        {"payload": {"request": {**common_decision_facts, **specific_facts}}},
                    )
                    if result.is_error:
                        raise AssertionError(
                            f"installed {tool_name} outbound denial returned a tool error"
                        )
                    decision_data = json.loads(_text(result))
                    if (
                        decision_data.get("status") != "blocked"
                        or decision_data.get("reason") != "outbound_data_not_permitted"
                        or decision_data.get("decision") != expected_decision
                    ):
                        raise AssertionError(
                            f"installed {tool_name} did not return its expected outbound denial"
                        )
                    source_policy_hashes = decision_data.get("source_policy_hashes")
                    if (
                        not isinstance(source_policy_hashes, dict)
                        or not source_policy_hashes
                        or any(
                            not isinstance(value, str)
                            or not re.fullmatch(r"[0-9a-fA-F]{64}", value)
                            for value in source_policy_hashes.values()
                        )
                    ):
                        raise AssertionError(
                            f"installed {tool_name} did not return loaded owner policy hashes"
                        )
                contract_actions = {
                    "en": (
                        "1. State the requested outcome in one sentence.",
                        "2. Record hard limits: user prohibitions, allowed runtime environments, "
                        "repository and worktree scope, permitted tools and paths, safety limits, "
                        "and explicitly authorized external effects.",
                        "3. Record material decisions already made, unresolved questions, and "
                        "acceptance conditions.",
                        "4. Separate facts observed from assumptions. Keep unresolved material "
                        "questions out of the implementation release.",
                        "5. Establish task intent and eligible output classification from direct "
                        "authoritative sources. Keep any advisory output separate from the "
                        "Contract; it cannot authorize scope. Apply [Decisions Advisory]("
                        "../../layer-01-fundamental-concepts/execution-planning/"
                        "decisions-advisory.md) "
                        "for advisory policy.",
                    ),
                    "zh_cn": (
                        "1. 用一句话说明用户要求的结果。",
                        "2. 记录硬性限制：用户禁止事项、允许的运行环境、仓库和 worktree 范围、"
                        "允许使用的工具和路径、安全限制，以及明确授权的外部影响。",
                        "3. 记录已经确定的实质性决策、未解决问题和验收条件。",
                        "4. 区分已观察到的事实与假设。未解决的实质性问题不得进入实现发布。",
                        "5. 从直接权威来源确定任务意图和符合条件的输出分类。任何建议输出都与 "
                        "Contract 分开；它不能授权范围。建议政策遵循[Decisions 建议]("
                        "../../layer-01-fundamental-concepts/execution-planning/decisions-advisory_zh_cn.md)。",
                    ),
                }
                for language, expected_actions in contract_actions.items():
                    expected_owner_section = {"en": "Actions", "zh_cn": "动作"}[language]
                    result = await client.call_tool(
                        "rules_get_context",
                        {"payload": {"node_id": "contract", "language": language}},
                    )
                    if result.is_error:
                        raise AssertionError(
                            f"installed wheel did not return the {language} Contract rule"
                        )
                    contract_context = json.loads(_text(result))
                    if (
                        contract_context.get("node_id") != "contract"
                        or contract_context.get("owner_section") != expected_owner_section
                        or contract_context.get("next_checkpoint_ids") != ["mode"]
                    ):
                        raise AssertionError(
                            f"installed wheel returned an unexpected {language} Contract route"
                        )
                    owner_text = contract_context.get("owner_text")
                    if not isinstance(owner_text, str) or any(
                        action not in owner_text for action in expected_actions
                    ):
                        raise AssertionError(
                            f"installed wheel returned incomplete {language} Contract Actions"
                        )
                denied = await client.call_tool(
                    "workflow_evaluate",
                    {
                        "payload": {
                            "node_id": "contract",
                            "expected_revision": 0,
                            "idempotency_key": "unbound-smoke-evaluation",
                        }
                    },
                )
            else:
                protected_calls = {
                    "root": (
                        "workflow_open",
                        {
                            "payload": {
                                "mode_count": {"mode": "Multi-Agent Coding", "child_count": 1},
                                "mode_source": "explicit",
                                "source": {
                                    "uri": "memory://unbound-smoke",
                                    "content_hash": "a" * 64,
                                },
                                "semantic_references": [],
                                "expected_revision": 0,
                                "idempotency_key": "unbound-smoke-open",
                            }
                        },
                    ),
                    "worker": ("worker_get_assignment", {}),
                    "share": ("state_get", {"payload": {}}),
                }
                protected_tool, arguments = protected_calls[profile]
                denied = await client.call_tool(protected_tool, arguments)
            if not denied.is_error or "binding" not in _text(denied).casefold():
                raise AssertionError("unbound profile operation was not denied by its binding gate")
            if profile == "share":
                status = await client.call_tool("database_schema_status", {})
                status_text = _text(status)
                if (
                    status.is_error
                    or '"available": false' not in status_text
                    or "no state path was inspected" not in status_text
                ):
                    raise AssertionError("unbound schema status inspected a state path")
            if list(cwd.iterdir()):
                raise AssertionError(
                    "public stdio calls wrote into their temporary working directory"
                )


def _exercise_codex_dry_run(cli_path: Path, repo_root: Path) -> None:
    if cli_path.name != "token-io-decoupling" or not cli_path.is_file():
        raise AssertionError(f"installed unified executable is missing or mislabeled: {cli_path}")
    if os.name != "nt" and not os.access(cli_path, os.X_OK):
        raise AssertionError("installed executable is not executable")
    with tempfile.TemporaryDirectory(prefix="token-io-codex-dry-run-") as temporary:
        temporary_path = Path(temporary).resolve()
        if temporary_path.is_relative_to(repo_root):
            raise AssertionError("setup dry-run working directory must be outside the checkout")
        empty_path = temporary_path / "empty-path"
        empty_path.mkdir()
        result = subprocess.run(
            [str(cli_path), "setup", "codex", "--all", "--dry-run"],
            cwd=temporary_path,
            env={"PATH": str(empty_path), "PYTHONDONTWRITEBYTECODE": "1", "PYTHONPATH": ""},
            capture_output=True,
            text=True,
            check=False,
            timeout=15,
        )
        if result.returncode != 0:
            raise AssertionError(
                f"installed setup dry-run failed ({result.returncode}): {result.stderr.strip()}"
            )
        lines = result.stdout.splitlines()
        if not lines or lines[0] != "Dry run: no Codex command or configuration preflight was run.":
            raise AssertionError("installed setup dry-run performed or claimed a preflight")
        plan = "Would merge env_vars ['OPENAI_API_KEY', 'OPENAI_BASE_URL'] into: " + ", ".join(
            name for _profile, name in SERVER_NAMES.items()
        )
        if not lines or lines[-1] != plan:
            raise AssertionError("installed setup dry-run omitted the forwarding plan")
        try:
            commands = [json.loads(line) for line in lines[1:-1]]
        except json.JSONDecodeError as exc:
            raise AssertionError("installed setup dry-run printed invalid command JSON") from exc
        expected = [
            [
                "codex",
                "mcp",
                "add",
                name,
                "--",
                str(cli_path.resolve()),
                "start-mcp-server",
                "--profile",
                profile,
            ]
            for profile, name in SERVER_NAMES.items()
        ]
        if commands != expected:
            raise AssertionError(f"installed setup dry-run commands differ: {commands}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cli", required=True, type=Path)
    args = parser.parse_args()
    repo_root = Path(__file__).resolve().parents[3]
    cli_path = args.cli.resolve(strict=True)
    for profile in EXPECTED_TOOLS:
        asyncio.run(_exercise(cli_path, profile, repo_root))
    _exercise_codex_dry_run(cli_path, repo_root)
    print("installed unified launcher profile discovery: ok")


if __name__ == "__main__":
    main()
