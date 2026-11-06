"""检查旧指令的逐文件、逐主题来源映射及替代目标。"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path, PurePosixPath

SKILL = Path("instruction-compiler/sources/skill")
SOURCE_MAP = Path("instruction-compiler/sources/hook-source-map.json")
SCOPE = {
    "references/coding/layer-01-fundamental-concepts",
    "references/coding/layer-02-workflow-concepts",
    "references/coding/layer-03-workflow-checkpoints",
    "references/coding/layer-04-workflows/modules",
}
TARGETS = {
    "references/coding/hooks/" + name + ".md"
    for name in (
        "README",
        "shared",
        "task-received",
        "boundary-requested",
        "action-observed",
        "progress-reported",
        "completion-requested",
        "session-resumed",
    )
}
# 固定的是本次核对过的静态记录完整性，不把指纹当作规则语义或当前授权证明。
BASELINE_FINGERPRINT = "b0693196c24d8dba8e2ab0c5a40d58fe727f83fdf44bddee0418dc8481c3dee3"
RETIREMENT_FINGERPRINT = "2e4928c01d31042f5fbabad87558bf8ef60ea8df960e1449ec2e2b571c716d5e"
ENTRY_FINGERPRINT = "c384afdbca2fe5438b85e2511694a953fe9203166b716ea43a1a8910d44225d2"
FENCE = re.compile(r"(?ms)^(`{3,}|~{3,})[^\n]*\n.*?^\1\s*$")
HEADINGS = re.compile(r"(?m)^#{1,6}\s+(.+?)\s*#*\s*$")


def read_text(root: Path, relative: str | Path, errors: list[str]) -> str:
    """只读根内非符号链接文档；故障累积到 errors，让 CLI 给出完整诊断而非回溯。"""
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
    """排除 fenced 示例后再检查标题，避免示例伪装成真实替代锚点。"""
    return FENCE.sub("", text)


def string_set(value: object) -> set[str] | None:
    """仅接受非空且无重复的文本列表；无效输入用 None 交给调用方报告。"""
    if not isinstance(value, list) or not value:
        return None
    if any(not isinstance(item, str) or not item.strip() for item in value):
        return None
    if len(value) != len(set(value)):
        return None
    return set(value)


def safe_relative(value: object) -> bool:
    """先拒绝绝对路径和逃逸写法；当前替代目标还须通过固定产品清单核验。"""
    if not isinstance(value, str) or not value:
        return False
    path = PurePosixPath(value)
    return not path.is_absolute() and ".." not in path.parts and "\\" not in value


def target_exists(root: Path, reference: object, errors: list[str]) -> None:
    """核对真实当前 Hook 及中文标题，拒绝退役入口、路径替换和符号链接。"""
    if not isinstance(reference, str):
        errors.append("source map: invalid replacement reference")
        return
    path, _, anchor = reference.partition("#")
    if not safe_relative(path) or path not in TARGETS:
        errors.append(f"source map: unsafe replacement reference: {reference}")
        return
    target = root / SKILL
    for part in Path(path).parts:
        target /= part
        if target.is_symlink():
            errors.append(f"source map: symlink replacement reference: {reference}")
            return
    text = read_text(root, SKILL / path, errors)
    if anchor:
        headings = {
            re.sub(r"\s+", "-", re.sub(r"[^\w\s-]", "", heading.casefold())).strip("-")
            for heading in HEADINGS.findall(operational_text(text))
        }
        if anchor not in headings:
            errors.append(f"source map: replacement anchor does not exist: {reference}")


def validate_metadata(mapping: dict, errors: list[str]) -> None:
    """固定已审核历史的范围与数量；严格类型避免浮点数冒充计数。"""
    expected = {
        "source_count": 218,
        "retired_document_count": 109,
        "current_target_document_count": 8,
        "baseline_commit": "b9bd394a39a38f7066ed2f77116d8c78d5be3311",
    }
    if string_set(mapping.get("baseline_scope")) != SCOPE:
        errors.append(f"{SOURCE_MAP}: four-directory baseline scope is incomplete")
    for key, value in expected.items():
        if type(mapping.get(key)) is not type(value) or mapping.get(key) != value:
            errors.append(f"{SOURCE_MAP}: wrong reviewed baseline identity or count: {key}")


def fingerprint(value: object) -> str:
    """对审核记录生成稳定指纹；只保护记录完整性，不证明政策语义或操作授权。"""
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode()).hexdigest()


def baseline_identity(source: dict) -> dict:
    """提取不可改写的历史身份和主题，替代锚点不参与历史事实指纹。"""
    fields = ("path", "language", "baseline_sha256", "baseline_bytes", "baseline_characters")
    topics = source.get("topics")
    return {
        **{key: source.get(key) for key in fields},
        "topics": [
            {key: topic.get(key) for key in ("heading", "canonical_heading")}
            for topic in topics
            if isinstance(topic, dict)
        ]
        if isinstance(topics, list)
        else None,
    }


def validate_reviewed_records(mapping: dict, sources: list, errors: list[str]) -> None:
    """核验历史、退役证据及入口基线三组审核记录，不依赖本地 Git 历史对象。"""
    ordered = sorted(
        (source for source in sources if isinstance(source, dict)),
        key=lambda source: str(source.get("path")),
    )
    if fingerprint([baseline_identity(source) for source in ordered]) != BASELINE_FINGERPRINT:
        errors.append(f"{SOURCE_MAP}: reviewed baseline records were changed")
    fields = ("path", "retired_path", "retired_sha256", "retired_bytes", "retired_characters")
    retired = [{key: source.get(key) for key in fields} for source in ordered]
    if fingerprint(retired) != RETIREMENT_FINGERPRINT:
        errors.append(f"{SOURCE_MAP}: reviewed retirement evidence was changed")
    entries = mapping.get("entry_baselines")
    if isinstance(entries, list) and all(isinstance(row, dict) for row in entries):
        entries = sorted(entries, key=lambda row: str(row.get("path")))
    if fingerprint(entries) != ENTRY_FINGERPRINT:
        errors.append(f"{SOURCE_MAP}: reviewed entry baseline records were changed")


def validate_source_identity(source: dict, errors: list[str]) -> str | None:
    """核对原路径、语言和基线规模；历史双语事实不代表仍有两个当前入口。"""
    path = source.get("path")
    if not safe_relative(path) or not any(path.startswith(prefix + "/") for prefix in SCOPE):
        errors.append(f"{SOURCE_MAP}: invalid source path: {path}")
        return None
    language = "zh_cn" if path.endswith("_zh_cn.md") else "en"
    if source.get("language") != language:
        errors.append(f"{SOURCE_MAP}: wrong source language: {path}")
    if not re.fullmatch(r"[a-f0-9]{64}", str(source.get("baseline_sha256", ""))):
        errors.append(f"{SOURCE_MAP}: missing baseline fingerprint: {path}")
    for key in ("baseline_characters", "baseline_bytes"):
        if type(source.get(key)) is not int or source[key] <= 0:
            errors.append(f"{SOURCE_MAP}: invalid {key}: {path}")
    if not source.get("disposition"):
        errors.append(f"{SOURCE_MAP}: missing disposition: {path}")
    return path


def source_replacements(source: dict, errors: list[str]) -> set[str]:
    """收集逐文件与逐主题替代引用，不能用文件级映射掩盖未解决的主题。"""
    references = string_set(source.get("target_refs"))
    if references is None:
        errors.append(f"{SOURCE_MAP}: missing replacement: {source.get('path')}")
        references = set()
    topics = source.get("topics")
    if not isinstance(topics, list):
        errors.append(f"{SOURCE_MAP}: invalid topics: {source.get('path')}")
        return references
    for topic in topics:
        if (
            not isinstance(topic, dict)
            or not topic.get("heading")
            or not topic.get("canonical_heading")
        ):
            errors.append(f"{SOURCE_MAP}: unnamed topic: {source.get('path')}")
            continue
        targets = string_set(topic.get("target_refs"))
        if not targets:
            errors.append(f"{SOURCE_MAP}: unresolved topic replacement: {source.get('path')}")
        else:
            references.update(targets)
    return references


def validate_retirement_evidence(source: dict, errors: list[str]) -> None:
    """检查删除时占位卡的真实指纹与规模，不把旧路径缺失当作内容迁移证明。"""
    if not re.fullmatch(r"[a-f0-9]{64}", str(source.get("retired_sha256", ""))):
        errors.append(f"{SOURCE_MAP}: missing retired placeholder fingerprint")
    for field in ("retired_bytes", "retired_characters"):
        if type(source.get(field)) is not int or source[field] <= 0:
            errors.append(f"{SOURCE_MAP}: invalid {field}")


def validate_sources(root: Path, sources: list, errors: list[str]) -> None:
    """逐条核验历史来源，再核对总体覆盖与当前替代目标，保留所有错误供审查。"""
    paths, retired, references = set(), set(), set()
    topics = 0
    for source in sources:
        if not isinstance(source, dict):
            errors.append(f"{SOURCE_MAP}: invalid source entry")
            continue
        path = validate_source_identity(source, errors)
        if path is None:
            continue
        if path in paths:
            errors.append(f"{SOURCE_MAP}: duplicate source: {path}")
        paths.add(path)
        expected = path.removesuffix("_zh_cn.md") + ".md" if path.endswith("_zh_cn.md") else path
        if source.get("retired_path") != expected:
            errors.append(f"{SOURCE_MAP}: invalid retired path: {path}")
        else:
            retired.add(expected)
        validate_retirement_evidence(source, errors)
        references.update(source_replacements(source, errors))
        if isinstance(source.get("topics"), list):
            topics += len(source["topics"])
    validate_source_totals(paths, retired, topics, errors)
    validate_current_targets(root, references, errors)


def validate_source_totals(
    paths: set[str], retired: set[str], topics: int, errors: list[str]
) -> None:
    """数量守卫与固定指纹互补，防止删来源、删主题或把双语历史当当前副本。"""
    if len(paths) != 218:
        errors.append(f"{SOURCE_MAP}: expected 218 unique baseline source paths")
    if topics != 1031 or len(retired) != 109:
        errors.append(f"{SOURCE_MAP}: expected all 1031 baseline topics and 109 retired documents")


def validate_current_targets(root: Path, references: set[str], errors: list[str]) -> None:
    """替代文档必须恰为审核后的八篇 Hook，四个退役目录也不得重新出现。"""
    for reference in sorted(references):
        target_exists(root, reference, errors)
    if {ref.partition("#")[0] for ref in references} != TARGETS:
        errors.append(
            f"{SOURCE_MAP}: replacement targets must cover the eight current Hook documents"
        )
    if current_source_paths(root):
        errors.append(f"{SOURCE_MAP}: retired source directories must not exist")


def current_source_paths(root: Path) -> set[str]:
    """旧目录仅是历史范围；连空目录或符号链接都不能重新成为当前来源。"""
    return {
        prefix
        for prefix in SCOPE
        if (root / SKILL / prefix).exists() or (root / SKILL / prefix).is_symlink()
    }


def validate_source_map(root: Path, errors: list[str]) -> dict:
    """读取 schema 2 静态追溯清单；缺失或损坏时报告错误，不重建历史记录。"""
    try:
        mapping = json.loads(read_text(root, SOURCE_MAP, errors))
    except json.JSONDecodeError:
        errors.append(f"{SOURCE_MAP}: invalid JSON")
        return {}
    if (
        not isinstance(mapping, dict)
        or type(mapping.get("schema_version")) is not int
        or mapping.get("schema_version") != 2
    ):
        errors.append(f"{SOURCE_MAP}: unsupported source map")
        return {}
    sources = mapping.get("sources")
    if not isinstance(sources, list):
        errors.append(f"{SOURCE_MAP}: missing sources")
        return mapping
    validate_metadata(mapping, errors)
    if len(sources) != 218:
        errors.append(f"{SOURCE_MAP}: expected all 218 baseline source files")
    validate_sources(root, sources, errors)
    validate_reviewed_records(mapping, sources, errors)
    return mapping
