from __future__ import annotations

import tomllib
from pathlib import Path


def test_package_installs_admin_and_two_fixed_mcp_entrypoints() -> None:
    project = Path(__file__).parents[2] / "pyproject.toml"
    scripts = tomllib.loads(project.read_text(encoding="utf-8"))["project"]["scripts"]
    assert scripts == {
        "token-io-decoupling": "token_io_decoupling.cli:main",
        "token-io-decoupling-workflow": "token_io_decoupling.cli:workflow_main",
        "token-io-decoupling-tools": "token_io_decoupling.cli:tools_main",
    }


def test_obsolete_root_forwarders_are_not_in_the_wheel_package() -> None:
    project = Path(__file__).parents[2]
    pyproject = tomllib.loads((project / "pyproject.toml").read_text(encoding="utf-8"))
    assert pyproject["tool"]["hatch"]["build"]["targets"]["wheel"]["packages"] == [
        "src/token_io_decoupling"
    ]
    obsolete = project / "src" / "token_io_decoupling_mcp"
    assert not list(obsolete.glob("*.py"))
