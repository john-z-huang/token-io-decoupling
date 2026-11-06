"""只用标准库校验批准的中文 Skill 归档，构建时不导入运行服务。"""

from __future__ import annotations

import hashlib
import io
import json
import re
import stat
import zipfile
from pathlib import PurePosixPath, PureWindowsPath
from typing import Literal, TypedDict


class SkillManifest(TypedDict):
    """批准中文 Skill 的版本、构建身份与完整文件 Hash 清单。"""

    schema_version: Literal[3]
    language: Literal["zh_cn"]
    build_id: str
    files: dict[str, str]


def _entry_name(entry: zipfile.ZipInfo, contents: dict[str, bytes]) -> str:
    """拒绝路径逃逸、链接、重复项及私有开发内容，只允许单中文产品文件。"""
    name = entry.filename
    path = PurePosixPath(name)
    forbidden = {
        "_project",
        "rule_sources",
        "instruction-compiler",
        "tests",
        "benchmarks",
        "scripts",
        "sources",
    }
    if (
        not name
        or "\\" in name
        or ":" in name
        or "\x00" in name
        or path.is_absolute()
        or PureWindowsPath(name).drive
        or path.as_posix() != name
        or any(part.startswith(".") or part in forbidden for part in path.parts)
        or path.stem.endswith("_zh_cn")
        or entry.is_dir()
        or stat.S_ISLNK(entry.external_attr >> 16)
        or name in contents
        or path.suffix not in {".md", ".yaml", ".json"}
    ):
        raise ValueError("unsafe or non-product packaged Skill entry")
    return name


def _archive_contents(payload: bytes) -> dict[str, bytes]:
    """逐项通过产品路径守卫后才读取归档，不接受 ZIP 目录或符号链接入口。"""
    contents = {}
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        for entry in archive.infolist():
            name = _entry_name(entry, contents)
            contents[name] = archive.read(entry)
    return contents


def _archive_manifest(
    contents: dict[str, bytes],
    expected_build_id: str | None,
    expected_files: dict[str, str] | None,
) -> SkillManifest:
    """清单须覆盖全部实际字节，并与已安装 workflow 的批准批次和文件表一致。"""
    manifest = json.loads(contents.get("manifest.json", b""))
    if not isinstance(manifest, dict):
        raise ValueError("compiled Skill manifest must be an object")
    build_id, declared = manifest.get("build_id"), manifest.get("files")
    if (
        type(manifest.get("schema_version")) is not int
        or manifest["schema_version"] != 3
        or manifest.get("language") != "zh_cn"
        or not isinstance(build_id, str)
        or re.fullmatch(r"[0-9a-f]{64}", build_id) is None
        or not isinstance(declared, dict)
        or set(declared) != set(contents) - {"manifest.json"}
    ):
        raise ValueError("incompatible or incomplete compiled Skill manifest")
    if expected_build_id is not None and build_id != expected_build_id:
        raise ValueError("compiled Skill and core resources belong to different batches")
    for name, digest in declared.items():
        if not isinstance(digest, str) or digest != hashlib.sha256(contents[name]).hexdigest():
            raise ValueError("compiled Skill integrity check failed")
    if expected_files is not None and declared != expected_files:
        raise ValueError("compiled Skill files do not match the core instruction map")
    return {"schema_version": 3, "language": "zh_cn", "build_id": build_id, "files": declared}


def _checkpoint_references(checkpoints: object) -> list[object]:
    """只接受单文档定位，明确拒绝退役的双语言 documents 映射。"""
    if not isinstance(checkpoints, dict) or not checkpoints:
        raise ValueError("compiled Skill index is missing rule lookups")
    references: list[object] = []
    for entry in checkpoints.values():
        if not isinstance(entry, dict) or "documents" in entry:
            raise ValueError("compiled Skill lookup must use one current document")
        references.append(entry.get("document"))
    return references


def _index_references(index: dict) -> list[object]:
    """汇总事件、流程、节点及片段的规范入口，供完整归档一致性校验。"""
    references: list[object] = []
    for category in ("events", "workflows"):
        table = index.get(category)
        if not isinstance(table, dict) or not table:
            raise ValueError("compiled Skill index is missing current instructions")
        references.extend(table.values())
    references.extend(_checkpoint_references(index.get("checkpoints")))
    fragments = index.get("fragments")
    if not isinstance(fragments, dict) or not fragments:
        raise ValueError("compiled Skill index is missing instruction fragments")
    for values in fragments.values():
        if not isinstance(values, list) or not values:
            raise ValueError("compiled Skill fragments must reference current documents")
        references.extend(values)
    return references


def _validate_document_index(contents: dict[str, bytes]) -> None:
    """核对索引版本及目标文件存在；具体章节锚点由文档检查验证。"""
    index = json.loads(contents["instruction-index.json"])
    if (
        not isinstance(index, dict)
        or type(index.get("schema_version")) is not int
        or index["schema_version"] != 3
        or index.get("language") != "zh_cn"
    ):
        raise ValueError("compiled Skill index must use the current Chinese schema")
    for reference in _index_references(index):
        if not isinstance(reference, str) or reference.partition("#")[0] not in contents:
            raise ValueError("compiled Skill index references unavailable product content")


def validate_skill_bundle(
    payload: bytes,
    *,
    expected_build_id: str | None = None,
    expected_files: dict[str, str] | None = None,
) -> tuple[SkillManifest, dict[str, bytes]]:
    """在任何安装写入前校验完整归档、同批清单与单中文导航入口。"""
    try:
        contents = _archive_contents(payload)
        manifest = _archive_manifest(contents, expected_build_id, expected_files)
        for name in ("SKILL.md", "agents/openai.yaml", "instruction-index.json"):
            if not contents.get(name, b"").strip():
                raise ValueError("required compiled Skill content is missing or empty")
        _validate_document_index(contents)
        return manifest, contents
    except (
        OSError,
        UnicodeError,
        KeyError,
        TypeError,
        RuntimeError,
        NotImplementedError,
        zipfile.BadZipFile,
    ) as exc:
        raise ValueError("compiled Skill bundle is malformed or unavailable") from exc
