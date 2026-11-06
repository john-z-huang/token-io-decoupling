"""同批次 Skill、资源清单及受保护的开发导出发布。"""

from __future__ import annotations

import io
import json
import zipfile
from collections.abc import Mapping
from pathlib import Path

from .models import (
    CompilationReport,
    CompilationSummary,
    CompiledDocument,
    DocumentIndex,
    Instruction,
)
from .sources import CompilationError, digest, json_bytes, safe_file

SCHEMA_VERSION = 3
_RESOURCE = Path(
    "mcp/packages/token_io_decoupling_workflow/src/token_io_decoupling_workflow/_resources"
)


def _entry_footer(build_id: str) -> str:
    """说明构建批次和完整文件核验口径，防止将正文 Hash 当作文档文件 Hash。"""
    note = (
        "只读取当前事件和已选短 workflow；链接仅用于导航，不要求预加载其它卡片。"
        "纯文档完整性：按 manifest.files 核验完整文件字节，并保持同一 manifest.build_id。"
        "MCP content_sha256/text_sha256 标识返回正文，不是文档文件字节。"
        "必需指令缺失或不匹配时停止依赖工作。"
    )
    return f"\n\n构建：`{build_id}`\n\n{note}\n"


def make_skill_files(
    cards: dict[str, str], build_id: str, index: DocumentIndex
) -> dict[str, bytes]:
    """用同一构建身份生成产品文件与清单；入口只追加完整性说明，不展开导航。"""
    files = {path: (text.rstrip() + "\n").encode() for path, text in cards.items()}
    files["SKILL.md"] = (cards["SKILL.md"].rstrip() + _entry_footer(build_id)).encode()
    files["instruction-index.json"] = json_bytes(index)
    files["manifest.json"] = json_bytes(
        {
            "schema_version": SCHEMA_VERSION,
            "language": "zh_cn",
            "build_id": build_id,
            "files": {path: digest(data) for path, data in sorted(files.items())},
        }
    )
    return files


def deterministic_zip(files: dict[str, bytes]) -> bytes:
    """固定元数据和顺序，使相同构建产生相同 ZIP 字节。"""
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path, data in sorted(files.items()):
            info = zipfile.ZipInfo(path, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data)
    return output.getvalue()


def _resource_files(body: CompiledDocument, report: CompilationReport) -> dict[Path, bytes]:
    """将资源正文、产品清单和开发报告序列化为同批次待发布字节。"""
    instructions = json_bytes(body)
    return {
        _RESOURCE / "instructions.json": instructions,
        _RESOURCE / "manifest.json": json_bytes(
            {
                "schema_version": SCHEMA_VERSION,
                "language": "zh_cn",
                "build_id": body["build_id"],
                "files": {"instructions.json": digest(instructions)},
            }
        ),
        Path("instruction-compiler/build-report.json"): json_bytes(
            {
                "build_id": body["build_id"],
                "language": "zh_cn",
                **report,
            }
        ),
    }


def _export_present(root: Path) -> bool:
    """可选导出只能是普通目录；符号链接或同名文件不能成为发布目标。"""
    export = root / "skills/token-io-decoupling"
    present = export.exists() or export.is_symlink()
    if present and (export.is_symlink() or not export.is_dir()):
        raise CompilationError("optional Skill export must be a regular directory")
    return present


def _stale_files(root: Path, files: dict[Path, bytes], skill_files: dict[str, bytes]) -> list[str]:
    """比对持久产物与已有可选导出；缺省不要求创建仅供开发的导出目录。"""
    stale = [
        path.as_posix()
        for path, data in files.items()
        if not (root / path).is_file() or (root / path).read_bytes() != data
    ]
    export = root / "skills/token-io-decoupling"
    if _export_present(root):
        expected = {Path(path) for path in skill_files}
        for path in export.rglob("*"):
            if path.is_file() and path.relative_to(export) not in expected:
                stale.append(
                    (Path("skills/token-io-decoupling") / path.relative_to(export)).as_posix()
                )
    return stale


def _previous_export(export: Path) -> dict[str, str]:
    """读取旧受管清单以保护本地修改；旧 schema 仅用于安全退役，不供执行读取。"""
    try:
        previous = json.loads(safe_file(export, "manifest.json").read_bytes())
    except (ValueError, UnicodeError) as exc:
        raise CompilationError("invalid previous export manifest") from exc
    if not isinstance(previous, dict) or previous.get("schema_version") not in {2, SCHEMA_VERSION}:
        raise CompilationError("invalid previous export manifest")
    # 旧清单只用于核验受管旧文件并安全退役，不是可执行指令的兼容读取。
    if previous["schema_version"] == SCHEMA_VERSION and previous.get("language") != "zh_cn":
        raise CompilationError("invalid previous export language")
    if not isinstance(previous.get("files"), dict):
        raise CompilationError("invalid previous export manifest")
    files: dict[str, str] = {}
    for path, fingerprint in previous["files"].items():
        if not isinstance(path, str) or not isinstance(fingerprint, str):
            raise CompilationError("invalid previous export manifest entry")
        files[path] = fingerprint
    return files


def _obsolete_exports(root: Path, skill_files: dict[str, bytes]) -> list[Path]:
    """仅列出旧清单管理且字节未变的过时文件，检查完成前不删除文件。"""
    export = root / "skills/token-io-decoupling"
    if not _export_present(root) or not (export / "manifest.json").exists():
        return []
    obsolete = []
    for name, expected_digest in _previous_export(export).items():
        if name in skill_files:
            continue
        path = export / name
        if not path.exists() and not path.is_symlink():
            continue
        path = safe_file(export, name)
        if digest(path.read_bytes()) != expected_digest:
            raise CompilationError(f"obsolete exported document has local changes: {name}")
        obsolete.append(path)
    return obsolete


def _instruction_sizes(
    entries: Mapping[str, Instruction],
) -> dict[str, int]:
    """按实际返回正文统计字符数，不将结构或导航开销混为正文预算。"""
    return {key: len(entry["text"]) for key, entry in entries.items()}


def publish_compilation(
    root: Path,
    body: CompiledDocument,
    skill_files: dict[str, bytes],
    report: CompilationReport,
    check: bool,
) -> CompilationSummary:
    """先核对陈旧产物和退役守卫，再检查或写出同一构建；不截断必需指令。"""
    files = _resource_files(body, report)
    if not check or _export_present(root):
        files.update(
            {Path("skills/token-io-decoupling") / path: data for path, data in skill_files.items()}
        )
    files[Path("mcp/src/token_io_decoupling/_resources/skill_bundle.zip")] = deterministic_zip(
        skill_files
    )
    stale = _stale_files(root, files, skill_files)
    if check and stale:
        raise CompilationError("generated instruction resources are stale: " + ", ".join(stale))
    obsolete = [] if check else _obsolete_exports(root, skill_files)
    if not check:
        for path, data in files.items():
            destination = root / path
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(data)
        for path in obsolete:
            path.unlink()
    return {
        "build_id": body["build_id"],
        "generated_files": len(files),
        "resource_bytes": len(files[_RESOURCE / "instructions.json"]),
        "instruction_characters": _instruction_sizes(body["nodes"]),
        "event_characters": _instruction_sizes(body.get("events", {})),
    }
