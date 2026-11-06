"""验证交付的 context bundle；不读取作者树或加载 SDK。"""

from __future__ import annotations

import hashlib
import re


class CompiledInstructionError(RuntimeError):
    """只返回固定校验错误，不回显指令或供应商输出。"""


def _validate_metadata(context, language):
    """检查外部bundle2、唯一中文、完整交付状态及身份；不依赖作者树或 SDK。"""
    metadata = context.get("node_metadata")
    if (
        language != "zh_cn"
        or context.get("schema_version") != 2
        or context.get("node_id") != "contract"
        or context.get("language") != language
        or context.get("complete") is not True
        or context.get("status") != "complete"
        or context.get("remaining_owner_refs") != []
        or context.get("remaining_owner_refs_truncated") is not False
        or not isinstance(metadata, dict)
        or metadata.get("next_checkpoint_ids") != []
        or not metadata.get("owner_path", "").startswith("compiled:")
    ):
        raise CompiledInstructionError("unexpected compiled MCP instruction bundle")
    for field in ("build_id", "context_hash"):
        if not isinstance(context.get(field), str) or not re.fullmatch(
            r"[0-9a-f]{64}", context[field]
        ):
            raise CompiledInstructionError("invalid compiled MCP instruction identity")


def _validate_fragments(context):
    """逐片段核对正文哈希，再验证完整文本预算和选择集合，防止部分指令被接受。"""
    fragments = context.get("fragments")
    if not isinstance(fragments, list) or not fragments:
        raise CompiledInstructionError("missing compiled MCP instruction fragments")
    for fragment in fragments:
        text = fragment.get("text")
        if (
            not isinstance(text, str)
            or not text.strip()
            or not fragment.get("owner_path", "").startswith("compiled:")
            or fragment.get("text_sha256") != hashlib.sha256(text.encode("utf-8")).hexdigest()
        ):
            raise CompiledInstructionError("incomplete or corrupt compiled MCP instruction text")
    total = sum(len(fragment["text"]) for fragment in fragments)
    if (
        context.get("text_characters") != total
        or context.get("required_text_characters") != total
        or type(context.get("text_budget")) is not int
        or total > context["text_budget"]
        or context.get("required_fragment_ids")
        != [fragment.get("fragment_id") for fragment in fragments]
    ):
        raise CompiledInstructionError("compiled MCP instruction budget/completeness mismatch")


def validate_compiled_rule_bundle(context, language):
    """只有元数据和全部正文都通过时，才返回可与安装资源对照的 build 身份。"""
    _validate_metadata(context, language)
    _validate_fragments(context)
    return context["build_id"]
