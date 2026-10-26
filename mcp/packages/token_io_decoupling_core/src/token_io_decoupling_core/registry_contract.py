"""Program-supported rule-registry structure, excluding policy prose."""

from __future__ import annotations

import hashlib
import json
from typing import Any


class UnsupportedRegistryShapeError(ValueError):
    """The registry structure is not implemented by this package version."""


# This contract intentionally covers node IDs, branch enums, evaluation modes,
# and the types/presence of fact/evidence collections. It does not pin owner text.
SUPPORTED_NODE_SHAPES: dict[str, tuple[str, tuple[str, ...]]] = {
    "contract": ("direct", ("ready", "amend", "blocked")),
    "environment": ("hybrid", ("available", "partially unavailable", "blocked")),
    "mode": ("hybrid", ("single-agent", "multi-agent", "blocked")),
    "context": ("direct", ("sufficient", "request evidence", "blocked")),
    "decision": ("hybrid", ("decided", "evidence-on-demand", "blocked")),
    "slice": ("deterministic", ("released", "amend", "stop")),
    "delegation": ("deterministic", ("not applicable", "reserved", "bound", "blocked")),
    "implementation": ("direct", ("complete", "blocked", "return for control")),
    "control": ("hybrid", ("continue", "amend", "stop", "evidence-on-demand")),
    "verification": (
        "hybrid",
        ("pass", "failure", "inconclusive", "not applicable with reason"),
    ),
    "repair": ("hybrid", ("not applicable with reason", "repair", "blocked")),
    "documentation": ("hybrid", ("complete", "not applicable with reason", "blocked")),
    "git": ("hybrid", ("no Git effect", "authorized effect", "blocked")),
    "acceptance": ("hybrid", ("complete", "incomplete", "blocked")),
    "task_intent": ("semantic", ("coding", "not coding", "unclear")),
    "output_class": (
        "semantic",
        ("code_configuration", "skill_instructions", "ordinary_documentation", "other", "unknown"),
    ),
    "contract_change": ("semantic", ("unchanged", "amend", "blocked")),
    "verification_impact": (
        "semantic",
        ("implementation/content", "documentation", "Git metadata", "multiple", "none"),
    ),
}

# Exact checkpoint facts and evidence are part of the executable contract. This
# digest is reviewed with the registry and implementation when that contract moves.
SUPPORTED_REQUIREMENTS_SHA256 = "13ec1bb451940e9f28ddbde4d3a41f7a72224b6f90d12aaf83760eea28add086"


def validate_supported_registry_shape(registry: dict[str, Any]) -> None:
    """Reject structural changes until this package's contract is updated."""
    if type(registry.get("contract_version")) is not int or registry["contract_version"] != 1:
        raise UnsupportedRegistryShapeError("unsupported registry contract_version")
    nodes = registry.get("nodes")
    if not isinstance(nodes, list):
        raise UnsupportedRegistryShapeError("registry nodes must be an array")
    by_id: dict[str, dict[str, Any]] = {}
    for node in nodes:
        if not isinstance(node, dict) or not isinstance(node.get("node_id"), str):
            raise UnsupportedRegistryShapeError("each node must have a string node_id")
        node_id = node["node_id"]
        if node_id in by_id:
            raise UnsupportedRegistryShapeError(f"duplicate node_id: {node_id}")
        by_id[node_id] = node
    if set(by_id) != set(SUPPORTED_NODE_SHAPES):
        missing = sorted(set(SUPPORTED_NODE_SHAPES) - set(by_id))
        extra = sorted(set(by_id) - set(SUPPORTED_NODE_SHAPES))
        raise UnsupportedRegistryShapeError(
            f"node ID set changed; missing={missing}, extra={extra}"
        )

    for node_id, (evaluation_mode, branches) in SUPPORTED_NODE_SHAPES.items():
        node = by_id[node_id]
        if node.get("evaluation_mode") != evaluation_mode:
            raise UnsupportedRegistryShapeError(f"evaluation mode changed for {node_id}")
        if node.get("legal_branches") != list(branches):
            raise UnsupportedRegistryShapeError(f"legal branches changed for {node_id}")
        for field in ("required_facts", "required_evidence"):
            values = node.get(field)
            if not isinstance(values, list) or not all(isinstance(value, str) for value in values):
                raise UnsupportedRegistryShapeError(
                    f"{node_id}.{field} must remain an array of strings"
                )
        if not isinstance(node.get("owner_path"), str) or not isinstance(
            node.get("owner_section"), str
        ):
            raise UnsupportedRegistryShapeError(f"English owner mapping is malformed for {node_id}")
        mirror = node.get("owner_mirrors", {}).get("zh_cn")
        if (
            not isinstance(mirror, dict)
            or not isinstance(mirror.get("path"), str)
            or not isinstance(mirror.get("section"), str)
        ):
            raise UnsupportedRegistryShapeError(f"Chinese owner mapping is malformed for {node_id}")

    requirements = [
        {
            field: by_id[node_id][field]
            for field in (
                "node_id",
                "evaluation_mode",
                "legal_branches",
                "required_facts",
                "required_evidence",
            )
        }
        for node_id in sorted(by_id)
    ]
    encoded = json.dumps(
        requirements, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    if hashlib.sha256(encoded).hexdigest() != SUPPORTED_REQUIREMENTS_SHA256:
        raise UnsupportedRegistryShapeError(
            "required facts or evidence changed without a supported contract update"
        )
