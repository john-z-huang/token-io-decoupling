"""Dynamic, bounded rule-context loading from the authoritative owner documents."""

from __future__ import annotations

import hashlib
import json
import re
from importlib import resources
from pathlib import Path, PurePosixPath

from pydantic import ValidationError

from token_io_decoupling_core.models import Language, RuleContext, RuleNode, RuleRegistry
from token_io_decoupling_core.owner_paths import OWNER_PATHS
from token_io_decoupling_core.registry_contract import (
    UnsupportedRegistryShapeError,
    validate_supported_registry_shape,
)

SUPPORTED_CONTRACT_VERSION = 1


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

    def load_delegation_policy(self, owner: str) -> tuple[str, str]:
        """Read an allowlisted current owner; standalone advice does not register a Core node."""
        allowed = {
            "child-role-selection",
            "task-assignment",
            "output-token-routing",
            "session-role-ownership",
            "decision-context-generation",
        }
        if owner not in allowed:
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
        if not text.strip() or len(text) > 18000:
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
        if pure_path.is_absolute() or ".." in pure_path.parts or not pure_path.parts:
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
    matches = list(re.finditer(r"^(#{1,6})\s+" + re.escape(title) + r"\s*$", source, re.M))
    if len(matches) != 1:
        raise RuleLoadError(f"expected one heading {title!r} in {path}, found {len(matches)}")
    match = matches[0]
    level = len(match.group(1))
    next_heading = re.search(r"^#{1," + str(level) + r"}\s+", source[match.end() :], re.M)
    end = match.end() + next_heading.start() if next_heading else len(source)
    text = source[match.end() : end].strip()
    if not text:
        raise RuleLoadError(f"owner heading {title!r} in {path} is empty")
    return text
