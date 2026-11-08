"""按稳定 owner 索引读取已编译中文规则。"""

from __future__ import annotations

import hashlib
import json
from importlib import resources
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from token_io_decoupling_core.models import (
    Language,
    RuleContext,
    RuleContextBundle,
    RuleContextFragmentResult,
    RuleContextIndex,
    RuleContextNodeMetadata,
    RuleRegistry,
)
from token_io_decoupling_core.registry_contract import (
    UnsupportedRegistryShapeError,
)
from token_io_decoupling_workflow.events.contracts import (
    EVENT_IDS,
    MAX_CONTEXT_TEXT_BUDGET,
    MIN_CONTEXT_TEXT_BUDGET,
    WORKFLOW_MODES,
    CompiledEvent,
    CompiledWorkflow,
)

from .context import _compiled_fragment, _context_bundle
from .contracts import (
    _REQUIRED_POLICY_SECTIONS,
    DEFAULT_CONTEXT_TEXT_BUDGET,
    MAX_COMPILED_RESOURCE_BYTES,
    CompiledDelegationPolicy,
    IncompatibleRuleContractError,
    RuleLoadError,
    UnknownRuleNodeError,
    _canonical_hash,
)
from .validation import _validate_manifest, _validate_resource_sections


class RuleLoader:
    """源码与安装环境都只读取批准 JSON；不解释作者 Markdown 或保存运行状态。"""

    def __init__(
        self, *, repository_root: Path | str | None = None, default_language: Language = "zh_cn"
    ) -> None:
        """repository_root 仅兼容旧调用，不参与资源选择；默认语言仍须通过加载校验。"""
        self._default_language = default_language

    def _load_document(self) -> dict[str, Any]:
        """只读取批准包资源，先限大小再验完整契约；任何失败都不回读作者源。"""
        try:
            root = resources.files("token_io_decoupling_workflow").joinpath("_resources")
            manifest_raw = root.joinpath("manifest.json").read_bytes()
            raw = root.joinpath("instructions.json").read_bytes()
            if len(raw) > MAX_COMPILED_RESOURCE_BYTES or len(manifest_raw) > 1_000_000:
                raise RuleLoadError("compiled resources exceed the supported bound")
            manifest, document = json.loads(manifest_raw), json.loads(raw)
            if not isinstance(manifest, dict) or not isinstance(document, dict):
                raise RuleLoadError("compiled resources must be JSON objects")
            _validate_manifest(manifest, document, raw)
            _validate_resource_sections(document)
            return document
        except UnsupportedRegistryShapeError as exc:
            raise IncompatibleRuleContractError(str(exc)) from exc
        except (OSError, ValidationError, json.JSONDecodeError, UnicodeError) as exc:
            raise RuleLoadError("cannot load valid compiled instruction resources") from exc

    @staticmethod
    def _language(language: str) -> Language:
        """执行中文单源边界，拒绝显式英文值而非静默切换成默认语言。"""
        if language != "zh_cn":
            raise RuleLoadError("unsupported instruction language")
        return language

    @staticmethod
    def _entry(document: dict[str, Any], collection: str, identity: str) -> dict[str, Any]:
        """按 ID 读取唯一编译项并验证正文与单元来源，缺失或损坏时拒绝。"""
        try:
            entry = document[collection][identity]
        except (KeyError, TypeError) as exc:
            raise RuleLoadError(f"missing compiled {collection} instruction: {identity}") from exc
        entry = RuleLoader._validate_text_entry(entry, identity)
        if collection != "policies":
            RuleLoader._validate_instruction_ids(entry, identity)
        return entry

    @staticmethod
    def _validate_instruction_ids(entry: dict[str, Any], identity: str) -> None:
        instruction_ids = entry.get("instruction_ids")
        if (
            not isinstance(instruction_ids, list)
            or not instruction_ids
            or not all(
                isinstance(item, str) and item and item == item.strip() for item in instruction_ids
            )
            or len(instruction_ids) != len(set(instruction_ids))
        ):
            raise RuleLoadError(f"missing or invalid compiled instruction identities: {identity}")

    @staticmethod
    def _validate_text_entry(entry: Any, identity: str) -> dict[str, Any]:
        if not isinstance(entry, dict):
            raise RuleLoadError(f"invalid compiled instruction: {identity}")
        text = entry.get("text")
        expected = entry.get("content_sha256", entry.get("text_sha256"))
        if (
            not isinstance(text, str)
            or not text.strip()
            or text != text.strip()
            or expected != hashlib.sha256(text.encode("utf-8")).hexdigest()
        ):
            raise RuleLoadError(f"invalid compiled instruction text/hash: {identity}")
        return entry

    @staticmethod
    def _metadata(
        document: dict[str, Any], node_id: str, language: Language
    ) -> RuleContextNodeMetadata:
        """从固定注册表投影唯一 owner 及需求，未知节点不能合成默认规则。"""
        registry = RuleRegistry.model_validate(document["registry"])
        node = next((item for item in registry.nodes if item.node_id == node_id), None)
        if node is None:
            raise UnknownRuleNodeError(f"unknown rule node: {node_id}")
        return RuleContextNodeMetadata.model_validate(
            {
                **node.model_dump(mode="json"),
                "language": language,
            }
        )

    def load_context(self, node_id: str, *, language: Language | None = None) -> RuleContext:
        """为一次检查返回完整默认节点，与公开 bundle 使用相同内容指纹。"""
        bundle = self.load_context_bundle(
            node_id, language=language, max_chars=MAX_CONTEXT_TEXT_BUDGET
        )
        if not bundle.complete:
            raise RuleLoadError("complete compiled node instruction exceeds the supported bound")
        return RuleContext.model_validate(
            {
                **bundle.node_metadata.model_dump(mode="json"),
                "schema_version": 2,
                "build_id": bundle.build_id,
                "owner_text": bundle.fragments[0].text,
                "context_hash": bundle.context_hash,
            }
        )

    @staticmethod
    def _instruction_fragments(
        document: dict, metadata: RuleContextNodeMetadata, requested: list[str]
    ) -> list[RuleContextFragmentResult]:
        """区分默认完整节点和显式单元选择，拒绝重复或未知 ID，不隐式补源。"""
        if len(requested) != len(set(requested)):
            raise RuleLoadError("fragment_ids must not contain duplicates")
        if not requested:
            entry = RuleLoader._entry(document, "nodes", metadata.node_id)
            return [
                _compiled_fragment(
                    f"{metadata.node_id}.compiled",
                    metadata.node_id,
                    metadata.owner_section,
                    entry["text"],
                )
            ]
        index = RuleContextIndex.model_validate(document["context_index"])
        source_nodes = {item.fragment_id: item for item in index.fragments}
        fragments = []
        for identity in requested:
            if identity not in source_nodes:
                raise RuleLoadError(f"unknown compiled fragment: {identity}")
            source = source_nodes[identity]
            entry = RuleLoader._entry(document, "fragments", identity)
            fragments.append(
                _compiled_fragment(identity, source.node_id, source.section, entry["text"])
            )
        return fragments

    def load_context_bundle(
        self,
        node_id: str,
        *,
        language: Language | None = None,
        fragment_ids: list[str] | None = None,
        max_chars: int = DEFAULT_CONTEXT_TEXT_BUDGET,
    ) -> RuleContextBundle:
        """按 schema 3 单中文资源原子交付，外部查询信封继续使用版本 2。"""
        if (
            type(max_chars) is not int
            or not MIN_CONTEXT_TEXT_BUDGET <= max_chars <= MAX_CONTEXT_TEXT_BUDGET
        ):
            raise RuleLoadError(
                f"max_chars must be between {MIN_CONTEXT_TEXT_BUDGET} and "
                f"{MAX_CONTEXT_TEXT_BUDGET} Unicode characters"
            )
        selected_language = self._language(self._default_language if language is None else language)
        document = self._load_document()
        metadata = self._metadata(document, node_id, selected_language)
        fragments = self._instruction_fragments(document, metadata, fragment_ids or [])
        return _context_bundle(document, metadata, fragments, max_chars)

    def load_delegation_policy(self, owner: str) -> CompiledDelegationPolicy:
        """加载当前中文政策及已编译选项，Hash 绑定正文与语义索引。"""
        document = self._load_document()
        entry = self._entry(document, "policies", owner)
        if len(entry["text"]) > 18_000:
            raise RuleLoadError("compiled delegation policy exceeds its supported bound")
        sections, choices = entry.get("sections"), entry.get("choices")
        if not isinstance(sections, dict) or not isinstance(choices, dict):
            raise RuleLoadError("compiled delegation sections/choices are invalid")
        required_sections = _REQUIRED_POLICY_SECTIONS.get(owner, ())
        if any(not sections.get(name) for name in required_sections):
            raise RuleLoadError("compiled delegation policy is missing its semantic sections")
        if any(
            not choices.get(name) for name in required_sections if "choice descriptions" in name
        ):
            raise RuleLoadError("compiled delegation policy is missing its choice descriptions")
        for values in [sections, *choices.values()]:
            if not isinstance(values, dict) or not all(
                isinstance(key, str) and isinstance(value, str) and value.strip()
                for key, value in values.items()
            ):
                raise RuleLoadError("compiled delegation sections/choices are invalid")
        policy_hash = _canonical_hash({"build_id": document["build_id"], "policy": entry})
        return CompiledDelegationPolicy(entry["text"], policy_hash, sections, choices)

    def load_event(
        self, event: str, *, language: Language = "zh_cn", mode: str | None = None
    ) -> CompiledEvent:
        """读取完整事件规则，不保存调用历史或选择后继步骤。"""
        if event not in EVENT_IDS:
            raise RuleLoadError("unknown compiled event")
        if mode is not None and mode not in WORKFLOW_MODES:
            raise RuleLoadError("unknown workflow mode")
        selected_language = self._language(language)
        document = self._load_document()
        entry = self._entry(document, "events", event)
        self._validate_instruction_ids(entry, f"event/{event}")
        try:
            compiled = CompiledEvent.model_validate(
                {
                    **entry,
                    "build_id": document["build_id"],
                    "language": selected_language,
                    "rule_hash": entry["content_sha256"],
                }
            )
        except ValidationError as exc:
            raise IncompatibleRuleContractError("invalid compiled event contract") from exc
        if compiled.event_id != event:
            raise IncompatibleRuleContractError("compiled event identity mismatch")
        if mode is not None and mode not in compiled.modes:
            raise RuleLoadError("event does not apply to the requested mode")
        return compiled

    def load_workflow(self, mode: str, *, language: Language = "zh_cn") -> CompiledWorkflow:
        """返回已选模式的短指令，模式选择与运行状态均由 Agent 持有。"""
        if mode not in WORKFLOW_MODES:
            raise RuleLoadError("unknown workflow mode")
        selected_language = self._language(language)
        document = self._load_document()
        entry = self._entry(document, "workflows", mode)
        self._validate_instruction_ids(entry, f"workflow/{mode}")
        try:
            return CompiledWorkflow.model_validate(
                {
                    **entry,
                    "schema_version": 1,
                    "build_id": document["build_id"],
                    "mode": mode,
                    "language": selected_language,
                }
            )
        except ValidationError as exc:
            raise IncompatibleRuleContractError("invalid compiled workflow contract") from exc

    def _load_registry(self) -> RuleRegistry:
        return RuleRegistry.model_validate(self._load_document()["registry"])
