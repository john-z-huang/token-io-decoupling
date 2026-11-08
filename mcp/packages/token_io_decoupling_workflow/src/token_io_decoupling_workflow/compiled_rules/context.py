"""构造有界规则上下文、预算缺口和指令片段。"""

from __future__ import annotations

import hashlib

from token_io_decoupling_core.models import (
    RuleContextBundle,
    RuleContextFragmentResult,
    RuleContextMissingFragment,
    RuleContextNodeMetadata,
)

from .contracts import _canonical_hash


def _context_hash(
    document: dict, metadata: RuleContextNodeMetadata, fragments: list[RuleContextFragmentResult]
) -> str:
    """绑定完整所选正文与节点需求，不把交付容量计入相同内容的身份。"""
    return _canonical_hash(
        {
            "schema_version": 2,
            "build_id": document["build_id"],
            "node_metadata": metadata.model_dump(mode="json"),
            "instructions": [item.model_dump(mode="json") for item in fragments],
        }
    )


def _budget_gaps(fragments: list[RuleContextFragmentResult]) -> list[RuleContextMissingFragment]:
    """原子交付超限时列出全部缺口，不把任何单元标成已经部分交付。"""
    return [
        RuleContextMissingFragment(
            fragment_id=item.fragment_id,
            node_id=item.node_id,
            owner_path=item.owner_path,
            owner_section=item.owner_section,
            reason="text_budget_exceeded",
        )
        for item in fragments
    ]


def _context_bundle(
    document: dict,
    metadata: RuleContextNodeMetadata,
    fragments: list[RuleContextFragmentResult],
    max_chars: int,
) -> RuleContextBundle:
    """全量正文超限时整体留空，仍保留完整需求及稳定指纹供调用方调整容量。"""
    required_chars = sum(len(item.text) for item in fragments)
    complete = required_chars <= max_chars
    return RuleContextBundle(
        schema_version=2,
        build_id=document["build_id"],
        index_sha256=_canonical_hash(document["context_index"]),
        node_id=metadata.node_id,
        language=metadata.language,
        node_metadata=metadata,
        fragments=fragments if complete else [],
        required_fragment_ids=[item.fragment_id for item in fragments],
        missing_fragments=[] if complete else _budget_gaps(fragments),
        remaining_owner_refs=[],
        remaining_owner_refs_truncated=False,
        complete=complete,
        status="complete" if complete else "incomplete_budget",
        text_budget=max_chars,
        text_characters=required_chars if complete else 0,
        required_text_characters=required_chars,
        context_hash=_context_hash(document, metadata, fragments),
    )


def _compiled_fragment(
    identity: str, node_id: str, section: str, text: str
) -> RuleContextFragmentResult:
    """生成内联单元与正文 Hash；compiled 定位不是可回读的作者路径。"""
    return RuleContextFragmentResult(
        fragment_id=identity,
        node_id=node_id,
        owner_path=f"compiled:{identity}",
        owner_section=section,
        text=text,
        text_sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(),
    )
