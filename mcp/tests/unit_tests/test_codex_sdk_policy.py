"""Keep SDK usage in tests and make model/credential constraints non-optional."""

from __future__ import annotations

import ast
import importlib.util
import tomllib
from pathlib import Path
from types import SimpleNamespace

import pytest

WORKSPACE = Path(__file__).resolve().parents[2]
ADAPTER = WORKSPACE / "tests/support/codex_sdk.py"
spec = importlib.util.spec_from_file_location("sdk_test_adapter", ADAPTER)
assert spec and spec.loader
adapter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter)


@pytest.fixture
def settings(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-test-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://synthetic.invalid/v1")
    executable = tmp_path / "codex"
    executable.touch()
    return executable, tmp_path, ["test-mcp"]


def test_sdk_is_only_a_test_dependency_and_single_import_boundary():
    project = tomllib.loads((WORKSPACE / "pyproject.toml").read_text())
    assert any(d.startswith("openai-codex") for d in project["dependency-groups"]["codex-test"])
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
    for path in [*(WORKSPACE / "packages").rglob("*.py"), *(WORKSPACE / "tests").rglob("*.py")]:
        if path == ADAPTER:
            continue
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.ImportFrom):
                assert not (node.module or "").startswith("openai_codex"), path
            elif isinstance(node, ast.Import):
                assert not any(a.name.startswith("openai_codex") for a in node.names), path


@pytest.mark.parametrize("name", ["OPENAI_API_KEY", "OPENAI_BASE_URL"])
@pytest.mark.parametrize("value", [None, "", "   "])
def test_missing_credentials_fail_before_sdk_import(settings, monkeypatch, name, value):
    if value is None:
        monkeypatch.delenv(name)
    else:
        monkeypatch.setenv(name, value)
    monkeypatch.setattr(
        adapter,
        "_sdk",
        lambda: (_ for _ in ()).throw(AssertionError("SDK imported before config check")),
    )
    with pytest.raises(adapter.CodexTestError, match=name):
        with adapter.fixed_codex_session(settings[0], settings[2], phase=adapter._FINAL_INSPECTION):
            (_ for _ in ()).throw(AssertionError("session launched without credentials"))


def test_fixed_settings_reuse_process_values_without_key_in_arguments(settings):
    overrides, environment = adapter.launch_settings(*settings)
    parsed = tomllib.loads("\n".join(overrides))
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
    config = SimpleNamespace(
        model=adapter.MODEL,
        model_reasoning_effort=adapter.EFFORT,
        model_provider=adapter.PROVIDER,
        model_dump=lambda: {"model_providers": {adapter.PROVIDER: provider}},
    )
    client = SimpleNamespace(request=lambda *a, **kw: SimpleNamespace(config=config))
    session = adapter.FixedCodexSession(
        client, [None], Path("/tmp"), "https://synthetic.invalid/v1"
    )
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
    client = SimpleNamespace(
        request=lambda *a, **kw: SimpleNamespace(config=SimpleNamespace(**fields))
    )
    session = adapter.FixedCodexSession(client, [None], Path("/tmp"), "unused")
    with pytest.raises(adapter.CodexTestError, match="violates test policy"):
        session.verify_configuration()


def test_sdk_launch_requires_final_inspection_phase(settings, monkeypatch):
    def unexpected_import():
        raise AssertionError("SDK imported before final phase")

    monkeypatch.setattr(adapter, "_sdk", unexpected_import)
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
    config = SimpleNamespace(
        model=adapter.MODEL,
        model_reasoning_effort=adapter.EFFORT,
        model_provider=adapter.PROVIDER,
        model_dump=lambda: {"model_providers": {adapter.PROVIDER: provider}},
    )
    client = SimpleNamespace(request=lambda *a, **kw: SimpleNamespace(config=config))
    session = adapter.FixedCodexSession(
        client, [None], Path("/tmp"), "https://synthetic.invalid/v1"
    )
    with pytest.raises(adapter.CodexTestError, match="API provider violates"):
        session.verify_configuration()


def test_raw_sdk_failures_do_not_expose_credentials(settings, monkeypatch):
    class BrokenClient:
        def __init__(self, config):
            raise RuntimeError("synthetic-test-key https://synthetic.invalid/v1")

    monkeypatch.setattr(adapter, "_sdk", lambda: (BrokenClient, lambda **kw: kw))
    with pytest.raises(adapter.CodexTestError) as error:
        with adapter.fixed_codex_session(settings[0], settings[2], phase=adapter._FINAL_INSPECTION):
            (_ for _ in ()).throw(AssertionError("unexpected launch"))
    assert "synthetic-test-key" not in str(error.value)
    assert "synthetic.invalid" not in str(error.value)


def test_sdk_factory_gets_explicit_cli_and_isolated_fixed_configuration(settings, monkeypatch):
    captured = {}

    class FakeClient:
        def __init__(self, config):
            captured.update(config)

        def start(self):
            pass

        def initialize(self):
            pass

        def request(self, *args, **kwargs):
            parsed = tomllib.loads("\n".join(captured["config_overrides"]))
            return SimpleNamespace(
                config=SimpleNamespace(
                    model=parsed["model"],
                    model_provider=parsed["model_provider"],
                    model_reasoning_effort=parsed["model_reasoning_effort"],
                    model_dump=lambda: parsed,
                )
            )

        def close(self):
            captured["closed"] = True

    monkeypatch.setattr(adapter, "_sdk", lambda: (FakeClient, lambda **kw: kw, None))
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
        "command/exec",
        "mcpServerStatus/list",
        "mcpServer/tool/call",
    }
    assert set(tools) == {"workflow_capabilities", "rules_get_context"}
