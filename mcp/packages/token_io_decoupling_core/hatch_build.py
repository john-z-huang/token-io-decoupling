"""Generate packaged rule excerpts from canonical Markdown owners at build time."""

from __future__ import annotations

import json
import re
import sys
import tempfile
from pathlib import Path, PurePosixPath
from typing import Any

from hatchling.builders.hooks.plugin.interface import BuildHookInterface


class RuleResourcesBuildHook(BuildHookInterface):
    """Generate bounded bilingual resources for wheels; carry sources in sdists."""

    def initialize(self, version: str, build_data: dict[str, Any]) -> None:
        project_root = Path(self.root).resolve()
        sdist_sources = project_root / "rule_sources"
        sdist_registry = sdist_sources / "mcp" / "rule-registry.json"
        checkout_root = project_root.parents[2]
        if sdist_sources.is_dir() and sdist_registry.is_file():
            registry_source = sdist_registry
            source_root = sdist_sources
        else:
            registry_source = checkout_root / "mcp" / "rule-registry.json"
            if (
                not (checkout_root / "references").is_dir()
                or not (checkout_root / "SKILL.md").is_file()
                or not registry_source.is_file()
            ):
                raise RuntimeError("project root is not a verified Skill checkout")
            source_root = checkout_root
        registry = json.loads(registry_source.read_text(encoding="utf-8"))
        sys.path.insert(0, str(project_root / "src"))
        try:
            from token_io_decoupling_core.registry_contract import validate_supported_registry_shape

            validate_supported_registry_shape(registry)
        except (ImportError, ValueError) as exc:
            raise RuntimeError(f"unsupported or malformed rule registry contract: {exc}") from exc
        finally:
            sys.path.pop(0)

        self._temporary = tempfile.TemporaryDirectory(prefix="token-io-rule-build-")
        staging_root = Path(self._temporary.name)
        force_include = build_data.setdefault("force_include", {})
        source_files: set[Path] = {registry_source.resolve()}

        for node in registry["nodes"]:
            node_id = node.get("node_id")
            if not isinstance(node_id, str) or not node_id:
                raise RuntimeError("registry nodes must have a non-empty node_id")
            owner_pairs = {
                "en": (node.get("owner_path"), node.get("owner_section")),
                "zh_cn": (
                    node.get("owner_mirrors", {}).get("zh_cn", {}).get("path"),
                    node.get("owner_mirrors", {}).get("zh_cn", {}).get("section"),
                ),
            }
            packaged_paths: dict[str, str] = {}
            for language, (relative_path, heading) in owner_pairs.items():
                source = _safe_source(source_root, relative_path)
                excerpt = _extract_heading(
                    source.read_text(encoding="utf-8"), heading, relative_path
                )
                resource_name = f"rules/{node_id}.{language}.md"
                staged = staging_root / resource_name
                staged.parent.mkdir(parents=True, exist_ok=True)
                staged.write_text(excerpt + "\n", encoding="utf-8")
                packaged_paths[language] = resource_name
                source_files.add(source)
                if self.target_name == "wheel":
                    force_include[str(staged)] = (
                        f"token_io_decoupling_core/_resources/{resource_name}"
                    )
            node["resource_paths"] = packaged_paths

        for owner in (
            "child-role-selection",
            "task-assignment",
            "output-token-routing",
            "session-role-ownership",
            "decision-context-generation",
        ):
            for language, suffix, heading in (
                ("en", "", "General rules"),
                ("zh_cn", "_zh_cn", "通用规范"),
            ):
                relative = f"references/coding/layer-01-fundamental-concepts/{owner}{suffix}.md"
                source = _safe_source(source_root, relative)
                excerpt = _extract_heading(source.read_text(encoding="utf-8"), heading, relative)
                staged = staging_root / "rules" / f"{owner}.{language}.md"
                staged.parent.mkdir(parents=True, exist_ok=True)
                staged.write_text(excerpt + "\n", encoding="utf-8")
                source_files.add(source)
                if self.target_name == "wheel":
                    force_include[str(staged)] = (
                        f"token_io_decoupling_core/_resources/rules/{owner}.{language}.md"
                    )

        if self.target_name == "wheel":
            staged_registry = staging_root / "registry.json"
            staged_registry.write_text(
                json.dumps(registry, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
            force_include[str(staged_registry)] = (
                "token_io_decoupling_core/_resources/registry.json"
            )
        elif self.target_name == "sdist":
            for source in source_files:
                relative = source.relative_to(source_root.resolve())
                force_include[str(source)] = (PurePosixPath("rule_sources") / relative).as_posix()

    def finalize(
        self,
        version: str,
        build_data: dict[str, Any],
        artifact_path: str,
    ) -> None:
        del version, build_data, artifact_path
        if hasattr(self, "_temporary"):
            self._temporary.cleanup()


def _safe_source(source_root: Path, relative_path: Any) -> Path:
    if not isinstance(relative_path, str):
        raise RuntimeError("registry owner paths must be strings")
    relative = PurePosixPath(relative_path)
    if relative.is_absolute() or ".." in relative.parts or not relative.parts:
        raise RuntimeError(f"unsafe rule source path: {relative_path}")
    root = source_root.resolve(strict=True)
    candidate = root
    for component in relative.parts:
        candidate /= component
        if candidate.is_symlink():
            raise RuntimeError(f"symlink in rule source path: {relative_path}")
    resolved = candidate.resolve(strict=True)
    if not resolved.is_relative_to(root) or not resolved.is_file():
        raise RuntimeError(f"rule source path escapes its root: {relative_path}")
    return resolved


def _extract_heading(source: str, title: Any, path: str) -> str:
    if not isinstance(title, str) or not title:
        raise RuntimeError(f"registry heading is missing for {path}")
    matches = list(re.finditer(r"^(#{1,6})\s+" + re.escape(title) + r"\s*$", source, re.M))
    if len(matches) != 1:
        raise RuntimeError(f"expected one {title!r} heading in {path}; found {len(matches)}")
    match = matches[0]
    level = len(match.group(1))
    next_heading = re.search(r"^#{1," + str(level) + r"}\s+", source[match.end() :], re.M)
    end = match.end() + next_heading.start() if next_heading else len(source)
    result = source[match.end() : end].strip()
    if not result:
        raise RuntimeError(f"owner heading {title!r} in {path} is empty")
    return result
