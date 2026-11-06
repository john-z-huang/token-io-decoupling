"""Flat, read-only MCP interfaces for a trusted Serena Memory reader."""

from __future__ import annotations

from typing import Annotated, Any

from mcp.types import ToolAnnotations
from pydantic import Field

from token_io_decoupling_tools.serena_memory import SerenaMemoryReadService
from token_io_decoupling_transport.registration import ToolRegistrar

MemoryPath = Annotated[
    str,
    Field(
        strict=True,
        min_length=1,
        max_length=4096,
        description=(
            "Relative name under the startup directory project's .serena/memories; "
            "optional mem: prefix and .md suffix."
        ),
    ),
]
TailLines = Annotated[
    int,
    Field(
        strict=True,
        ge=0,
        le=10000,
        description="Last N logical lines; zero returns line-count metadata with empty content.",
    ),
]
ChangedContent = Annotated[
    str,
    Field(
        strict=True,
        min_length=1,
        max_length=64000,
        description="Nonempty text to find literally in the tail; no normalization or regex.",
    ),
]


def register_serena_memory_tools(
    registrar: ToolRegistrar, service: SerenaMemoryReadService
) -> None:
    """Expose independent configured-scope read operations."""

    def tail_read(memory_path: MemoryPath, tail_lines: TailLines) -> dict[str, Any]:
        return service.tail_read(memory_path, tail_lines)

    def write_check(
        memory_path: MemoryPath, changed_content: ChangedContent, tail_lines: TailLines
    ) -> dict[str, Any]:
        return service.write_check(memory_path, changed_content, tail_lines)

    for name, callback in (
        ("serena_memory_tail_read", tail_read),
        ("serena_memory_write_check", write_check),
    ):
        if registrar.include(name):
            registrar.server.tool(
                name=name,
                description=registrar.description_for(name),
                annotations=ToolAnnotations(
                    read_only_hint=True,
                    destructive_hint=False,
                    idempotent_hint=True,
                    open_world_hint=False,
                ),
                structured_output=False,
            )(callback)
