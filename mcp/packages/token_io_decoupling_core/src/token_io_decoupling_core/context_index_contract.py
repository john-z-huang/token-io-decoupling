"""Standard-library validation shared by runtime loading and package builds."""

from __future__ import annotations

import re
from typing import Any, cast

from token_io_decoupling_core.owner_paths import OPTIONAL_FRAGMENT_OWNER_BINDINGS

_FRAGMENT_ID = re.compile(r"^[a-z][a-z0-9._-]{0,119}$")
CONTEXT_INDEX_SCHEMA_VERSION = 1
MAX_CONTEXT_FRAGMENTS = 64


def validate_context_index(
    index: Any, registry: Any, *, max_fragments: int = MAX_CONTEXT_FRAGMENTS
) -> None:
    """Validate version, node/fragment identity, references, paths, and acyclic closure."""
    if not isinstance(index, dict) or type(index.get("schema_version")) is not int:
        raise ValueError("context index must have an integer schema_version")
    if set(index) != {"schema_version", "nodes", "fragments"}:
        raise ValueError("context index has unsupported fields")
    if index["schema_version"] != CONTEXT_INDEX_SCHEMA_VERSION:
        raise ValueError("unsupported context index schema_version")
    nodes = index.get("nodes")
    fragments = index.get("fragments")
    if not isinstance(nodes, list) or not isinstance(fragments, list) or not fragments:
        raise ValueError("context index nodes and fragments must be arrays")

    registry_value = registry if isinstance(registry, dict) else registry.model_dump(mode="json")
    registry_nodes = registry_value.get("nodes")
    if not isinstance(registry_nodes, list):
        raise ValueError("rule registry nodes must be an array")
    registry_ids: set[str] = set()
    registry_sections: dict[str, tuple[str, str]] = {}
    for node in registry_nodes:
        node_id = node.get("node_id") if isinstance(node, dict) else node.node_id
        if not isinstance(node_id, str) or not node_id:
            raise ValueError("registry node IDs must be non-empty strings")
        if node_id in registry_ids:
            raise ValueError(f"duplicate registry node: {node_id}")
        registry_ids.add(node_id)
        if isinstance(node, dict):
            owner_path = node.get("owner_path")
            owner_section = node.get("owner_section")
            mirror = node.get("owner_mirrors", {}).get("zh_cn", {})
            mirror_path = mirror.get("path") if isinstance(mirror, dict) else None
            mirror_section = mirror.get("section") if isinstance(mirror, dict) else None
        else:
            owner_path = node.owner_path
            owner_section = node.owner_section
            mirror = node.owner_mirrors.get("zh_cn")
            mirror_path = mirror.path if mirror is not None else None
            mirror_section = mirror.section if mirror is not None else None
        for value, limit, label in (
            (owner_path, 512, "owner_path"),
            (owner_section, 256, "owner_section"),
            (mirror_path, 512, "zh_cn owner_path"),
            (mirror_section, 256, "zh_cn owner_section"),
        ):
            if (
                not isinstance(value, str)
                or not value
                or value != value.strip()
                or len(value) > limit
            ):
                raise ValueError(f"invalid bounded {label} for registry node {node_id}")
        registry_sections[node_id] = (cast(str, owner_section), cast(str, mirror_section))

    node_map: dict[str, dict[str, Any]] = {}
    for node in nodes:
        if not isinstance(node, dict) or set(node) != {"node_id", "default_fragment_ids"}:
            raise ValueError("context index nodes have unsupported fields")
        if not _canonical_string(node.get("node_id")):
            raise ValueError("context index nodes must have string node_id values")
        node_id = node["node_id"]
        if node_id in node_map:
            raise ValueError(f"duplicate context index node: {node_id}")
        defaults = node.get("default_fragment_ids")
        if (
            not isinstance(defaults, list)
            or not defaults
            or not all(_canonical_string(item) for item in defaults)
        ):
            raise ValueError(f"invalid default fragments for {node_id}")
        if len(defaults) != len(set(defaults)):
            raise ValueError(f"duplicate default fragment for {node_id}")
        node_map[node_id] = node
    if set(node_map) != registry_ids:
        raise ValueError("context index node set does not match registry")

    fragment_map: dict[str, dict[str, Any]] = {}
    for fragment in fragments:
        if not isinstance(fragment, dict):
            raise ValueError("context fragments must be objects")
        if set(fragment) not in (
            {"fragment_id", "node_id", "section_en", "section_zh_cn"},
            {"fragment_id", "node_id", "section_en", "section_zh_cn", "dependencies"},
        ):
            raise ValueError("context fragments have unsupported fields")
        fragment_id = fragment.get("fragment_id")
        if not _canonical_string(fragment_id) or not _FRAGMENT_ID.fullmatch(fragment_id):
            raise ValueError(f"invalid context fragment_id: {fragment_id!r}")
        if fragment_id in fragment_map:
            raise ValueError(f"duplicate context fragment_id: {fragment_id}")
        if not _canonical_string(fragment.get("node_id")):
            raise ValueError(f"invalid node_id for context fragment {fragment_id}")
        if fragment.get("node_id") not in registry_ids:
            raise ValueError(f"unknown registry node for fragment {fragment_id}")
        if any(
            not _canonical_string(fragment.get(key)) or len(fragment[key]) > 256
            for key in ("section_en", "section_zh_cn")
        ):
            raise ValueError(f"invalid bilingual section mapping for {fragment_id}")
        dependencies = fragment.get("dependencies", [])
        if not isinstance(dependencies, list) or not all(
            _canonical_string(item) for item in dependencies
        ):
            raise ValueError(f"invalid dependencies for {fragment_id}")
        if len(dependencies) != len(set(dependencies)):
            raise ValueError(f"duplicate dependency for {fragment_id}")
        fragment_map[fragment_id] = fragment
    if len(fragment_map) > max_fragments:
        raise ValueError("context index exceeds the fragment limit")

    missing_owner_fragments = set(OPTIONAL_FRAGMENT_OWNER_BINDINGS) - set(fragment_map)
    if missing_owner_fragments:
        raise ValueError(
            "context index is missing controlled owner fragments: "
            + ", ".join(sorted(missing_owner_fragments))
        )
    for fragment_id, (expected_node, _owner_key) in OPTIONAL_FRAGMENT_OWNER_BINDINGS.items():
        fragment = fragment_map[fragment_id]
        if fragment["node_id"] != expected_node:
            raise ValueError(
                f"controlled owner fragment {fragment_id} must belong to node {expected_node}"
            )
        if fragment["section_en"] != "General rules" or fragment["section_zh_cn"] != "通用规范":
            raise ValueError(
                f"controlled owner fragment {fragment_id} must select General rules sections"
            )

    for node_id, node in node_map.items():
        default_fragments: list[dict[str, Any]] = []
        for fragment_id in node["default_fragment_ids"]:
            if fragment_id not in fragment_map:
                raise ValueError(f"unknown default fragment {fragment_id} for node {node_id}")
            fragment = fragment_map[fragment_id]
            if fragment["node_id"] != node_id:
                raise ValueError(
                    f"default fragment {fragment_id} does not belong to node {node_id}"
                )
            default_fragments.append(fragment)
        owner_section, mirror_section = registry_sections[node_id]
        if not any(
            fragment["section_en"] == owner_section and fragment["section_zh_cn"] == mirror_section
            for fragment in default_fragments
        ):
            raise ValueError(
                f"default fragments for {node_id} do not include registry owner sections"
            )
    for fragment_id, fragment in fragment_map.items():
        for dependency in fragment.get("dependencies", []):
            if dependency not in fragment_map:
                raise ValueError(f"unknown dependency {dependency} for {fragment_id}")

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(fragment_id: str) -> None:
        if fragment_id in visiting:
            raise ValueError(f"dependency cycle at {fragment_id}")
        if fragment_id in visited:
            return
        visiting.add(fragment_id)
        for dependency in fragment_map[fragment_id].get("dependencies", []):
            visit(dependency)
        visiting.remove(fragment_id)
        visited.add(fragment_id)

    for fragment_id in fragment_map:
        visit(fragment_id)


def _canonical_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value) and value == value.strip()
