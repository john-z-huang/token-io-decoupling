"""Verify product-only artifacts and detached builds from approved resources."""

from __future__ import annotations

import hashlib
import io
import json
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path

import pytest

from token_io_decoupling.skills import validate_skill_bundle

REPOSITORY = next(
    parent
    for parent in Path(__file__).resolve().parents
    if (parent / "mcp/pyproject.toml").is_file()
)
WORKSPACE = REPOSITORY / "mcp"
PRIVATE_PARTS = {
    "_project",
    "rule_sources",
    ".agents",
    "instruction-compiler",
    "tests",
    "benchmarks",
    "sources",
}


def _build(project: Path, output: Path, *args: str):
    return subprocess.run(
        [
            "uv",
            "build",
            "--no-build-isolation",
            "--python",
            sys.executable,
            "--out-dir",
            str(output),
            *args,
        ],
        cwd=project,
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.fixture(scope="module")
def artifacts(tmp_path_factory):
    output = tmp_path_factory.mktemp("compiled-product-artifacts")
    built = _build(WORKSPACE, output, "--all-packages")
    assert built.returncode == 0, built.stderr
    assert len(list(output.glob("*.whl"))) == 4
    assert len(list(output.glob("*.tar.gz"))) == 4
    return output


def _wheel(output: Path, distribution: str) -> Path:
    return next(output.glob(f"{distribution}-0.1.0-*.whl"))


def _detach(output: Path, distribution: str, destination: Path) -> Path:
    destination.mkdir()
    with tarfile.open(next(output.glob(f"{distribution}-0.1.0.tar.gz"))) as archive:
        archive.extractall(destination, filter="data")
    return next(destination.iterdir())


def _assert_product_names(names):
    for name in names:
        assert not PRIVATE_PARTS.intersection(Path(name).parts), name
        assert not name.endswith((".pyc", ".sh")), name
        assert Path(name).name not in {
            "MULTI_LINGUAL.md",
            "MULTI_LINGUAL_zh_cn.md",
            "multilingual-docs.md",
            "multilingual-docs_zh_cn.md",
        }, name


def test_four_distributions_have_disjoint_product_payloads(artifacts):
    owners = {}
    for wheel in artifacts.glob("*.whl"):
        with zipfile.ZipFile(wheel) as archive:
            _assert_product_names(archive.namelist())
            for name in archive.namelist():
                if name.endswith(".dist-info/METADATA"):
                    runtime = archive.read(name).decode()
                    assert not any(
                        "openai-codex" in line.lower()
                        for line in runtime.splitlines()
                        if line.startswith("Requires-Dist:")
                    )
                elif ".dist-info/" not in name:
                    assert name not in owners, (name, owners.get(name), wheel.name)
                    owners[name] = wheel.name
    assert "token_io_decoupling/cli.py" in owners
    assert "token_io_decoupling_core/_resources/instructions.json" in owners
    assert "token_io_decoupling_transport/registration.py" in owners
    assert "token_io_decoupling_workflow/checkpoint_evaluation.py" in owners
    assert not any(name.endswith("/heading_parser.py") for name in owners)
    for sdist in artifacts.glob("*.tar.gz"):
        with tarfile.open(sdist) as archive:
            _assert_product_names(archive.getnames())


def test_skill_and_core_are_one_complete_compiled_batch(artifacts):
    with zipfile.ZipFile(_wheel(artifacts, "token_io_decoupling_core")) as core:
        prefix = "token_io_decoupling_core/_resources/"
        resources = {
            name.removeprefix(prefix) for name in core.namelist() if name.startswith(prefix)
        }
        assert resources == {"instructions.json", "manifest.json"}
        payload = core.read(prefix + "instructions.json")
        manifest = json.loads(core.read(prefix + "manifest.json"))
        instructions = json.loads(payload)
        assert manifest["schema_version"] == instructions["schema_version"] == 2
        assert manifest["build_id"] == instructions["build_id"]
        assert manifest["files"] == {"instructions.json": hashlib.sha256(payload).hexdigest()}
    with zipfile.ZipFile(_wheel(artifacts, "token_io_decoupling")) as root:
        bundle = root.read("token_io_decoupling/_resources/skill_bundle.zip")
    skill_manifest, contents = validate_skill_bundle(
        bundle, expected_build_id=manifest["build_id"], expected_files=instructions["skill_files"]
    )
    _assert_product_names(contents)
    assert skill_manifest["schema_version"] == 2
    assert (
        bundle == (WORKSPACE / "src/token_io_decoupling/_resources/skill_bundle.zip").read_bytes()
    )


@pytest.mark.parametrize("distribution", ["token_io_decoupling", "token_io_decoupling_core"])
def test_detached_sdist_rebuild_preserves_approved_resources(artifacts, tmp_path, distribution):
    project = _detach(artifacts, distribution, tmp_path / "detached")
    assert not (project / "rule_sources").exists()
    assert not (project / "instruction-compiler").exists()
    output = tmp_path / "rebuilt"
    built = _build(project, output, "--wheel")
    assert built.returncode == 0, built.stderr
    with (
        zipfile.ZipFile(_wheel(artifacts, distribution)) as original,
        zipfile.ZipFile(_wheel(output, distribution)) as rebuilt,
    ):
        names = [name for name in original.namelist() if "/_resources/" in name]
        assert names
        for name in names:
            assert rebuilt.read(name) == original.read(name)


@pytest.mark.parametrize("distribution", ["token_io_decoupling", "token_io_decoupling_core"])
@pytest.mark.parametrize("damage", ["missing", "corrupt", "extra"])
def test_detached_build_rejects_unapproved_resources(artifacts, tmp_path, distribution, damage):
    project = _detach(artifacts, distribution, tmp_path / "detached")
    resources = project / "src" / distribution / "_resources"
    resource = resources / (
        "skill_bundle.zip" if distribution == "token_io_decoupling" else "instructions.json"
    )
    if damage == "missing":
        resource.unlink()
    elif damage == "corrupt":
        resource.write_bytes(b"corrupt")
    else:
        (resources / "DEVELOPMENT.md").write_text("private development instructions")
    built = _build(project, tmp_path / "failed", "--wheel")
    assert built.returncode != 0
    assert "compiled" in built.stderr.lower()


def test_detached_build_rejects_internally_valid_mixed_batch(artifacts, tmp_path):
    project = _detach(artifacts, "token_io_decoupling_core", tmp_path / "detached")
    resources = project / "src/token_io_decoupling_core/_resources"
    payload = json.loads((resources / "instructions.json").read_bytes())
    payload["build_id"] = "another-batch"
    serialized = json.dumps(payload).encode()
    (resources / "instructions.json").write_bytes(serialized)
    manifest = json.loads((resources / "manifest.json").read_text())
    manifest["files"]["instructions.json"] = hashlib.sha256(serialized).hexdigest()
    (resources / "manifest.json").write_text(json.dumps(manifest))
    built = _build(project, tmp_path / "failed", "--wheel")
    assert built.returncode != 0
    assert "mixed-batch" in built.stderr


def test_skill_payload_contains_no_executable_or_private_attachment(artifacts):
    with zipfile.ZipFile(_wheel(artifacts, "token_io_decoupling")) as root:
        payload = root.read("token_io_decoupling/_resources/skill_bundle.zip")
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        _assert_product_names(archive.namelist())
        assert all(Path(name).suffix in {".md", ".json", ".yaml"} for name in archive.namelist())
