"""Program-supported rule-registry structure, excluding policy prose."""

from __future__ import annotations

import hashlib
import json


class UnsupportedRegistryShapeError(ValueError):
    """资源结构超出当前消费者已实现并审阅的契约。"""


# This contract intentionally covers node IDs, branch enums, evaluation modes,
# and the types/presence of fact/evidence collections. It does not pin owner text.
SUPPORTED_NODE_SHAPES: dict[str, tuple[str, tuple[str, ...]]] = {
    "contract": ("direct", ("ready", "amend", "blocked")),
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
    "repair": ("direct", ("ready", "blocked")),
    "repair_scope": ("direct", ("released", "amend", "blocked")),
    "repair_execution": ("direct", ("complete", "blocked")),
    "repair_handoff": ("direct", ("ready", "blocked")),
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
SUPPORTED_REQUIREMENTS_SHA256 = "86dfc953b6174b0534bacbd5bdbb08a5b823e667981c073ec76d43c2971706ad"


def _supported_nodes(registry: dict[str, object]) -> dict[str, dict[str, object]]:
    """验证注册表版本和固定节点集合，不接受旧语言镜像结构。"""
    if type(registry.get("contract_version")) is not int or registry["contract_version"] != 3:
        raise UnsupportedRegistryShapeError("unsupported registry contract_version")
    if set(registry) != {"contract_version", "nodes"}:
        raise UnsupportedRegistryShapeError("unsupported registry fields")
    nodes = registry.get("nodes")
    if not isinstance(nodes, list):
        raise UnsupportedRegistryShapeError("registry nodes must be an array")
    by_id: dict[str, dict[str, object]] = {}
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
    return by_id


def _validate_node(node_id: str, node: dict[str, object]) -> None:
    """保持机器事实和分支契约，owner 只使用一个当前中文入口。"""
    fields = {
        "node_id",
        "owner_path",
        "owner_section",
        "required_facts",
        "required_evidence",
        "legal_branches",
        "evaluation_mode",
        "failure_action",
        "next_checkpoint_ids",
    }
    if set(node) != fields:
        raise UnsupportedRegistryShapeError(f"unsupported node fields for {node_id}")
    evaluation_mode, branches = SUPPORTED_NODE_SHAPES[node_id]
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
    successors = node.get("next_checkpoint_ids")
    if not isinstance(successors, list) or any(
        not isinstance(successor, str) or successor not in SUPPORTED_NODE_SHAPES
        for successor in successors
    ):
        raise UnsupportedRegistryShapeError(f"invalid successor checkpoint for {node_id}")
    for field in ("owner_path", "owner_section", "failure_action"):
        value = node.get(field)
        if not isinstance(value, str) or not value.strip():
            raise UnsupportedRegistryShapeError(f"{node_id}.{field} must remain nonblank text")


def _requirements_hash(nodes: dict[str, dict[str, object]]) -> str:
    """仅绑定固定需求字段，避免 owner 定位改名改变已审阅的行为契约指纹。"""
    fields = (
        "node_id",
        "evaluation_mode",
        "legal_branches",
        "required_facts",
        "required_evidence",
        "next_checkpoint_ids",
    )
    requirements = []
    for node_id in sorted(nodes):
        requirements.append({field: nodes[node_id][field] for field in fields})
    encoded = json.dumps(
        requirements, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def validate_supported_registry_shape(registry: dict[str, object]) -> None:
    """仅接受当前实现已审阅的单中文注册表，不以外部 Hash 放宽契约。"""
    by_id = _supported_nodes(registry)
    for node_id, node in by_id.items():
        _validate_node(node_id, node)
    if _requirements_hash(by_id) != SUPPORTED_REQUIREMENTS_SHA256:
        raise UnsupportedRegistryShapeError(
            "required facts, evidence or successors changed without a supported contract update"
        )
