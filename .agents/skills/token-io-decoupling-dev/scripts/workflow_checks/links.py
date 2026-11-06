"""枚举已审核的 Hook 文档依赖；不改变共享链接安全规则。"""

from __future__ import annotations

import json
from pathlib import Path, PurePosixPath

SKILL = PurePosixPath("instruction-compiler/sources/skill")
HOOKS = "references/coding/hooks/"
EVENTS = (
    "task-received",
    "boundary-requested",
    "action-observed",
    "progress-reported",
    "completion-requested",
    "session-resumed",
)
HOOK_FILES = {HOOKS + name + ".md" for name in ("README", "shared", *EVENTS)}
FLOWS = {
    "references/coding/layer-04-workflows/coding-single-agent.md",
    "references/coding/layer-04-workflows/coding-multi-agent.md",
}
SCOPE = (
    "references/coding/layer-01-fundamental-concepts/",
    "references/coding/layer-02-workflow-concepts/",
    "references/coding/layer-03-workflow-checkpoints/",
    "references/coding/layer-04-workflows/modules/",
)


def adoption_edges() -> set[tuple[str, str]]:
    """仅枚举六事件、共享约束和两个中文入口的已审核关系。"""
    canonical = {(HOOKS + name + ".md", HOOKS + "shared.md") for name in EVENTS}
    canonical.update((HOOKS + name + ".md", HOOKS + "README.md") for name in EVENTS)
    canonical.update((HOOKS + "README.md", target) for target in HOOK_FILES | FLOWS)
    for source in FLOWS:
        canonical.update((source, target) for target in HOOK_FILES)
    canonical.update(
        ("workflows/coding.md", HOOKS + target + ".md")
        for target in ("task-received", "shared", "README")
    )
    canonical.add(("references/coding/layer-04-workflows/INDEX.md", HOOKS + "README.md"))
    return {
        ((SKILL / source).as_posix(), (SKILL / target).as_posix()) for source, target in canonical
    }


class HookLinkMapError(ValueError):
    """存在的来源映射不可读或结构损坏时，阻止分层验收。"""


def read_source_map(root: Path) -> dict | None:
    """兼容旧仓库缺失映射；存在却不可读或畸形的配置必须报告。"""
    path = root / "instruction-compiler/sources/hook-source-map.json"
    if path.is_symlink():
        raise HookLinkMapError("source map cannot be a symlink")
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        # 旧仓库/隔离夹具可以没有迁移映射；存在的坏配置不能当成缺失。
        return None
    except (OSError, UnicodeError) as error:
        raise HookLinkMapError("source map could not be read") from error
    try:
        mapping = json.loads(text)
    except json.JSONDecodeError as error:
        raise HookLinkMapError("source map contains invalid JSON") from error
    if not isinstance(mapping, dict) or type(mapping.get("schema_version")) is not int:
        raise HookLinkMapError("source map has an invalid schema")
    if mapping["schema_version"] != 2 or not isinstance(mapping.get("sources"), list):
        raise HookLinkMapError("source map has an unsupported schema or sources")
    return mapping


def approved_edges(root: Path) -> set[tuple[str, str]]:
    """历史来源只保留追溯，不会重新获得当前文档依赖权限。"""
    mapping = read_source_map(root)
    if mapping is not None:
        for source in mapping["sources"]:
            if not isinstance(source, dict):
                raise HookLinkMapError("source map contains an invalid source entry")
            if "canonical_path" in source:
                raise HookLinkMapError("source map cannot restore live retired dependencies")
    return adoption_edges()
