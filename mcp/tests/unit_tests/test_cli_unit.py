from __future__ import annotations

import importlib
import tomllib
from pathlib import Path

from token_io_decoupling_core.binding import BindingError

from token_io_decoupling import cli


def test_package_installs_one_unified_console_script() -> None:
    project = Path(__file__).parents[2] / "pyproject.toml"
    scripts = tomllib.loads(project.read_text(encoding="utf-8"))["project"]["scripts"]
    assert scripts == {"token-io-decoupling": "token_io_decoupling.cli:main"}


def test_legacy_adapter_is_disjoint_and_importable() -> None:
    from token_io_decoupling_mcp.binding import BindingError as LegacyBindingError

    import token_io_decoupling_mcp

    legacy_server = importlib.import_module("token_io_decoupling_mcp.server")

    assert token_io_decoupling_mcp.__version__ == "0.1.0"
    assert LegacyBindingError is BindingError
    assert legacy_server.create_server is cli.create_server
