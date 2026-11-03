"""Deterministic, fail-closed compiler for versioned runtime instruction manifests."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import stat
from collections.abc import Mapping
from contextlib import ExitStack
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import unquote, urlsplit

from token_io_decoupling_core.heading_parser import extract_heading

from .markdown_refs import extract_markdown_links, markdown_heading_locations

FORMAT = "token-io-runtime-instructions/v1"
COMPILER_VERSION = 1
MANIFEST_FORMAT = "token-io-runtime-instructions-manifest/v1"
POLICY_CONTRACT_VERSION = 2
LEGACY_CONTEXT_INDEX_VERSION = 1
MAX_ARTIFACT_BYTES = 8 * 1024 * 1024
MAX_SOURCE_UNITS = 512
MAX_ENTRY_CHARS = 262144
REFERENCE_CLASSES = {"required", "conditional", "navigation", "internal_already_included"}
LOCALES = {"en", "zh_cn"}
_ID = re.compile(r"^[a-z][a-z0-9._-]{0,119}$")


class CompileError(ValueError):
    """Invalid or incomplete compiler input; no artifact is produced."""


def _canonical(value: Any) -> bytes:
    try:
        return json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode("utf-8")
    except (TypeError, ValueError, UnicodeError) as exc:
        raise CompileError("value is not canonical JSON") from exc


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _reject_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise CompileError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_json_constant(_value: str) -> Any:
    raise CompileError("non-finite JSON constants are not permitted")


def load_json_strict(path: Path) -> Any:
    try:
        return json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_reject_duplicate_pairs,
            parse_constant=_reject_json_constant,
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise CompileError(f"cannot read strict JSON: {exc.__class__.__name__}") from exc


def _source_path(root: Path, relative: str) -> Path:
    rel = Path(relative)
    if rel.is_absolute() or not relative or ".." in rel.parts or "\\" in relative:
        raise CompileError(f"unsafe source path: {relative!r}")
    resolved_root = root.resolve(strict=True)
    candidate = root / rel
    current = root
    for part in rel.parts:
        current = current / part
        if current.is_symlink():
            raise CompileError(f"symlink source paths are not permitted: {relative!r}")
    resolved = candidate.resolve(strict=True)
    if not resolved.is_relative_to(resolved_root) or not resolved.is_file():
        raise CompileError(f"source path escapes the pinned root: {relative!r}")
    return resolved


def _local_reference_target(
    root: Path, source_relative: str, destination: str
) -> tuple[Path, int | None] | None:
    """Resolve a local link within the pinned root, or identify an external link."""
    try:
        parsed = urlsplit(destination)
        if parsed.scheme.lower() == "file":
            raise CompileError(f"unsafe local Markdown destination: {destination!r}")
        if parsed.scheme or parsed.netloc or re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", destination):
            return None
        if re.search(r"%(?![0-9a-fA-F]{2})", parsed.path + parsed.fragment):
            raise CompileError(f"invalid Markdown destination encoding: {destination!r}")
        relative = unquote(parsed.path, encoding="utf-8", errors="strict")
        anchor = unquote(parsed.fragment, encoding="utf-8", errors="strict")
        if "\\" in relative or "\x00" in relative or "\x00" in anchor:
            raise CompileError(f"unsafe local Markdown destination: {destination!r}")
        if relative.startswith("/"):
            raise CompileError(f"unsafe local Markdown destination: {destination!r}")

        current = root / PurePosixPath(source_relative).parent
        if not relative:
            current = root / source_relative
        else:
            for part in PurePosixPath(relative).parts:
                if part == "..":
                    if current == root:
                        raise CompileError(
                            f"Markdown destination escapes the pinned root: {destination!r}"
                        )
                    current = current.parent
                elif part != ".":
                    current = current / part
                    if current.is_symlink():
                        raise CompileError(f"symlink Markdown destination: {destination!r}")
        target = _source_path(root, current.relative_to(root).as_posix())
        if not anchor:
            return target, None
        text = target.read_text(encoding="utf-8")
        locations = markdown_heading_locations(text)
        match = next((position for position, _, _, _, slug in locations if slug == anchor), None)
        if match is None:
            raise CompileError(f"Markdown destination anchor is unavailable: {destination!r}")
        return target, match
    except (OSError, UnicodeError, ValueError) as exc:
        if isinstance(exc, CompileError):
            raise
        raise CompileError(f"invalid or unavailable Markdown destination: {destination!r}") from exc


def _reference_target_matches_unit(
    root: Path, target: tuple[Path, int | None], unit: Mapping[str, Any]
) -> bool:
    """Check both the target document and, when present, its covered anchor."""
    path, anchor_offset = target
    source = unit["source"]
    if _source_path(root, source["path"]) != path:
        return False
    if anchor_offset is None:
        return True
    text = path.read_text(encoding="utf-8")
    headings = markdown_heading_locations(text)
    matches = [
        item
        for item in headings
        if item[3] == source["heading"] and re.match(r" {0,3}#{1,6}[ \t]", text[item[0] :])
    ]
    if len(matches) != 1:
        return False
    start, end, level, _, _ = matches[0]
    limit = next((item[0] for item in headings if item[0] >= end and item[2] <= level), None)
    return anchor_offset >= start and (limit is None or anchor_offset < limit)


def fixed_manifest_path(root: Path) -> Path:
    """Return the trusted fixed manifest only after rejecting symlink traversal."""
    relative = Path("mcp-project-dev/compiler-manifest.v1.json")
    current = root.resolve(strict=True)
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise CompileError("fixed manifest path contains a symlink")
    resolved = current.resolve(strict=True)
    if not resolved.is_relative_to(root.resolve(strict=True)) or not resolved.is_file():
        raise CompileError("fixed manifest is unavailable inside the pinned root")
    return resolved


def fixed_output_path(root: Path) -> Path:
    """Return the fixed output path after validating existing parent components."""
    relative = Path("mcp-project-dev/generated/runtime-instructions.v1.json")
    current = root.resolve(strict=True)
    for part in relative.parts[:-1]:
        current = current / part
        if current.is_symlink():
            raise CompileError("fixed output path contains a symlink")
    output = root / relative
    if output.is_symlink():
        raise CompileError("fixed output must not be a symlink")
    return output


def read_fixed_output(root: Path, *, expected_root_identity: tuple[int, int]) -> tuple[bool, Any]:
    """Read a bounded fixed output through pinned, no-follow directory descriptors."""
    if any(not hasattr(os, name) for name in ("O_DIRECTORY", "O_NOFOLLOW", "O_NONBLOCK")):
        raise CompileError("safe fixed output inspection is unavailable")
    directory_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    with ExitStack() as stack:
        try:
            directory = os.open(root, directory_flags)
        except OSError as exc:
            raise CompileError("pinned project root is unavailable") from exc
        stack.callback(os.close, directory)
        try:
            info = os.fstat(directory)
            if (info.st_dev, info.st_ino) != expected_root_identity:
                raise CompileError("pinned project root identity changed")
            for part in ("mcp-project-dev", "generated"):
                child = os.open(part, directory_flags, dir_fd=directory)
                stack.callback(os.close, child)
                directory = child
            fd = os.open(
                "runtime-instructions.v1.json",
                os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                dir_fd=directory,
            )
            stack.callback(os.close, fd)
            before = os.fstat(fd)
            if not stat.S_ISREG(before.st_mode) or before.st_size > MAX_ARTIFACT_BYTES:
                raise CompileError("fixed output must be a bounded regular file")
            remaining = MAX_ARTIFACT_BYTES + 1
            chunks = []
            while remaining:
                chunk = os.read(fd, min(remaining, 65536))
                if not chunk:
                    break
                chunks.append(chunk)
                remaining -= len(chunk)
            after = os.fstat(fd)
        except FileNotFoundError:
            return False, None
        except OSError as exc:
            raise CompileError("fixed output is unsafe or unavailable") from exc
    raw = b"".join(chunks)

    def identity(item: os.stat_result) -> tuple[int, int, int, int]:
        return item.st_dev, item.st_ino, item.st_mtime_ns, item.st_size

    if len(raw) > MAX_ARTIFACT_BYTES or identity(before) != identity(after):
        raise CompileError("fixed output changed during inspection")
    try:
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_reject_duplicate_pairs,
            parse_constant=_reject_json_constant,
        )
        return True, value
    except (UnicodeError, ValueError) as exc:
        raise CompileError("fixed output is not strict JSON") from exc


def validate_manifest(manifest: Any) -> dict[str, Any]:
    if not isinstance(manifest, dict) or manifest.get("manifest_format") != MANIFEST_FORMAT:
        raise CompileError("unsupported manifest format")
    allowed_manifest_fields = {
        "manifest_format",
        "policy_contract_version",
        "legacy_context_index_version",
        "budgets",
        "source_units",
        "runtime_entries",
        "output_baseline_sha256",
        "legacy_source_hashes",
        "legacy_bindings",
        "owner_views",
    }
    required_manifest_fields = allowed_manifest_fields - {
        "output_baseline_sha256",
        "legacy_bindings",
        "owner_views",
    }
    if set(manifest) - allowed_manifest_fields or not required_manifest_fields <= set(manifest):
        raise CompileError("manifest has unsupported or missing fields")
    baseline = manifest.get("output_baseline_sha256")
    if baseline is not None and (
        not isinstance(baseline, str) or not re.fullmatch(r"[0-9a-f]{64}", baseline)
    ):
        raise CompileError("output_baseline_sha256 must be lowercase SHA-256 hex")
    legacy_hashes = manifest.get("legacy_source_hashes")
    if (
        not isinstance(legacy_hashes, dict)
        or not {"registry_sha256", "context_index_sha256"} <= set(legacy_hashes)
        or set(legacy_hashes) - {"registry_sha256", "context_index_sha256", "owner_paths_sha256"}
        or any(
            not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value)
            for value in legacy_hashes.values()
        )
    ):
        raise CompileError("legacy source SHA-256 provenance is required")
    if (
        type(manifest.get("policy_contract_version")) is not int
        or manifest["policy_contract_version"] != POLICY_CONTRACT_VERSION
    ):
        raise CompileError("unsupported policy contract version")
    if (
        type(manifest.get("legacy_context_index_version")) is not int
        or manifest["legacy_context_index_version"] != LEGACY_CONTEXT_INDEX_VERSION
    ):
        raise CompileError("unsupported legacy context-index version")

    budgets = manifest.get("budgets")
    budget_fields = {"artifact_bytes", "source_unit_records", "entry_closure_unicode_chars"}
    if not isinstance(budgets, dict) or set(budgets) - budget_fields:
        raise CompileError("budgets are required")
    artifact_limit = budgets.get("artifact_bytes", MAX_ARTIFACT_BYTES)
    unit_limit = budgets.get("source_unit_records", MAX_SOURCE_UNITS)
    closure_limit = budgets.get("entry_closure_unicode_chars", MAX_ENTRY_CHARS)
    if any(
        type(value) is not int or value <= 0
        for value in (artifact_limit, unit_limit, closure_limit)
    ):
        raise CompileError("budgets must be positive integers")
    if (
        artifact_limit > MAX_ARTIFACT_BYTES
        or unit_limit > MAX_SOURCE_UNITS
        or closure_limit > MAX_ENTRY_CHARS
    ):
        raise CompileError("declared budget exceeds the hard maximum")

    source_units = manifest.get("source_units")
    runtime_entries = manifest.get("runtime_entries")
    if not isinstance(source_units, list) or not source_units:
        raise CompileError("source_units must be a nonempty array")
    if len(source_units) > unit_limit:
        raise CompileError(
            f"source unit budget exceeded: required={len(source_units)} allowed={unit_limit}"
        )
    if not isinstance(runtime_entries, list) or not runtime_entries:
        raise CompileError("runtime_entries must be a nonempty array")
    if len(runtime_entries) > MAX_SOURCE_UNITS:
        raise CompileError(
            f"runtime entry record budget exceeded: required={len(runtime_entries)} "
            f"allowed={MAX_SOURCE_UNITS}"
        )

    unit_fields = {
        "source_unit_id",
        "source_kind",
        "locale",
        "source",
        "expected_hashes",
        "references",
    }
    unit_optional_fields = {"legacy_id", "legacy_node_id", "semantic_dependencies"}
    unit_map: dict[tuple[str, str], dict[str, Any]] = {}
    unit_pairs: dict[str, dict[str, dict[str, Any]]] = {}
    path_headings: set[tuple[str, str, str]] = set()
    for unit in source_units:
        if not isinstance(unit, dict) or set(unit) - unit_fields - unit_optional_fields:
            raise CompileError("source unit has unsupported fields")
        if not unit_fields <= set(unit):
            raise CompileError("source unit has missing fields")
        source_unit_id = unit["source_unit_id"]
        if not isinstance(source_unit_id, str) or not _ID.fullmatch(source_unit_id):
            raise CompileError("source_unit_id must use canonical stable syntax")
        if not isinstance(unit["source_kind"], str) or unit["source_kind"] not in {
            "fragment",
            "owner",
            "semantic_owner",
            "node_mapping",
        }:
            raise CompileError(f"unsupported source kind: {unit['source_kind']!r}")
        if unit.get("legacy_id") is not None and (
            not isinstance(unit["legacy_id"], str) or not _ID.fullmatch(unit["legacy_id"])
        ):
            raise CompileError("legacy_id must use canonical stable syntax")
        if unit.get("legacy_node_id") is not None and (
            not isinstance(unit["legacy_node_id"], str) or not _ID.fullmatch(unit["legacy_node_id"])
        ):
            raise CompileError("legacy_node_id must use canonical stable syntax")
        locale = unit.get("locale")
        if not isinstance(locale, str) or locale not in LOCALES:
            raise CompileError(f"unsupported locale: {locale}")
        source = unit.get("source")
        if (
            not isinstance(source, dict)
            or set(source) != {"path", "heading"}
            or not all(
                isinstance(source.get(key), str) and source[key].strip()
                for key in ("path", "heading")
            )
        ):
            raise CompileError("source path and heading are required")
        source_path = source["path"]
        if (
            PurePosixPath(source_path).as_posix() != source_path
            or PurePosixPath(source_path).is_absolute()
            or ".." in PurePosixPath(source_path).parts
            or "\\" in source_path
            or "\x00" in source_path
        ):
            raise CompileError(f"unsafe source path: {source_path!r}")
        hashes = unit.get("expected_hashes")
        if (
            not isinstance(hashes, dict)
            or set(hashes) != {"source_sha256", "excerpt_sha256"}
            or any(
                not isinstance(hashes.get(key), str)
                or not re.fullmatch(r"[0-9a-f]{64}", hashes[key])
                for key in ("source_sha256", "excerpt_sha256")
            )
        ):
            raise CompileError("expected source and excerpt hashes are required")
        references = unit.get("references")
        if not isinstance(references, list):
            raise CompileError("source unit references must be an array")
        if not isinstance(unit.get("semantic_dependencies", []), list):
            raise CompileError("semantic dependencies must be an array")
        key = (source_unit_id, locale)
        if key in unit_map:
            raise CompileError(f"duplicate source unit ID: {key}")
        path_heading_key = (locale, source["path"], source["heading"])
        if path_heading_key in path_headings:
            raise CompileError(f"duplicate source selector: {path_heading_key}")
        path_headings.add(path_heading_key)
        unit_map[key] = unit
        unit_pairs.setdefault(source_unit_id, {})[locale] = unit

    bindings = manifest.get("legacy_bindings", {"fragments": {}, "owners": {}})
    if not isinstance(bindings, dict) or set(bindings) != {"fragments", "owners"}:
        raise CompileError("legacy bindings must contain fragment and owner mappings")
    for category in ("fragments", "owners"):
        mapping = bindings[category]
        if not isinstance(mapping, dict) or any(
            not isinstance(key, str)
            or not _ID.fullmatch(key)
            or not isinstance(value, str)
            or not _ID.fullmatch(value)
            or any((value, locale) not in unit_map for locale in LOCALES)
            for key, value in mapping.items()
        ):
            raise CompileError(f"invalid legacy {category} bindings")

    def validate_link_selector(selector: Any) -> tuple[str, int]:
        if (
            not isinstance(selector, dict)
            or set(selector) != {"raw", "occurrence"}
            or not isinstance(selector.get("raw"), str)
            or not selector["raw"]
            or type(selector.get("occurrence")) is not int
            or selector["occurrence"] < 0
        ):
            raise CompileError("invalid Markdown link selector")
        return selector["raw"], selector["occurrence"]

    def validate_source_selector(selector: Any) -> tuple[str, int]:
        if (
            not isinstance(selector, dict)
            or set(selector) != {"source_unit_id", "quote", "occurrence"}
            or not isinstance(selector.get("source_unit_id"), str)
            or not _ID.fullmatch(selector["source_unit_id"])
            or not isinstance(selector.get("quote"), str)
            or not selector["quote"].strip()
            or type(selector.get("occurrence")) is not int
            or selector["occurrence"] < 0
        ):
            raise CompileError("invalid source quote selector")
        return selector["source_unit_id"], selector["occurrence"]

    for unit in source_units:
        locale = unit["locale"]
        seen_selectors: set[tuple[str, int]] = set()
        for reference in unit["references"]:
            if (
                not isinstance(reference, dict)
                or not isinstance(reference.get("class"), str)
                or reference["class"] not in REFERENCE_CLASSES
            ):
                raise CompileError(
                    f"unclassified or invalid Markdown reference in {unit['source_unit_id']}"
                )
            reference_class = reference["class"]
            expected_fields = {
                "required": {
                    "class",
                    "selector",
                    "label",
                    "destination",
                    "target_source_unit_id",
                },
                "conditional": {
                    "class",
                    "selector",
                    "label",
                    "destination",
                    "target_source_unit_id",
                    "condition_id",
                    "trigger_selector",
                },
                "navigation": {"class", "selector", "label", "destination"},
                "internal_already_included": {
                    "class",
                    "selector",
                    "label",
                    "destination",
                    "target_source_unit_id",
                    "included_in_source_unit_id",
                },
            }[reference_class]
            allowed_fields = set(expected_fields)
            if reference_class == "navigation":
                allowed_fields.add("target_source_unit_id")
            if set(reference) != expected_fields and not (
                reference_class == "navigation" and set(reference) == allowed_fields
            ):
                raise CompileError(
                    f"reference has unsupported or missing fields in {unit['source_unit_id']}"
                )
            selector_key = validate_link_selector(reference.get("selector"))
            if selector_key in seen_selectors:
                raise CompileError(f"duplicate Markdown link selector in {unit['source_unit_id']}")
            seen_selectors.add(selector_key)
            if not isinstance(reference.get("label"), str) or not isinstance(
                reference.get("destination"), str
            ):
                raise CompileError(f"unresolved Markdown link in {unit['source_unit_id']}")
            target_id = reference.get("target_source_unit_id")
            if (
                reference_class in {"required", "conditional", "internal_already_included"}
                or target_id is not None
            ):
                if not isinstance(target_id, str) or not _ID.fullmatch(target_id):
                    raise CompileError(
                        f"reference target ID is invalid in {unit['source_unit_id']}"
                    )
                if (target_id, locale) not in unit_map:
                    raise CompileError(f"missing referenced source unit: {target_id} ({locale})")
            if reference_class == "conditional":
                condition_id = reference.get("condition_id")
                if not isinstance(condition_id, str) or not _ID.fullmatch(condition_id):
                    raise CompileError(
                        f"conditional reference lacks a stable ID in {unit['source_unit_id']}"
                    )
                trigger_id, _ = validate_source_selector(reference.get("trigger_selector"))
                if (trigger_id, locale) not in unit_map:
                    raise CompileError(
                        f"missing conditional trigger source unit: {trigger_id} ({locale})"
                    )
            if reference_class == "internal_already_included":
                included_id = reference.get("included_in_source_unit_id")
                if not isinstance(included_id, str) or not _ID.fullmatch(included_id):
                    raise CompileError(
                        "internal reference lacks an included source unit "
                        f"in {unit['source_unit_id']}"
                    )
                if (included_id, locale) not in unit_map:
                    raise CompileError(f"missing included source unit: {included_id} ({locale})")

        seen_semantic: set[bytes] = set()
        for edge in unit.get("semantic_dependencies", []):
            if (
                not isinstance(edge, dict)
                or not isinstance(edge.get("class"), str)
                or edge["class"] not in {"required", "conditional"}
            ):
                raise CompileError(f"invalid semantic dependency in {unit['source_unit_id']}")
            fields = {"class", "target_source_unit_id", "provenance"}
            if edge["class"] == "conditional":
                fields |= {"condition_id", "trigger_selector"}
            if set(edge) != fields:
                raise CompileError(
                    f"semantic dependency has unsupported fields in {unit['source_unit_id']}"
                )
            target = edge["target_source_unit_id"]
            if not isinstance(target, str) or (target, locale) not in unit_map:
                raise CompileError(f"missing semantic dependency target: {target} ({locale})")
            provenance = edge["provenance"]
            if not isinstance(provenance, dict):
                raise CompileError("semantic dependency provenance is required")
            if provenance.get("kind") == "markdown_quote":
                if set(provenance) != {"kind", "selector"}:
                    raise CompileError("invalid Markdown semantic dependency provenance")
                source_id, _ = validate_source_selector(provenance["selector"])
                if source_id != unit["source_unit_id"]:
                    raise CompileError("semantic dependency quote must belong to its source unit")
            elif provenance.get("kind") == "legacy_index_dependency":
                if (
                    set(provenance)
                    != {
                        "kind",
                        "json_pointer",
                        "fragment_id",
                        "dependency_fragment_id",
                        "source_sha256",
                    }
                    or edge["class"] != "required"
                ):
                    raise CompileError("invalid legacy semantic dependency provenance")
                fragment, dependency = (
                    provenance["fragment_id"],
                    provenance["dependency_fragment_id"],
                )
                if (
                    not isinstance(fragment, str)
                    or not isinstance(dependency, str)
                    or bindings["fragments"].get(fragment) != unit["source_unit_id"]
                    or bindings["fragments"].get(dependency) != target
                    or provenance["source_sha256"] != legacy_hashes["context_index_sha256"]
                    or not isinstance(provenance["json_pointer"], str)
                    or not re.fullmatch(
                        r"/fragments/\d+/dependencies/\d+", provenance["json_pointer"]
                    )
                ):
                    raise CompileError("unbound legacy semantic dependency provenance")
            else:
                raise CompileError("unsupported semantic dependency provenance")
            if edge["class"] == "conditional":
                if not isinstance(edge["condition_id"], str) or not _ID.fullmatch(
                    edge["condition_id"]
                ):
                    raise CompileError("semantic conditional dependency lacks a stable ID")
                source_id, _ = validate_source_selector(edge["trigger_selector"])
                if source_id != unit["source_unit_id"]:
                    raise CompileError("semantic dependency trigger must belong to its source unit")
            encoded = _canonical(edge)
            if encoded in seen_semantic:
                raise CompileError("duplicate semantic dependency")
            seen_semantic.add(encoded)

    if {unit_id for unit_id, _locale in unit_map} != set(unit_pairs):
        raise CompileError("source unit locale mapping is incomplete")
    for source_unit_id, translations in unit_pairs.items():
        if set(translations) != LOCALES:
            raise CompileError(f"bilingual source unit pair is incomplete: {source_unit_id}")
        en, zh = translations["en"], translations["zh_cn"]
        if (
            en["source_kind"] != zh["source_kind"]
            or en.get("legacy_id") != zh.get("legacy_id")
            or en.get("legacy_node_id") != zh.get("legacy_node_id")
        ):
            raise CompileError(f"bilingual source unit identity mismatch: {source_unit_id}")

        def reference_shape(unit: dict[str, Any]) -> list[tuple[Any, ...]]:
            return sorted(
                (
                    reference["class"],
                    reference.get("target_source_unit_id", ""),
                    reference.get("condition_id", ""),
                    reference.get("trigger_selector", {}).get("source_unit_id", ""),
                    reference.get("trigger_selector", {}).get("occurrence", -1),
                    reference.get("included_in_source_unit_id", ""),
                )
                for reference in unit["references"]
            )

        if reference_shape(en) != reference_shape(zh):
            raise CompileError(f"bilingual source reference graph mismatch: {source_unit_id}")

        def semantic_shape(unit: dict[str, Any]) -> list[tuple[Any, ...]]:
            return sorted(
                (
                    edge["class"],
                    edge["target_source_unit_id"],
                    edge.get("condition_id", ""),
                    edge.get("trigger_selector", {}).get("occurrence", -1),
                    edge["provenance"]["kind"],
                    edge["provenance"].get("json_pointer", ""),
                    edge["provenance"].get("fragment_id", ""),
                    edge["provenance"].get("dependency_fragment_id", ""),
                    edge["provenance"].get("selector", {}).get("occurrence", -1),
                )
                for edge in unit.get("semantic_dependencies", [])
            )

        if semantic_shape(en) != semantic_shape(zh):
            raise CompileError(f"bilingual semantic dependency mismatch: {source_unit_id}")

    entry_fields = {
        "tool_id",
        "node_id",
        "stage_id",
        "locale",
        "source_unit_ids",
        "actions",
        "branches",
    }
    runtime_entry_map: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    entry_pairs: dict[tuple[str, str, str], dict[str, dict[str, Any]]] = {}
    for entry in runtime_entries:
        if not isinstance(entry, dict) or set(entry) != entry_fields:
            raise CompileError("runtime entry has unsupported or missing fields")
        for field in ("tool_id", "node_id", "stage_id"):
            if not isinstance(entry.get(field), str) or not _ID.fullmatch(entry[field]):
                raise CompileError(f"runtime entry {field} must use canonical stable syntax")
        locale = entry.get("locale")
        if not isinstance(locale, str) or locale not in LOCALES:
            raise CompileError(f"unsupported locale: {locale}")
        key = (entry["tool_id"], entry["node_id"], entry["stage_id"], locale)
        if key in runtime_entry_map:
            raise CompileError(f"duplicate runtime entry ID: {key}")
        source_unit_ids = entry.get("source_unit_ids")
        if (
            not isinstance(source_unit_ids, list)
            or not source_unit_ids
            or any(
                not isinstance(unit_id, str) or not _ID.fullmatch(unit_id)
                for unit_id in source_unit_ids
            )
            or len(set(source_unit_ids)) != len(source_unit_ids)
        ):
            raise CompileError(f"runtime entry has invalid source_unit_ids: {key}")
        if any((unit_id, locale) not in unit_map for unit_id in source_unit_ids):
            raise CompileError(f"runtime entry references a missing source unit: {key}")
        actions = entry.get("actions")
        if not isinstance(actions, list) or not actions:
            raise CompileError(f"runtime entry has no source-backed actions: {key}")
        selectors: list[dict[str, Any]] = list(actions)
        for selector in selectors:
            source_unit_id, _occurrence = validate_source_selector(selector)
            if (source_unit_id, locale) not in unit_map:
                raise CompileError(f"runtime action selector has no source unit: {key}")
        branches = entry.get("branches")
        if not isinstance(branches, list) or not branches:
            raise CompileError(f"runtime entry must define at least one sourced branch: {key}")
        branch_ids: set[str] = set()
        for branch in branches:
            branch_fields = {"id", "trigger", "actions", "pass", "failure"}
            if (
                not isinstance(branch, dict)
                or not branch_fields <= set(branch)
                or set(branch) - branch_fields - {"legacy_branch"}
            ):
                raise CompileError(f"runtime entry has an incomplete branch: {key}")
            if "legacy_branch" in branch and (
                not isinstance(branch["legacy_branch"], str)
                or not branch["legacy_branch"].strip()
                or branch["legacy_branch"] != branch["legacy_branch"].strip()
            ):
                raise CompileError(f"runtime entry has an invalid legacy branch binding: {key}")
            branch_id = branch.get("id")
            if (
                not isinstance(branch_id, str)
                or not _ID.fullmatch(branch_id)
                or branch_id in branch_ids
            ):
                raise CompileError(f"runtime entry has an invalid or duplicate branch ID: {key}")
            branch_ids.add(branch_id)
            for field in ("trigger", "actions", "pass", "failure"):
                source_unit_id, _occurrence = validate_source_selector(branch[field])
                if (source_unit_id, locale) not in unit_map:
                    raise CompileError(f"runtime branch selector has no source unit: {key}")
        runtime_entry_map[key] = entry
        entry_pairs.setdefault((entry["tool_id"], entry["node_id"], entry["stage_id"]), {})[
            locale
        ] = entry

    def selector_shape(selector: dict[str, Any]) -> tuple[str, int]:
        return selector["source_unit_id"], selector["occurrence"]

    for stable_id, translations in entry_pairs.items():
        if set(translations) != LOCALES:
            raise CompileError(f"bilingual runtime entry pair is incomplete: {stable_id}")
        en, zh = translations["en"], translations["zh_cn"]
        if sorted(en["source_unit_ids"]) != sorted(zh["source_unit_ids"]):
            raise CompileError(f"bilingual runtime entry source mapping mismatch: {stable_id}")
        if [selector_shape(item) for item in en["actions"]] != [
            selector_shape(item) for item in zh["actions"]
        ]:
            raise CompileError(f"bilingual runtime action selector mismatch: {stable_id}")
        en_branches = [
            (
                branch["id"],
                branch.get("legacy_branch"),
                *(
                    selector_shape(branch[field])
                    for field in ("trigger", "actions", "pass", "failure")
                ),
            )
            for branch in en["branches"]
        ]
        zh_branches = [
            (
                branch["id"],
                branch.get("legacy_branch"),
                *(
                    selector_shape(branch[field])
                    for field in ("trigger", "actions", "pass", "failure")
                ),
            )
            for branch in zh["branches"]
        ]
        if en_branches != zh_branches:
            raise CompileError(f"bilingual runtime branch selector mismatch: {stable_id}")

    owner_view_map: dict[tuple[str, str], dict[str, Any]] = {}
    owner_views = manifest.get("owner_views", [])
    if not isinstance(owner_views, list) or len(owner_views) > MAX_SOURCE_UNITS:
        raise CompileError("owner_views must be a bounded array")
    for view in owner_views:
        if not isinstance(view, dict) or set(view) != {
            "legacy_owner_id",
            "locale",
            "source_unit_ids",
        }:
            raise CompileError("owner view has unsupported or missing fields")
        owner_id, locale, roots = view["legacy_owner_id"], view["locale"], view["source_unit_ids"]
        if not isinstance(owner_id, str) or owner_id not in bindings["owners"]:
            raise CompileError("owner view has an unknown legacy owner binding")
        if not isinstance(locale, str) or locale not in LOCALES:
            raise CompileError("owner view has an invalid locale")
        if (
            not isinstance(roots, list)
            or not roots
            or any(
                not isinstance(source_id, str) or (source_id, locale) not in unit_map
                for source_id in roots
            )
            or len(roots) != len(set(roots))
            or bindings["owners"][owner_id] not in roots
        ):
            raise CompileError("owner view has invalid or missing bound source roots")
        key = (owner_id, locale)
        if key in owner_view_map:
            raise CompileError(f"duplicate owner view: {key}")
        owner_view_map[key] = view
    for owner_id, _locale in owner_view_map:
        if any((owner_id, locale) not in owner_view_map for locale in LOCALES):
            raise CompileError(f"bilingual owner view pair is incomplete: {owner_id}")
        if sorted(owner_view_map[(owner_id, "en")]["source_unit_ids"]) != sorted(
            owner_view_map[(owner_id, "zh_cn")]["source_unit_ids"]
        ):
            raise CompileError(f"bilingual owner view roots mismatch: {owner_id}")

    return {
        "budgets": budgets,
        "source_units": source_units,
        "source_unit_map": unit_map,
        "runtime_entries": runtime_entries,
        "runtime_entry_map": runtime_entry_map,
        "legacy_source_hashes": legacy_hashes,
        "legacy_bindings": bindings,
        "owner_view_map": owner_view_map,
    }


def compile_manifest(root: Path, manifest: Mapping[str, Any]) -> dict[str, Any]:
    """Compile the full source-unit graph and source-backed runtime entries."""
    checked = validate_manifest(dict(manifest))
    source_root = root.resolve(strict=True)
    legacy_provenance = []
    legacy_index: Any = None
    for relative, key, version_field, expected_version in (
        ("mcp/rule-registry.json", "registry_sha256", "contract_version", POLICY_CONTRACT_VERSION),
        (
            "mcp/rule-context-index.json",
            "context_index_sha256",
            "schema_version",
            LEGACY_CONTEXT_INDEX_VERSION,
        ),
    ):
        source = _source_path(source_root, relative)
        raw = source.read_bytes()
        parsed = load_json_strict(source)
        if (
            not isinstance(parsed, dict)
            or type(parsed.get(version_field)) is not int
            or parsed[version_field] != expected_version
        ):
            raise CompileError(f"unsupported legacy source version: {relative}")
        source_hash = _sha(raw)
        if source_hash != checked["legacy_source_hashes"][key]:
            raise CompileError(f"stale legacy source hash: {relative}")
        legacy_provenance.append(
            {"path": relative, "version": expected_version, "source_sha256": source_hash}
        )
        if key == "context_index_sha256":
            legacy_index = parsed
    if "owner_paths_sha256" in checked["legacy_source_hashes"]:
        owner_relative = (
            "mcp/packages/token_io_decoupling_core/src/token_io_decoupling_core/owner_paths.py"
        )
        owner_hash = _sha(_source_path(source_root, owner_relative).read_bytes())
        if owner_hash != checked["legacy_source_hashes"]["owner_paths_sha256"]:
            raise CompileError("stale legacy source hash: owner_paths.py")
        legacy_provenance.append({"path": owner_relative, "source_sha256": owner_hash})

    def resolve_quote(selector: Mapping[str, Any], locale: str) -> dict[str, Any]:
        source_unit_id = selector["source_unit_id"]
        key = (source_unit_id, locale)
        unit = source_unit_payloads.get(key)
        if unit is None:
            raise CompileError(
                f"source quote references a missing unit: {source_unit_id} ({locale})"
            )
        quote = selector["quote"]
        positions: list[int] = []
        cursor = 0
        while True:
            position = unit["excerpt"].find(quote, cursor)
            if position < 0:
                break
            positions.append(position)
            cursor = position + 1
        occurrence = selector["occurrence"]
        if occurrence >= len(positions):
            raise CompileError(
                f"source quote selector did not match: {source_unit_id} occurrence={occurrence}"
            )
        return {
            "source_unit_id": source_unit_id,
            "quote": quote,
            "occurrence": occurrence,
            "text": quote,
        }

    source_unit_payloads: dict[tuple[str, str], dict[str, Any]] = {}
    actual_source_selectors: set[tuple[str, int, int, str]] = set()
    source_units = sorted(
        checked["source_units"], key=lambda unit: (unit["source_unit_id"], unit["locale"])
    )
    for unit in source_units:
        source = unit["source"]
        path = _source_path(source_root, source["path"])
        info = path.stat()
        actual_selector = (unit["locale"], info.st_dev, info.st_ino, source["heading"])
        if actual_selector in actual_source_selectors:
            raise CompileError(f"duplicate actual source selector: {source}")
        actual_source_selectors.add(actual_selector)
        raw = path.read_bytes()
        try:
            text = raw.decode("utf-8")
            excerpt = extract_heading(text, source["heading"]).strip()
        except (UnicodeDecodeError, ValueError) as exc:
            raise CompileError(f"source heading unavailable: {source}") from exc
        if not excerpt:
            raise CompileError(f"empty source excerpt: {source}")
        source_hash, excerpt_hash = _sha(raw), _sha(excerpt.encode("utf-8"))
        expected = unit["expected_hashes"]
        if expected["source_sha256"] != source_hash or expected["excerpt_sha256"] != excerpt_hash:
            raise CompileError(f"stale source hashes: {source}")

        observed_links = extract_markdown_links(excerpt)
        if any(link.destination is None for link in observed_links):
            raise CompileError(f"unresolved Markdown link in source unit: {unit['source_unit_id']}")
        references_by_selector = {
            (reference["selector"]["raw"], reference["selector"]["occurrence"]): reference
            for reference in unit["references"]
        }
        observed_by_selector = {(link.raw, link.occurrence): link for link in observed_links}
        if set(references_by_selector) != set(observed_by_selector):
            raise CompileError(
                f"Markdown reference coverage mismatch in source unit: {unit['source_unit_id']}"
            )
        ordered_references = []
        for link in observed_links:
            selector_key = (link.raw, link.occurrence)
            reference = references_by_selector[selector_key]
            if reference["label"] != link.label or reference["destination"] != link.destination:
                raise CompileError(
                    f"Markdown link selector changed in source unit: {unit['source_unit_id']}"
                )
            rendered_reference = dict(reference)
            ordered_references.append(rendered_reference)

        payload = {
            "source_unit_id": unit["source_unit_id"],
            "source_kind": unit["source_kind"],
            "locale": unit["locale"],
            "source": dict(source),
            "source_sha256": source_hash,
            "excerpt_sha256": excerpt_hash,
            "excerpt": excerpt,
            "references": ordered_references,
            "semantic_dependencies": copy.deepcopy(unit.get("semantic_dependencies", [])),
        }
        if "legacy_id" in unit:
            payload["legacy_id"] = unit["legacy_id"]
        if "legacy_node_id" in unit:
            payload["legacy_node_id"] = unit["legacy_node_id"]
        source_unit_payloads[(unit["source_unit_id"], unit["locale"])] = payload

    # Resolve links and sourced condition triggers only after every unit has
    # been loaded, so self-references and forward selectors are order-independent.
    for key, unit in source_unit_payloads.items():
        locale = key[1]
        for reference in unit["references"]:
            target = _local_reference_target(
                source_root, unit["source"]["path"], reference["destination"]
            )
            target_id = reference.get("target_source_unit_id")
            if target_id is not None:
                target_unit = source_unit_payloads.get((target_id, locale))
                if (
                    target is None
                    or target_unit is None
                    or not _reference_target_matches_unit(source_root, target, target_unit)
                ):
                    raise CompileError(
                        f"Markdown destination does not match target source unit: "
                        f"{unit['source_unit_id']} -> {target_id}"
                    )
            if reference["class"] == "conditional":
                reference["trigger_text"] = resolve_quote(reference["trigger_selector"], locale)
            if (
                reference["class"] in {"required", "conditional"}
                and (
                    reference["target_source_unit_id"],
                    locale,
                )
                not in source_unit_payloads
            ):
                raise CompileError(
                    f"missing execution dependency: {unit['source_unit_id']} -> "
                    f"{reference['target_source_unit_id']}"
                )
            if reference["class"] == "internal_already_included":
                for source_unit_id in (
                    reference["target_source_unit_id"],
                    reference["included_in_source_unit_id"],
                ):
                    if (source_unit_id, locale) not in source_unit_payloads:
                        raise CompileError(
                            f"unbound internal source reference: {unit['source_unit_id']} -> "
                            f"{source_unit_id}"
                        )
        for edge in unit["semantic_dependencies"]:
            provenance = edge["provenance"]
            if provenance["kind"] == "markdown_quote":
                provenance["resolved_quote"] = resolve_quote(provenance["selector"], locale)
            else:
                parts = provenance["json_pointer"].split("/")
                try:
                    fragment_index, dependency_index = int(parts[2]), int(parts[4])
                    if str(fragment_index) != parts[2] or str(dependency_index) != parts[4]:
                        raise ValueError("noncanonical JSON pointer")
                    fragment = legacy_index["fragments"][fragment_index]
                    dependency = fragment["dependencies"][dependency_index]
                    if (
                        fragment["fragment_id"] != provenance["fragment_id"]
                        or dependency != provenance["dependency_fragment_id"]
                    ):
                        raise ValueError("JSON pointer does not identify the declared dependency")
                except (IndexError, KeyError, TypeError, ValueError) as exc:
                    raise CompileError(
                        "legacy semantic dependency JSON pointer is invalid"
                    ) from exc
            if edge["class"] == "conditional":
                edge["trigger_text"] = resolve_quote(edge["trigger_selector"], locale)
        unit["source_unit_sha256"] = _sha(_canonical(unit))

    visiting: set[tuple[str, str]] = set()
    visited: set[tuple[str, str]] = set()

    def visit(key: tuple[str, str]) -> None:
        if key in visiting:
            raise CompileError(f"execution source-unit cycle at {key[0]}")
        if key in visited:
            return
        visiting.add(key)
        for reference in (
            source_unit_payloads[key]["references"]
            + source_unit_payloads[key]["semantic_dependencies"]
        ):
            if reference["class"] in {"required", "conditional"}:
                visit((reference["target_source_unit_id"], key[1]))
        visiting.remove(key)
        visited.add(key)

    for key in source_unit_payloads:
        visit(key)

    def source_key(selector: Mapping[str, Any], locale: str) -> tuple[str, str]:
        return selector["source_unit_id"], locale

    def collect(source_unit_id: str, locale: str, closure_ids: set[tuple[str, str]]) -> None:
        source_key_value = (source_unit_id, locale)
        if source_key_value in closure_ids:
            return
        closure_ids.add(source_key_value)
        for reference in (
            source_unit_payloads[source_key_value]["references"]
            + source_unit_payloads[source_key_value]["semantic_dependencies"]
        ):
            if reference["class"] in {"required", "conditional"}:
                collect(reference["target_source_unit_id"], locale, closure_ids)

    def validate_closure(closure_ids: set[tuple[str, str]], locale: str, label: str) -> None:
        for source_unit_id in closure_ids:
            for reference in source_unit_payloads[source_unit_id]["references"]:
                if reference["class"] == "conditional":
                    trigger = reference["trigger_selector"]
                    if source_key(trigger, locale) not in closure_ids:
                        raise CompileError(
                            f"conditional trigger source is outside the entry closure: "
                            f"{label} -> {trigger['source_unit_id']}"
                        )
                    resolve_quote(trigger, locale)
                elif reference["class"] == "internal_already_included":
                    target = (reference["target_source_unit_id"], locale)
                    included_in = (reference["included_in_source_unit_id"], locale)
                    if target not in closure_ids or included_in not in closure_ids:
                        raise CompileError(
                            f"internal back-reference is not already in the final entry closure: "
                            f"{label} -> {reference['target_source_unit_id']}"
                        )

    entry_closures: dict[tuple[str, str, str, str], set[tuple[str, str]]] = {}
    for key, entry in checked["runtime_entry_map"].items():
        locale = entry["locale"]
        closure_ids: set[tuple[str, str]] = set()

        for source_unit_id in entry["source_unit_ids"]:
            collect(source_unit_id, locale, closure_ids)

        selectors = list(entry["actions"])
        for branch in entry["branches"]:
            selectors.extend(branch[field] for field in ("trigger", "actions", "pass", "failure"))
        for selector in selectors:
            if source_key(selector, locale) not in closure_ids:
                raise CompileError(
                    f"runtime policy selector source is outside the entry closure: "
                    f"{entry['stage_id']} -> {selector['source_unit_id']}"
                )

        validate_closure(closure_ids, locale, entry["stage_id"])
        entry_closures[key] = closure_ids

    owner_closures: dict[tuple[str, str], set[tuple[str, str]]] = {}
    for key, view in checked["owner_view_map"].items():
        closure_ids = set()
        for source_unit_id in view["source_unit_ids"]:
            collect(source_unit_id, view["locale"], closure_ids)
        validate_closure(closure_ids, view["locale"], view["legacy_owner_id"])
        owner_closures[key] = closure_ids

    all_reachable_units = set().union(*entry_closures.values(), *owner_closures.values())
    if all_reachable_units != set(source_unit_payloads):
        unreferenced = sorted(set(source_unit_payloads) - all_reachable_units)
        raise CompileError(
            f"source units are not included by any runtime entry or owner view: "
            f"{[unit_id for unit_id, _locale in unreferenced]}"
        )

    def render_selector(selector: Mapping[str, Any], locale: str) -> dict[str, Any]:
        return resolve_quote(selector, locale)

    compiled_entries: list[dict[str, Any]] = []
    closure_limit = checked["budgets"].get("entry_closure_unicode_chars", MAX_ENTRY_CHARS)
    for key in sorted(checked["runtime_entry_map"]):
        entry = checked["runtime_entry_map"][key]
        locale = entry["locale"]
        closure_ids = entry_closures[key]
        ordered_closure = sorted(closure_ids)
        closed_units = [source_unit_payloads[source_key] for source_key in ordered_closure]
        source_provenance = [
            {
                "source_unit_id": unit["source_unit_id"],
                "source_kind": unit["source_kind"],
                "source": unit["source"],
                "source_sha256": unit["source_sha256"],
                "excerpt_sha256": unit["excerpt_sha256"],
                "source_unit_sha256": unit["source_unit_sha256"],
            }
            for unit in closed_units
        ]
        instructions = {
            "actions": [render_selector(selector, locale) for selector in entry["actions"]],
            "branches": [
                {
                    "id": branch["id"],
                    **(
                        {"legacy_branch": branch["legacy_branch"]}
                        if "legacy_branch" in branch
                        else {}
                    ),
                    "trigger": render_selector(branch["trigger"], locale),
                    "actions": render_selector(branch["actions"], locale),
                    "pass": render_selector(branch["pass"], locale),
                    "failure": render_selector(branch["failure"], locale),
                }
                for branch in entry["branches"]
            ],
        }
        closure_sha256 = _sha(_canonical(closed_units))
        entry_content = {
            "format": FORMAT,
            "compiler_version": COMPILER_VERSION,
            "manifest_format": MANIFEST_FORMAT,
            "policy_contract_version": POLICY_CONTRACT_VERSION,
            "legacy_context_index_version": LEGACY_CONTEXT_INDEX_VERSION,
            "legacy_source_hashes": dict(checked["legacy_source_hashes"]),
            "legacy_bindings": {
                category: {
                    legacy_id: source_id
                    for legacy_id, source_id in checked["legacy_bindings"][category].items()
                    if (source_id, locale) in closure_ids
                }
                for category in ("fragments", "owners")
            },
            "tool_id": entry["tool_id"],
            "node_id": entry["node_id"],
            "stage_id": entry["stage_id"],
            "locale": locale,
            "source_unit_ids": sorted(entry["source_unit_ids"]),
            "closure_source_unit_ids": [source_unit_id for source_unit_id, _ in ordered_closure],
            "source_provenance": source_provenance,
            "instructions": instructions,
            "closure_sha256": closure_sha256,
        }
        size = len(
            _canonical({"entry": entry_content, "source_units": closed_units}).decode("utf-8")
        )
        if size > closure_limit:
            raise CompileError(
                f"entry closure budget exceeded: required={size} allowed={closure_limit}"
            )
        entry_content["content_sha256"] = _sha(_canonical(entry_content))
        compiled_entries.append(entry_content)

    compiled_owner_views: list[dict[str, Any]] = []
    for key in sorted(checked["owner_view_map"]):
        view = checked["owner_view_map"][key]
        locale = view["locale"]
        closure_ids = owner_closures[key]
        ordered_closure = sorted(closure_ids)
        closed_units = [source_unit_payloads[source_key] for source_key in ordered_closure]
        owner_content = {
            "format": FORMAT,
            "compiler_version": COMPILER_VERSION,
            "manifest_format": MANIFEST_FORMAT,
            "policy_contract_version": POLICY_CONTRACT_VERSION,
            "legacy_context_index_version": LEGACY_CONTEXT_INDEX_VERSION,
            "legacy_source_hashes": dict(checked["legacy_source_hashes"]),
            "legacy_owner_id": view["legacy_owner_id"],
            "locale": locale,
            "source_unit_ids": sorted(view["source_unit_ids"]),
            "closure_source_unit_ids": [source_unit_id for source_unit_id, _ in ordered_closure],
            "source_provenance": [
                {
                    "source_unit_id": unit["source_unit_id"],
                    "source_kind": unit["source_kind"],
                    "source": unit["source"],
                    "source_sha256": unit["source_sha256"],
                    "excerpt_sha256": unit["excerpt_sha256"],
                    "source_unit_sha256": unit["source_unit_sha256"],
                }
                for unit in closed_units
            ],
            "legacy_bindings": {
                category: {
                    legacy_id: source_id
                    for legacy_id, source_id in checked["legacy_bindings"][category].items()
                    if (source_id, locale) in closure_ids
                }
                for category in ("fragments", "owners")
            },
            "closure_sha256": _sha(_canonical(closed_units)),
        }
        size = len(
            _canonical({"owner_view": owner_content, "source_units": closed_units}).decode("utf-8")
        )
        if size > closure_limit:
            raise CompileError(
                f"owner view closure budget exceeded: required={size} allowed={closure_limit}"
            )
        owner_content["content_sha256"] = _sha(_canonical(owner_content))
        compiled_owner_views.append(owner_content)

    artifact: dict[str, Any] = {
        "format": FORMAT,
        "compiler_version": COMPILER_VERSION,
        "policy_contract_version": POLICY_CONTRACT_VERSION,
        "legacy_context_index_version": LEGACY_CONTEXT_INDEX_VERSION,
        "legacy_source_provenance": legacy_provenance,
        "legacy_bindings": checked["legacy_bindings"],
        "manifest_format": MANIFEST_FORMAT,
        "complete": True,
        "source_units": [source_unit_payloads[key] for key in sorted(source_unit_payloads)],
        "runtime_entries": compiled_entries,
        "owner_views": compiled_owner_views,
    }
    artifact["canonical_sha256"] = _sha(_canonical(artifact))
    serialized = _canonical(artifact)
    allowed_bytes = checked["budgets"].get("artifact_bytes", MAX_ARTIFACT_BYTES)
    serialized_size = len(serialized) + 1
    if serialized_size > allowed_bytes:
        raise CompileError(
            f"artifact budget exceeded: required={serialized_size} allowed={allowed_bytes}"
        )
    if len(source_unit_payloads) > checked["budgets"].get("source_unit_records", MAX_SOURCE_UNITS):
        raise CompileError(
            "source unit record budget exceeded: "
            f"required={len(source_unit_payloads)} "
            f"allowed={checked['budgets']['source_unit_records']}"
        )
    return artifact


def write_fixed_output(
    root: Path,
    artifact: Mapping[str, Any],
    *,
    expected_baseline_sha256: str | None = None,
    expected_root_identity: tuple[int, int] | None = None,
) -> Path:
    """Publish a verified artifact through pinned directory descriptors.

    No baseline permits only creation or a byte-identical no-op. A supplied
    baseline must match even for a no-op; it never permits creating a missing
    target. The temporary file serializes cooperating compiler writers.
    """
    if expected_baseline_sha256 is not None and (
        not isinstance(expected_baseline_sha256, str)
        or not re.fullmatch(r"[0-9a-f]{64}", expected_baseline_sha256)
    ):
        raise CompileError("invalid fixed output baseline")

    def digest(value: Any) -> str:
        if not isinstance(value, dict) or (
            value.get("format") != FORMAT
            or type(value.get("compiler_version")) is not int
            or value["compiler_version"] != COMPILER_VERSION
            or value.get("manifest_format") != MANIFEST_FORMAT
            or value.get("complete") is not True
            or type(value.get("policy_contract_version")) is not int
            or value["policy_contract_version"] != POLICY_CONTRACT_VERSION
            or type(value.get("legacy_context_index_version")) is not int
            or value["legacy_context_index_version"] != LEGACY_CONTEXT_INDEX_VERSION
            or not isinstance(value.get("source_units"), list)
            or not value["source_units"]
            or not isinstance(value.get("runtime_entries"), list)
            or not value["runtime_entries"]
            or not isinstance(value.get("owner_views"), list)
        ):
            raise CompileError("fixed output artifact format is invalid")
        body = dict(value)
        claimed = body.pop("canonical_sha256", None)
        if not isinstance(claimed, str) or claimed != _sha(_canonical(body)):
            raise CompileError("fixed output artifact integrity check failed")
        units: dict[tuple[str, str], dict[str, Any]] = {}
        for unit in value["source_units"]:
            if not isinstance(unit, dict):
                raise CompileError("fixed output source unit is invalid")
            unit_body = dict(unit)
            unit_hash = unit_body.pop("source_unit_sha256", None)
            unit_id, locale = unit.get("source_unit_id"), unit.get("locale")
            if (
                not isinstance(unit_id, str)
                or not isinstance(locale, str)
                or (unit_id, locale) in units
                or unit_hash != _sha(_canonical(unit_body))
            ):
                raise CompileError("fixed output source unit integrity check failed")
            units[(unit_id, locale)] = unit
        for item in [*value["runtime_entries"], *value["owner_views"]]:
            if not isinstance(item, dict):
                raise CompileError("fixed output closure is invalid")
            item_body = dict(item)
            item_hash = item_body.pop("content_sha256", None)
            locale, source_ids = item.get("locale"), item.get("closure_source_unit_ids")
            if (
                not isinstance(locale, str)
                or not isinstance(source_ids, list)
                or not source_ids
                or any(not isinstance(source_id, str) for source_id in source_ids)
                or len(set(source_ids)) != len(source_ids)
                or any((source_id, locale) not in units for source_id in source_ids)
                or item_hash != _sha(_canonical(item_body))
            ):
                raise CompileError("fixed output closure integrity check failed")
            closure = [units[(source_id, locale)] for source_id in source_ids]
            if item.get("closure_sha256") != _sha(_canonical(closure)):
                raise CompileError("fixed output transitive closure integrity check failed")
        return claimed

    candidate = dict(artifact)
    digest(candidate)
    data = _canonical(candidate) + b"\n"
    if len(data) > MAX_ARTIFACT_BYTES:
        raise CompileError("fixed output artifact budget exceeded")
    output = fixed_output_path(root)
    root_path = root.resolve(strict=True)
    required_flags = ("O_DIRECTORY", "O_NOFOLLOW", "O_NONBLOCK")
    if any(not hasattr(os, flag) for flag in required_flags):
        raise CompileError("safe fixed output publication is unavailable")
    directory_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    with ExitStack() as stack:
        try:
            directory = os.open(root_path, directory_flags)
            stack.callback(os.close, directory)
            root_info = os.fstat(directory)
            if (
                expected_root_identity is not None
                and (root_info.st_dev, root_info.st_ino) != expected_root_identity
            ):
                raise CompileError("pinned project root identity changed")
            for part in ("mcp-project-dev", "generated"):
                try:
                    child = os.open(part, directory_flags, dir_fd=directory)
                except FileNotFoundError:
                    os.mkdir(part, mode=0o755, dir_fd=directory)
                    child = os.open(part, directory_flags, dir_fd=directory)
                stack.callback(os.close, child)
                directory = child
        except OSError as exc:
            raise CompileError("fixed output directory is unsafe or unavailable") from exc

        def observe() -> tuple[bytes, tuple[int, int, int, int]] | None:
            try:
                fd = os.open(
                    output.name,
                    os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                    dir_fd=directory,
                )
            except FileNotFoundError:
                return None
            except OSError as exc:
                raise CompileError("fixed output is unsafe or unavailable") from exc
            try:
                before = os.fstat(fd)
                if not stat.S_ISREG(before.st_mode) or before.st_size > MAX_ARTIFACT_BYTES:
                    raise CompileError("fixed output must be a bounded regular file")
                chunks = []
                remaining = MAX_ARTIFACT_BYTES + 1
                while remaining:
                    chunk = os.read(fd, min(remaining, 65536))
                    if not chunk:
                        break
                    chunks.append(chunk)
                    remaining -= len(chunk)
                raw = b"".join(chunks)
                after = os.fstat(fd)
            except OSError as exc:
                raise CompileError("fixed output read failed") from exc
            finally:
                os.close(fd)

            def identity(value: os.stat_result) -> tuple[int, int, int, int]:
                return value.st_dev, value.st_ino, value.st_mtime_ns, value.st_size

            if len(raw) > MAX_ARTIFACT_BYTES or identity(before) != identity(after):
                raise CompileError("fixed output changed during read")
            return raw, identity(after)

        observed = observe()
        if observed is None:
            if expected_baseline_sha256 is not None:
                raise CompileError("fixed output baseline conflict: expected target is missing")
        else:
            try:
                existing = json.loads(
                    observed[0].decode("utf-8"),
                    object_pairs_hook=_reject_duplicate_pairs,
                    parse_constant=_reject_json_constant,
                )
            except (UnicodeError, json.JSONDecodeError) as exc:
                raise CompileError("fixed output baseline is unreadable") from exc
            existing_hash = digest(existing)
            if expected_baseline_sha256 is not None and existing_hash != expected_baseline_sha256:
                raise CompileError("fixed output baseline conflict")
            if observed[0] == data:
                return output
            if expected_baseline_sha256 is None:
                raise CompileError("fixed output baseline conflict")

        temporary = output.name + ".tmp"
        created = False
        temporary_identity: tuple[int, int] | None = None
        try:
            fd = os.open(
                temporary,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                0o600,
                dir_fd=directory,
            )
            created = True
            info = os.fstat(fd)
            temporary_identity = (info.st_dev, info.st_ino)
            with os.fdopen(fd, "wb") as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            if observe() != observed:
                raise CompileError("fixed output changed before publication")
            if observed is None:
                os.link(
                    temporary,
                    output.name,
                    src_dir_fd=directory,
                    dst_dir_fd=directory,
                    follow_symlinks=False,
                )
            else:
                os.replace(temporary, output.name, src_dir_fd=directory, dst_dir_fd=directory)
                created = False
            return output
        except OSError as exc:
            raise CompileError("fixed output publication failed") from exc
        finally:
            if created:
                try:
                    info = os.stat(temporary, dir_fd=directory, follow_symlinks=False)
                    if (info.st_dev, info.st_ino) != temporary_identity:
                        raise CompileError("temporary output ownership changed")
                    os.unlink(temporary, dir_fd=directory)
                except FileNotFoundError:
                    pass
                except OSError as exc:
                    raise CompileError("temporary output cleanup failed") from exc
