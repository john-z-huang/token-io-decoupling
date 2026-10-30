"""Capability discovery with controlled providers; no live host or API requests."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any, cast

import pytest
from mcp import Client
from mcp.types import TextContent
from token_io_decoupling_core.binding import BindingError
from token_io_decoupling_core.host_binding import HostChannelBindingProvider
from token_io_decoupling_core.state_models import (
    BindingIdentity,
    HostCapability,
    HostGuard,
    SessionRole,
    VerifiedChildBinding,
)
from token_io_decoupling_transport.identity import binding_details, bound_role
from token_io_decoupling_workflow.decisions import DecisionsRuntimeConfig

from token_io_decoupling.server import create_server

SECRET = "sensitive-exception-provider-identity-path-marker"


def _identity(role: SessionRole = SessionRole.PARENT) -> BindingIdentity:
    return BindingIdentity(
        project_id=SECRET,
        root_session_id=SECRET,
        current_session_id=SECRET if role is SessionRole.PARENT else "worker",
        parent_session_id=SECRET if role is SessionRole.WORKER else None,
        role=role,
        capabilities=frozenset(HostCapability),
        guards=frozenset(HostGuard),
    )


class ControlledProvider:
    def __init__(self, outcome: object) -> None:
        self.outcome = outcome
        self.reads = 0

    @property
    def transport(self) -> str:
        raise RuntimeError(SECRET)

    def current_binding(self) -> BindingIdentity:
        self.reads += 1
        if isinstance(self.outcome, Exception):
            raise self.outcome
        return cast(BindingIdentity, self.outcome)

    def verify_child_binding(
        self, parent: BindingIdentity, child_session_id: str
    ) -> VerifiedChildBinding:
        raise BindingError(SECRET)


def _capabilities(server: Any) -> dict[str, Any]:
    async def read() -> dict[str, Any]:
        async with Client(server, mode="auto") as client:
            result = await client.call_tool("workflow_capabilities", {})
            assert not result.is_error
            return json.loads(cast(TextContent, result.content[0]).text)

    return asyncio.run(read())


def _assert_safe_details(report: dict[str, Any]) -> None:
    assert SECRET not in json.dumps(report)
    details = report["capability_details"]
    assert details["schema_version"] == 1
    entries = list(details["configuration"].values()) + list(details["runtime"].values())
    for adapter in details["support"]["host_adapters"].values():
        entries.extend(adapter.values())
    for entry in entries:
        assert {"status", "reason_code", "message", "source", "next_step"} <= entry.keys()
        assert all(isinstance(value, str) and value for value in entry.values())


def test_default_report_distinguishes_support_configuration_and_unprobed_runtime(
    tmp_path: Path,
) -> None:
    report = _capabilities(create_server(state_root=tmp_path / "untouched"))
    _assert_safe_details(report)
    assert report["enhanced_binding"] == "unverified"
    assert report["binding_transport"] == "unavailable"
    assert report["caller_match"] == report["api_decisions"] == "disabled"
    assert report["mode_fallback"] == "Native"
    details = report["capability_details"]
    for adapter in details["support"]["host_adapters"].values():
        for entry in adapter.values():
            assert entry["status"] == "unavailable"
            assert entry["reason_code"] == "adapter_not_implemented"
    configuration = details["configuration"]
    for name in ("caller_match", "api_decisions"):
        assert configuration[name]["reason_code"] == "configured_disabled"
    assert configuration["task_plan_tools"]["status"] == "unavailable"
    assert configuration["task_plan_tools"]["reason_code"] == "task_plan_backend_not_configured"
    assert details["runtime"]["binding"]["status"] == "unverified"
    assert details["runtime"]["binding"]["reason_code"] == "provider_not_configured"
    assert details["runtime"]["server_mode"]["status"] == "public_only"
    assert not (tmp_path / "untouched").exists()


@pytest.mark.parametrize("role", [SessionRole.PARENT, SessionRole.WORKER])
def test_embedded_report_probes_once_and_does_not_claim_builtin_adapter_support(
    role: SessionRole,
    tmp_path: Path,
) -> None:
    provider = ControlledProvider(_identity(role))
    server = create_server(provider, state_root=tmp_path / "untouched")
    provider.reads = 0
    report = _capabilities(server)
    assert provider.reads == 1
    assert report["enhanced_binding"] == "available"
    assert report["binding_transport"] == "embedded_provider"
    runtime = report["capability_details"]["runtime"]
    assert runtime["binding"]["reason_code"] == "baseline_verified"
    assert runtime["binding"]["role"] == role.value
    assert runtime["binding_transport"]["reason_code"] == "transport_not_reported"
    assert runtime["server_mode"]["status"] == "embedded"
    assert report["host_adapters"]["Codex Desktop"]["identity_attestation"] == "unavailable"
    _assert_safe_details(report)
    assert not (tmp_path / "untouched").exists()


@pytest.mark.parametrize("initially_embedded", [False, True])
@pytest.mark.parametrize(
    ("outcome", "status", "code"),
    [
        (PermissionError(SECRET), "unavailable", "permission_denied"),
        (BindingError(SECRET), "unknown", "binding_unavailable"),
        (RuntimeError(SECRET), "unknown", "probe_failed"),
        (None, "unknown", "invalid_binding_response"),
        ({"role": SECRET}, "unknown", "invalid_binding_response"),
        (
            _identity().model_copy(update={"guards": frozenset()}),
            "unavailable",
            "required_guards_missing",
        ),
        (
            _identity().model_copy(update={"current_session_id": "wrong-session"}),
            "unavailable",
            "session_identity_mismatch",
        ),
        (
            _identity(SessionRole.WORKER).model_copy(update={"parent_session_id": "wrong-parent"}),
            "unavailable",
            "session_identity_mismatch",
        ),
        (
            _identity(SessionRole.WORKER).model_copy(
                update={"guards": frozenset(HostGuard) - {HostGuard.WORKER_STORE_ISOLATION}}
            ),
            "unavailable",
            "required_guards_missing",
        ),
    ],
)
def test_initial_and_later_provider_failures_are_safe_and_fail_closed(
    outcome: object,
    status: str,
    code: str,
    initially_embedded: bool,
    tmp_path: Path,
) -> None:
    provider = ControlledProvider(_identity() if initially_embedded else outcome)
    server = create_server(provider, profile="workflow", state_root=tmp_path / "untouched")
    provider.outcome = outcome
    provider.reads = 0
    report = _capabilities(server)
    assert provider.reads == 1
    diagnostic = report["capability_details"]["runtime"]["binding"]
    assert (diagnostic["status"], diagnostic["reason_code"]) == (status, code)
    assert "role" not in diagnostic
    assert report["enhanced_binding"] == ("unavailable" if initially_embedded else "unverified")
    assert bound_role(provider) is None
    _assert_safe_details(report)

    async def protected_call() -> None:
        async with Client(server, mode="auto") as client:
            result = await client.call_tool("workflow_evaluate", {"payload": {}})
            assert result.is_error
            text = cast(TextContent, result.content[0]).text
            assert "trusted host binding or required guard is unavailable" in text
            assert SECRET not in text

    asyncio.run(protected_call())
    assert not (tmp_path / "untouched").exists()


def test_later_valid_probe_never_promotes_startup_public_scope() -> None:
    provider = ControlledProvider(BindingError(SECRET))
    server = create_server(provider)
    original_tools = {tool.name for tool in server._tool_manager.list_tools()}
    provider.outcome = _identity()
    report = _capabilities(server)
    assert report["enhanced_binding"] == "unverified"
    assert report["binding_transport"] == "unavailable"
    runtime = report["capability_details"]["runtime"]
    assert runtime["binding"]["status"] == "available"
    assert runtime["server_mode"]["status"] == "public_only"
    assert {tool.name for tool in server._tool_manager.list_tools()} == original_tools
    assert "workflow_open" not in original_tools


def test_enabled_configuration_does_not_probe_api_or_verify_request_context(tmp_path: Path) -> None:
    def forbidden_api_factory(*args: Any) -> object:
        raise AssertionError("capability discovery must not create an API client")

    report = _capabilities(
        create_server(
            ControlledProvider(_identity()),
            require_codex_context=True,
            decisions_config=DecisionsRuntimeConfig(enabled=True, outbound_data_permitted=True),
            decisions_client_factory=forbidden_api_factory,
            state_root=tmp_path / "untouched",
        )
    )
    assert report["caller_match"] == "required"
    assert report["api_decisions"] == "enabled"
    config = report["capability_details"]["configuration"]
    assert config["caller_match"]["reason_code"] == "configured_required"
    assert config["api_decisions"]["reason_code"] == "configured_enabled"
    _assert_safe_details(report)
    assert not (tmp_path / "untouched").exists()


def test_role_and_diagnostic_use_the_same_baseline_predicate() -> None:
    provider = ControlledProvider(_identity())
    assert binding_details(provider)["role"] == bound_role(provider) == "parent"
    provider.outcome = _identity().model_copy(update={"guards": frozenset()})
    assert binding_details(provider)["status"] == "unavailable"
    assert bound_role(provider) is None


def test_known_transport_is_classified_without_serializing_provider_attributes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Only exercise type-based reporting; this is not a real host attestation.
    provider = object.__new__(HostChannelBindingProvider)
    monkeypatch.setattr(HostChannelBindingProvider, "current_binding", lambda self: _identity())
    monkeypatch.setattr(HostChannelBindingProvider, "transport", SECRET)
    report = _capabilities(create_server(provider))
    assert report["binding_transport"] == "authenticated_inherited_unix_socket"
    detail = report["capability_details"]["runtime"]["binding_transport"]
    assert (detail["status"], detail["reason_code"]) == ("available", "known_transport")
    _assert_safe_details(report)
