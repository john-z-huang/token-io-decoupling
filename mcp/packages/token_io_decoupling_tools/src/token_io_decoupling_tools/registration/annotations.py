"""工具的读写、破坏性、幂等性及外部世界注解。"""

from __future__ import annotations

from mcp.types import ToolAnnotations

_LOCAL_READ = ToolAnnotations(read_only_hint=True, open_world_hint=False)


_REMOTE_READ = ToolAnnotations(read_only_hint=True, open_world_hint=True)


_AI_READ = ToolAnnotations(
    read_only_hint=True, destructive_hint=False, idempotent_hint=False, open_world_hint=True
)


_MEMORY_READ = ToolAnnotations(
    read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=False
)


_LOCAL_WRITE = ToolAnnotations(
    read_only_hint=False, destructive_hint=False, idempotent_hint=False, open_world_hint=False
)


_LOCAL_DESTRUCTIVE = ToolAnnotations(
    read_only_hint=False, destructive_hint=True, idempotent_hint=False, open_world_hint=False
)


_LOCAL_IDEMPOTENT = ToolAnnotations(
    read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False
)


_REMOTE_WRITE = ToolAnnotations(
    read_only_hint=False, destructive_hint=False, idempotent_hint=False, open_world_hint=True
)


_REMOTE_DESTRUCTIVE = ToolAnnotations(
    read_only_hint=False, destructive_hint=True, idempotent_hint=False, open_world_hint=True
)


_REMOTE_IDEMPOTENT = ToolAnnotations(
    read_only_hint=False, destructive_hint=True, idempotent_hint=True, open_world_hint=True
)
