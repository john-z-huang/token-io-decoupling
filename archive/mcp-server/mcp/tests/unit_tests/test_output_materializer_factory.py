from __future__ import annotations

from pathlib import Path
from types import ModuleType

from token_io_decoupling_tools.materialization_storage import MaterializationStorage
from token_io_decoupling_tools.output_materialization import OutputMaterializerConfig

from token_io_decoupling import cli
from token_io_decoupling import output_materializer_factory as factory_module
from token_io_decoupling.output_materializer_factory import load_output_materializer_config


class _GrantProvider:
    def current_grant(self) -> None:
        return None


class _AuthorizationProvider:
    def current_context(self):
        return None


def _config(tmp_path: Path) -> OutputMaterializerConfig:
    return OutputMaterializerConfig(
        project_root=tmp_path / "project",
        artifact_root=tmp_path / "artifacts",
        grant_provider=_GrantProvider(),
        authorization_provider=_AuthorizationProvider(),
    )


def test_absent_factory_does_not_import_operator_code(monkeypatch) -> None:
    def forbidden(_module_name: str) -> ModuleType:
        raise AssertionError("absent factory must not import operator code")

    monkeypatch.setattr(factory_module, "import_module", forbidden)
    assert load_output_materializer_config(None) is None


def test_explicit_factory_loads_only_a_typed_configuration(tmp_path, monkeypatch) -> None:
    module = ModuleType("test_output_materializer_operator")
    config = _config(tmp_path)

    def build() -> OutputMaterializerConfig:
        return config

    module.__dict__["build"] = build
    monkeypatch.setattr(factory_module, "import_module", lambda _name: module)

    loaded = load_output_materializer_config("test_output_materializer_operator:build")

    assert loaded is config


def test_cli_forwards_typed_factory_configuration_to_server(tmp_path, monkeypatch) -> None:
    config = _config(tmp_path)
    forwarded: dict[str, object] = {}

    class _Server:
        _output_materializer = None

        def run(self, *, transport: str) -> None:
            forwarded["transport"] = transport

    def load_config(spec: str | None) -> OutputMaterializerConfig:
        assert spec == "operator_module:build"
        return config

    def create_tools_server(**kwargs):
        forwarded.update(kwargs)
        return _Server()

    monkeypatch.setattr(cli, "load_compliance_service", lambda _spec: None)
    monkeypatch.setattr(cli, "load_output_materializer_config", load_config)
    monkeypatch.setattr(cli, "create_tools_server", create_tools_server)

    assert (
        cli._run_tools(
            prog="token-io-decoupling-tools",
            argv=["--output-materializer-factory", "operator_module:build"],
        )
        == 0
    )
    assert forwarded["output_materializer_config"] is config
    assert forwarded["transport"] == "stdio"


def test_worker_capability_is_unavailable_without_factory_or_path_probe(monkeypatch) -> None:
    def forbidden_storage_init(*_args, **_kwargs) -> None:
        raise AssertionError("unconfigured materialization must not probe storage roots")

    monkeypatch.setattr(MaterializationStorage, "__init__", forbidden_storage_init)
    from token_io_decoupling.server import create_tools_server

    server = create_tools_server()

    assert server._output_materializer is None
