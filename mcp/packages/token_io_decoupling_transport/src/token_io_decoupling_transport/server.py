"""Shared MCP server behavior, independent of either service implementation."""

from typing import Any

from mcp.server import MCPServer
from mcp.server.mcpserver import Context
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import ValidationError


class SafeMCPServer(MCPServer[Any]):
    """Keep SDK argument-validation errors from echoing caller-supplied values."""

    async def call_tool(
        self, name: str, arguments: dict[str, Any], context: Context | None = None
    ) -> Any:
        try:
            return await super().call_tool(name, arguments, context)
        except ToolError as error:
            if isinstance(error.__cause__, ValidationError):
                raise ToolError(
                    "Invalid tool arguments; review the published input schema."
                ) from None
            raise
