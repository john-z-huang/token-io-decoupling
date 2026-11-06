from __future__ import annotations

import tomllib
from pathlib import Path


def test_package_installs_admin_and_two_fixed_mcp_entrypoints() -> None:
    project = (Path(__file__).parents[6] / "mcp") / "pyproject.toml"
    scripts = tomllib.loads(project.read_text(encoding="utf-8"))["project"]["scripts"]
    assert scripts == {
        "token-io-decoupling": "token_io_decoupling.cli:main",
    }
    for suffix in ("workflow", "tools"):
        member = project.parent / "packages" / f"token_io_decoupling_{suffix}" / "pyproject.toml"
        metadata = tomllib.loads(member.read_text(encoding="utf-8"))["project"]
        assert metadata["scripts"] == {
            f"token-io-decoupling-{suffix}": f"token_io_decoupling_{suffix}.cli:main"
        }
        sibling = "tools" if suffix == "workflow" else "workflow"
        assert not any(f"token-io-decoupling-{sibling}" in dep for dep in metadata["dependencies"])


def test_obsolete_root_forwarders_are_not_in_the_wheel_package() -> None:
    project = Path(__file__).parents[6] / "mcp"
    pyproject = tomllib.loads((project / "pyproject.toml").read_text(encoding="utf-8"))
    assert pyproject["tool"]["hatch"]["build"]["targets"]["wheel"]["packages"] == [
        "src/token_io_decoupling"
    ]
    obsolete = project / "src" / "token_io_decoupling_mcp"
    assert not list(obsolete.glob("*.py"))
