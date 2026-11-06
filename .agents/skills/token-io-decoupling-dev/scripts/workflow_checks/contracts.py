"""校验文档中的 Hook 契约、语义边界和来源整合映射。"""

from __future__ import annotations

import json
import re
from pathlib import Path

from markdown_discovery import discover_markdown

from workflow_checks.chinese import canonical_issues
from workflow_checks.semantics import SEMANTIC_REQUIREMENTS
from workflow_checks.sources import validate_source_map

ROOT = Path(__file__).resolve().parents[5]
SKILL = Path("instruction-compiler/sources/skill")
HOOKS = SKILL / "references/coding/hooks"
SOURCE_MAP = Path("instruction-compiler/sources/hook-source-map.json")
EVENTS = {
    "task_received": ({"task", "constraints", "session_context"}, {"request_source"}),
    "boundary_requested": (
        {"objective", "proposed_action", "scope", "session_context"},
        {"authorization_scope"},
    ),
    "action_observed": ({"action", "result", "scope"}, {"operation_result"}),
    "progress_reported": ({"objective", "progress", "boundary"}, {"progress_signal"}),
    "completion_requested": (
        {"objective", "acceptance", "results"},
        {"verification_result", "final_state"},
    ),
    "session_resumed": (
        {"retained_context", "pending_work", "effect_status"},
        {"context_source"},
    ),
}
MODES = {"single-agent", "multi-agent"}
OUTCOMES = {"continue", "needs_evidence", "amend", "wait", "stop", "not_applicable"}
CONTRACT_KEYS = {
    "schema_version",
    "event_id",
    "modes",
    "required_facts",
    "required_evidence",
    "allowed_outcomes",
}
SECTIONS = ("触发", "适用范围", "上下文与证据", "判断", "结果与反馈", "失败与恢复")
JSON_FENCE = re.compile(r"(?ms)^```json\s*\n(.*?)^```\s*$")
FENCE = re.compile(r"(?ms)^(`{3,}|~{3,})[^\n]*\n.*?^\1\s*$")


def read_text(root: Path, relative: str | Path, errors: list[str]) -> str:
    """只读取仓库内真实文件，拒绝路径回退及中间目录符号链接，并记录缺失原因。"""
    candidate = root / relative
    try:
        parts = candidate.relative_to(root).parts
        if ".." in parts:
            raise ValueError("document path leaves its source root")
        current = root
        for part in parts:
            current /= part
            if current.is_symlink():
                raise ValueError("document path contains a symlink")
        return candidate.read_text(encoding="utf-8")
    except (OSError, UnicodeError, ValueError) as error:
        errors.append(f"{relative}: cannot read required document ({type(error).__name__})")
        return ""


def operational_text(text: str) -> str:
    """提取可执行正文，代码围栏和纯参考章节不能充当安全约束已经存在的证据。"""
    return FENCE.sub("", text)


def section(text: str, title: str) -> str:
    """按明确章节边界提取当前语义段，避免其他章节的同名词汇造成误通过。"""
    pattern = rf"(?ms)^## {re.escape(title)}\s*\n(.*?)(?=^## |\Z)"
    matches = re.findall(pattern, operational_text(text))
    return matches[0].strip() if len(matches) == 1 else ""


def require_terms(
    text: str, terms: tuple[str, ...], relative: str | Path, errors: list[str]
) -> None:
    """逐项保留必需安全语义的失败定位，不以一个词命中替代全部约束。"""
    folded = text.casefold()
    for term in terms:
        if term.casefold() not in folded:
            errors.append(f"{relative}: missing semantic requirement: {term}")


def string_set(value: object) -> set[str] | None:
    """验证机器契约中的非空且无重复字符串集合，布尔值或其他类型不能冒充字段。"""
    if not isinstance(value, list) or not value:
        return None
    if any(not isinstance(item, str) or not item.strip() for item in value):
        return None
    if len(value) != len(set(value)):
        return None
    return set(value)


def event_contract(text: str, relative: Path, errors: list[str]) -> dict | None:
    """要求文档仅有一个身份正确的机器契约，额外字段不能引入隐藏的下一阶段。"""
    matches = JSON_FENCE.findall(text)
    if len(matches) != 1:
        errors.append(f"{relative}: expected one machine contract JSON fence")
        return None
    try:
        contract = json.loads(matches[0])
    except json.JSONDecodeError:
        errors.append(f"{relative}: invalid contract JSON")
        return None
    if not isinstance(contract, dict) or set(contract) != CONTRACT_KEYS:
        errors.append(f"{relative}: contract fields differ from the approved contract")
        return None
    return contract


def validate_event_document(root: Path, event_id: str, errors: list[str]) -> dict | None:
    """核对一个中文事件的章节、事实、证据与允许结果，并要求消费规范共享契约。"""
    relative = HOOKS / (event_id.replace("_", "-") + ".md")
    text = read_text(root, relative, errors)
    contract = event_contract(text, relative, errors)
    for heading in SECTIONS:
        if not section(text, heading):
            errors.append(f"{relative}: missing or empty operational section: {heading}")
    if contract is None:
        return None
    if (
        type(contract["schema_version"]) is not int
        or contract["schema_version"] != 1
        or contract["event_id"] != event_id
    ):
        errors.append(f"{relative}: wrong schema or event identity")
    facts, evidence = EVENTS[event_id]
    expected_fields = {
        "modes": MODES,
        "allowed_outcomes": OUTCOMES,
        "required_facts": facts,
        "required_evidence": evidence,
    }
    for key, expected in expected_fields.items():
        if string_set(contract[key]) != expected:
            errors.append(f"{relative}: invalid or incomplete {key}")
    if "](shared.md)" not in operational_text(text):
        errors.append(f"{relative}: must consume the canonical shared contract")
    return contract


def validate_events(root: Path, errors: list[str]) -> None:
    """遍历六个已批准事件，事件缺失不能被目录中的未知文件替代。"""
    for event_id in EVENTS:
        validate_event_document(root, event_id, errors)


def validate_semantics(root: Path, errors: list[str]) -> None:
    """检查共享约束和各事件正文中的职责、授权、恢复与验收含义。"""
    for name, sections in SEMANTIC_REQUIREMENTS.items():
        relative = HOOKS / name
        text = read_text(root, relative, errors)
        for title, terms in sections.items():
            require_terms(section(text, title), terms, relative, errors)


def validate_workflow(root: Path, baseline: dict, errors: list[str]) -> dict:
    """核对一个精简流程的动态执行语义、六事件链接与相对历史入口的实际缩短。"""
    path = baseline["canonical_path"]
    text = read_text(root, SKILL / path, errors)
    previous = baseline.get("baseline_characters", 0)
    if type(previous) is not int or previous <= 0 or len(text) * 2 >= previous:
        errors.append(f"{path}: entry/workflow must be substantially shorter than baseline")
    if path.startswith("references/"):
        for event in EVENTS:
            link = event.replace("_", "-") + ".md"
            if f"../hooks/{link}" not in operational_text(text):
                errors.append(f"{path}: missing current event instruction: {event}")
        terms = ("Agent", "上下文", "Python")
    else:
        terms = ("workflow_check_event", "不由 Python 阶段执行器", "Agent 在自身上下文")
    require_terms(operational_text(text), terms, path, errors)
    if re.search(r"\bnext_stage\b|\bdecide_decoupling_workflow\b|\b(?:SA|MA)0[1-7]\b", text):
        errors.append(f"{path}: retired numbered-stage runtime instruction remains")
    return {"baseline_characters": previous, "current_characters": len(text)}


def validate_workflows(root: Path, mapping: dict, errors: list[str]) -> dict[str, dict]:
    """保留六条历史入口证据，按三个当前中文入口执行精简与一致性检查。"""
    baselines = mapping.get("entry_baselines", [])
    expected = {
        "SKILL.md",
        "references/coding/layer-04-workflows/coding-single-agent.md",
        "references/coding/layer-04-workflows/coding-multi-agent.md",
    }
    if not isinstance(baselines, list) or len(baselines) != 6:
        errors.append(f"{SOURCE_MAP}: incomplete entry/workflow length baselines")
        return {}
    current = {}
    for row in baselines:
        if not isinstance(row, dict) or not isinstance(row.get("path"), str):
            errors.append(f"{SOURCE_MAP}: invalid entry baseline")
            continue
        canonical = row.get("canonical_path")
        normalized = (
            row["path"].removesuffix("_zh_cn.md") + ".md"
            if row["path"].endswith("_zh_cn.md")
            else row["path"]
        )
        if canonical != normalized or canonical not in expected:
            errors.append(f"{SOURCE_MAP}: invalid entry canonical path")
        if row["path"].endswith("_zh_cn.md") and canonical in expected:
            current[canonical] = validate_workflow(root, row, errors)
    if set(current) != expected:
        errors.append(f"{SOURCE_MAP}: incomplete Chinese entry/workflow baselines")
    return current


def check_repository(root: Path) -> list[str]:
    """组合当前 Hook 形状、中文单源、语义和历史来源检查，返回全部可定位问题。"""
    errors: list[str] = []
    for path in discover_markdown(root / SKILL):
        errors.extend(
            canonical_issues(path.relative_to(root).as_posix(), read_text(root, path, errors))
        )
    validate_events(root, errors)
    validate_semantics(root, errors)
    mapping = validate_source_map(root, errors)
    validate_workflows(root, mapping, errors)
    return errors


def main(root: Path = ROOT) -> int:
    """输出契约检查结果并返回稳定退出码，让旧入口与 CI 使用同一审核结论。"""
    errors = check_repository(root)
    if errors:
        print("Workflow Hook contract validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print(
        "Workflow Hook contract validation passed "
        "(6 Chinese events, 218 historical sources, 2 workflows)."
    )
    return 0


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    arguments = parser.parse_args()
    raise SystemExit(main(arguments.root.resolve()))
