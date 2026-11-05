from __future__ import annotations

import pytest
from token_io_decoupling_workflow.serena_memory import SerenaMemoryReadService

from token_io_decoupling.cli_commands import dispatch_command
from token_io_decoupling.serena_memory_factory import (
    SerenaMemoryFactoryError,
    load_serena_memory_service,
)


def make_service() -> SerenaMemoryReadService:
    return SerenaMemoryReadService()


def invalid_service() -> object:
    return object()


def failing_factory() -> object:
    raise RuntimeError("private operator failure")


NON_CALLABLE = 42


def test_factory_requires_explicit_startup_specification() -> None:
    assert load_serena_memory_service(None) is None
    service = load_serena_memory_service(f"{__name__}:make_service")
    assert isinstance(service, SerenaMemoryReadService)
    assert service.capability()["status"] == "unavailable"


@pytest.mark.parametrize(
    ("spec", "reason"),
    [
        ("invalid", "factory_spec_invalid"),
        (f"{__name__}:_private", "factory_spec_invalid"),
        (f"{__name__}:missing", "factory_import_failed"),
        (f"{__name__}:NON_CALLABLE", "factory_not_callable"),
        (f"{__name__}:invalid_service", "factory_result_invalid"),
        (f"{__name__}:failing_factory", "factory_call_failed"),
    ],
)
def test_factory_failures_are_bounded(spec: str, reason: str) -> None:
    with pytest.raises(SerenaMemoryFactoryError) as caught:
        load_serena_memory_service(spec)
    assert caught.value.reason == reason
    assert "private operator failure" not in str(caught.value)


@pytest.mark.parametrize("prefix", [[], ["start-mcp-server"]])
def test_memory_factory_is_a_server_startup_option(prefix: list[str]) -> None:
    result = dispatch_command(
        "token-io-decoupling", "workflow", [*prefix, "--serena-memory-factory", "operator:reader"]
    )
    assert not isinstance(result, int)
    assert result.serena_memory_factory == "operator:reader"


@pytest.mark.parametrize("command", [["skills", "install"], ["setup", "codex", "--dry-run"]])
def test_admin_commands_reject_memory_factory(command: list[str]) -> None:
    assert (
        dispatch_command(
            "token-io-decoupling",
            "workflow",
            ["--serena-memory-factory", "operator:reader", *command],
        )
        == 2
    )
