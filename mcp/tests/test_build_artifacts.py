from __future__ import annotations

import json
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path


def test_detached_core_sdist_builds_bilingual_rule_resources(tmp_path: Path) -> None:
    workspace = Path(__file__).parents[1]
    sdist_output = tmp_path / "sdist-output"
    sdist_output.mkdir()
    subprocess.run(
        [
            "uv",
            "build",
            "--package",
            "token-io-decoupling-core",
            "--sdist",
            "--no-build-isolation",
            "--python",
            sys.executable,
            "--out-dir",
            str(sdist_output),
        ],
        cwd=workspace,
        check=True,
        capture_output=True,
        text=True,
    )
    sdist_path = next(sdist_output.glob("*.tar.gz"))
    detached_parent = tmp_path / "detached"
    detached_parent.mkdir()
    with tarfile.open(sdist_path, "r:gz") as archive:
        archive.extractall(detached_parent, filter="data")
    detached_project = next(path for path in detached_parent.iterdir() if path.is_dir())
    registry = json.loads(
        (detached_project / "rule_sources" / "mcp" / "rule-registry.json").read_text()
    )
    assert registry["nodes"]
    wheel_output = tmp_path / "wheel-output"
    subprocess.run(
        [
            "uv",
            "build",
            "--wheel",
            "--no-build-isolation",
            "--python",
            sys.executable,
            "--out-dir",
            str(wheel_output),
        ],
        cwd=detached_project,
        check=True,
        capture_output=True,
        text=True,
    )
    with zipfile.ZipFile(next(wheel_output.glob("*.whl"))) as wheel:
        members = set(wheel.namelist())
        assert "token_io_decoupling_core/_resources/registry.json" in members
        assert (
            len(
                [
                    name
                    for name in members
                    if name.startswith("token_io_decoupling_core/_resources/rules/")
                ]
            )
            == 36
        )
        assert not any(name.startswith("token_io_decoupling_mcp/_resources/") for name in members)


def test_workspace_builds_eight_wheels_with_disjoint_files(tmp_path: Path) -> None:
    workspace = Path(__file__).parents[1]
    output = tmp_path / "dist"
    subprocess.run(
        ["uv", "build", "--all-packages", "--out-dir", str(output)],
        cwd=workspace,
        check=True,
        capture_output=True,
        text=True,
    )
    wheels = sorted(output.glob("*.whl"))
    assert len(wheels) == 8
    owners: dict[str, Path] = {}
    for wheel_path in wheels:
        with zipfile.ZipFile(wheel_path) as wheel:
            for name in wheel.namelist():
                if name.endswith(".py") and ".dist-info/" not in name:
                    assert name not in owners, (
                        f"{name} is duplicated in {owners.get(name)} and {wheel_path}"
                    )
                    owners[name] = wheel_path
    assert "token_io_decoupling_core/models.py" in owners
    assert "token_io_decoupling_state/service.py" in owners
    assert "token_io_decoupling_transport/registration.py" in owners
    assert "token_io_decoupling/cli.py" in owners
    assert "token_io_decoupling_mcp/__init__.py" in owners
    assert not any(name.startswith("token_io_mcp/") for name in owners)
