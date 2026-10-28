"""Smoke-test the unified installed launcher through real stdio subprocesses."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import subprocess
import tempfile
from pathlib import Path

from mcp import Client, StdioServerParameters

EXPECTED_TOOLS = {
    "workflow": {
        "workflow_capabilities",
        "rules_get_context",
        "workflow_select_child_effort",
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
                for language, expected_text in (
                    ("en", "Before Mode and Session pass"),
                    ("zh_cn", "Mode 和 Session 通过前"),
                ):
                    result = await client.call_tool(
                        "rules_get_context",
                        {"payload": {"node_id": "contract", "language": language}},
                    )
                    if result.is_error or expected_text not in _text(result):
                        raise AssertionError(
                            f"installed wheel did not return the {language} Contract rule"
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
    repo_root = Path(__file__).resolve().parents[2]
    cli_path = args.cli.resolve(strict=True)
    for profile in EXPECTED_TOOLS:
        asyncio.run(_exercise(cli_path, profile, repo_root))
    _exercise_codex_dry_run(cli_path, repo_root)
    print("installed unified launcher profile discovery: ok")


if __name__ == "__main__":
    main()
