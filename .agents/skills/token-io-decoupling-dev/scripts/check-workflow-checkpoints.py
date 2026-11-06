#!/usr/bin/env python3
"""Validate Layer-03 owners and their real Layer-04 module-step consumption."""
from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import unquote
from workflow_module_contracts import MODULE_CHECKPOINT_L3_OWNERS, MODULE_L3_OWNERS, MODULE_PREFIXES

ROOT = Path(__file__).resolve().parents[4]
L3 = ROOT / "instruction-compiler/sources/skill/references/coding/layer-03-workflow-checkpoints"
MODULES = ROOT / "instruction-compiler/sources/skill/references/coding/layer-04-workflows/modules"
SLUGS = (
    "route-entry", "workflow-navigation-selection", "session-audit-resolution",
    "session-state-resolution", "context-source-selection", "decision-context-selection",
    "planning-output-selection", "bootstrap-selection", "executor-selection",
    "output-route-selection", "role-reservation", "advisory-selection",
    "repair-disposition", "documentation-impact", "module-entry-resolution",
)
MODULE_NAMES = (
    "entry-readiness", "session-readiness", "work-definition", "single-execution",
    "delegated-execution", "verification-repair", "documentation", "delivery-acceptance",
)
SECTIONS = {
    "en": ("## Trigger and inputs", "## Decision and result", "## Failure boundary", "## Related concepts"),
    "zh": ("## 触发与输入", "## 决策与结果", "## 失败边界", "## 相关概念"),
}
SECTION_ALIASES = {
    "module-entry-resolution_zh_cn.md": {"## 触发与输入", "## Trigger 和输入"},
}
OWNER_TERMS = {
    "workflow-navigation-selection": {
        "en": ('current complete instruction text', 'supplied input', 'none establishes identity, permission', 'exact suspended position', 'authorized same-build generated document-only', 'resource errors never authorize author-source fallback'),
        "zh": ('当前完整指令正文', '所供输入', '不建立身份、权限', '准确暂停位置', '获授权的同构建生成纯文档', '资源错误不授权作者源回退'),
    },
    "session-audit-resolution": {
        "en": ("balanced/milestone_only", "full", "apply the defaults immediately", "do not ask a mandatory first-use question", "do not start a timer"),
        "zh": ("balanced/milestone_only", "full", "立即应用缺省值", "不得强制首次提问", "不得启动计时器"),
    },
    "session-state-resolution": {
        "en": ("canonical parent-controlled workflow record", "current Session facts", "read back", "does not grant authority", "does not establish cross-call sequencing"),
        "zh": ("规范的父级控制工作流记录", "当前 Session 事实", "回读", "不授予授权", "不建立跨调用顺序"),
    },
    "context-source-selection": {
        "en": ('source pointers', 'freshness', 'Memory', 'active plan', 'read every match for this task', 'current instructions take precedence', 'plan never grants authorization', 'do not substitute filesystem files', 'If listing or reading a relevant active plan fails, block work depending on it', 'compiled node/unit from one build and language', 'Verify identity, completeness and unresolved facts', 'each named instruction continuation', 'exact return position', 'authorized same-build generated document-only', 'never search author owners'),
        "zh": ('来源指针', '新鲜度', 'Memory', '活动计划', '读取每个匹配项', '当前指令优先', '计划不授予授权', '不得用文件替代该计划', '若无法列出或读取相关活动计划，阻塞依赖工作', '同一构建、语言的明确当前编译节点或单元', '核验标识、完整性及未解决事实', '每个明确指令继续入口', '准确返回位置', '获授权的同构建生成纯文档', '绝不查找作者 owner'),
    },
    "decision-context-selection": {
        "en": ("explicit user direction", "source provenance", "input hash", "policy binding", "do not send it to downstream advice", "verified facts are sufficient"),
        "zh": ("用户明确指令", "来源溯源", "输入 Hash", "政策绑定", "不得发送给下游建议", "已核实事实足够"),
    },
    "planning-output-selection": {
        "en": ("For every Coding task", "select a shared plan by default", "verified project facts", "confirm the authorized persistence operation", "content verification only when the lifecycle owner requires it", "Not applicable", "explicit user prohibition", "failed persistence are not skip conditions", "before those actions", "Ordinary progress reports do not independently trigger a plan write", "failed owner-required verification blocks dependent work", "does not replace owner-required complete-content checks", "Archive remains conditional on completed Acceptance"),
        "zh": ("每项 Coding 任务", "默认选择共享计划", "已核实项目事实", "确认获准持久化操作", "仅在生命周期 owner 要求时核验存储内容", "Not applicable", "用户明确禁止", "持久化失败不是跳过条件", "须在该动作前记录并分析", "普通进度汇报本身不触发计划写入", "owner 要求的核验失败时阻塞依赖工作", "不能替代 owner 要求的完整内容检查", "归档仍以 Acceptance 完成为条件"),
    },
    "bootstrap-selection": {
        "en": ("Bootstrap/Refresh", "separately review and authorize", "not applicable", "current task", "role occupancy", "does not reserve"),
        "zh": ("Bootstrap/Refresh", "另行审查并授权", "Not applicable", "当前任务", "角色占用", "不预留"),
    },
    "executor-selection": {
        "en": ("new-executor-needed", "does not authorize creation", "Root", "two or more eligible idle candidates", "route each requested direct Root output", "explicit `sub_agent` conflicts", "suitable children exist but are busy", "never defaults to Root", "does not reserve"),
        "zh": ("new-executor-needed", "不授权创建", "Root", "两个或更多合格空闲候选", "路由每项 Root 直接输出", "明确 `sub_agent` 与模式冲突", "若合适子代理均忙碌", "绝不默认 Root", "不预留"),
    },
    "output-route-selection": {
        "en": ("does not select an executor", "does not authorize creating a child", "single-agent", "expected output volume", "Multi-Agent mode"),
        "zh": ("不选择执行者", "不授权创建子代理", "Single-Agent", "预期输出量", "Multi-Agent 模式"),
    },
    "role-reservation": {
        "en": ("new-executor-needed", "locked capacity", "does not release a Slice", "unique reservation", "exactly `+1`", "all four roles", "block without requesting more capacity", "Slice release and child creation remain later, separate gates"),
        "zh": ("new-executor-needed", "锁定容量", "不释放 Slice", "唯一预留", "恰好 `+1`", "四种角色", "阻塞且不申请更多容量", "Slice 放行和子代理创建仍是后续独立门禁"),
    },
    "advisory-selection": {
        "en": ("Root authorization", "freshness", "policy/input/context hashes", "direct-owner comparison", "Task Assignment", "advice never authorizes work", "replaces a pass condition"),
        "zh": ("Root 授权", "新鲜度", "政策/输入/上下文 Hash", "与直接 owner 的比较", "Task Assignment", "不授权工作", "替代通过条件"),
    },
    "repair-disposition": {
        "en": ("concrete failing evidence", "affected paths", "smallest repair candidate", "new fingerprint", "changed epochs"),
        "zh": ("具体失败证据", "受影响路径", "最小修复候选", "新指纹", "变更 epoch"),
    },
    "documentation-impact": {
        "en": ("before/after fingerprints", "Git metadata", "required checks", "evidence that remains reusable", "Verification disposition"),
        "zh": ("变更前后指纹", "Git 元数据", "必需检查", "仍可复用的证据", "Verification 处置结果"),
    },
}
LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
FENCED_CODE_RE = re.compile(r"```[^\n]*\n.*?\n```", re.S)
INLINE_CODE_SPAN_RE = re.compile(r"(`+)(.*?)\1", re.S)


def markdown_link_targets(text: str) -> list[str]:
    without_fences = FENCED_CODE_RE.sub("", text)
    without_inline_code = INLINE_CODE_SPAN_RE.sub("", without_fences)
    return LINK_RE.findall(without_inline_code)
STEP_RE = re.compile(r"^(\d+)\. \*\*([A-Z]+\d{2}) —")
REL_LINK_PREFIX = "../../layer-03-workflow-checkpoints/"


def numbered_steps(path: Path) -> list[tuple[str, str, list[str]]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    title = "## 有序模块清单" if path.stem.endswith("_zh_cn") else "## Ordered module checklist"
    try:
        start = lines.index(title) + 1
    except ValueError:
        return []
    result: list[tuple[str, str, list[str]]] = []
    current_id: str | None = None
    current_body: list[str] = []
    for line in lines[start:]:
        if line.startswith("## "):
            break
        match = STEP_RE.match(line)
        if match:
            if current_id is not None:
                result.append((current_id, "\n".join(current_body), current_body))
            current_id = match.group(2)
            current_body = [line]
        elif current_id is not None:
            current_body.append(line)
    if current_id is not None:
        result.append((current_id, "\n".join(current_body), current_body))
    return result


def main() -> int:
    errors: list[str] = []
    consumed: dict[str, set[str]] = {"en": set(), "zh": set()}
    for slug in SLUGS:
        for suffix, lang in ((".md", "en"), ("_zh_cn.md", "zh")):
            path = L3 / f"{slug}{suffix}"
            if not path.is_file():
                errors.append(f"missing Layer-03 owner: {path.relative_to(ROOT)}")
                continue
            lines = path.read_text(encoding="utf-8").splitlines()
            for section in SECTIONS[lang]:
                aliases = SECTION_ALIASES.get(path.name) if section == SECTIONS[lang][0] else None
                matches = [candidate for candidate in (aliases or {section}) if lines.count(candidate) == 1]
                if len(matches) != 1:
                    errors.append(f"{path.relative_to(ROOT)}: expected exactly one {section}")
                    continue
                start = lines.index(matches[0]) + 1
                end = next((i for i in range(start, len(lines)) if lines[i].startswith("## ")), len(lines))
                if not any(line.strip() for line in lines[start:end]):
                    errors.append(f"{path.relative_to(ROOT)}: empty section {section}")
            text = "\n".join(lines)
            operational_text = FENCED_CODE_RE.sub("", text).split("\n## Related concepts", 1)[0].split("\n## 相关概念", 1)[0]
            for term in OWNER_TERMS.get(slug, {}).get(lang, ()):
                if term.casefold() not in operational_text.casefold():
                    errors.append(f"{path.relative_to(ROOT)}: missing semantic requirement: {term}")
            if "[English]" not in text or "[简体中文]" not in text:
                errors.append(f"{path.relative_to(ROOT)}: missing language switch")

    for module in MODULE_NAMES:
        for suffix, lang in ((".md", "en"), ("_zh_cn.md", "zh")):
            module_consumed: set[str] = set()
            path = MODULES / f"{module}{suffix}"
            if not path.is_file():
                errors.append(f"missing module: {path.relative_to(ROOT)}")
                continue
            steps = numbered_steps(path)
            if not steps:
                errors.append(f"{path.relative_to(ROOT)}: missing ordered module checklist")
                continue
            ids = [step_id for step_id, _, _ in steps]
            if len(ids) != len(set(ids)):
                errors.append(f"{path.relative_to(ROOT)}: duplicate local checkpoint ID")
            expected_entry = "module-entry-resolution" + ("_zh_cn" if lang == "zh" else "") + ".md"
            if not any(REL_LINK_PREFIX + expected_entry in body for _, body, _ in steps):
                errors.append(f"{path.relative_to(ROOT)}: module-entry-resolution is not consumed by a numbered step")
            entry_id = MODULE_PREFIXES[module] + "00"
            entry_step = next((body for step_id, body, _ in steps if step_id == entry_id), "")
            if REL_LINK_PREFIX + expected_entry not in entry_step:
                errors.append(f"{path.relative_to(ROOT)}: {entry_id} must directly link module-entry-resolution")
            by_id = {step_id: body for step_id, body, _ in steps}
            for checkpoint, owners in MODULE_CHECKPOINT_L3_OWNERS[module].items():
                body = by_id.get(checkpoint, "")
                if not body:
                    errors.append(f"{path.relative_to(ROOT)}: required checkpoint step is missing: {checkpoint}")
                    continue
                for owner in owners:
                    target = f"{REL_LINK_PREFIX}{owner}{'_zh_cn' if lang == 'zh' else ''}.md"
                    if target not in markdown_link_targets(body):
                        errors.append(f"{path.relative_to(ROOT)}: {checkpoint} must directly consume {owner}")
            for _, body, _ in steps:
                for raw in markdown_link_targets(body):
                    target = unquote(raw.split("#", 1)[0].split("?", 1)[0])
                    if "layer-03-workflow-checkpoints/" not in target:
                        continue
                    if not target.startswith(REL_LINK_PREFIX):
                        errors.append(f"{path.relative_to(ROOT)}: invalid Layer-03 target {target}")
                        continue
                    target_name = target.removeprefix(REL_LINK_PREFIX)
                    if "/" in target_name or not target_name.endswith(".md"):
                        errors.append(f"{path.relative_to(ROOT)}: invalid Layer-03 target {target}")
                        continue
                    slug = target_name.removesuffix("_zh_cn.md").removesuffix(".md")
                    if lang == "zh" and not target_name.endswith("_zh_cn.md"):
                        errors.append(f"{path.relative_to(ROOT)}: cross-language Layer-03 target {target}")
                        continue
                    if lang == "en" and target_name.endswith("_zh_cn.md"):
                        errors.append(f"{path.relative_to(ROOT)}: cross-language Layer-03 target {target}")
                        continue
                    if not (L3 / target_name).is_file():
                        errors.append(f"{path.relative_to(ROOT)}: missing Layer-03 target {target}")
                        continue
                    module_consumed.add(slug)
                    consumed[lang].add(slug)
            for slug in MODULE_L3_OWNERS[module]:
                if slug not in module_consumed:
                    errors.append(f"{path.relative_to(ROOT)}: missing direct numbered-step consumption for {slug}")

    for lang, suffix in (("en", ""), ("zh", "_zh_cn")):
        selector = ROOT / f"instruction-compiler/sources/skill/workflows/coding{suffix}.md"
        text = selector.read_text(encoding="utf-8")
        section = "## Entry" if lang == "en" else "## 入口"
        body = text.split(section, 1)[-1].split("\n## ", 1)[0]
        expected = f"../references/coding/layer-03-workflow-checkpoints/route-entry{suffix}.md"
        verb = "Call [Route Entry]" if lang == "en" else "调用[路线入口]"
        if expected in markdown_link_targets(body) and verb in body:
            consumed[lang].add("route-entry")
        else:
            errors.append(f"{selector.relative_to(ROOT)}: Route Entry must be a real same-language Entry link in the selector")
    for slug in SLUGS:
        for lang in ("en", "zh"):
            if slug not in consumed[lang]:
                errors.append(f"Layer-03 owner has no same-language numbered module-step/selector consumer: {slug} ({lang})")

    if errors:
        print("Workflow checkpoint ownership validation failed:", file=sys.stderr)
        print("\n".join(f"- {item}" for item in errors), file=sys.stderr)
        return 1
    print(f"Workflow checkpoint ownership validation passed ({len(SLUGS)} owners and 8 bilingual module checklists).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
