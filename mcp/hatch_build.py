"""Bundle the authored Skill snapshot in wheels and detached source distributions."""

from __future__ import annotations

import os
import re
import tempfile
import zipfile
from pathlib import Path
from urllib.parse import unquote

from hatchling.builders.hooks.plugin.interface import BuildHookInterface


class SkillBuildHook(BuildHookInterface):
    def initialize(self, version, build_data):
        project = Path(self.root)
        bundled = project / "skill_bundle.zip"
        if not bundled.is_file():
            repo = project.parent
            source = repo / "docs/skill"
            if not (source / "SKILL.md").is_file():
                raise RuntimeError("Skill sources unavailable")
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
                    if target.is_file() and target not in files:
                        files.add(target)
                        pending.append(target)

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
        target = (
            "token_io_decoupling/skill_bundle.zip"
            if self.target_name == "wheel"
            else "skill_bundle.zip"
        )
        build_data.setdefault("force_include", {})[str(bundled)] = target

    def finalize(self, version, build_data, artifact_path):
        if hasattr(self, "_temp"):
            self._temp.cleanup()
