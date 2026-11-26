"""Flat, read-only MCP interfaces for a trusted Serena Memory reader."""

from __future__ import annotations

from typing import Annotated, Any

from pydantic import Field

from token_io_decoupling_tools.serena_memory import SerenaMemoryReadService

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


def create_memory_callbacks(service: SerenaMemoryReadService) -> dict[str, Any]:
    """Expose only the tools server's two public, configured-scope read operations."""

    def tail_read(memory_path: MemoryPath, tail_lines: TailLines) -> dict[str, Any]:
        return service.tail_read(memory_path, tail_lines)

    def write_check(
        memory_path: MemoryPath, changed_content: ChangedContent, tail_lines: TailLines
    ) -> dict[str, Any]:
        return service.write_check(memory_path, changed_content, tail_lines)

    return {
        "serena_memory_tail_read": tail_read,
        "serena_memory_write_check": write_check,
    }
