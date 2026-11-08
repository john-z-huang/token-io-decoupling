"""已编译规则的版本、结构合同与稳定错误类型。"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any, NamedTuple

SUPPORTED_CONTRACT_VERSION = 3


SUPPORTED_CONTEXT_INDEX_VERSION = 2


DEFAULT_CONTEXT_TEXT_BUDGET = 12_000


MAX_REMAINING_OWNER_REFS = 16


MAX_COMPILED_RESOURCE_BYTES = 32 * 1024 * 1024


_REQUIRED_RESOURCE_SECTIONS = (
    "registry",
    "context_index",
    "nodes",
    "fragments",
    "policies",
    "events",
    "workflows",
)


_REQUIRED_POLICY_SECTIONS = {
    "child-role-selection": ("Role Decisions instructions", "Role choice descriptions"),
    "task-assignment": (
        "Executor Decisions instructions",
        "Executor choice descriptions",
        "Child-selection Decisions instructions",
        "Child-candidate choice descriptions",
    ),
    "output-token-routing": (
        "Output-token Decisions instructions",
        "Output-token choice descriptions",
    ),
}


_DOCUMENT_FIELDS = {"text", "content_sha256", "instruction_ids"}


_ENTRY_FIELDS = {
    "nodes": _DOCUMENT_FIELDS,
    "fragments": {"text", "text_sha256", "instruction_ids"},
    "policies": _DOCUMENT_FIELDS | {"sections", "choices"},
    "workflows": _DOCUMENT_FIELDS,
    "events": _DOCUMENT_FIELDS
    | {
        "schema_version",
        "event_id",
        "modes",
        "required_facts",
        "required_evidence",
        "allowed_outcomes",
    },
}


_SHA256 = re.compile(r"[0-9a-f]{64}")


class RuleLoadError(RuntimeError):
    """批准资源缺失、不完整或无效，不能退回作者源继续执行。"""


class UnknownRuleNodeError(RuleLoadError):
    """所请求节点不属于当前注册表。"""


class IncompatibleRuleContractError(RuleLoadError):
    """已安装资源与消费者支持的结构或固定需求不兼容。"""


class UnsafeRulePathError(RuleLoadError):
    """保留的异常接口；当前 Reader 已不接受作者路径加载。"""


class CompiledDelegationPolicy(NamedTuple):
    """从实际 Hook 段落编译的分工政策及选项，不依赖旧导航卡。"""

    text: str
    content_sha256: str
    sections: dict[str, str]
    choices: dict[str, dict[str, str]]


def _canonical_hash(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(encoded).hexdigest()
