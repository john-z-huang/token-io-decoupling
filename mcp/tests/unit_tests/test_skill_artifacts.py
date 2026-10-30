"""Exercise the released CLI with only built artifacts in a fresh environment."""

from __future__ import annotations

import os
import re
import subprocess
import sys
import tarfile
from pathlib import Path


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
    run(cli, "skills", "install", env=env)
    skill = legacy.with_name("token-io-decoupling-skill")
    baseline = (skill / "SKILL.md").read_bytes()
    assert b"name: token-io-decoupling-skill" in baseline
    assert (skill / "SKILL_zh_cn.md").is_file()
    assert (skill / "workflows/coding.md").is_file()
    for doc in skill.rglob("*.md"):
        for raw in re.findall(
            r"\]\(([^)]+)\)", re.sub(r"```.*?```", "", doc.read_text(), flags=re.S)
        ):
            target = raw.split("#")[0].split("?")[0]
            if target.endswith(".md") and "://" not in target:
                resolved = (doc.parent / target).resolve()
                assert resolved.is_relative_to(skill), (doc, raw)
                assert resolved.is_file(), (doc, raw)
    # Remove detached source too: updates still read the installed package snapshot.
    import shutil

    shutil.rmtree(project)
    run(cli, "skills", "update", env=env)
    assert (skill / "SKILL.md").read_bytes() == baseline
    rejected = subprocess.run(
        [cli, "skills", "install", "--name", "token-io-decoupling"],
        cwd=tmp_path,
        env=env,
        capture_output=True,
    )
    assert rejected.returncode == 2
    assert (legacy / "uncommitted.txt").read_text() == "preserve me"
    assert (legacy / ".git").is_dir()
