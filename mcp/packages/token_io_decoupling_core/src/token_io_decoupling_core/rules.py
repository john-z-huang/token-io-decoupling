"""Load approved compiled instructions without interpreting author documents."""

from __future__ import annotations

import hashlib
import json
import re
from importlib import resources
from pathlib import Path
from typing import Any, NamedTuple

from pydantic import ValidationError

from token_io_decoupling_core.models import (
    Language,
    RuleContext,
    RuleContextBundle,
    RuleContextFragmentResult,
    RuleContextMissingFragment,
    RuleContextNodeMetadata,
    RuleRegistry,
)
from token_io_decoupling_core.registry_contract import (
    UnsupportedRegistryShapeError,
    validate_supported_registry_shape,
)

SUPPORTED_CONTRACT_VERSION = 2
SUPPORTED_CONTEXT_INDEX_VERSION = 2
DEFAULT_CONTEXT_TEXT_BUDGET = 12_000
MIN_CONTEXT_TEXT_BUDGET = 256
MAX_CONTEXT_TEXT_BUDGET = 60_000
MAX_REMAINING_OWNER_REFS = 16
MAX_COMPILED_RESOURCE_BYTES = 32 * 1024 * 1024
_SHA256 = re.compile(r"[0-9a-f]{64}")
_STAGES = (
    "entry_readiness",
    "session_readiness",
    "work_definition",
    "execution",
    "verification_repair",
    "documentation",
    "delivery_acceptance",
)


class RuleLoadError(RuntimeError):
    """An approved instruction resource is unavailable, incomplete, or invalid."""


class UnknownRuleNodeError(RuleLoadError):
    """The requested instruction node is not registered."""


class IncompatibleRuleContractError(RuleLoadError):
    """The installed resource and consumer contracts are incompatible."""


class UnsafeRulePathError(RuleLoadError):
    """Retained exception type for the retired author-path loader."""


class CompiledDelegationPolicy(NamedTuple):
    text: str
    content_sha256: str
    sections: dict[str, str]
    choices: dict[str, dict[str, str]]


def _canonical_hash(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(encoded).hexdigest()


class RuleLoader:
    """Use the same approved package JSON in source and installed executions.

    ``repository_root`` is a constructor compatibility argument only. It never
    selects author files, runs a compiler, or changes the trusted resource location.
    Every call validates the current manifest without a source fallback.
    """

    def __init__(
        self, *, repository_root: Path | str | None = None, default_language: Language = "en"
    ) -> None:
        self._default_language = default_language

    def _load_document(self) -> dict[str, Any]:
        try:
            root = resources.files("token_io_decoupling_core").joinpath("_resources")
            manifest_raw = root.joinpath("manifest.json").read_bytes()
            raw = root.joinpath("instructions.json").read_bytes()
            if len(raw) > MAX_COMPILED_RESOURCE_BYTES or len(manifest_raw) > 1_000_000:
                raise RuleLoadError("compiled resources exceed the supported bound")
            manifest, document = json.loads(manifest_raw), json.loads(raw)
            if not isinstance(manifest, dict) or not isinstance(document, dict):
                raise RuleLoadError("compiled resources must be JSON objects")
            if any(
                type(value.get("schema_version")) is not int or value["schema_version"] != 2
                for value in (manifest, document)
            ):
                raise IncompatibleRuleContractError("compiled instruction schema_version must be 2")
            build_id = document.get("build_id")
            if (
                not isinstance(build_id, str)
                or _SHA256.fullmatch(build_id) is None
                or manifest.get("build_id") != build_id
            ):
                raise IncompatibleRuleContractError("compiled instruction build identity mismatch")
            files = manifest.get("files")
            if (
                not isinstance(files, dict)
                or files.get("instructions.json") != hashlib.sha256(raw).hexdigest()
            ):
                raise RuleLoadError("compiled instruction resource hash mismatch")
            for key in ("registry", "context_index", "nodes", "fragments", "policies", "routes"):
                if not isinstance(document.get(key), dict):
                    raise RuleLoadError(f"compiled instruction resource is missing {key}")
            validate_supported_registry_shape(document["registry"])
            RuleRegistry.model_validate(document["registry"])
            return document
        except UnsupportedRegistryShapeError as exc:
            raise IncompatibleRuleContractError(str(exc)) from exc
        except (OSError, ValidationError, json.JSONDecodeError, UnicodeError) as exc:
            raise RuleLoadError("cannot load valid compiled instruction resources") from exc

    @staticmethod
    def _language(language: str) -> Language:
        if language not in {"en", "zh_cn"}:
            raise RuleLoadError("unsupported instruction language")
        return language

    @staticmethod
    def _entry(
        document: dict[str, Any], collection: str, identity: str, language: Language
    ) -> dict[str, Any]:
        try:
            entry = document[collection][identity][language]
        except (KeyError, TypeError) as exc:
            raise RuleLoadError(
                f"missing compiled {collection} instruction: {identity}/{language}"
            ) from exc
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
        registry = RuleRegistry.model_validate(document["registry"])
        node = next((item for item in registry.nodes if item.node_id == node_id), None)
        if node is None:
            raise UnknownRuleNodeError(f"unknown rule node: {node_id}")
        return RuleContextNodeMetadata.model_validate(
            {
                **node.model_dump(exclude={"owner_mirrors", "resource_paths"}, mode="json"),
                "language": language,
                "owner_path": f"compiled:{node_id}:{language}",
                "owner_section": node_id,
            }
        )

    def load_context(self, node_id: str, *, language: Language | None = None) -> RuleContext:
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

    def load_context_bundle(
        self,
        node_id: str,
        *,
        language: Language | None = None,
        fragment_ids: list[str] | None = None,
        max_chars: int = DEFAULT_CONTEXT_TEXT_BUDGET,
    ) -> RuleContextBundle:
        """Return compiler-expanded units atomically; an insufficient budget returns no text."""
        if (
            type(max_chars) is not int
            or not MIN_CONTEXT_TEXT_BUDGET <= max_chars <= MAX_CONTEXT_TEXT_BUDGET
        ):
            raise RuleLoadError(
                f"max_chars must be between {MIN_CONTEXT_TEXT_BUDGET} and "
                f"{MAX_CONTEXT_TEXT_BUDGET} Unicode characters"
            )
        selected_language = self._language(language or self._default_language)
        document = self._load_document()
        metadata = self._metadata(document, node_id, selected_language)
        entry = self._entry(document, "nodes", node_id, selected_language)
        requested = fragment_ids or []
        if len(requested) != len(set(requested)):
            raise RuleLoadError("fragment_ids must not contain duplicates")
        units = [] if requested else [(f"{node_id}.compiled", entry)]
        for fragment_id in requested:
            units.append(
                (fragment_id, self._entry(document, "fragments", fragment_id, selected_language))
            )
        source_nodes = {
            item["fragment_id"]: item["node_id"]
            for item in document["context_index"].get("fragments", [])
            if isinstance(item, dict) and "fragment_id" in item and "node_id" in item
        }
        fragments = [
            RuleContextFragmentResult(
                fragment_id=identity,
                node_id=source_nodes.get(identity, node_id),
                owner_path=f"compiled:{identity}:{selected_language}",
                owner_section=identity,
                text=unit["text"],
                text_sha256=hashlib.sha256(unit["text"].encode("utf-8")).hexdigest(),
            )
            for identity, unit in units
        ]
        required_chars = sum(len(item.text) for item in fragments)
        complete = required_chars <= max_chars
        missing = (
            []
            if complete
            else [
                RuleContextMissingFragment(
                    fragment_id=item.fragment_id,
                    node_id=item.node_id,
                    owner_path=item.owner_path,
                    owner_section=item.owner_section,
                    reason="text_budget_exceeded",
                )
                for item in fragments
            ]
        )
        identity_body = {
            "schema_version": 2,
            "build_id": document["build_id"],
            "node_metadata": metadata.model_dump(mode="json"),
            "instructions": [item.model_dump(mode="json") for item in fragments],
        }
        return RuleContextBundle(
            schema_version=2,
            build_id=document["build_id"],
            index_sha256=_canonical_hash(document["context_index"]),
            node_id=node_id,
            language=selected_language,
            node_metadata=metadata,
            fragments=fragments if complete else [],
            required_fragment_ids=[item.fragment_id for item in fragments],
            missing_fragments=missing,
            remaining_owner_refs=[],
            remaining_owner_refs_truncated=False,
            complete=complete,
            status="complete" if complete else "incomplete_budget",
            text_budget=max_chars,
            text_characters=required_chars if complete else 0,
            required_text_characters=required_chars,
            context_hash=_canonical_hash(identity_body),
        )

    def load_delegation_policy(self, owner: str) -> CompiledDelegationPolicy:
        document = self._load_document()
        entry = self._entry(document, "policies", owner, "en")
        if len(entry["text"]) > 18_000:
            raise RuleLoadError("compiled delegation policy exceeds its supported bound")
        sections, choices = entry.get("sections"), entry.get("choices")
        if not isinstance(sections, dict) or not isinstance(choices, dict):
            raise RuleLoadError("compiled delegation sections/choices are invalid")
        for values in [sections, *choices.values()]:
            if not isinstance(values, dict) or not all(
                isinstance(key, str) and isinstance(value, str) and value.strip()
                for key, value in values.items()
            ):
                raise RuleLoadError("compiled delegation sections/choices are invalid")
        policy_hash = _canonical_hash({"build_id": document["build_id"], "policy": entry})
        return CompiledDelegationPolicy(entry["text"], policy_hash, sections, choices)

    def load_stage(self, route_id: str, stage: str, *, language: Language = "en") -> dict[str, Any]:
        route_key = {
            "coding-single-agent": "single_agent",
            "coding-multi-agent": "multi_agent",
        }.get(route_id)
        if route_key is None:
            raise RuleLoadError("unknown compiled route")
        if stage not in _STAGES:
            raise RuleLoadError("unknown compiled route stage")
        selected_language = self._language(language)
        document = self._load_document()
        try:
            entry = document["routes"][route_key][selected_language]["stages"][stage]
        except (KeyError, TypeError) as exc:
            raise RuleLoadError("missing compiled route stage") from exc
        entry = self._validate_text_entry(entry, f"{route_id}/{stage}")
        self._validate_instruction_ids(entry, f"{route_id}/{stage}")
        position = _STAGES.index(stage)
        prefix = "SM" if route_key == "single_agent" else "MM"
        next_stage = _STAGES[position + 1] if position + 1 < len(_STAGES) else None
        if (
            entry.get("module_id") != f"{prefix}{position + 1:02d}"
            or entry.get("next_stage") != next_stage
        ):
            raise IncompatibleRuleContractError("compiled route checkpoint/continuation mismatch")
        if len(entry["text"]) > MAX_CONTEXT_TEXT_BUDGET:
            raise RuleLoadError("compiled route stage exceeds its supported bound")
        self._validate_shared_requirements(document, entry, route_key, selected_language)
        return {
            **entry,
            "schema_version": 2,
            "build_id": document["build_id"],
            "route_id": route_id,
            "stage": stage,
            "language": selected_language,
        }

    def _validate_shared_requirements(
        self,
        document: dict[str, Any],
        entry: dict[str, Any],
        route_key: str,
        language: Language,
    ) -> None:
        expected = {
            "common.hard_constraints": ("before_any_action", "contract"),
            f"route.{route_key}.return_map": ("needs_prerequisite", "context"),
        }
        requirements = entry.get("shared_requirements")
        if not isinstance(requirements, list) or len(requirements) != len(expected):
            raise RuleLoadError("compiled stage is missing its shared instruction requirements")
        seen: set[str] = set()
        for requirement in requirements:
            if not isinstance(requirement, dict):
                raise RuleLoadError("invalid shared instruction requirement")
            identity = requirement.get("instruction_id")
            if not isinstance(identity, str) or identity not in expected or identity in seen:
                raise RuleLoadError("invalid shared instruction identity")
            seen.add(identity)
            trigger, node_id = expected[identity]
            unit = self._entry(document, "fragments", identity, language)
            payload = {
                "node_id": node_id,
                "context_version": 2,
                "language": language,
                "fragment_ids": [identity],
            }
            lookup = requirement.get("lookup")
            if not isinstance(lookup, dict) or not isinstance(lookup.get("arguments"), dict):
                raise RuleLoadError("missing shared instruction lookup")
            actual = lookup["arguments"].get("payload")
            if not isinstance(actual, dict):
                raise RuleLoadError("invalid shared instruction lookup payload")
            budget = actual.get("max_chars")
            if (
                lookup
                != {
                    "tool": "rules_get_context",
                    "arguments": {"payload": {**payload, "max_chars": budget}},
                }
                or type(budget) is not int
                or not max(MIN_CONTEXT_TEXT_BUDGET, len(unit["text"]))
                <= budget
                <= MAX_CONTEXT_TEXT_BUDGET
                or requirement.get("when") != trigger
                or requirement.get("language") != language
                or requirement.get("text_sha256") != unit["text_sha256"]
                or requirement.get("reuse")
                != "only_exact_held_unit_from_current_build_and_matching_hash"
            ):
                raise RuleLoadError("compiled shared instruction lookup/hash/guard mismatch")

    def _load_registry(self) -> RuleRegistry:
        return RuleRegistry.model_validate(self._load_document()["registry"])
