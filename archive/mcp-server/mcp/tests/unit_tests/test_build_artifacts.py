from __future__ import annotations

import io
import json
import posixpath
import re
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path
from urllib.parse import unquote

import pytest
from token_io_decoupling_core.owner_paths import DELEGATION_POLICY_OWNERS, OWNER_PATHS
from token_io_decoupling_core.rules import RuleLoader

DETACHED_SKILL_REQUIRED_TEXT_ENTRIES = (
    "SKILL.md",
    "agents/openai.yaml",
    "_project/docs/DOCUMENTATION_STANDARDS.md",
    "_project/scripts/_compliance_core.py",
    "_project/scripts/compliance_core_loader.py",
)


@pytest.fixture(scope="module")
def launcher_sdist_path(tmp_path_factory: pytest.TempPathFactory) -> Path:
    workspace = Path(__file__).parents[2]
    output = tmp_path_factory.mktemp("launcher-source")
    subprocess.run(
        [
            "uv",
            "build",
            "--package",
            "token-io-decoupling",
            "--sdist",
            "--no-build-isolation",
            "--python",
            sys.executable,
            "--out-dir",
            str(output),
        ],
        cwd=workspace,
        check=True,
        capture_output=True,
        text=True,
    )
    return next(output.glob("*.tar.gz"))


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
    assert (detached_project / "rule_sources" / "mcp" / "rule-context-index.json").is_file()
    assert registry["nodes"]
    source_loader = RuleLoader(repository_root=workspace.parent)
    control_bundle = source_loader.load_context_bundle("control")
    assert control_bundle.required_fragment_ids == [
        "control.checkpoint",
        "slice.interaction_slice",
        "contract.actions",
        "contract.pass",
        "contract.boundary",
    ]
    optional_context_requests = (
        ("decision", "decision.workflow_routing_advice"),
        ("implementation", "implementation.candidate_compliance"),
        ("implementation", "implementation.output_materialization"),
    )
    for node_id, fragment_id in optional_context_requests:
        assert fragment_id not in source_loader.load_context_bundle(node_id).required_fragment_ids
    baseline = {
        "contexts": {
            f"{node['node_id']}:{language}": source_loader.load_context(
                node["node_id"], language=language
            ).model_dump(mode="json")
            for node in registry["nodes"]
            for language in ("en", "zh_cn")
        },
        "bundles": {
            f"{node}:{language}": source_loader.load_context_bundle(
                node, language=language
            ).model_dump(mode="json")
            for node in ("contract", "control")
            for language in ("en", "zh_cn")
        },
        "optional_bundles": {
            f"{node_id}:{fragment_id}:{language}": source_loader.load_context_bundle(
                node_id, language=language, fragment_ids=[fragment_id]
            ).model_dump(mode="json")
            for node_id, fragment_id in optional_context_requests
            for language in ("en", "zh_cn")
        },
        "policies": {
            owner: source_loader.load_delegation_policy(owner) for owner in DELEGATION_POLICY_OWNERS
        },
    }
    baseline_path = tmp_path / "source-rules.json"
    baseline_path.write_text(json.dumps(baseline, ensure_ascii=False))
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
        assert "token_io_decoupling_core/_resources/context-index.json" in members
        assert "token_io_decoupling_core/owner_paths.py" in members
        rule_resources = {
            name
            for name in members
            if name.startswith("token_io_decoupling_core/_resources/rules/")
        }
        assert len(rule_resources) == 2 * len(registry["nodes"]) + 2 * len(OWNER_PATHS)
        fragment_resources = {
            name
            for name in members
            if name.startswith("token_io_decoupling_core/_resources/fragments/")
        }
        context_index = json.loads(
            (detached_project / "rule_sources" / "mcp/rule-context-index.json").read_text()
        )
        assert len(fragment_resources) == 2 * len(context_index["fragments"])
        assert not any("environment." in name for name in rule_resources)
        expected_delegation_owners = {
            f"token_io_decoupling_core/_resources/rules/{owner}.{language}.md"
            for owner in DELEGATION_POLICY_OWNERS
            for language in ("en", "zh_cn")
        }
        assert expected_delegation_owners <= rule_resources
        expected_owner_resources = {
            f"token_io_decoupling_core/_resources/rules/{owner}.{language}.md"
            for owner in OWNER_PATHS
            for language in ("en", "zh_cn")
        }
        assert expected_owner_resources <= rule_resources
        assert not any(name.startswith("token_io_decoupling_mcp/_resources/") for name in members)

    packaged_owner_check = r"""
import hashlib
import json
import sys
from importlib.resources import files
from pathlib import Path

sys.path.insert(0, sys.argv[1])

from token_io_decoupling_core.rules import RuleLoader, UnknownRuleNodeError
from token_io_decoupling_core.owner_paths import OWNER_PATHS
mapped_owner = OWNER_PATHS["child-role-selection"]
assert mapped_owner.endswith("delegation/child-role-selection.md")

markers = {
    "child-role-selection": ("Role Decisions instructions", "职责 Decisions 指令"),
    "task-assignment": ("Child-selection Decisions instructions", "子代理选择 Decisions 指令"),
    "output-token-routing": ("Output-token Decisions instructions", "Output Token Decisions 指令"),
    "session-role-ownership": ("Primary Output Role", "Primary 输出角色"),
    "decision-context-generation": ("Source and provenance boundary", "来源和 provenance 边界"),
}
resources = files("token_io_decoupling_core").joinpath("_resources", "rules")
loader = RuleLoader()
baseline = json.loads(Path(sys.argv[2]).read_text())
for key, expected in baseline["contexts"].items():
    node, language = key.split(":")
    assert loader.load_context(node, language=language).model_dump(mode="json") == expected
for key, expected in baseline["bundles"].items():
    node, language = key.split(":")
    assert loader.load_context_bundle(node, language=language).model_dump(mode="json") == expected
for key, expected in baseline["optional_bundles"].items():
    node, fragment, language = key.split(":")
    assert loader.load_context_bundle(
        node, language=language, fragment_ids=[fragment]
    ).model_dump(mode="json") == expected
assert loader.load_context("contract").next_checkpoint_ids == ["mode"]
try:
    loader.load_context("environment")
except UnknownRuleNodeError:
    pass
else:
    raise AssertionError("retired environment checkpoint remains active")
for owner, (english_marker, chinese_marker) in markers.items():
    english = resources.joinpath(f"{owner}.en.md").read_text(encoding="utf-8")
    chinese = resources.joinpath(f"{owner}.zh_cn.md").read_text(encoding="utf-8")
    assert chinese_marker in english
    assert english == chinese
    assert chinese_marker in chinese
    loaded, digest = loader.load_delegation_policy(owner)
    assert loaded == english.strip()
    assert digest == hashlib.sha256(loaded.encode("utf-8")).hexdigest()
    assert [loaded, digest] == baseline["policies"][owner]
"""
    subprocess.run(
        [sys.executable, "-I", "-c", packaged_owner_check, str(wheel_path), str(baseline_path)],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    )


def test_workspace_builds_four_wheels_with_disjoint_files(tmp_path: Path) -> None:
    workspace = Path(__file__).parents[2]
    output = tmp_path / "dist"
    build = subprocess.run(
        ["uv", "build", "--all-packages", "--out-dir", str(output)],
        cwd=workspace,
        check=False,
        capture_output=True,
        text=True,
    )
    assert build.returncode == 0, build.stderr
    wheels = sorted(output.glob("*.whl"))
    assert len(wheels) == 4
    owners: dict[str, Path] = {}
    for wheel_path in wheels:
        with zipfile.ZipFile(wheel_path) as wheel:
            for name in wheel.namelist():
                if name.endswith(".dist-info/METADATA"):
                    metadata = wheel.read(name).decode()
                if name.endswith(".py") and ".dist-info/" not in name:
                    assert "/tests/" not in name
                    assert name not in owners, (
                        f"{name} is duplicated in {owners.get(name)} and {wheel_path}"
                    )
                    owners[name] = wheel_path
    assert "token_io_decoupling_core/models.py" in owners
    assert "token_io_decoupling_tools/output_materialization.py" in owners
    assert not any(name.startswith("token_io_decoupling_workflow/") for name in owners)
    assert "token_io_decoupling_transport/registration.py" in owners
    assert not any(name.startswith("token_io_decoupling_state/") for name in owners)
    assert "token_io_decoupling/cli.py" in owners
    core_wheel = owners["token_io_decoupling_core/models.py"]
    for compatibility_module in (
        "__init__", "binding", "models", "project_identity",
        "registry_contract", "rules",
    ):
        assert owners[f"token_io_decoupling_mcp/{compatibility_module}.py"] == core_wheel
    for facade in ("cli", "cli_commands", "decisions", "server"):
        assert f"token_io_decoupling_mcp/{facade}.py" not in owners
    assert not any(name.startswith("token_io_mcp/") for name in owners)
    launcher_wheel = next(path for path in wheels if path.name.startswith("token_io_decoupling-"))
    canonical_core = (
        workspace
        / "packages/token_io_decoupling_core/src/token_io_decoupling_core/compliance_core.py"
    ).read_bytes()
    with zipfile.ZipFile(launcher_wheel) as wheel:
        entries = wheel.read("token_io_decoupling-0.1.0.dist-info/entry_points.txt").decode()
        assert set(entries.splitlines()) == {
            "[console_scripts]",
            "token-io-decoupling-tools = token_io_decoupling.cli:tools_main",
        }
        skill_bundle = wheel.read("token_io_decoupling/skill_bundle.zip")
    with zipfile.ZipFile(io.BytesIO(skill_bundle)) as bundle:
        helper_path = "_project/scripts/_compliance_core.py"
        assert helper_path in bundle.namelist()
        assert bundle.read(helper_path) == canonical_core
        assert "_project/scripts/compliance_core_loader.py" in bundle.namelist()
        bundle_names = set(bundle.namelist())
        projected_guides = {
            f"_project/docs/mcp/{guide}.md"
            for guide in ("DEVELOPMENT", "CANDIDATE_COMPLIANCE", "OUTPUT_MATERIALIZATION")
        }
        assert projected_guides <= bundle_names
        for document in projected_guides:
            content = bundle.read(document).decode("utf-8")
            for raw in re.findall(r"\]\(([^)]+)\)", content):
                if "://" in raw or raw.startswith(("#", "mailto:", "{{")):
                    continue
                target_text = re.split(r"[#?]", raw)[0]
                if not target_text:
                    continue
                target = posixpath.normpath(
                    posixpath.join(posixpath.dirname(document), unquote(target_text))
                )
                assert target in bundle_names, f"{document} has unresolved projected link {raw}"
                if target.endswith(".md"):
                    language_switch = (
                        document.removesuffix("_zh_cn.md") + ".md"
                        if document.endswith("_zh_cn.md")
                        else document.removesuffix(".md") + "_zh_cn.md"
                    )
                    if target != language_switch:
                        assert target.endswith("_zh_cn.md") == document.endswith("_zh_cn.md")


def test_detached_launcher_sdist_builds_offline_skill_bundle(tmp_path: Path) -> None:
    workspace = Path(__file__).parents[2]
    sdist_output = tmp_path / "launcher-sdist"
    sdist_output.mkdir()
    subprocess.run(
        [
            "uv",
            "build",
            "--package",
            "token-io-decoupling",
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
    detached_root = tmp_path / "detached-launcher"
    detached_root.mkdir()
    sdist_path = next(sdist_output.glob("*.tar.gz"))
    with tarfile.open(sdist_path, "r:gz") as archive:
        archive.extractall(detached_root, filter="data")
    detached_project = next(path for path in detached_root.iterdir() if path.is_dir())
    assert (detached_project / "skill_bundle.zip").is_file()
    assert not (
        detached_root
        / "mcp/packages/token_io_decoupling_core/src/token_io_decoupling_core/compliance_core.py"
    ).exists()

    wheel_output = tmp_path / "detached-wheel"
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
        skill_bundle = wheel.read("token_io_decoupling/skill_bundle.zip")
    with zipfile.ZipFile(io.BytesIO(skill_bundle)) as bundle:
        names = set(bundle.namelist())
        helper_path = "_project/scripts/_compliance_core.py"
        loader_path = "_project/scripts/compliance_core_loader.py"
        assert helper_path in names
        canonical_core = (
            workspace
            / "packages/token_io_decoupling_core/src/token_io_decoupling_core/compliance_core.py"
        ).read_bytes()
        assert bundle.read(helper_path) == canonical_core
        assert loader_path in names
        assert "SKILL.md" in names
        assert "agents/openai.yaml" in names
        assert "_project/docs/DOCUMENTATION_STANDARDS.md" in names
        assert not any(Path(name).name == "check-multilingual-docs.py" for name in names)
        snapshot_root = tmp_path / "standalone-skill-snapshot"
        bundle.extractall(snapshot_root)

    assert not (
        snapshot_root
        / "_project/mcp/packages/token_io_decoupling_core/src/token_io_decoupling_core/"
        "compliance_core.py"
    ).exists()
    (detached_project / "skill_bundle.zip").write_bytes(b"not a complete bundle")
    invalid_output = tmp_path / "invalid-bundle-wheel"
    failed_build = subprocess.run(
        [
            "uv",
            "build",
            "--wheel",
            "--no-build-isolation",
            "--python",
            sys.executable,
            "--out-dir",
            str(invalid_output),
        ],
        cwd=detached_project,
        check=False,
        capture_output=True,
        text=True,
    )
    assert failed_build.returncode != 0
    assert (
        "complete Skill sources or a valid bundled Skill snapshot are unavailable"
        in failed_build.stderr
    )


def test_build_refreshes_existing_bundle_after_skill_source_changes(tmp_path: Path) -> None:
    workspace = Path(__file__).parents[2]
    repo = tmp_path / "fixture-repository"
    project = repo / "mcp"
    project.mkdir(parents=True)
    (project / "hatch_build.py").write_bytes((workspace / "hatch_build.py").read_bytes())
    package = project / "src/token_io_decoupling"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("", encoding="utf-8")
    (project / "pyproject.toml").write_text(
        """
[build-system]
requires = ["hatchling>=1.27,<2"]
build-backend = "hatchling.build"

[project]
name = "token-io-decoupling"
version = "0.0.1"

[tool.hatch.build.targets.wheel]
packages = ["src/token_io_decoupling"]

[tool.hatch.build.hooks.custom]
path = "hatch_build.py"
""".strip()
        + "\n",
        encoding="utf-8",
    )
    skill = repo / "skill"
    (skill / "agents").mkdir(parents=True)
    (skill / "SKILL.md").write_text("Old Skill instructions.\n", encoding="utf-8")
    (skill / "SKILL_zh_cn.md").write_text("旧 Skill 指令。\n", encoding="utf-8")
    documentation_standards = repo / "docs/DOCUMENTATION_STANDARDS.md"
    documentation_standards.parent.mkdir(parents=True)
    documentation_standards.write_text("Old documentation standards.\n", encoding="utf-8")
    (skill / "agents/openai.yaml").write_text("short_description: fixture\n", encoding="utf-8")
    canonical_core = (
        repo
        / "mcp/packages/token_io_decoupling_core/src/token_io_decoupling_core/compliance_core.py"
    )
    canonical_core.parent.mkdir(parents=True)
    canonical_core.write_bytes(b"# unchanged canonical helper\n")
    scripts = repo / "scripts"
    scripts.mkdir()
    (scripts / "compliance_core_loader.py").write_text("# loader\n", encoding="utf-8")

    stale_bundle = project / "skill_bundle.zip"
    with zipfile.ZipFile(stale_bundle, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("SKILL.md", "Old Skill instructions.\n")
        archive.writestr("SKILL_zh_cn.md", "旧 Skill 指令。\n")
        archive.writestr("agents/openai.yaml", "short_description: fixture\n")
        archive.writestr(
            "_project/docs/DOCUMENTATION_STANDARDS.md",
            "Old documentation standards.\n",
        )
        archive.writestr("_project/scripts/_compliance_core.py", canonical_core.read_bytes())
        archive.writestr("_project/scripts/compliance_core_loader.py", "# loader\n")

    (skill / "SKILL.md").write_text("Updated Skill instructions.\n", encoding="utf-8")
    documentation_standards.write_text("Updated documentation standards.\n", encoding="utf-8")
    output = tmp_path / "wheel-output"
    subprocess.run(
        [
            "uv",
            "build",
            "--wheel",
            "--no-build-isolation",
            "--python",
            sys.executable,
            "--out-dir",
            str(output),
        ],
        cwd=project,
        check=True,
        capture_output=True,
        text=True,
    )
    wheel_path = next(output.glob("*.whl"))
    with zipfile.ZipFile(wheel_path) as wheel:
        skill_bundle = wheel.read("token_io_decoupling/skill_bundle.zip")
    with zipfile.ZipFile(io.BytesIO(skill_bundle)) as archive:
        assert archive.read("SKILL.md") == b"Updated Skill instructions.\n"
        assert (
            archive.read("_project/docs/DOCUMENTATION_STANDARDS.md")
            == b"Updated documentation standards.\n"
        )
        assert archive.read("_project/scripts/_compliance_core.py") == canonical_core.read_bytes()


@pytest.mark.parametrize("required_entry", DETACHED_SKILL_REQUIRED_TEXT_ENTRIES)
@pytest.mark.parametrize(
    "empty_payload",
    [pytest.param(b"", id="empty"), pytest.param(b" \t\n", id="whitespace-only")],
)
def test_detached_build_rejects_empty_required_text_entries(
    tmp_path: Path,
    launcher_sdist_path: Path,
    required_entry: str,
    empty_payload: bytes,
) -> None:
    detached_root = tmp_path / "detached-launcher"
    detached_root.mkdir()
    with tarfile.open(launcher_sdist_path, "r:gz") as archive:
        archive.extractall(detached_root, filter="data")
    detached_project = next(path for path in detached_root.iterdir() if path.is_dir())
    bundle_path = detached_project / "skill_bundle.zip"
    with zipfile.ZipFile(bundle_path) as archive:
        contents = [(item.filename, archive.read(item.filename)) for item in archive.infolist()]
    assert required_entry in {name for name, _contents in contents}
    with zipfile.ZipFile(bundle_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, content in contents:
            archive.writestr(name, empty_payload if name == required_entry else content)
    with zipfile.ZipFile(bundle_path) as archive:
        assert archive.testzip() is None
        assert archive.read(required_entry) == empty_payload

    output = tmp_path / "invalid-empty-bundle-wheel"
    failed_build = subprocess.run(
        [
            "uv",
            "build",
            "--wheel",
            "--no-build-isolation",
            "--python",
            sys.executable,
            "--out-dir",
            str(output),
        ],
        cwd=detached_project,
        check=False,
        capture_output=True,
        text=True,
    )
    assert failed_build.returncode != 0
    assert (
        "complete Skill sources or a valid bundled Skill snapshot are unavailable"
        in failed_build.stderr
    )
