#!/usr/bin/env python3
"""Check the Layer-03 decision-node owners and their Layer-04 consumers."""
from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
DIR = ROOT / "references/coding/layer-03-workflow-checkpoints"
SLUGS = (
    "route-entry", "enhanced-path-selection", "session-audit-resolution",
    "session-state-resolution", "context-source-selection", "decision-context-selection",
    "planning-output-selection", "bootstrap-selection",
    "executor-selection", "output-route-selection", "role-reservation",
    "advisory-selection", "repair-disposition", "documentation-impact",
)
REQUIRED_SECTIONS = {
    "en": ("## Trigger and inputs", "## Decision and result", "## Failure boundary", "## Related concepts"),
    "zh": ("## 触发与输入", "## 决策与结果", "## 失败边界", "## 相关概念"),
}
CONSUMERS = {
    "coding-single-agent.md": {
        "route-entry": ("3.",), "enhanced-path-selection": ("2.",),
        "session-state-resolution": ("4.",), "session-audit-resolution": ("4.",),
        "context-source-selection": ("5.",), "decision-context-selection": ("5.",),
        "planning-output-selection": ("6.",), "advisory-selection": ("6.", "9.", "10."),
        "executor-selection": ("6.",), "output-route-selection": ("6.",),
        "repair-disposition": ("11.",), "documentation-impact": ("12.",),
    },
    "coding-multi-agent.md": {
        "route-entry": ("3.",), "enhanced-path-selection": ("2.",),
        "session-state-resolution": ("4.",), "session-audit-resolution": ("4.",),
        "context-source-selection": ("6.",), "decision-context-selection": ("6.",),
        "planning-output-selection": ("7.",), "bootstrap-selection": ("7.",),
        "executor-selection": ("7.",), "output-route-selection": ("7.",), "role-reservation": ("7.",),
        "advisory-selection": ("7.", "11.", "12."),
        "repair-disposition": ("13.",), "documentation-impact": ("14.",),
    },
}
MARKDOWN_LINK = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


def main() -> int:
    errors: list[str] = []
    for slug in SLUGS:
        for suffix, lang in ((".md", "en"), ("_zh_cn.md", "zh")):
            path = DIR / f"{slug}{suffix}"
            if not path.is_file():
                errors.append(f"missing owner: {path.relative_to(ROOT)}")
                continue
            text = path.read_text(encoding="utf-8")
            lines = text.splitlines()
            for section in REQUIRED_SECTIONS[lang]:
                if lines.count(section) != 1:
                    errors.append(f"{path.relative_to(ROOT)}: expected one {section}")
                    continue
                start = lines.index(section) + 1
                end = next((i for i in range(start, len(lines)) if lines[i].startswith("## ")), len(lines))
                if not any(line.strip() for line in lines[start:end]):
                    errors.append(f"{path.relative_to(ROOT)}: empty section {section}")
            if "[English]" not in text or "[简体中文]" not in text:
                errors.append(f"{path.relative_to(ROOT)}: missing language switch")
    for route, nodes in CONSUMERS.items():
        for suffix in ("", "_zh_cn"):
            path = ROOT / "references/coding/layer-04-workflows" / route.replace(".md", f"{suffix}.md")
            lines = path.read_text(encoding="utf-8").splitlines()
            for slug, steps in nodes.items():
                for step in steps:
                    start = next((i for i, line in enumerate(lines) if line.startswith(f"{step} **")), None)
                    if start is None:
                        errors.append(f"{path.relative_to(ROOT)}: missing {slug} at route step {step}")
                        continue
                    end = next((i for i in range(start + 1, len(lines)) if re.match(r"^\d+\. \*\*", lines[i])), len(lines))
                    expected = f"../layer-03-workflow-checkpoints/{slug}{suffix}.md"
                    linked_targets = [unquote(target.strip()) for line in lines[start:end] for target in MARKDOWN_LINK.findall(line)]
                    if expected not in linked_targets:
                        errors.append(f"{path.relative_to(ROOT)}: {slug} not consumed with a same-language Markdown link within route step {step}")
    if errors:
        print("Workflow checkpoint ownership validation failed:")
        print("\n".join(f"- {item}" for item in errors))
        return 1
    print(f"Workflow checkpoint ownership validation passed ({len(SLUGS)} bilingual nodes and route consumers).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
