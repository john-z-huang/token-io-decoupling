"""Read-only adapter for the legacy registry/index; output remains a review draft."""

from __future__ import annotations

import ast
import hashlib
from pathlib import Path
from typing import Any

from token_io_decoupling_core.context_index_contract import validate_context_index
from token_io_decoupling_core.heading_parser import extract_heading
from token_io_decoupling_core.registry_contract import validate_supported_registry_shape

from .compiler import CompileError, _source_path, load_json_strict

OWNER_SOURCE = "mcp/packages/token_io_decoupling_core/src/token_io_decoupling_core/owner_paths.py"


def read_legacy_sources(root: Path) -> dict[str, Any]:
    """Validate the actual registry, index, and literal owner mapping without executing it."""
    registry_path = _source_path(root, "mcp/rule-registry.json")
    index_path = _source_path(root, "mcp/rule-context-index.json")
    owner_path = _source_path(root, OWNER_SOURCE)
    registry = load_json_strict(registry_path)
    index = load_json_strict(index_path)
    try:
        validate_supported_registry_shape(registry)
        validate_context_index(index, registry)
        module = ast.parse(owner_path.read_text(encoding="utf-8"), filename=OWNER_SOURCE)
        wanted = {"OWNER_PATHS", "DELEGATION_POLICY_OWNERS", "OPTIONAL_FRAGMENT_OWNER_BINDINGS"}
        values: dict[str, Any] = {}
        for statement in module.body:
            if not isinstance(statement, (ast.AnnAssign, ast.Assign)):
                continue
            target = statement.target if isinstance(statement, ast.AnnAssign) else None
            if isinstance(statement, ast.Assign) and len(statement.targets) == 1:
                target = statement.targets[0]
            if isinstance(target, ast.Name) and target.id in wanted:
                if target.id in values or statement.value is None:
                    raise ValueError(f"duplicate or missing owner mapping: {target.id}")
                values[target.id] = ast.literal_eval(statement.value)
        if set(values) != wanted:
            raise ValueError("owner mapping is missing required literal assignments")
        owners = values["OWNER_PATHS"]
        policies = values["DELEGATION_POLICY_OWNERS"]
        optional = values["OPTIONAL_FRAGMENT_OWNER_BINDINGS"]
        if (
            not isinstance(owners, dict)
            or len(owners) != 8
            or any(not isinstance(k, str) or not isinstance(v, str) for k, v in owners.items())
            or not isinstance(policies, tuple)
            or len(policies) != 5
            or len(set(policies)) != 5
            or any(owner not in owners for owner in policies)
            or not isinstance(optional, dict)
            or len(optional) != 3
            or any(
                not isinstance(fragment, str)
                or not isinstance(pair, tuple)
                or len(pair) != 2
                or not all(isinstance(value, str) for value in pair)
                or pair[1] not in owners
                for fragment, pair in optional.items()
            )
            or set(policies) | {pair[1] for pair in optional.values()} != set(owners)
        ):
            raise ValueError("unsupported owner mapping shape")
        fragments = {item["fragment_id"]: item for item in index["fragments"]}
        for fragment, (node, _owner) in optional.items():
            if fragment not in fragments or fragments[fragment]["node_id"] != node:
                raise ValueError(f"invalid optional fragment mapping: {fragment}")
    except (
        OSError,
        UnicodeError,
        SyntaxError,
        TypeError,
        ValueError,
        KeyError,
        AttributeError,
    ) as exc:
        raise CompileError(f"invalid legacy project sources: {exc}") from exc
    return {
        "registry": registry,
        "index": index,
        "owner_paths": owners,
        "delegation_policy_owners": policies,
        "optional_fragment_owner_bindings": optional,
        "source_hashes": {
            "registry_sha256": hashlib.sha256(registry_path.read_bytes()).hexdigest(),
            "context_index_sha256": hashlib.sha256(index_path.read_bytes()).hexdigest(),
            "owner_paths_sha256": hashlib.sha256(owner_path.read_bytes()).hexdigest(),
        },
    }


def build_legacy_mapping_draft(root: Path) -> dict[str, Any]:
    """Inventory current IDs and source mappings without guessing reference classes."""
    sources = read_legacy_sources(root)
    registry, index = sources["registry"], sources["index"]
    OWNER_PATHS = sources["owner_paths"]
    DELEGATION_POLICY_OWNERS = sources["delegation_policy_owners"]
    OPTIONAL_FRAGMENT_OWNER_BINDINGS = sources["optional_fragment_owner_bindings"]
    registry_hash = sources["source_hashes"]["registry_sha256"]
    index_hash = sources["source_hashes"]["context_index_sha256"]
    nodes = {item["node_id"]: item for item in registry["nodes"]}
    fragments = []
    for item in index["fragments"]:
        node = nodes[item["node_id"]]
        mirror = node["owner_mirrors"]["zh_cn"]
        optional = OPTIONAL_FRAGMENT_OWNER_BINDINGS.get(item["fragment_id"])
        source_path_en = OWNER_PATHS[optional[1]] if optional else node["owner_path"]
        source_path_zh = (
            source_path_en.removesuffix(".md") + "_zh_cn.md" if optional else mirror["path"]
        )

        def source_record(path_text: str, heading: str, locale: str) -> dict[str, str]:
            path = Path(path_text)
            current = root
            for part in path.parts:
                current = current / part
                if current.is_symlink():
                    raise ValueError(f"legacy source contains a symlink: {path_text}")
            resolved = current.resolve(strict=True)
            if not resolved.is_relative_to(root.resolve(strict=True)) or not resolved.is_file():
                raise ValueError(f"legacy source path escapes or is missing: {path_text}")
            raw = resolved.read_bytes()
            excerpt = extract_heading(raw.decode("utf-8"), heading).strip()
            return {
                "path": path_text,
                "heading": heading,
                "locale": locale,
                "source_sha256": hashlib.sha256(raw).hexdigest(),
                "excerpt_sha256": hashlib.sha256(excerpt.encode("utf-8")).hexdigest(),
            }

        fragments.append(
            {
                "legacy_fragment_id": item["fragment_id"],
                "legacy_node_id": item["node_id"],
                "source_en": source_record(source_path_en, item["section_en"], "en"),
                "source_zh_cn": source_record(source_path_zh, item["section_zh_cn"], "zh_cn"),
                "legacy_dependencies_unclassified": list(item.get("dependencies", [])),
                "default": item["fragment_id"]
                in next(n for n in index["nodes"] if n["node_id"] == item["node_id"])[
                    "default_fragment_ids"
                ],
                "reference_classification": "UNCLASSIFIED_REQUIRES_ROOT_REVIEW",
                "actions_branches_pass_failure": "NOT_IN_LEGACY_INDEX_REQUIRES_EXPLICIT_MAPPING",
            }
        )
    owners = []
    for key, path in OWNER_PATHS.items():
        owners.append(
            {
                "legacy_owner_id": key,
                "source_en": path,
                "source_zh_cn": path.removesuffix(".md") + "_zh_cn.md",
                "binding_type": (
                    "delegation_policy_owner"
                    if key in DELEGATION_POLICY_OWNERS
                    else "optional_fragment_owner"
                ),
                "fragment_binding": next(
                    (
                        fragment
                        for fragment, (_node, owner) in OPTIONAL_FRAGMENT_OWNER_BINDINGS.items()
                        if owner == key
                    ),
                    None,
                ),
                "reference_classification": "UNCLASSIFIED_REQUIRES_ROOT_REVIEW",
            }
        )
    return {
        "draft_format": "token-io-legacy-mapping-review-draft/v1",
        "review_status": "DRAFT_REQUIRES_ROOT_REVIEW",
        "legacy_contract_version": registry["contract_version"],
        "legacy_context_index_version": index["schema_version"],
        "legacy_source_hashes": {
            "registry_sha256": registry_hash,
            "context_index_sha256": index_hash,
            "owner_paths_sha256": sources["source_hashes"]["owner_paths_sha256"],
        },
        "legacy_source_provenance": [
            {
                "path": "mcp/rule-registry.json",
                "version": registry["contract_version"],
                "source_sha256": registry_hash,
            },
            {
                "path": "mcp/rule-context-index.json",
                "version": index["schema_version"],
                "source_sha256": index_hash,
            },
            {"path": OWNER_SOURCE, "source_sha256": sources["source_hashes"]["owner_paths_sha256"]},
        ],
        "nodes": sorted(nodes),
        "fragments": fragments,
        "owner_mappings": owners,
        "classification_policy": (
            "No dependency is treated as required, conditional, navigation, or already "
            "included until reviewed."
        ),
    }
