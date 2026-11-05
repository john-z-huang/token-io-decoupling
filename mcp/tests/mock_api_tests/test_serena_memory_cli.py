from __future__ import annotations

from argparse import Namespace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from token_io_decoupling.cli import _run
from token_io_decoupling.serena_memory_runtime import IsolatedSerenaMemoryService


def _args(project: Path, python: Path, *, profile: str | None = "workflow") -> Namespace:
    return Namespace(
        profile=profile,
        codex_context=False,
        host_fd=None,
        task_plan_factory=None,
        serena_memory_factory=None,
        serena_project_root=project,
        serena_python=python,
        compliance_factory=None,
        output_materializer_factory=None,
    )


def test_cli_uses_isolated_binding_only_for_workflow(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    python = tmp_path / "serena" / "bin" / "python"
    python.parent.mkdir(parents=True)
    python.touch()
    python.chmod(0o755)
    server = SimpleNamespace(_output_materializer=None, run=Mock())

    with (
        patch("token_io_decoupling.cli.dispatch_command", return_value=_args(project, python)),
        patch("token_io_decoupling.cli.load_task_plan_service", return_value=None),
        patch("token_io_decoupling.cli.load_compliance_service", return_value=None),
        patch("token_io_decoupling.cli.load_output_materializer_config", return_value=None),
        patch("token_io_decoupling.cli.load_serena_memory_service") as legacy_factory,
        patch("token_io_decoupling.cli.create_server", return_value=server) as create_server,
    ):
        code = _run(prog="codex", default_profile=None)

    assert code == 0
    service = create_server.call_args.kwargs["serena_memory_service"]
    assert isinstance(service, IsolatedSerenaMemoryService)
    assert service._python_executable == python
    legacy_factory.assert_not_called()
    server.run.assert_called_once_with(transport="stdio")


def test_cli_rejects_partial_pair_and_non_workflow_profile(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    python = tmp_path / "python"
    args = _args(project, python)
    args.serena_python = None
    with patch("token_io_decoupling.cli.dispatch_command", return_value=args):
        assert _run(prog="codex", default_profile=None) == 2

    args = _args(project, python, profile="root")
    with patch("token_io_decoupling.cli.dispatch_command", return_value=args):
        assert _run(prog="codex", default_profile=None) == 2
