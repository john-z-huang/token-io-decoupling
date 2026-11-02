"""Dynamic, bounded rule-context loading from the authoritative owner documents."""

from __future__ import annotations

import hashlib
import json
import posixpath
import re
from importlib import resources
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any
from urllib.parse import unquote, urlsplit

from pydantic import ValidationError

from token_io_decoupling_core.context_index_contract import (
    CONTEXT_INDEX_SCHEMA_VERSION,
    MAX_CONTEXT_FRAGMENTS,
    validate_context_index,
)
from token_io_decoupling_core.heading_parser import (
    DuplicateHeadingError,
    HeadingNotFoundError,
    extract_heading,
)
from token_io_decoupling_core.models import (
    Language,
    RuleContext,
    RuleContextBundle,
    RuleContextFragmentResult,
    RuleContextIndex,
    RuleContextMissingFragment,
    RuleContextNodeMetadata,
    RuleContextOwnerReference,
    RuleNode,
    RuleRegistry,
)
from token_io_decoupling_core.owner_paths import (
    DELEGATION_POLICY_OWNERS,
    OPTIONAL_FRAGMENT_OWNER_BINDINGS,
    OWNER_PATHS,
)
from token_io_decoupling_core.registry_contract import (
    UnsupportedRegistryShapeError,
    validate_supported_registry_shape,
)

SUPPORTED_CONTRACT_VERSION = 2
SUPPORTED_CONTEXT_INDEX_VERSION = CONTEXT_INDEX_SCHEMA_VERSION
DEFAULT_CONTEXT_TEXT_BUDGET = 12_000
MIN_CONTEXT_TEXT_BUDGET = 256
MAX_CONTEXT_TEXT_BUDGET = 60_000
MAX_REMAINING_OWNER_REFS = 16
_MARKDOWN_LINK = re.compile(r"\]\(([^)]+)\)")


class RuleLoadError(RuntimeError):
    """Base error for an unavailable or invalid rule context."""


class UnknownRuleNodeError(RuleLoadError):
    """Raised when a caller requests a node that is not registered."""


class IncompatibleRuleContractError(RuleLoadError):
    """Raised when a registry was authored for a different contract version."""


class UnsafeRulePathError(RuleLoadError):
    """Raised when a registry path traverses outside its trusted source root."""


class RuleLoader:
    """Load only a selected node and its bilingual owner heading on each request.

    The default loader reads resources generated into the built package. Source
    development must opt in with ``repository_root``; this avoids guessing a
    checkout location after installation.
    """

    def __init__(
        self,
        *,
        repository_root: Path | str | None = None,
        default_language: Language = "en",
    ) -> None:
        self._repository_root = Path(repository_root) if repository_root is not None else None
        self._default_language = default_language

    def load_context(self, node_id: str, *, language: Language | None = None) -> RuleContext:
        selected_language = language or self._default_language
        registry = self._load_registry()
        if registry.contract_version != SUPPORTED_CONTRACT_VERSION:
            raise IncompatibleRuleContractError(
                f"unsupported contract_version={registry.contract_version}; "
                f"supported={SUPPORTED_CONTRACT_VERSION}"
            )
        node = next((item for item in registry.nodes if item.node_id == node_id), None)
        if node is None:
            raise UnknownRuleNodeError(f"unknown rule node: {node_id}")

        owner_path, owner_section = self._owner_for_language(node, selected_language)
        if self._repository_root is None:
            owner_text = self._read_packaged_owner(node, selected_language)
        else:
            owner_text = self._read_repository_owner(owner_path, owner_section)

        # Hash the same canonical text returned by RuleContext, for either source.
        owner_text = owner_text.strip()
        if not owner_text:
            raise RuleLoadError("owner text is empty")
        node_shape = node.model_dump(exclude={"resource_paths"}, mode="json")
        bound_context = json.dumps(
            {"node": node_shape, "language": selected_language, "owner_text": owner_text},
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return RuleContext.model_validate(
            {
                "node_id": node.node_id,
                "language": selected_language,
                "owner_path": owner_path,
                "owner_section": owner_section,
                "owner_text": owner_text,
                "required_facts": node.required_facts,
                "required_evidence": node.required_evidence,
                "legal_branches": node.legal_branches,
                "evaluation_mode": node.evaluation_mode,
                "failure_action": node.failure_action,
                "next_checkpoint_ids": node.next_checkpoint_ids,
                "context_hash": hashlib.sha256(bound_context).hexdigest(),
            }
        )

    def load_context_bundle(
        self,
        node_id: str,
        *,
        language: Language | None = None,
        fragment_ids: list[str] | None = None,
        max_chars: int = DEFAULT_CONTEXT_TEXT_BUDGET,
    ) -> RuleContextBundle:
        """Load the versioned indexed owner closure under a text-character budget."""
        selected_language = language or self._default_language
        if not MIN_CONTEXT_TEXT_BUDGET <= max_chars <= MAX_CONTEXT_TEXT_BUDGET:
            raise RuleLoadError(
                f"max_chars must be between {MIN_CONTEXT_TEXT_BUDGET} and "
                f"{MAX_CONTEXT_TEXT_BUDGET} Unicode text characters"
            )
        registry = self._load_registry()
        if registry.contract_version != SUPPORTED_CONTRACT_VERSION:
            raise IncompatibleRuleContractError(
                f"unsupported contract_version={registry.contract_version}; "
                f"supported={SUPPORTED_CONTRACT_VERSION}"
            )
        rule_node = next((item for item in registry.nodes if item.node_id == node_id), None)
        if rule_node is None:
            raise UnknownRuleNodeError(f"unknown rule node: {node_id}")

        _index, index_nodes, index_fragments, index_sha256 = self._load_context_index(registry)
        index_node = index_nodes.get(node_id)
        if index_node is None:
            raise IncompatibleRuleContractError(f"node {node_id} is missing from context index")
        requested = list(index_node.default_fragment_ids)
        if fragment_ids is not None:
            if len(fragment_ids) != len(set(fragment_ids)):
                raise RuleLoadError("fragment_ids must not contain duplicates")
            requested.extend(fragment_ids)
        closure = self._fragment_closure(requested, index_fragments)

        owner_path, owner_section = self._owner_for_language(rule_node, selected_language)
        metadata = RuleContextNodeMetadata.model_validate(
            {
                "node_id": rule_node.node_id,
                "language": selected_language,
                "owner_path": owner_path,
                "owner_section": owner_section,
                "required_facts": rule_node.required_facts,
                "required_evidence": rule_node.required_evidence,
                "legal_branches": rule_node.legal_branches,
                "evaluation_mode": rule_node.evaluation_mode,
                "failure_action": rule_node.failure_action,
                "next_checkpoint_ids": rule_node.next_checkpoint_ids,
            }
        )

        loaded: list[tuple[str, str, str, str, str]] = []
        missing: list[RuleContextMissingFragment] = []
        for fragment_id in closure:
            fragment = index_fragments[fragment_id]
            mapped_node = next(
                (item for item in registry.nodes if item.node_id == fragment.node_id), None
            )
            if mapped_node is None:
                raise IncompatibleRuleContractError(
                    f"fragment {fragment_id} refers to unknown node {fragment.node_id}"
                )
            owner_binding = OPTIONAL_FRAGMENT_OWNER_BINDINGS.get(fragment_id)
            if owner_binding is None:
                path, _registered_section = self._owner_for_language(mapped_node, selected_language)
            else:
                _expected_node, owner_key = owner_binding
                path = OWNER_PATHS[owner_key]
                if selected_language == "zh_cn":
                    path = path.removesuffix(".md") + "_zh_cn.md"
            section = fragment.section_en if selected_language == "en" else fragment.section_zh_cn
            try:
                text = self._read_indexed_fragment(fragment_id, path, section, selected_language)
            except FileNotFoundError:
                missing.append(
                    RuleContextMissingFragment.model_validate(
                        {
                            "fragment_id": fragment_id,
                            "node_id": fragment.node_id,
                            "owner_path": path,
                            "owner_section": section,
                            "reason": "owner_resource_missing",
                        }
                    )
                )
                continue
            except HeadingNotFoundError:
                missing.append(
                    RuleContextMissingFragment.model_validate(
                        {
                            "fragment_id": fragment_id,
                            "node_id": fragment.node_id,
                            "owner_path": path,
                            "owner_section": section,
                            "reason": "owner_heading_missing_or_empty",
                        }
                    )
                )
                continue
            except DuplicateHeadingError as exc:
                raise RuleLoadError(
                    f"duplicate indexed owner heading {section!r} in {path}"
                ) from exc
            loaded.append((fragment_id, fragment.node_id, path, section, text))

        required_text_characters = sum(len(item[4]) for item in loaded)
        available: list[RuleContextFragmentResult] = []
        used_text_characters = 0
        for fragment_id, fragment_node_id, path, section, text in loaded:
            if used_text_characters + len(text) > max_chars:
                missing.append(
                    RuleContextMissingFragment.model_validate(
                        {
                            "fragment_id": fragment_id,
                            "node_id": fragment_node_id,
                            "owner_path": path,
                            "owner_section": section,
                            "reason": "text_budget_exceeded",
                        }
                    )
                )
                continue
            digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
            available.append(
                RuleContextFragmentResult.model_validate(
                    {
                        "fragment_id": fragment_id,
                        "node_id": fragment_node_id,
                        "owner_path": path,
                        "owner_section": section,
                        "text": text,
                        "text_sha256": digest,
                    }
                )
            )
            used_text_characters += len(text)

        status = (
            "incomplete_content"
            if any(item.reason != "text_budget_exceeded" for item in missing)
            else "incomplete_budget"
            if missing
            else "complete"
        )
        remaining_refs, refs_truncated = _remaining_owner_references(available)
        hash_body = {
            "schema_version": SUPPORTED_CONTEXT_INDEX_VERSION,
            "index_sha256": index_sha256,
            "node_id": node_id,
            "language": selected_language,
            "node_metadata": metadata.model_dump(mode="json"),
            "required_fragment_ids": closure,
            "fragments": [item.model_dump(mode="json") for item in available],
            "missing_fragments": [item.model_dump(mode="json") for item in missing],
            "remaining_owner_refs": [item.model_dump(mode="json") for item in remaining_refs],
            "remaining_owner_refs_truncated": refs_truncated,
            "text_budget": max_chars,
            "text_characters": used_text_characters,
            "required_text_characters": required_text_characters,
            "complete": not missing,
            "status": status,
        }
        encoded = json.dumps(
            hash_body, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        return RuleContextBundle.model_validate(
            {
                **hash_body,
                "context_hash": hashlib.sha256(encoded).hexdigest(),
            }
        )

    def _load_context_index(
        self, registry: RuleRegistry
    ) -> tuple[RuleContextIndex, dict[str, Any], dict[str, Any], str]:
        try:
            if self._repository_root is not None:
                raw = self._safe_repository_path("mcp/rule-context-index.json").read_bytes()
            else:
                raw = (
                    resources.files("token_io_decoupling_core")
                    .joinpath("_resources", "context-index.json")
                    .read_bytes()
                )
            decoded = json.loads(raw)
            validate_context_index(decoded, registry.model_dump(mode="json"))
            index = RuleContextIndex.model_validate(decoded)
        except (OSError, ValidationError, json.JSONDecodeError) as exc:
            raise RuleLoadError(f"cannot load valid context index: {exc}") from exc
        except ValueError as exc:
            raise IncompatibleRuleContractError(str(exc)) from exc
        index_nodes = {item.node_id: item for item in index.nodes}
        index_fragments = {item.fragment_id: item for item in index.fragments}
        self._fragment_closure(list(index_fragments), index_fragments)
        canonical_index = json.dumps(
            index.model_dump(mode="json"),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return index, index_nodes, index_fragments, hashlib.sha256(canonical_index).hexdigest()

    @staticmethod
    def _fragment_closure(requested: list[str], fragments: dict[str, Any]) -> list[str]:
        ordered: list[str] = []
        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(fragment_id: str) -> None:
            if fragment_id not in fragments:
                raise RuleLoadError(f"unknown context fragment: {fragment_id}")
            if fragment_id in visiting:
                raise IncompatibleRuleContractError(
                    f"cycle in context fragment dependencies at {fragment_id}"
                )
            if fragment_id in visited:
                return
            visiting.add(fragment_id)
            visited.add(fragment_id)
            ordered.append(fragment_id)
            for dependency in fragments[fragment_id].dependencies:
                visit(dependency)
            visiting.remove(fragment_id)

        for fragment_id in requested:
            visit(fragment_id)
        if len(ordered) > MAX_CONTEXT_FRAGMENTS:
            raise IncompatibleRuleContractError("selected context exceeds the fragment limit")
        return ordered

    def _read_indexed_fragment(
        self, fragment_id: str, owner_path: str, section: str, language: Language
    ) -> str:
        if self._repository_root is not None:
            path = self._safe_repository_path(owner_path)
            return extract_heading(path.read_text(encoding="utf-8"), section)
        try:
            resource = (
                resources.files("token_io_decoupling_core")
                .joinpath("_resources", "fragments", f"{fragment_id}.{language}.md")
                .read_text(encoding="utf-8")
            )
        except OSError as exc:
            raise FileNotFoundError(fragment_id) from exc
        text = resource.strip()
        if not text:
            raise HeadingNotFoundError(f"empty packaged fragment: {fragment_id}")
        return text

    def load_delegation_policy(self, owner: str) -> tuple[str, str]:
        """Read an allowlisted current owner; standalone advice does not register a Core node."""
        if owner not in DELEGATION_POLICY_OWNERS:
            raise RuleLoadError("unknown delegation policy")
        path = OWNER_PATHS.get(owner)
        if not isinstance(path, str):
            raise RuleLoadError("missing mapped delegation policy")
        if self._repository_root is not None:
            text = self._read_repository_owner(path, "General rules")
        else:
            try:
                text = (
                    resources.files("token_io_decoupling_core")
                    .joinpath("_resources", "rules", f"{owner}.en.md")
                    .read_text(encoding="utf-8")
                )
            except OSError as exc:
                raise RuleLoadError("missing packaged delegation policy") from exc
        text = text.strip()
        if not text or len(text) > 18000:
            raise RuleLoadError("delegation policy is empty or exceeds its budget")
        return text, hashlib.sha256(text.encode("utf-8")).hexdigest()

    def _load_registry(self) -> RuleRegistry:
        try:
            if self._repository_root is not None:
                registry_path = self._safe_repository_path("mcp/rule-registry.json")
                raw = registry_path.read_bytes()
            else:
                raw = (
                    resources.files("token_io_decoupling_core")
                    .joinpath("_resources", "registry.json")
                    .read_bytes()
                )
            decoded = json.loads(raw)
            validate_supported_registry_shape(decoded)
            return RuleRegistry.model_validate(decoded)
        except UnsupportedRegistryShapeError as exc:
            raise IncompatibleRuleContractError(str(exc)) from exc
        except (OSError, ValidationError, json.JSONDecodeError) as exc:
            raise RuleLoadError(f"cannot load valid rule registry: {exc}") from exc

    @staticmethod
    def _owner_for_language(node: RuleNode, language: Language) -> tuple[str, str]:
        if language == "en":
            return node.owner_path, node.owner_section
        mirror = node.owner_mirrors.get("zh_cn")
        if mirror is None:
            raise RuleLoadError(f"node {node.node_id} has no {language} owner mapping")
        return mirror.path, mirror.section

    def _read_repository_owner(self, owner_path: str, owner_section: str) -> str:
        path = self._safe_repository_path(owner_path)
        return _extract_heading(path.read_text(encoding="utf-8"), owner_section, owner_path)

    def _safe_repository_path(self, relative: str) -> Path:
        if self._repository_root is None:
            raise RuntimeError("repository_root is not configured")
        pure_path = PurePosixPath(relative)
        windows_path = PureWindowsPath(relative)
        if (
            pure_path.is_absolute()
            or windows_path.is_absolute()
            or windows_path.drive
            or "\\" in relative
            or "\x00" in relative
            or ".." in pure_path.parts
            or not pure_path.parts
        ):
            raise UnsafeRulePathError(f"unsafe relative path: {relative}")

        root = self._repository_root.resolve(strict=True)
        candidate = root
        for component in pure_path.parts:
            candidate = candidate / component
            if candidate.is_symlink():
                raise UnsafeRulePathError(f"symlink in owner path: {relative}")
        resolved = candidate.resolve(strict=True)
        if not resolved.is_relative_to(root) or not resolved.is_file():
            raise UnsafeRulePathError(f"path escapes repository root: {relative}")
        return resolved

    @staticmethod
    def _read_packaged_owner(node: RuleNode, language: Language) -> str:
        resource_path = node.resource_paths.get(language)
        if resource_path is None:
            raise RuleLoadError(f"node {node.node_id} has no packaged resource for {language}")
        pure_path = PurePosixPath(resource_path)
        if pure_path.is_absolute() or ".." in pure_path.parts:
            raise UnsafeRulePathError(f"unsafe packaged resource path: {resource_path}")
        try:
            return (
                resources.files("token_io_decoupling_core")
                .joinpath("_resources", *pure_path.parts)
                .read_text(encoding="utf-8")
            )
        except OSError as exc:
            raise RuleLoadError(f"missing packaged owner resource: {resource_path}") from exc


def _extract_heading(source: str, title: str, path: str) -> str:
    try:
        return extract_heading(source, title)
    except DuplicateHeadingError as exc:
        raise RuleLoadError(f"expected one heading {title!r} in {path}: {exc}") from exc
    except HeadingNotFoundError as exc:
        raise RuleLoadError(f"owner heading {title!r} in {path} is missing or empty") from exc


def _remaining_owner_references(
    fragments: list[RuleContextFragmentResult],
) -> tuple[list[RuleContextOwnerReference], bool]:
    """List direct local Markdown links not present among returned fragments."""
    included_sections = {(item.owner_path, _heading_slug(item.owner_section)) for item in fragments}
    remaining: dict[tuple[str, str | None], RuleContextOwnerReference] = {}
    references_truncated = False
    for fragment in fragments:
        fence: str | None = None
        fence_length = 0
        for line in fragment.text.splitlines():
            fence_match = re.match(r"^ {0,3}(`{3,}|~{3,})(.*)$", line)
            if fence is not None:
                if (
                    fence_match
                    and fence_match.group(1)[0] == fence
                    and len(fence_match.group(1)) >= fence_length
                    and not fence_match.group(2).strip(" \t")
                ):
                    fence = None
                    fence_length = 0
                continue
            if fence_match:
                marker = fence_match.group(1)
                if marker[0] != "`" or "`" not in fence_match.group(2):
                    fence = marker[0]
                    fence_length = len(marker)
                continue
            for match in _MARKDOWN_LINK.finditer(line):
                destination = match.group(1).strip()
                if not destination:
                    continue
                if destination.startswith("<") and ">" in destination:
                    destination = destination[1 : destination.index(">")]
                else:
                    destination = destination.split(maxsplit=1)[0]
                parsed = urlsplit(destination)
                if parsed.scheme or parsed.netloc or "\\" in parsed.path or "\x00" in parsed.path:
                    continue
                linked_path = unquote(parsed.path)
                if linked_path and not linked_path.endswith(".md"):
                    continue
                source_dir = posixpath.dirname(fragment.owner_path)
                target_path = (
                    posixpath.normpath(posixpath.join(source_dir, linked_path))
                    if linked_path
                    else fragment.owner_path
                )
                if (
                    target_path.startswith("../")
                    or target_path == ".."
                    or target_path.startswith("/")
                ):
                    continue
                section = unquote(parsed.fragment) or None
                if len(target_path) > 512 or (section is not None and len(section) > 256):
                    references_truncated = True
                    continue
                if section is None:
                    # A returned section never proves that the complete owner file was read.
                    already_included = False
                else:
                    already_included = (target_path, _heading_slug(section)) in included_sections
                if already_included:
                    continue
                key = (target_path, section)
                remaining.setdefault(
                    key,
                    RuleContextOwnerReference.model_validate(
                        {"path": target_path, "section": section}
                    ),
                )
    ordered = [
        remaining[key] for key in sorted(remaining, key=lambda item: (item[0], item[1] or ""))
    ]
    return (
        ordered[:MAX_REMAINING_OWNER_REFS],
        references_truncated or len(ordered) > MAX_REMAINING_OWNER_REFS,
    )


def _heading_slug(value: str) -> str:
    return re.sub(r"[^\w-]+", "-", value.strip().lower(), flags=re.UNICODE).strip("-")
