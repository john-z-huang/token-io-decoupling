"""Smoke-test the two installed MCP executables through real stdio subprocesses."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path

from codex_sdk import validate_compiled_rule_bundle
from mcp import Client, StdioServerParameters

from token_io_decoupling_core.server_tools import TOOLS_SERVER_TOOLS, WORKFLOW_TOOLS

EXPECTED_TOOLS = {"workflow": WORKFLOW_TOOLS, "tools": TOOLS_SERVER_TOOLS}
SERVER_NAMES = {
    "workflow": "token-io-decoupling-workflow",
    "tools": "token-io-decoupling-tools",
}


def _text(result: object) -> str:
    content = getattr(result, "content", None)
    if not content:
        raise AssertionError("stdio call returned no content")
    return "\n".join(getattr(item, "text", "") for item in content)


async def _exercise(
    cli_path: Path,
    server_kind: str,
    repo_root: Path,
    memory_content: str | None = None,
) -> None:
    if not cli_path.is_absolute():
        raise AssertionError("installed CLI path must be absolute")
    cli_path = cli_path.resolve(strict=True)
    if cli_path.is_relative_to(repo_root):
        raise AssertionError("installed CLI must be an absolute path outside the checkout")

    with tempfile.TemporaryDirectory(prefix="token-io-installed-stdio-") as temporary:
        cwd = Path(temporary).resolve()
        if cwd.is_relative_to(repo_root):
            raise AssertionError("stdio subprocess working directory must be outside the checkout")
        if memory_content is not None:
            memory_file = cwd / ".serena" / "memories" / "notes.md"
            memory_file.parent.mkdir(parents=True)
            memory_file.write_text(memory_content, encoding="utf-8")
        parameters = StdioServerParameters(
            command=str(cli_path),
            args=[],
            cwd=str(cwd),
            env={
                "PATH": "" if memory_content is not None else os.defpath,
                "PYTHONDONTWRITEBYTECODE": "1",
                "PYTHONPATH": "",
            },
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
                or client.server_info.name != SERVER_NAMES[server_kind]
            ):
                raise AssertionError(f"installed {server_kind} server omitted discovery metadata")
            tools = await client.list_tools()
            if server_kind == "tools" and "workflow_capabilities" in client.instructions:
                raise AssertionError("standalone tools inherited workflow entry instructions")
            names = {tool.name for tool in tools.tools}
            if names != EXPECTED_TOOLS[server_kind]:
                raise AssertionError(
                    f"unbound {server_kind} server exposed unexpected tools: {names}"
                )
            if any(not tool.description for tool in tools.tools):
                raise AssertionError(f"installed {server_kind} server has an undescribed tool")
            if server_kind == "tools" and memory_content is not None:
                tail = await client.call_tool(
                    "serena_memory_tail_read", {"memory_path": "notes", "tail_lines": 1}
                )
                tail_data = json.loads(_text(tail))
                if tail.is_error or tail_data.get("content") != memory_content:
                    raise AssertionError("installed local Memory tail did not match this project")
                check = await client.call_tool(
                    "serena_memory_write_check",
                    {
                        "memory_path": "mem:notes.md",
                        "changed_content": memory_content.strip(),
                        "tail_lines": 1,
                    },
                )
                check_data = json.loads(_text(check))
                if check.is_error or check_data.get("success") is not True:
                    raise AssertionError("installed local Memory check did not match this project")
            if server_kind == "workflow":
                capabilities = await client.call_tool("workflow_capabilities", {})
                capability_data = json.loads(_text(capabilities))
                if capabilities.is_error:
                    raise AssertionError("installed unbound CLI did not return capability data")
                details = capability_data["capability_details"]
                if (
                    details["schema_version"] != 3
                    or details["support"]["agent_runtime"]["status"] != "available"
                    or details["runtime"]["binding"]["reason_code"] != "provider_not_configured"
                    or details["runtime"]["server_mode"]["status"] != "public_only"
                    or details["configuration"]["public_interfaces"]["reason_code"]
                    != "tool_dependencies_not_probed"
                ):
                    raise AssertionError("installed CLI misstated capability boundaries")
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
                        "State the requested outcome",
                        "Record hard limits",
                        "acceptance conditions",
                        "Separate facts observed",
                    ),
                    "zh_cn": ("用一句话说明", "记录硬性限制", "验收条件", "区分已观察到的事实"),
                }
                instruction_build_id = None
                for language, expected_actions in contract_actions.items():
                    result = await client.call_tool(
                        "rules_get_context",
                        {
                            "payload": {
                                "node_id": "contract",
                                "language": language,
                                "context_version": 2,
                            }
                        },
                    )
                    if result.is_error:
                        raise AssertionError(
                            f"installed wheel did not return the {language} Contract rule"
                        )
                    context = json.loads(_text(result))
                    build_id = validate_compiled_rule_bundle(context, language)
                    if instruction_build_id is not None and instruction_build_id != build_id:
                        raise AssertionError("installed wheel mixed bilingual instruction builds")
                    instruction_build_id = build_id
                    delivered_text = "\n".join(
                        fragment["text"] for fragment in context["fragments"]
                    )
                    if any(action not in delivered_text for action in expected_actions):
                        raise AssertionError(
                            f"installed wheel returned incomplete {language} Contract Actions"
                        )
            expected_entries = {".serena"} if memory_content is not None else set()
            if {entry.name for entry in cwd.iterdir()} != expected_entries:
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
            [str(cli_path), "setup", "codex", "--dry-run"],
            cwd=temporary_path,
            env={
                "CODEX_HOME": str(temporary_path),
                "PATH": str(empty_path),
                "PYTHONDONTWRITEBYTECODE": "1",
                "PYTHONPATH": "",
            },
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
        if (temporary_path / "config.toml").exists():
            raise AssertionError("setup dry-run wrote a Codex configuration")
        for name in SERVER_NAMES.values():
            command = cli_path.with_name(name).resolve(strict=True)
            if f"Would configure {name}: {command} (args=[])" not in lines:
                raise AssertionError(f"setup dry-run omitted the installed {name} command")
        if (
            "OPENAI_TIMEOUT_MAX_RETRIES" not in result.stdout
            or "Discovery grants no authority" not in result.stdout
        ):
            raise AssertionError("setup dry-run omitted environment forwarding or install limits")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cli", required=True, type=Path)
    args = parser.parse_args()
    repo_root = Path(__file__).resolve().parents[6]
    cli_path = args.cli.resolve(strict=True)
    for content in ("synthetic project A\n", "synthetic project B\n"):
        workflow = cli_path.with_name(SERVER_NAMES["workflow"])
        asyncio.run(_exercise(workflow, "workflow", repo_root, content))
    tools = cli_path.with_name(SERVER_NAMES["tools"])
    asyncio.run(_exercise(tools, "tools", repo_root))
    _exercise_codex_dry_run(cli_path, repo_root)
    print("installed workflow and tools discovery: ok")


if __name__ == "__main__":
    main()
