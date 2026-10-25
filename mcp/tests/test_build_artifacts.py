from __future__ import annotations

import json
import os
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path


def test_detached_sdist_build_uses_embedded_rules_and_complete_wheel(tmp_path: Path) -> None:
    project_root = Path(__file__).parents[1]
    sdist_output = tmp_path / "sdist-output"
    sdist_output.mkdir()
    subprocess.run(
        [
            "uv",
            "build",
            "--sdist",
            "--no-build-isolation",
            "--python",
            sys.executable,
            "--out-dir",
            str(sdist_output),
        ],
        cwd=project_root,
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

    # A plausible but unrelated checkout is placed beside the unpacked sdist.
    # The build must use its rule_sources snapshot instead of these files.
    registry = json.loads(
        (detached_project / "rule_sources" / "mcp" / "rule-registry.json").read_text(
            encoding="utf-8"
        )
    )
    (detached_parent / "SKILL.md").write_text("# Wrong checkout\n", encoding="utf-8")
    (detached_parent / "references").mkdir()
    for node in registry["nodes"]:
        pairs = [
            (node["owner_path"], node["owner_section"]),
            (
                node["owner_mirrors"]["zh_cn"]["path"],
                node["owner_mirrors"]["zh_cn"]["section"],
            ),
        ]
        for path, heading in pairs:
            fake = detached_parent / path
            fake.parent.mkdir(parents=True, exist_ok=True)
            fake.write_text(
                f"# Wrong owner\n\n## {heading}\nSENTINEL unrelated version\n", encoding="utf-8"
            )

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
    import_root = tmp_path / "wheel-import"
    import_root.mkdir()
    with zipfile.ZipFile(wheel_path) as wheel:
        members = set(wheel.namelist())
        assert "token_io_mcp/migrations/workflow/v0001_initial.py" in members
        assert "token_io_mcp/migrations/workflow/v0005_native_resolution.py" in members
        assert "token_io_mcp/migrations/worker/v0001_initial.py" in members
        assert (
            len([name for name in members if name.startswith("token_io_mcp/_resources/rules/")])
            == 36
        )
        wheel.extractall(import_root)

    code = (
        "from token_io_mcp.rules import RuleLoader; "
        "en=RuleLoader().load_context('contract'); "
        "zh=RuleLoader().load_context('contract', language='zh_cn'); "
        "assert en.owner_text and zh.owner_text; "
        "assert 'SENTINEL' not in en.owner_text and 'SENTINEL' not in zh.owner_text; "
        "print('detached bilingual resources: ok')"
    )
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(import_root)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    subprocess.run(
        [sys.executable, "-c", code],
        cwd=tmp_path,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )

    installed_target = tmp_path / "installed-wheel"
    subprocess.run(
        ["uv", "pip", "install", "--no-deps", "--target", str(installed_target), str(wheel_path)],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    )
    state_script = r"""
from pathlib import Path
from token_io_mcp.models import CodingMode, ModeCount, SemanticRef
from token_io_mcp.state_models import (
    BindingIdentity, HostCapability, HostGuard, SessionRole,
    WorkflowOpenRequest, CheckpointNode,
)
from token_io_mcp.state_service import StateService

class Provider:
    def __init__(self):
        self.binding = BindingIdentity(
            project_id="wheel-project", root_session_id="wheel-root",
            current_session_id="wheel-root", role=SessionRole.PARENT,
            capabilities=frozenset({HostCapability.WORKFLOW_WRITE, HostCapability.WORKFLOW_READ}),
            guards=frozenset(
                {HostGuard.IDENTITY_BOUND, HostGuard.SESSION_BOUND, HostGuard.PATH_BOUNDARY}
            ),
        )
    def current_binding(self):
        return self.binding

state_root = Path(__import__("sys").argv[1])
service = StateService(Provider(), state_root=state_root)
service.workflow_open(WorkflowOpenRequest(
    mode_count=ModeCount(mode=CodingMode.MULTI_AGENT, child_count=1),
    mode_source="explicit",
    source=SemanticRef(uri="test://wheel-plan", content_hash="a" * 64),
    idempotency_key="wheel-open",
))
revision = service.workflow_get_state().revision
result = service.workflow_evaluate(
    CheckpointNode.CONTRACT, expected_revision=revision,
    idempotency_key="wheel-contract-evaluation",
)
assert result.outcome == "incomplete"
assert result.rule_hash and result.missing_facts
print("installed wheel state service: ok")
"""
    installed_environment = os.environ.copy()
    installed_environment.pop("PYTHONPATH", None)
    installed_environment["PYTHONPATH"] = str(installed_target)
    installed_environment["PYTHONDONTWRITEBYTECODE"] = "1"
    subprocess.run(
        [sys.executable, "-c", state_script, str(tmp_path / "wheel-state")],
        cwd=tmp_path,
        env=installed_environment,
        check=True,
        capture_output=True,
        text=True,
    )
