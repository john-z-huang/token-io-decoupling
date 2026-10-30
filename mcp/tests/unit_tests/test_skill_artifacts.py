"""Exercise the released CLI with only built artifacts in a fresh environment."""

from __future__ import annotations

import hashlib
import os
import re
import subprocess
import sys
import tarfile
import unicodedata
from pathlib import Path
from urllib.parse import unquote


def _assert_local_links(documents: Path, boundary: Path) -> None:
    def prose(path):
        return re.sub(r"```.*?```", "", path.read_text(), flags=re.S)

    def anchors(path):
        counts = {}
        result = set()
        for line in prose(path).splitlines():
            heading = re.match(r"^#{1,6}\s+(.+?)\s*#*$", line)
            if heading is None:
                continue
            text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", heading[1]).lower()
            slug = "".join(
                c for c in text if unicodedata.category(c)[0] in "LN" or c in "_- "
            ).replace(" ", "-")
            count = counts.get(slug, 0)
            counts[slug] = count + 1
            result.add(slug + (f"-{count}" if count else ""))
        return result

    for doc in documents.rglob("*.md"):
        text = re.sub(r"(`+).*?\1", "", prose(doc))
        for raw in re.findall(r"\]\(([^)]+)\)", text):
            if "://" in raw or raw.startswith(("mailto:", "{{")):
                continue
            target, _, fragment = raw.partition("#")
            resolved = (doc.parent / unquote(target.split("?")[0])).resolve() if target else doc
            assert resolved.is_relative_to(boundary), (doc, raw)
            assert resolved.exists(), (doc, raw)
            if fragment and resolved.suffix == ".md":
                assert unquote(fragment) in anchors(resolved), (doc, raw)


def test_migrated_skill_source_links_and_anchors():
    repository = Path(__file__).resolve().parents[3]
    _assert_local_links(repository / "docs/skill", repository)


def test_detached_sdist_cli_installs_without_checkout(tmp_path):
    workspace = Path(__file__).resolve().parents[2]
    wheels = tmp_path / "wheels"

    def run(*args, cwd=tmp_path, env=None):
        return subprocess.run(args, cwd=cwd, env=env, text=True, capture_output=True, check=True)

    run(
        "uv",
        "build",
        "--all-packages",
        "--wheel",
        "--no-build-isolation",
        "--python",
        sys.executable,
        "--out-dir",
        str(wheels),
        cwd=workspace,
    )
    sdists = tmp_path / "sdists"
    run(
        "uv",
        "build",
        "--package",
        "token-io-decoupling",
        "--sdist",
        "--no-build-isolation",
        "--python",
        sys.executable,
        "--out-dir",
        str(sdists),
        cwd=workspace,
    )
    detached = tmp_path / "detached"
    detached.mkdir()
    with tarfile.open(next(sdists.glob("*.tar.gz"))) as archive:
        archive.extractall(detached, filter="data")
    project = next(detached.iterdir())
    assert (project / "skill_bundle.zip").is_file()
    run(
        "uv",
        "build",
        "--wheel",
        "--no-build-isolation",
        "--python",
        sys.executable,
        "--out-dir",
        str(wheels),
        cwd=project,
    )
    venv = tmp_path / "standalone"
    run("uv", "venv", "--python", sys.executable, str(venv))
    run(
        "uv",
        "pip",
        "install",
        "--offline",
        "--python",
        str(venv / "bin/python"),
        "--find-links",
        str(wheels),
        *map(str, wheels.glob("*.whl")),
    )
    home = tmp_path / "home"
    legacy = home / ".agents/skills/token-io-decoupling"
    (legacy / ".git").mkdir(parents=True)
    (legacy / "uncommitted.txt").write_text("preserve me")
    env = {**os.environ, "HOME": str(home)}
    env.pop("PYTHONPATH", None)
    cli = str(venv / "bin/token-io-decoupling")
    config = home / ".codex/config.toml"
    config.parent.mkdir()
    config.write_text('[mcp_servers.preserved]\ncommand = "existing-mcp"\n')
    config_before = config.read_bytes()
    # MCP reads its own packaged policies, regardless of the installed Skill tree.
    rule_probe = """
import json
from token_io_decoupling_core.rules import RuleLoader
from token_io_decoupling_core.owner_paths import OWNER_PATHS
loader = RuleLoader()
registry = loader._load_registry()
print(json.dumps({
    'contexts': [loader.load_context(n.node_id, language=language).context_hash
                 for n in registry.nodes for language in ('en', 'zh_cn')],
    'policies': {name: loader.load_delegation_policy(name)[1] for name in OWNER_PATHS},
}, sort_keys=True))
"""

    def probe():
        return run(str(venv / "bin/python"), "-I", "-c", rule_probe, env=env).stdout

    def program_snapshot():
        return {
            p.relative_to(venv).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in venv.rglob("*")
            if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc"
        }

    rules_before = probe()
    program_before = program_snapshot()
    run(cli, "skills", "install", env=env)
    skill = legacy.with_name("token-io-decoupling-skill")
    baseline = (skill / "SKILL.md").read_bytes()
    assert b"name: token-io-decoupling-skill" in baseline
    assert (skill / "SKILL_zh_cn.md").is_file()
    assert (skill / "workflows/coding.md").is_file()
    _assert_local_links(skill, skill)
    assert (skill / "_project/mcp/rule-registry.json").is_file()
    assert (skill / "_project/.github/workflows/mcp.yml").is_file()
    # Remove detached source too: updates still read the installed package snapshot.
    import shutil

    shutil.rmtree(project)
    run(cli, "skills", "update", env=env)
    assert (skill / "SKILL.md").read_bytes() == baseline
    assert config.read_bytes() == config_before
    assert probe() == rules_before
    assert program_snapshot() == program_before
    # Editing installed instructions cannot change the MCP's packaged rules.
    (skill / "SKILL.md").write_text("local Skill edits")
    assert probe() == rules_before
    assert run(cli, "--version", env=env).returncode == 0
    run(
        sys.executable,
        str(workspace / "tests/support/installed_stdio_smoke.py"),
        "--cli",
        cli,
        env=env,
    )
    rejected = subprocess.run(
        [cli, "skills", "install", "--name", "token-io-decoupling"],
        cwd=tmp_path,
        env=env,
        capture_output=True,
    )
    assert rejected.returncode == 2
    assert (legacy / "uncommitted.txt").read_text() == "preserve me"
    assert (legacy / ".git").is_dir()
