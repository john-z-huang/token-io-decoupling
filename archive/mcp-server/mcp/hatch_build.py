"""Bundle the compiled Skill snapshot in wheels and detached source distributions."""

from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path, PurePosixPath
from urllib.parse import unquote

from hatchling.builders.hooks.plugin.interface import BuildHookInterface


class SkillBuildHook(BuildHookInterface):
    def initialize(self, version, build_data):
        project = Path(self.root)
        repo = project.parent
        bundled = project / "skill_bundle.zip"
        compliance_core = (
            repo / "mcp/packages/token_io_decoupling_core/src/token_io_decoupling_core/"
            "compliance_core.py"
        )
        expected_compliance_core = (
            compliance_core.read_bytes()
            if compliance_core.is_file() and not compliance_core.is_symlink()
            else None
        )
        if (repo / "rules/SKILL.yaml").is_file():
            subprocess.run(
                [sys.executable, str(repo / "scripts/compile-reference-dsl.py")],
                cwd=repo,
                check=True,
            )
        source = repo / "skill"
        source_markers = (
            source / "SKILL.md",
            source / "agents/openai.yaml",
            repo / "docs/DOCUMENTATION_STANDARDS.md",
            repo / "scripts/compliance_core_loader.py",
        )
        source_available = (
            expected_compliance_core is not None
            and source.is_dir()
            and not source.is_symlink()
            and all(path.is_file() and not path.is_symlink() for path in source_markers)
        )
        bundled_snapshot_valid = False
        if not source_available and bundled.is_file() and not bundled.is_symlink():
            try:
                with zipfile.ZipFile(bundled) as archive:
                    required_entries = {
                        "SKILL.md",
                        "agents/openai.yaml",
                        "_project/docs/DOCUMENTATION_STANDARDS.md",
                        "_project/scripts/_compliance_core.py",
                        "_project/scripts/compliance_core_loader.py",
                    }
                    entry_names = [item.filename for item in archive.infolist()]
                    entries = set(entry_names)
                    safe_entries = len(entries) == len(entry_names) and all(
                        name
                        and not PurePosixPath(name).is_absolute()
                        and ".." not in PurePosixPath(name).parts
                        and "\\" not in name
                        for name in entry_names
                    )
                    if required_entries <= entries and safe_entries and archive.testzip() is None:
                        required_text = {
                            name: archive.read(name).decode("utf-8") for name in required_entries
                        }
                        if all(text.strip() for text in required_text.values()):
                            bundled_helper = archive.read("_project/scripts/_compliance_core.py")
                            bundled_loader = archive.read(
                                "_project/scripts/compliance_core_loader.py"
                            )
                            bundled_snapshot_valid = bool(bundled_helper and bundled_loader) and (
                                expected_compliance_core is None
                                or bundled_helper == expected_compliance_core
                            )
            except (
                OSError,
                KeyError,
                RuntimeError,
                EOFError,
                NotImplementedError,
                UnicodeDecodeError,
                zipfile.BadZipFile,
            ):
                bundled_snapshot_valid = False
        if not source_available and not bundled_snapshot_valid:
            raise RuntimeError(
                "complete Skill sources or a valid bundled Skill snapshot are unavailable"
            )
        if source_available:
            self._temp = tempfile.TemporaryDirectory(prefix="skill-build-")
            bundled = Path(self._temp.name) / "skill_bundle.zip"
            files = list(source.rglob("*"))
            # Supporting repository docs and scripts retain their own source owners.
            for directory in (repo / "mcp", repo / "docs", repo / "scripts"):
                files.extend(p for p in directory.rglob("*") if p.suffix == ".md")
            files.extend(repo.glob("*.md"))
            files.extend((repo / "scripts").glob("*.py"))
            files.extend((repo / "scripts").glob("*.sh"))
            files = {
                path
                for path in files
                if path.is_file()
                and "_NOT_USE_" not in path.name
                and not path.is_symlink()
                and not any(
                    part.startswith(".") or part in ("__pycache__", "dist", "build")
                    for part in path.relative_to(repo).parts
                )
            }
            # Include linked attachments as well as Markdown: manifests, package
            # metadata and CI files are readable supporting snapshots, never imports.
            pending = list(files)
            while pending:
                document = pending.pop()
                if document.suffix != ".md":
                    continue
                prose = re.sub(r"```.*?```", "", document.read_text(), flags=re.S)
                prose = re.sub(r"(`+).*?\1", "", prose)
                for raw in re.findall(r"\]\(([^)]+)\)", prose):
                    if "://" in raw or raw.startswith(("#", "mailto:", "{{")):
                        continue
                    base = re.split("[#?]", raw)[0]
                    target = document.parent / unquote(base)
                    if target.is_symlink():
                        raise RuntimeError(f"symlinked Skill attachment: {base}")
                    target = target.resolve()
                    if not target.is_relative_to(repo) or ".git" in target.relative_to(repo).parts:
                        raise RuntimeError(f"Skill attachment escapes authored sources: {base}")
                    if not target.exists():
                        raise RuntimeError(f"missing Skill attachment: {base}")
                    attachments = [target] if target.is_file() else list(target.rglob("*"))
                    for attachment in attachments:
                        if attachment.is_symlink():
                            raise RuntimeError(f"symlinked Skill attachment: {attachment}")
                        if (
                            attachment.is_file()
                            and attachment not in files
                            and not any(
                                part.startswith(".") or part in ("__pycache__", "dist", "build")
                                for part in attachment.relative_to(repo).parts
                            )
                        ):
                            files.add(attachment)
                            pending.append(attachment)

            def destination(path):
                if path.is_relative_to(source):
                    return path.relative_to(source)
                return Path("_project") / path.relative_to(repo)

            with zipfile.ZipFile(bundled, "w", zipfile.ZIP_DEFLATED) as archive:
                for path in sorted(files):
                    data = path.read_bytes()
                    if path.suffix == ".md":

                        def link(match, path=path):
                            raw = match[1]
                            if "://" in raw or raw.startswith(("#", "mailto:", "{{")):
                                return match[0]
                            base = re.split("[#?]", raw)[0]
                            target = (path.parent / unquote(base)).resolve()
                            if not target.is_relative_to(repo) or not target.exists():
                                return match[0]
                            relative = os.path.relpath(
                                destination(target), destination(path).parent
                            )
                            return "](" + relative + raw[len(base) :] + ")"

                        data = re.sub(r"\]\(([^)]+)\)", link, data.decode()).encode()
                    archive.writestr(destination(path).as_posix(), data)
                archive.writestr("_project/scripts/_compliance_core.py", expected_compliance_core)
        target = (
            "token_io_decoupling/skill_bundle.zip"
            if self.target_name == "wheel"
            else "skill_bundle.zip"
        )
        build_data.setdefault("force_include", {})[str(bundled)] = target

    def finalize(self, version, build_data, artifact_path):
        if hasattr(self, "_temp"):
            self._temp.cleanup()
