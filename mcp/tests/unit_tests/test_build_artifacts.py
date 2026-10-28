from __future__ import annotations

import json
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path


def test_detached_core_sdist_builds_bilingual_rule_resources(tmp_path: Path) -> None:
    workspace = Path(__file__).parents[2]
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
    wheel_path = next(wheel_output.glob("*.whl"))
    with zipfile.ZipFile(wheel_path) as wheel:
        members = set(wheel.namelist())
        assert "token_io_decoupling_core/_resources/registry.json" in members
        rule_resources = {
            name
            for name in members
            if name.startswith("token_io_decoupling_core/_resources/rules/")
        }
        assert len(rule_resources) == 46
        expected_delegation_owners = {
            f"token_io_decoupling_core/_resources/rules/{owner}.{language}.md"
            for owner in (
                "child-role-selection",
                "task-assignment",
                "output-token-routing",
                "session-role-ownership",
                "decision-context-generation",
            )
            for language in ("en", "zh_cn")
        }
        assert expected_delegation_owners <= rule_resources
        assert not any(name.startswith("token_io_decoupling_mcp/_resources/") for name in members)

    packaged_owner_check = r"""
import hashlib
import sys
from importlib.resources import files

sys.path.insert(0, sys.argv[1])

from token_io_decoupling_core.rules import RuleLoader

markers = {
    "child-role-selection": ("Role Decisions instructions", "职责 Decisions 指令"),
    "task-assignment": ("Child-selection Decisions instructions", "子代理选择 Decisions 指令"),
    "output-token-routing": ("Output-token Decisions instructions", "Output Token Decisions 指令"),
    "session-role-ownership": ("Primary Output Role", "Primary 输出角色"),
    "decision-context-generation": ("Source and provenance boundary", "来源和 provenance 边界"),
}
resources = files("token_io_decoupling_core").joinpath("_resources", "rules")
loader = RuleLoader()
for owner, (english_marker, chinese_marker) in markers.items():
    english = resources.joinpath(f"{owner}.en.md").read_text(encoding="utf-8")
    chinese = resources.joinpath(f"{owner}.zh_cn.md").read_text(encoding="utf-8")
    assert english_marker in english
    assert chinese_marker in chinese
    loaded, digest = loader.load_delegation_policy(owner)
    assert loaded == english
    assert digest == hashlib.sha256(english.encode("utf-8")).hexdigest()
"""
    subprocess.run(
        [sys.executable, "-I", "-c", packaged_owner_check, str(wheel_path)],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    )


def test_workspace_builds_eight_wheels_with_disjoint_files(tmp_path: Path) -> None:
    workspace = Path(__file__).parents[2]
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
