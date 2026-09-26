#!/usr/bin/env python3
"""Reject provider and Agent-product details in Layer-02 and Layer-03 Markdown."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


LAYERS = (
    Path("references/coding/layer-02-workflow-concepts"),
    Path("references/coding/layer-03-workflows"),
)
FORBIDDEN = {
    "厂商或 Agent 产品": re.compile(r"\b(?:Codex|ChatGPT|OpenAI|Claude|Anthropic)\b", re.IGNORECASE),
    "厂商专属模型": re.compile(r"\b(?:Sonnet|Haiku|Opus|Luna|GPT(?:-[\w.-]+)?)\b", re.IGNORECASE),
    "厂商专属工具": re.compile(
        r"\b(?:MultiAgentV[12]|AskUserQuestion|SendMessage|EnterWorktree|ExitWorktree)\b",
        re.IGNORECASE,
    ),
    "厂商专属参数或命令": re.compile(
        r"\b(?:reasoning_effort|subagent_type|run_in_background|CLAUDE_CODE_[A-Z0-9_]+)\b"
        r"|(?<!\w)/(?:tasks|effort|agents)\b",
        re.IGNORECASE,
    ),
    "厂商配置路径": re.compile(r"(?:~?/|\b)\.(?:codex|claude)(?:/|\b)", re.IGNORECASE),
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    root = args.root.resolve()
    errors: list[str] = []
    checked = 0

    for layer in LAYERS:
        directory = root / layer
        if not directory.is_dir():
            errors.append(f"缺少文档目录: {directory}")
            continue
        documents = sorted(directory.rglob("*.md"))
        if not documents:
            errors.append(f"文档目录为空: {directory}")
        for path in documents:
            checked += 1
            relative_name = path.relative_to(directory).as_posix()
            name_matches = [
                f"{category} `{match.group()}`"
                for category, pattern in FORBIDDEN.items()
                if (match := pattern.search(relative_name))
            ]
            if name_matches:
                errors.append(f"{path.relative_to(root)}: 文件名包含 {', '.join(name_matches)}")
            for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                matches = [
                    f"{category} `{match.group()}`"
                    for category, pattern in FORBIDDEN.items()
                    if (match := pattern.search(line))
                ]
                if matches:
                    errors.append(f"{path.relative_to(root)}:{number}: {', '.join(matches)}")

    if errors:
        print("Layer-02/03 厂商无关检查未通过；将特调移至对应的 Layer-01 厂商章节:")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"Layer-02/03 厂商无关检查通过（{checked} 份 Markdown 文档）。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
