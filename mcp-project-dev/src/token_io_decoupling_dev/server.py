"""Compiler MCP server; project access is injected by a trusted factory."""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

from mcp.server import MCPServer
from mcp.server.mcpserver import Context
from mcp.types import CallToolResult, InputRequiredResult, TextContent, Tool, ToolAnnotations

from token_io_decoupling_dev.compiler import (
    CompileError,
    fixed_manifest_path,
    load_json_strict,
    read_fixed_output,
    write_fixed_output,
)
from token_io_decoupling_dev.project_compiler import compile_project_manifest
from token_io_decoupling_dev.project_root import PinnedProjectRoot
from token_io_decoupling_dev.schema import PROJECT_MANIFEST_SCHEMA

SERVER_NAME = "token-io-decoupling-dev"
SERVER_DESCRIPTION = (
    "Standalone development MCP server for deterministic runtime-instruction compilation. "
    "It serves local Codex CLI clients. The compiler validates versioned manifests and source "
    "provenance; project identity is pinned at startup with --project-root, "
    "never selected in tool input. Without a configured root, compiler operations are "
    "unavailable. The service does not call OpenAI, read chats, write Memory, or perform "
    "Git/GitHub operations; compilation only writes its one fixed generated resource. "
    "Compliance checks and output materialization are unavailable."
)
SERVER_INSTRUCTIONS = (
    "Start with dev_capabilities. If compiler tools are available, call "
    "compile_runtime_instructions to compile only the trusted fixed manifest "
    "mcp-project-dev/compiler-manifest.v1.json into the fixed resource "
    "mcp-project-dev/generated/runtime-instructions.v1.json, or call "
    "check_runtime_instructions_freshness for a read-only comparison. Both take no arguments. "
    "Do not infer root, paths, authorization, or availability from discovery. Compilation is "
    "deterministic, local, and fail-closed; drafts with unresolved classifications are rejected. "
    "It never calls OpenAI, the network, Git/GitHub, chats, or Memory."
)
TOOL_DESCRIPTION = (
    "Reports compiler, compliance, and materialization availability before use. "
    "The result includes implemented/unavailable arrays, configured_root (boolean only), "
    "side_effects, and the complete "
    "manifest JSON Schema when a trusted root is configured. Available entries mean the tool is "
    "registered, not that the manifest passes validation. The project manifest schema requires "
    "three source hashes, legacy bindings, and original branch values; live legacy coverage "
    "is also validated when compiling. No arguments. Read-only; reports startup-pinned "
    "configuration. No network, OpenAI API, Git/GitHub, chat, or Memory access."
)


class NoArgumentServer(MCPServer[Any]):
    """Advertise and enforce empty argument objects for every registered tool."""

    async def list_tools(self) -> list[Tool]:
        result = await super().list_tools()
        for tool in result:
            tool.input_schema = {**tool.input_schema, "additionalProperties": False}
        return result

    async def call_tool(
        self, name: str, arguments: dict[str, Any], context: Context[Any, Any] | None = None
    ) -> CallToolResult | InputRequiredResult:
        if arguments:
            return CallToolResult(
                content=[TextContent(type="text", text="This tool accepts no arguments.")],
                is_error=True,
            )
        return await super().call_tool(name, arguments, context)


def dev_capabilities(configured: bool = False) -> dict[str, Any]:
    implemented = [
        {
            "id": "dev_capabilities",
            "status": "available",
            "description": "Return this deterministic capability inventory.",
        }
    ]
    unavailable = [
        {
            "id": "project_compliance_checks",
            "status": "unavailable",
            "description": "Development compliance checks are not implemented in this stage.",
        },
        {
            "id": "output_materialization",
            "status": "unavailable",
            "description": "Development output materialization is not implemented in this stage.",
        },
    ]
    if configured:
        implemented.extend(
            [
                {
                    "id": "compile_runtime_instructions",
                    "status": "available",
                    "description": (
                        "Compile the fixed manifest to the fixed output after strict validation."
                    ),
                },
                {
                    "id": "check_runtime_instructions_freshness",
                    "status": "available",
                    "description": (
                        "Compare current sources and manifest with the fixed output "
                        "without writing."
                    ),
                },
            ]
        )
    else:
        unavailable.append(
            {
                "id": "rule_compiler",
                "status": "unavailable",
                "description": (
                    "No trusted project root is configured; compile_runtime_instructions and "
                    "check_runtime_instructions_freshness are not registered."
                ),
            }
        )
    return {
        "server": SERVER_NAME,
        "status": "compiler_configured" if configured else "unconfigured",
        "client_support": ["local Codex CLI"],
        "transport": "stdio",
        "implemented": implemented,
        "unavailable": unavailable,
        "side_effects": {
            "network": False,
            "openai_api": False,
            "filesystem_read": configured,
            "filesystem_write": configured,
            "git_or_github": False,
            "memory_read_or_write": False,
        },
        "configured_root": configured,
        "compiler_manifest_schema": copy.deepcopy(PROJECT_MANIFEST_SCHEMA) if configured else None,
    }


def create_server(project_root: Path | None = None) -> MCPServer[Any]:
    """Create the server, pinning any startup-specified project root identity."""
    pinned = PinnedProjectRoot.open(project_root) if project_root is not None else None
    root = pinned.path if pinned is not None else None
    server: MCPServer[Any] = NoArgumentServer(
        name=SERVER_NAME,
        version="0.1.0",
        description=SERVER_DESCRIPTION,
        instructions=SERVER_INSTRUCTIONS,
    )

    @server.tool(
        name="dev_capabilities",
        description=TOOL_DESCRIPTION,
        annotations=ToolAnnotations(
            read_only_hint=True,
            destructive_hint=False,
            idempotent_hint=True,
            open_world_hint=False,
        ),
    )
    def capabilities_tool() -> dict[str, Any]:
        return dev_capabilities(root is not None)

    if root is not None:

        @server.tool(
            name="compile_runtime_instructions",
            description=(
                "Compiles the startup-pinned project's fixed manifest into one fixed resource. "
                "Use only after Root reviews classifications. Reads local Markdown/JSON and writes "
                "one file atomically. No args; input cannot choose root, manifest, output, model, "
                "or permissions. Schema, provenance, hash, graph, and budget failures return a "
                "failure with no partial artifact. Result status is compiled or failed; "
                "fields include "
                "format, entry_count, canonical_sha256, fixed output, and partial_artifact=false "
                "on failure. A changed existing artifact requires output_baseline_sha256 equal "
                "to its validated canonical_sha256, not its raw file hash; an explicit baseline "
                "must also match an identical no-op and cannot create a missing output. Without "
                "a baseline only creation or a byte-identical no-op is allowed. A successful "
                "baseline-authorized call can replace the output. No network/OpenAI/Git/Memory."
            ),
            annotations=ToolAnnotations(
                read_only_hint=False,
                destructive_hint=True,
                idempotent_hint=True,
                open_world_hint=False,
            ),
        )
        def compile_tool() -> dict[str, Any]:
            try:
                assert pinned is not None
                pinned.verify()
                manifest = load_json_strict(fixed_manifest_path(root))
                artifact = compile_project_manifest(root, manifest)
                pinned.verify()
                write_fixed_output(
                    root,
                    artifact,
                    expected_baseline_sha256=manifest.get("output_baseline_sha256"),
                    expected_root_identity=pinned.identity,
                )
                return {
                    "status": "compiled",
                    "format": artifact["format"],
                    "entry_count": len(artifact["runtime_entries"]),
                    "canonical_sha256": artifact["canonical_sha256"],
                    "output": "mcp-project-dev/generated/runtime-instructions.v1.json",
                }
            except (CompileError, OSError) as exc:
                return {"status": "failed", "error": str(exc), "partial_artifact": False}

        @server.tool(
            name="check_runtime_instructions_freshness",
            description=(
                "Recompiles the trusted fixed manifest in memory and compares its canonical hash "
                "with the fixed output. Read-only: never creates or changes files. No args or "
                "tool-controlled paths. Returns fresh, stale, missing, or failed; only fresh means "
                "the output matches validated inputs. A failed result contains fresh=false and a "
                "validation error. No network/OpenAI/Git/Memory."
            ),
            annotations=ToolAnnotations(
                read_only_hint=True,
                destructive_hint=False,
                idempotent_hint=True,
                open_world_hint=False,
            ),
        )
        def freshness_tool() -> dict[str, Any]:
            try:
                assert pinned is not None
                pinned.verify()
                artifact = compile_project_manifest(
                    root, load_json_strict(fixed_manifest_path(root))
                )
                pinned.verify()
                present, stored = read_fixed_output(root, expected_root_identity=pinned.identity)
                pinned.verify()
                if not present:
                    return {"status": "missing", "fresh": False}
                return {
                    "status": "fresh" if stored == artifact else "stale",
                    "fresh": stored == artifact,
                    "canonical_sha256": artifact["canonical_sha256"],
                }
            except (CompileError, OSError) as exc:
                return {"status": "failed", "fresh": False, "error": str(exc)}

    return server
