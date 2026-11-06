"""校验当前维护文档的中文单源、入口及本地链接完整性。"""

from __future__ import annotations

import re
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urlsplit

from _compliance_core import links_in_markdown, normalize_markdown_target
from markdown_discovery import discover_markdown

ROOT = Path(__file__).resolve().parents[5]
SKILL = Path("instruction-compiler/sources/skill")
CORE_DOCS = (SKILL / "references/share/shared-protocols.md",)
FENCE = re.compile(r"(?ms)^(`{3,}|~{3,})[^\n]*\n.*?^\1\s*$")
SWITCH = re.compile(r"\[(?:English|简体中文|中文|EN|ZH)\]\([^)]*\)", re.IGNORECASE)
PRODUCT_SPECIFIC_PATTERNS = {
    label: re.compile(pattern, re.IGNORECASE)
    for label, pattern in (
        ("Luna", r"\bLuna\b"),
        ("GPT model", r"\bgpt-[a-z0-9_.-]+"),
        ("Codex", r"\bCodex\b"),
        ("OpenAI", r"\bOpenAI\b"),
        ("Claude", r"\bClaude(?:\s+Code)?\b"),
        ("Anthropic", r"\bAnthropic\b"),
        ("Sonnet", r"\bSonnet\b"),
        ("Opus", r"\bOpus\b"),
        ("Codex home", r"~/.codex(?:/|\b)"),
        ("Claude home", r"~/.claude(?:/|\b)"),
        ("reasoning_effort", r"\breasoning_effort\b"),
    )
}


def canonical_issues(path: str, text: str) -> list[str]:
    """拒绝当前文档的语言副本、切换导航和无中文正文，围栏内示例不参与正文判断。"""
    issues = []
    prose = FENCE.sub("", text)
    if path.endswith("_zh_cn.md") or "/zh-cn/" in path:
        issues.append(f"noncanonical Chinese document path: {path}")
    if SWITCH.search(prose):
        issues.append(f"language-switch navigation remains: {path}")
    if not re.search(r"[\u3400-\u9fff]", prose):
        issues.append(f"document has no Chinese prose: {path}")
    if "sed: --: No such file or directory" in text:
        issues.append(f"stray shell-error text: {path}")
    return issues


def heading_anchors(text: str) -> set[str]:
    """按 Markdown 标题及显式 HTML 标识生成可用锚点，保留重复标题的编号语义。"""
    prose = FENCE.sub("", text)
    anchors = set(re.findall(r'<a\s+(?:id|name)=["\']([^"\']+)', prose))
    counts: dict[str, int] = {}
    for heading in re.findall(r"(?m)^#{1,6}\s+(.+?)\s*#*\s*$", prose):
        slug = re.sub(r"\s", "-", re.sub(r"[^\w\s-]", "", heading.casefold()))
        occurrence = counts.get(slug, 0)
        counts[slug] = occurrence + 1
        anchors.add(slug if occurrence == 0 else f"{slug}-{occurrence}")
    return anchors


def plain_target(root: Path, relative: str) -> Path | None:
    """沿本地目标的每一级检查符号链接，避免链接借目录别名逃离当前仓库。"""
    target = root
    for part in PurePosixPath(relative).parts:
        target /= part
        if target.is_symlink():
            return None
    return target if target.is_file() else None


def local_link_issues(root: Path, path: str, text: str) -> list[str]:
    """检查当前文档的本地目标和锚点，不跟随符号链接或接受退役语言路径。"""
    issues = []
    for line, _label, raw in links_in_markdown(text):
        target = normalize_markdown_target(PurePosixPath(path), raw)
        if target is None:
            continue
        if not target:
            issues.append(f"target escapes repository: {path}:{line}")
            continue
        if not target.endswith(".md"):
            continue
        if target.endswith("_zh_cn.md") or "/zh-cn/" in target:
            issues.append(f"retired mirror dependency: {path}:{line} -> {target}")
        current = plain_target(root, target)
        if current is None:
            issues.append(f"missing or symlink local target: {path}:{line} -> {target}")
            continue
        anchor = unquote(urlsplit(raw).fragment)
        if anchor and anchor not in heading_anchors(current.read_text(encoding="utf-8")):
            issues.append(f"missing local anchor: {path}:{line} -> {target}#{anchor}")
    return issues


def entrypoint_issues(root: Path) -> list[str]:
    """核对 Skill、仓库开发入口和中文元数据，避免规范文件存在但实际入口仍指向旧副本。"""
    issues = []
    entry = root / SKILL / "SKILL.md"
    if not entry.is_file() or not entry.read_text(encoding="utf-8").startswith("---\n"):
        issues.append("Skill entry must start with YAML front matter")
    agents = root / "AGENTS.md"
    owner = ".agents/skills/token-io-decoupling-dev/AGENTS.md"
    if not agents.is_file() or owner not in agents.read_text(encoding="utf-8"):
        issues.append("AGENTS.md must link the canonical private development guidance")
    metadata = root / SKILL / "agents/openai.yaml"
    if not metadata.is_file():
        issues.append("missing Skill interface metadata")
        return issues
    description = re.search(r"short_description:\s*[\"']([^\"']+)", metadata.read_text())
    if (
        not description
        or not re.search(r"[\u3400-\u9fff]", description[1])
        or " | " in description[1]
    ):
        issues.append("Skill short_description must be a single Chinese description")
    return issues


def neutral_core_issues(root: Path) -> list[str]:
    """检查共享核心指令是否混入具体供应商、模型或用户主目录，保留既有中立边界。"""
    issues = []
    for relative in CORE_DOCS:
        path = plain_target(root, relative.as_posix())
        if path is None:
            issues.append(f"missing product-neutral core document: {relative}")
            continue
        opening = path.read_text(encoding="utf-8").split("\n## Codex CLI / ChatGPT Desktop", 1)[0]
        for label, pattern in PRODUCT_SPECIFIC_PATTERNS.items():
            if pattern.search(opening):
                issues.append(f"product-specific term in core ({label}): {relative}")
    return issues


def check_repository(root: Path) -> list[str]:
    """对同一批实际维护文档执行单源、入口、链接和核心指令检查。"""
    issues = []
    for markdown in discover_markdown(root):
        relative = markdown.relative_to(root).as_posix()
        text = markdown.read_text(encoding="utf-8")
        issues.extend(canonical_issues(relative, text))
        issues.extend(local_link_issues(root, relative, text))
    issues.extend(entrypoint_issues(root))
    issues.extend(neutral_core_issues(root))
    for obsolete in ("MULTI_LINGUAL.md", "MULTI_LINGUAL_zh_cn.md"):
        if (root / obsolete).exists():
            issues.append(
                f"development-only documentation policy must not exist at root: {obsolete}"
            )
    return issues


def main(root: Path = ROOT) -> int:
    """把可预期的读取或编码故障转为明确检查失败，不把缺失文档视为通过。"""
    try:
        issues = check_repository(root.resolve())
    except (OSError, UnicodeError) as error:
        issues = [f"cannot inspect required documentation ({type(error).__name__})"]
    if issues:
        print("中文单源文档检查未通过：")
        for issue in issues:
            print(f"- {issue}")
        return 1
    print("中文单源文档检查通过。")
    return 0
