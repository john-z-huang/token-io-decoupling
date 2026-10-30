from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

SUPPORT = Path(__file__).resolve().parents[1] / "support"
sys.path.insert(0, str(SUPPORT))
spec = importlib.util.spec_from_file_location("final_codex_check", SUPPORT / "final_codex_check.py")
assert spec and spec.loader
coordinator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(coordinator)


def test_sdk_only_follows_all_checks_and_tool_update():
    trace = []
    result = coordinator.run_final(
        [("unit", [], Path("/tmp")), ("package", [], Path("/tmp"))],
        lambda label, *_: trace.append(label),
        lambda: trace.append("uv tool update") or Path("/tmp/installed"),
        lambda installed: trace.append("new SDK CLI") or {"passed": True},
    )
    assert trace == ["unit", "package", "uv tool update", "new SDK CLI"]
    assert result == {"passed": True}


@pytest.mark.parametrize("phase", ["checks", "install"])
def test_failure_prevents_sdk_launch(phase):
    trace = []

    def run(*_):
        trace.append("checks")
        if phase == "checks":
            raise RuntimeError("failed check")

    def install():
        trace.append("install")
        raise RuntimeError("failed install")

    with pytest.raises(RuntimeError):
        coordinator.run_final(
            [("unit", [], Path("/tmp"))], run, install, lambda _: trace.append("SDK")
        )
    assert "SDK" not in trace
