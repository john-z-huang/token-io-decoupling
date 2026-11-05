"""Read-only discovery server for the development-tool boundary."""

from __future__ import annotations

from typing import Any

from mcp.server import MCPServer
from mcp.types import ToolAnnotations

SERVER_NAME = "token-io-decoupling-dev"
SERVER_DESCRIPTION = (
    "Standalone development MCP server for discovering project-maintenance capabilities. "
    "This skeleton exposes only a read-only capability inventory; it does not compile rules, "
    "run compliance checks, materialize files, or perform Git operations."
)
SERVER_INSTRUCTIONS = (
    "Use this local Codex CLI MCP server to inspect the current development-tool boundary. "
    "Start with dev_capabilities, which takes no arguments and reports implemented versus "
    "unavailable capabilities. This skeleton currently implements only deterministic, "
    "read-only discovery. It does not access project files, call OpenAI, access the network, "
    "read or write Memory, or run Git/GitHub operations. Future compiler, compliance, and "
    "materialization operations are unavailable; do not infer that this server performs them."
)
TOOL_DESCRIPTION = (
    "Reports the standalone development server's current implemented and unavailable "
    "capabilities. Use before relying on development automation or to identify the boundary "
    "between this server and the product MCP server. The result contains server, status, "
    "implemented, unavailable, and side_effects fields. status=skeleton describes the "
    "current project stage; implemented entries with status=available can be called, while "
    "unavailable entries are not implemented. Discovery grants no authority for later writes. "
    "This no-argument tool is deterministic and read-only; it does not inspect repository "
    "contents or execute checks. Compiler, compliance-check, and output-materialization "
    "capabilities are currently unavailable. No project-file read/write, network, OpenAI API, "
    "Git/GitHub, or Memory access occurs."
)

CAPABILITIES: dict[str, Any] = {
    "server": SERVER_NAME,
    "status": "skeleton",
    "client_support": ["local Codex CLI"],
    "transport": "stdio",
    "implemented": [
        {
            "id": "dev_capabilities",
            "status": "available",
            "description": "Return this deterministic development capability inventory.",
        }
    ],
    "unavailable": [
        {
            "id": "rule_compiler",
            "status": "unavailable",
            "description": "Rule compilation is not implemented in this stage.",
        },
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
    ],
    "side_effects": {
        "network": False,
        "openai_api": False,
        "filesystem_read": False,
        "filesystem_write": False,
        "git_or_github": False,
        "memory_read_or_write": False,
    },
}


def dev_capabilities() -> dict[str, Any]:
    """Return a fresh JSON-compatible capability inventory."""
    return {
        **CAPABILITIES,
        "implemented": [dict(item) for item in CAPABILITIES["implemented"]],
        "unavailable": [dict(item) for item in CAPABILITIES["unavailable"]],
        "client_support": list(CAPABILITIES["client_support"]),
        "side_effects": dict(CAPABILITIES["side_effects"]),
    }


def create_server() -> MCPServer[Any]:
    """Create the standalone development MCP server."""
    server: MCPServer[Any] = MCPServer(
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
        return dev_capabilities()

    return server
