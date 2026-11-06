"""审核后的 Hook 标识、政策来源和同文档结构契约。"""

from __future__ import annotations

import json
import re

from .models import HookContract, RuleNode, RuleRegistry
from .sources import CompilationError, extract_heading

_CONTRACT = re.compile(r"^```json\s*\n(.*?)^```\s*$", re.MULTILINE | re.DOTALL)
HOOK_ROOT = "references/coding/hooks/"
EVENTS = (
    "task_received",
    "boundary_requested",
    "action_observed",
    "progress_reported",
    "completion_requested",
    "session_resumed",
)
WORKFLOWS = {
    "single-agent": "references/coding/layer-04-workflows/coding-single-agent.md",
    "multi-agent": "references/coding/layer-04-workflows/coding-multi-agent.md",
}
POLICY_SECTION_KEYS = {
    "职责 Decisions 指令": "Role Decisions instructions",
    "职责选项说明": "Role choice descriptions",
    "执行主体 Decisions 指令": "Executor Decisions instructions",
    "执行主体选项说明": "Executor choice descriptions",
    "子代理选择 Decisions 指令": "Child-selection Decisions instructions",
    "子代理选项说明": "Child-candidate choice descriptions",
    "Output Token Decisions 指令": "Output-token Decisions instructions",
    "Output Token 选项说明": "Output-token choice descriptions",
}
# 这些选择仅定义既有细粒度 API 的政策来源，不定义运行节点或跳转。
POLICIES = {
    "child-role-selection": [
        ("shared", "协作与可见性"),
        ("boundary-requested", "职责 Decisions 指令"),
        ("boundary-requested", "职责选项说明"),
        ("boundary-requested", "子代理选择 Decisions 指令"),
        ("boundary-requested", "子代理选项说明"),
    ],
    "task-assignment": [
        ("boundary-requested", "执行主体 Decisions 指令"),
        ("boundary-requested", "执行主体选项说明"),
        ("boundary-requested", "子代理选择 Decisions 指令"),
        ("boundary-requested", "子代理选项说明"),
    ],
    "output-token-routing": [
        ("boundary-requested", "Output Token Decisions 指令"),
        ("boundary-requested", "Output Token 选项说明"),
    ],
    "session-role-ownership": [
        ("shared", "协作与可见性"),
        ("boundary-requested", "委派与输出"),
    ],
    "decision-context-generation": [("shared", "生成指令")],
    "workflow-routing-advice": [
        ("progress-reported", "Control 决策"),
        ("progress-reported", "上下文与建议"),
    ],
    "candidate-compliance": [
        ("shared", "独立工具"),
        ("boundary-requested", "可选资源操作"),
        ("action-observed", "修复证据"),
    ],
    "output-materialization": [
        ("shared", "独立工具"),
        ("boundary-requested", "可选资源操作"),
        ("action-observed", "观察效果"),
    ],
}


INSTRUCTION_IDENTITIES = {
    HOOK_ROOT + "shared.md": "common.shared",
    "SKILL.md#硬约束": "common.hard_constraints",
    **{HOOK_ROOT + event.replace("_", "-") + ".md": "event." + event for event in EVENTS},
    **{path: "workflow." + mode for mode, path in WORKFLOWS.items()},
}


def _author_text(value: object) -> str:
    """作者注册表的文本必须非空，不能由运行时类型注解掩盖无效 JSON。"""
    if not isinstance(value, str) or not value.strip():
        raise CompilationError("author registry text must be nonblank")
    return value


def _author_texts(value: object) -> list[str]:
    """保留要求列表的原始顺序；非数组和空白条目均作为契约错误。"""
    if not isinstance(value, list):
        raise CompilationError("author registry requirements must be string arrays")
    return [_author_text(item) for item in value]


def _author_node(value: object) -> RuleNode:
    """显式重建单中文节点字段，拒绝旧镜像或未审核字段进入产品契约。"""
    if not isinstance(value, dict) or set(value) != set(RuleNode.__annotations__):
        raise CompilationError("unsupported author registry node fields")
    return {
        "node_id": _author_text(value["node_id"]),
        "owner_path": _author_text(value["owner_path"]),
        "owner_section": _author_text(value["owner_section"]),
        "evaluation_mode": _author_text(value["evaluation_mode"]),
        "failure_action": _author_text(value["failure_action"]),
        "required_facts": _author_texts(value["required_facts"]),
        "required_evidence": _author_texts(value["required_evidence"]),
        "legal_branches": _author_texts(value["legal_branches"]),
        "next_checkpoint_ids": _author_texts(value["next_checkpoint_ids"]),
    }


def validate_author_registry(value: object) -> RuleRegistry:
    """验证作者 JSON 的实际结构，旧镜像字段不能被类型注解静默掩盖。"""
    if not isinstance(value, dict) or set(value) != {"contract_version", "nodes"}:
        raise CompilationError("unsupported author registry fields")
    if type(value["contract_version"]) is not int or value["contract_version"] != 3:
        raise CompilationError("unsupported author registry contract")
    if not isinstance(value["nodes"], list):
        raise CompilationError("author registry nodes must be an array")
    return {"contract_version": 3, "nodes": [_author_node(node) for node in value["nodes"]]}


def _contract_strings(value: object, field: str) -> list[str]:
    """解析有界、唯一的事件结构字段；正文判断政策仍来自同一规范文档。"""
    if not isinstance(value, list) or not value:
        raise CompilationError(f"Hook contract {field} must be a nonempty array")
    result = []
    for item in value:
        if not isinstance(item, str) or not item or len(item) > 80:
            raise CompilationError(f"invalid Hook contract {field} value")
        result.append(item)
    if len(result) != len(set(result)):
        raise CompilationError(f"duplicate Hook contract {field} value")
    return result


def _validate_contract_values(contract: HookContract) -> None:
    """核对支持的模式、结果与机器事实键，不在运行时代替 Agent 作语义决定。"""
    if set(contract["modes"]) != set(WORKFLOWS) or set(contract["allowed_outcomes"]) != {
        "continue",
        "needs_evidence",
        "amend",
        "wait",
        "stop",
        "not_applicable",
    }:
        raise CompilationError("unsupported Hook modes/outcomes")
    for key in ("required_facts", "required_evidence"):
        for value in contract[key]:
            if re.fullmatch(r"[a-z][a-z0-9_]*", value) is None:
                raise CompilationError("Hook fact/evidence keys must use snake_case")


def parse_event_contract(source: str, event_id: str, path: str) -> HookContract:
    """从规范文档解析结构字段；判断政策仍以同一文档正文为准。"""
    matches = _CONTRACT.findall(source)
    if len(matches) != 1:
        raise CompilationError(f"expected exactly one Hook contract: {path}")
    value = json.loads(matches[0])
    if not isinstance(value, dict) or set(value) != set(HookContract.__annotations__):
        raise CompilationError(f"unsupported Hook contract fields: {path}")
    if type(value["schema_version"]) is not int or value["schema_version"] != 1:
        raise CompilationError(f"unsupported Hook contract version: {path}")
    if value["event_id"] != event_id:
        raise CompilationError(f"Hook event identity mismatch: {path}")
    contract: HookContract = {
        "schema_version": 1,
        "event_id": event_id,
        "modes": _contract_strings(value["modes"], "modes"),
        "required_facts": _contract_strings(value["required_facts"], "required_facts"),
        "required_evidence": _contract_strings(value["required_evidence"], "required_evidence"),
        "allowed_outcomes": _contract_strings(value["allowed_outcomes"], "allowed_outcomes"),
    }
    _validate_contract_values(contract)
    headings = ("触发", "适用范围", "上下文与证据", "判断", "结果与反馈", "失败与恢复")
    for heading in headings:
        extract_heading(source, heading)
    return contract
