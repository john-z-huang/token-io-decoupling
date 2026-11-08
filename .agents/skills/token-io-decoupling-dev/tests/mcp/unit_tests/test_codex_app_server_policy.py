"""Keep App Server usage in tests and make model/credential constraints non-optional."""

from __future__ import annotations

import ast
import tomllib
from pathlib import Path
from types import SimpleNamespace

import pytest
from support import codex_app_server as adapter

WORKSPACE = Path(__file__).resolve().parents[6] / "mcp"
MCP_TESTS = Path(__file__).resolve().parents[1]
ADAPTER = MCP_TESTS / "support/codex_app_server.py"


@pytest.fixture
def settings(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-test-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://synthetic.invalid/v1")
    executable = tmp_path / "codex"
    executable.touch()
    return executable, tmp_path, tmp_path / "bin"


def test_codex_python_sdk_is_not_a_dependency_or_import():
    project = tomllib.loads((WORKSPACE / "pyproject.toml").read_text())
    assert "codex-test" not in project["dependency-groups"]
    assert "openai-codex" not in (WORKSPACE / "uv.lock").read_text()
    for path in (WORKSPACE / "src").rglob("*.py"):
        assert "openai_codex" not in path.read_text(), path
    for path in WORKSPACE.rglob("pyproject.toml"):
        if ".venv" in path.parts:
            continue
        metadata = tomllib.loads(path.read_text()).get("project", {})
        runtime = metadata.get("dependencies", [])
        for optional in metadata.get("optional-dependencies", {}).values():
            runtime.extend(optional)
        assert not any("openai-codex" in d for d in runtime), path
    for path in [*(WORKSPACE / "packages").rglob("*.py"), *MCP_TESTS.rglob("*.py")]:
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.ImportFrom):
                assert not (node.module or "").startswith("openai_codex"), path
            elif isinstance(node, ast.Import):
                assert not any(a.name.startswith("openai_codex") for a in node.names), path


@pytest.mark.parametrize("name", ["OPENAI_API_KEY", "OPENAI_BASE_URL"])
@pytest.mark.parametrize("value", [None, "", "   "])
def test_missing_credentials_fail_before_app_server_import(settings, monkeypatch, name, value):
    if value is None:
        monkeypatch.delenv(name)
    else:
        monkeypatch.setenv(name, value)
    monkeypatch.setattr(
        adapter,
        "AppServerClient",
        lambda *args: (_ for _ in ()).throw(
            AssertionError("App Server imported before config check")
        ),
    )
    with pytest.raises(adapter.CodexTestError, match=name):
        with adapter.fixed_codex_session(settings[0], settings[2], phase=adapter._FINAL_INSPECTION):
            (_ for _ in ()).throw(AssertionError("session launched without credentials"))


def test_fixed_settings_reuse_process_values_without_key_in_arguments(settings):
    overrides, environment = adapter.launch_settings(*settings)
    parsed = tomllib.loads("\n".join(overrides))
    assert parsed["mcp_servers"] == {
        name: {
            "command": str(settings[2] / name),
            "args": [],
            "env_vars": [],
            "startup_timeout_sec": 30,
        }
        for name in ("token-io-decoupling-tools", "token-io-decoupling-workflow")
    }
    assert parsed["model"] == "gpt-6-luna"
    assert parsed["model_reasoning_effort"] == "medium"
    assert parsed["forced_login_method"] == "api"
    provider = parsed["model_providers"][adapter.PROVIDER]
    assert provider["env_key"] == "OPENAI_API_KEY"
    assert provider["base_url"] == environment["OPENAI_BASE_URL"]
    assert provider["requires_openai_auth"] is False
    assert environment["OPENAI_API_KEY"] == "synthetic-test-key"
    assert environment["OPENAI_BASE_URL"] == "https://synthetic.invalid/v1"
    assert "synthetic-test-key" not in repr(overrides)
    assert 'model="gpt-6-luna"' in overrides
    assert 'model_reasoning_effort="medium"' in overrides
    assert environment["CODEX_HOME"] == str(settings[1] / ".codex")
    assert not (settings[1] / ".codex/auth.json").exists()


def test_configuration_accepts_only_the_fixed_provider():
    provider = {
        "base_url": "https://synthetic.invalid/v1",
        "env_key": "OPENAI_API_KEY",
        "requires_openai_auth": False,
        "wire_api": "responses",
    }
    config = {
        "model": adapter.MODEL,
        "model_reasoning_effort": adapter.EFFORT,
        "model_provider": adapter.PROVIDER,
        "model_providers": {adapter.PROVIDER: provider},
    }
    client = SimpleNamespace(request=lambda *a, **kw: {"config": config})
    session = adapter.FixedCodexSession(client, Path("/tmp"), "https://synthetic.invalid/v1")
    session.verify_configuration()


@pytest.mark.parametrize(
    "field,value",
    [("model", "another-model"), ("model_reasoning_effort", "high"), ("model_provider", "openai")],
)
def test_effective_configuration_cannot_override_policy(field, value):
    fields = {
        "model": adapter.MODEL,
        "model_reasoning_effort": adapter.EFFORT,
        "model_provider": adapter.PROVIDER,
    }
    fields[field] = value
    client = SimpleNamespace(request=lambda *a, **kw: {"config": fields})
    session = adapter.FixedCodexSession(client, Path("/tmp"), "unused")
    with pytest.raises(adapter.CodexTestError, match="violates test policy"):
        session.verify_configuration()


def test_app_server_launch_requires_final_inspection_phase(settings, monkeypatch):
    def unexpected_import(*args):
        raise AssertionError("App Server imported before final phase")

    monkeypatch.setattr(adapter, "AppServerClient", unexpected_import)
    with pytest.raises(adapter.CodexTestError, match="final post-install"):
        with adapter.fixed_codex_session(settings[0], settings[2]):
            raise AssertionError("unexpected launch")


@pytest.mark.parametrize(
    "field,value",
    [
        ("base_url", "https://wrong.invalid"),
        ("env_key", "OTHER_KEY"),
        ("requires_openai_auth", True),
        ("wire_api", "chat"),
    ],
)
def test_effective_provider_cannot_fall_back(field, value):
    provider = {
        "base_url": "https://synthetic.invalid/v1",
        "env_key": "OPENAI_API_KEY",
        "requires_openai_auth": False,
        "wire_api": "responses",
    }
    provider[field] = value
    config = {
        "model": adapter.MODEL,
        "model_reasoning_effort": adapter.EFFORT,
        "model_provider": adapter.PROVIDER,
        "model_providers": {adapter.PROVIDER: provider},
    }
    client = SimpleNamespace(request=lambda *a, **kw: {"config": config})
    session = adapter.FixedCodexSession(client, Path("/tmp"), "https://synthetic.invalid/v1")
    with pytest.raises(adapter.CodexTestError, match="API provider violates"):
        session.verify_configuration()


def test_raw_app_server_failures_do_not_expose_credentials(settings, monkeypatch):
    class BrokenClient:
        def __init__(self, *args):
            raise RuntimeError("synthetic-test-key https://synthetic.invalid/v1")

    monkeypatch.setattr(adapter, "AppServerClient", BrokenClient)
    with pytest.raises(adapter.CodexTestError) as error:
        with adapter.fixed_codex_session(settings[0], settings[2], phase=adapter._FINAL_INSPECTION):
            (_ for _ in ()).throw(AssertionError("unexpected launch"))
    assert "synthetic-test-key" not in str(error.value)
    assert "synthetic.invalid" not in str(error.value)


def test_version_failure_reports_only_bounded_classifications(settings, monkeypatch):
    """版本子进程失败只报告固定分类，原始诊断中的凭据或端点不能泄漏。"""

    class FailedVersionClient:
        def request(self, *_args, **_kwargs):
            return {
                "exitCode": 126,
                "stdout": "synthetic-test-key",
                "stderr": "Permission denied: https://synthetic.invalid/v1",
            }

    session = adapter.FixedCodexSession(FailedVersionClient(), settings[1], "unused", settings[2])
    monkeypatch.setattr(session, "verify_configuration", lambda: None)
    with pytest.raises(adapter.CodexTestError) as error:
        session.check_mcp()
    message = str(error.value)
    assert "exit=126" in message
    assert "permission_denied=True" in message
    assert "synthetic-test-key" not in message
    assert "synthetic.invalid" not in message


def _standard_capability_report():
    """提供当前中文诊断样例，供版本和保护边界的逐项损坏测试使用。"""

    def detail(status, reason, message="configured diagnostic"):
        return {
            "status": status,
            "reason_code": reason,
            "message": message,
            "source": "test fixture",
            "next_step": "inspect the protected-operation boundary",
        }

    return {
        "agent_runtime": "codex_cli",
        "trusted_binding": "unverified",
        "capability_details": {
            "schema_version": 3,
            "support": {
                "identity_bound_operations": detail(
                    "unavailable", "workflow_has_no_identity_bound_operations"
                )
            },
            "runtime": {
                "binding": detail("unverified", "provider_not_configured"),
                "server_mode": detail(
                    "public_only",
                    "startup_binding_unverified",
                    "此处不建立调用方身份或 workflow 状态存储。",
                ),
            },
            "configuration": {},
        },
    }


def test_standard_capability_diagnostics_report_verified_current_boundary():
    assert adapter._standard_capability_diagnostics(_standard_capability_report()) == {
        "capability_schema_version": 3,
        "trusted_binding": "unverified",
        "binding_reason": "provider_not_configured",
        "server_mode": "public_only",
        "materialization": "separate_service",
    }


@pytest.mark.parametrize(
    "mutate",
    [
        lambda report: report["capability_details"].update(schema_version=2),
        lambda report: report["capability_details"].pop("runtime"),
        lambda report: report["capability_details"]["runtime"].pop("server_mode"),
        lambda report: report["capability_details"]["support"]["identity_bound_operations"].update(
            status="available"
        ),
        lambda report: report["capability_details"]["configuration"].update(
            output_materialization={"status": "available"}
        ),
    ],
)
def test_standard_capability_diagnostics_reject_stale_or_missing_schema(mutate):
    report = _standard_capability_report()
    mutate(report)
    with pytest.raises(adapter.CodexTestError):
        adapter._standard_capability_diagnostics(report)


def test_app_server_factory_gets_explicit_cli_and_isolated_fixed_configuration(
    settings, monkeypatch
):
    captured = {}

    class FakeClient:
        def __init__(self, executable, overrides, environment, directory):
            captured.update(codex_bin=str(executable), config_overrides=overrides, env=environment)

        def initialize(self):
            pass

        def request(self, *args, **kwargs):
            return {"config": tomllib.loads("\n".join(captured["config_overrides"]))}

        def close(self):
            captured["closed"] = True

    monkeypatch.setattr(adapter, "AppServerClient", FakeClient)
    with adapter.fixed_codex_session(settings[0], settings[2], phase=adapter._FINAL_INSPECTION):
        assert captured["codex_bin"] == str(settings[0])
        assert captured["env"]["OPENAI_API_KEY"] == "synthetic-test-key"
        assert captured["env"]["OPENAI_BASE_URL"] == "https://synthetic.invalid/v1"
        temporary_home = Path(captured["env"]["HOME"])
        assert captured["env"]["CODEX_HOME"] == str(temporary_home / ".codex")
        assert (temporary_home / ".codex").is_dir()
        assert not (temporary_home / ".codex/auth.json").exists()
    assert not temporary_home.exists()
    assert captured["closed"] is True


def test_final_inspection_cannot_start_model_turns_or_arbitrary_commands():
    tree = ast.parse(ADAPTER.read_text())
    requests = []
    tools = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        assert node.func.attr not in {"turn_start", "turn", "run", "run_streamed"}
        if node.func.attr == "request":
            assert isinstance(node.args[0], ast.Constant)
            requests.append(node.args[0].value)
            for field in ast.walk(node.args[1]):
                if isinstance(field, ast.Dict):
                    for key, value in zip(field.keys, field.values, strict=True):
                        if isinstance(key, ast.Constant) and key.value == "tool":
                            assert isinstance(value, ast.Constant)
                            tools.append(value.value)
    assert set(requests) == {
        "config/read",
        "thread/start",
        "command/exec",
        "mcpServerStatus/list",
        "mcpServer/tool/call",
    }
    assert set(tools) == {"workflow_capabilities", "rules_get_context"}


def test_compiled_rule_validation_requires_no_app_server_or_author_tree():
    """正文校验只消费外部bundle，不依赖 App Server 启动或作者仓库。"""
    from token_io_decoupling_workflow.rules import RuleLoader

    context = RuleLoader().load_context_bundle("contract").model_dump(mode="json")
    assert adapter.validate_compiled_rule_bundle(context, "zh_cn") == context["build_id"]


@pytest.mark.parametrize(
    "mutate",
    [
        lambda context: context.update(schema_version=1),
        lambda context: context.update(language="en"),
        lambda context: context.update(complete=False),
        lambda context: context.update(remaining_owner_refs=[{"path": "original-owner.md"}]),
        lambda context: context.update(build_id="unknown-build"),
        lambda context: context["node_metadata"].update(owner_path="original-owner.md"),
        lambda context: context["fragments"][0].update(text="corrupt text"),
        lambda context: context.update(text_budget=0),
    ],
)
def test_compiled_rule_validation_rejects_incomplete_or_corrupt_results(mutate):
    """分别破坏版本、语言、身份、正文或预算，均不得被验收为完整指令。"""
    from token_io_decoupling_workflow.rules import RuleLoader

    context = RuleLoader().load_context_bundle("contract").model_dump(mode="json")
    mutate(context)
    with pytest.raises(adapter.CodexTestError):
        adapter.validate_compiled_rule_bundle(context, "zh_cn")
