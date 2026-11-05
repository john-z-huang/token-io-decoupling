from __future__ import annotations

import sys
from pathlib import Path
from types import ModuleType

import pytest
from token_io_decoupling_workflow.compliance_preflight import CompliancePreflightService

from token_io_decoupling import cli
from token_io_decoupling.compliance_factory import (
    ComplianceFactoryError,
    load_compliance_service,
)


def test_absent_factory_does_not_configure_or_probe_a_service() -> None:
    assert load_compliance_service(None) is None


@pytest.mark.parametrize("entry", [cli.workflow_main, cli.tools_main])
def test_server_cli_loads_only_the_explicit_compliance_factory(entry, monkeypatch):
    specs = []

    def load(spec):
        specs.append(spec)
        raise ComplianceFactoryError("factory_import_failed")

    monkeypatch.setattr(cli, "load_compliance_service", load)
    monkeypatch.setattr(sys, "argv", ["server", "--compliance-factory", "operator:build"])
    assert entry() == 2
    assert specs == ["operator:build"]


def test_explicit_factory_returns_only_an_operator_configured_service(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = ModuleType("test_operator_compliance_factory")
    captured: list[CompliancePreflightService] = []

    def factory() -> CompliancePreflightService:
        service = CompliancePreflightService(tmp_path, {"skill_maintenance"})
        captured.append(service)
        return service

    module.__dict__["create"] = factory
    monkeypatch.setitem(sys.modules, module.__name__, module)
    service = load_compliance_service(f"{module.__name__}:create")
    assert service is captured[0]
    assert service.capability() == {
        "status": "available",
        "reason_code": "configured_secure_read_only_backend",
        "policy_scopes": ["skill_maintenance"],
    }
    service.close()


@pytest.mark.parametrize(
    ("factory_spec", "module", "callable_name", "expected_reason"),
    [
        ("bad-spec", None, None, "factory_spec_invalid"),
        ("test_missing_compliance_factory:create", None, None, "factory_import_failed"),
        (
            "test_wrong_compliance_factory:create",
            "test_wrong_compliance_factory",
            "create",
            "factory_result_invalid",
        ),
    ],
)
def test_invalid_factories_fail_closed(
    factory_spec: str,
    module: str | None,
    callable_name: str | None,
    expected_reason: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    if module is not None and callable_name is not None:
        loaded = ModuleType(module)
        setattr(loaded, callable_name, lambda: object())
        monkeypatch.setitem(sys.modules, module, loaded)
    with pytest.raises(ComplianceFactoryError) as error:
        load_compliance_service(factory_spec)
    assert error.value.reason == expected_reason
