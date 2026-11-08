"""Exercise real MCP calls while forbidden sibling imports fail immediately."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from support.isolated_runtime import run_runtime_probe


@pytest.mark.parametrize("service", ["tools", "workflow"])
def test_services_never_import_the_sibling_or_admin(service: str, tmp_path: Path) -> None:
    memory = tmp_path / ".serena/memories"
    memory.mkdir(parents=True)
    (memory / "notes.md").write_text("independent Memory\n", encoding="utf-8")
    completed = run_runtime_probe(
        sys.executable, "service_independence_probe.py", tmp_path, service
    )
    assert completed.returncode == 0, completed.stderr
