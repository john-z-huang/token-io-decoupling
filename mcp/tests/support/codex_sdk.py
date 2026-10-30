"""Test-only Codex SDK boundary. No configurable model, effort or credentials."""

from __future__ import annotations

import json
import os
import tempfile
from contextlib import contextmanager
from pathlib import Path

MODEL = "gpt-6-luna"
EFFORT = "medium"
PROVIDER = "token_io_test"
_FINAL_INSPECTION = object()
SERVER = "token-io-sdk-test"


class CodexTestError(RuntimeError):
    """Safe failure without SDK stderr, configuration values or credential data."""


def launch_settings(executable: Path, directory: Path, mcp_command: list[str]):
    key = os.environ.get("OPENAI_API_KEY", "")
    base_url = os.environ.get("OPENAI_BASE_URL", "")
    for name, value in (("OPENAI_API_KEY", key), ("OPENAI_BASE_URL", base_url)):
        if not value.strip():
            raise CodexTestError(f"required process environment variable missing: {name}")
    if not executable.is_absolute() or not executable.is_file():
        raise CodexTestError("an explicit installed Codex executable is required")
    overrides = (
        f"model={json.dumps(MODEL)}",
        f"model_reasoning_effort={json.dumps(EFFORT)}",
        f"model_provider={json.dumps(PROVIDER)}",
        'forced_login_method="api"',
        f"model_providers.{PROVIDER}="
        + json.dumps(
            {
                "name": "Test API",
                "base_url": base_url,
                "env_key": "OPENAI_API_KEY",
                "wire_api": "responses",
                "requires_openai_auth": False,
                "request_max_retries": 0,
                "stream_max_retries": 0,
            }
        ).replace(": ", " = "),
        "mcp_servers={"
        + json.dumps(SERVER)
        + "={command="
        + json.dumps(mcp_command[0])
        + ",args="
        + json.dumps(mcp_command[1:])
        + ",env_vars=[],startup_timeout_sec=30}}",
    )
    # SDK merges this into its process environment; isolate config/auth/plugin state.
    environment = {
        "OPENAI_API_KEY": key,
        "OPENAI_BASE_URL": base_url,
        "HOME": str(directory),
        "CODEX_HOME": str(directory / ".codex"),
        "PYTHONPATH": "",
    }
    return overrides, environment


def _sdk():
    # The sole permitted SDK import site in this repository.
    from openai_codex.client import CodexClient, CodexConfig
    from openai_codex.generated.v2_all import (
        CommandExecResponse,
        ConfigReadResponse,
        ListMcpServerStatusResponse,
        McpServerToolCallResponse,
    )

    return (
        CodexClient,
        CodexConfig,
        ConfigReadResponse,
        ListMcpServerStatusResponse,
        McpServerToolCallResponse,
        CommandExecResponse,
    )


class FixedCodexSession:
    def __init__(self, client, types, directory, base_url, mcp_command=None):
        self._client = client
        self._types = types
        self._directory = directory
        self._base_url = base_url
        self._thread_id = None
        self._mcp_command = mcp_command

    def verify_configuration(self):
        config = self._client.request(
            "config/read", {"includeLayers": False}, response_model=self._types[0]
        ).config
        if (
            config.model != MODEL
            or config.model_provider != PROVIDER
            or config.model_reasoning_effort != EFFORT
        ):
            raise CodexTestError("effective model/provider/effort violates test policy")
        providers = config.model_dump().get("model_providers", {})
        provider = providers.get(PROVIDER, {})
        if (
            provider.get("base_url") != self._base_url
            or provider.get("env_key") != "OPENAI_API_KEY"
            or provider.get("requires_openai_auth") is not False
            or provider.get("wire_api") != "responses"
        ):
            raise CodexTestError("effective API provider violates test policy")

    def start_thread(self):
        self.verify_configuration()
        started = self._client.thread_start(
            {
                "cwd": str(self._directory),
                "ephemeral": True,
                "model": MODEL,
                "modelProvider": PROVIDER,
                "config": {"model_reasoning_effort": EFFORT},
                "approvalPolicy": "never",
                "sandbox": "read-only",
            }
        )
        if (
            started.model != MODEL
            or started.model_provider != PROVIDER
            or started.reasoning_effort != EFFORT
        ):
            raise CodexTestError("thread model/provider/effort violates test policy")
        self._thread_id = started.thread.id

    def check_mcp(self):
        self.verify_configuration()
        if self._mcp_command is None:
            raise CodexTestError("newly installed MCP command is required")
        command = self._client.request(
            "command/exec",
            {
                "command": self._mcp_command + ["--version"],
                "cwd": str(self._directory),
                "sandboxPolicy": {"type": "readOnly"},
                "timeoutMs": 10000,
            },
            response_model=self._types[3],
        )
        if command.exit_code != 0 or "token-io-" not in command.stdout:
            raise CodexTestError("installed MCP executable version check failed")
        self.start_thread()
        status = self._client.request(
            "mcpServerStatus/list",
            {
                "threadId": self._thread_id,
                "serverName": SERVER,
                "detail": "toolsAndAuthOnly",
            },
            response_model=self._types[1],
        )
        servers = [s for s in status.data if s.name == SERVER]
        if len(servers) != 1 or "workflow_capabilities" not in servers[0].tools:
            raise CodexTestError("expected MCP server/tools unavailable")
        result = self._client.request(
            "mcpServer/tool/call",
            {
                "threadId": self._thread_id,
                "server": SERVER,
                "tool": "workflow_capabilities",
                "arguments": {},
            },
            response_model=self._types[2],
        )
        if result.is_error:
            raise CodexTestError("MCP capabilities call failed")
        report = json.loads(result.content[0]["text"])
        if report.get("agent_runtime") != "codex_cli":
            raise CodexTestError("unexpected MCP capabilities response")
        for language in ("en", "zh_cn"):
            rules = self._client.request(
                "mcpServer/tool/call",
                {
                    "threadId": self._thread_id,
                    "server": SERVER,
                    "tool": "rules_get_context",
                    "arguments": {"payload": {"node_id": "contract", "language": language}},
                },
                response_model=self._types[2],
            )
            if rules.is_error:
                raise CodexTestError("packaged MCP rule lookup failed")
            context = json.loads(rules.content[0]["text"])
            if (
                context.get("language") != language
                or not context.get("owner_text")
                or not context.get("owner_path", "").startswith("docs/skill/")
                or len(context.get("context_hash", "")) != 64
            ):
                raise CodexTestError("unexpected packaged MCP rule context")
        return {"model": MODEL, "effort": EFFORT, "mcp": "passed", "model_turns": 0}


@contextmanager
def fixed_codex_session(executable: Path, mcp_command: list[str], *, phase=None):
    if phase is not _FINAL_INSPECTION:
        raise CodexTestError("SDK launch is restricted to the final post-install inspection phase")
    # No SDK launch or dependency import until both existing values are verified.
    with tempfile.TemporaryDirectory(prefix="token-io-sdk-test-") as temporary:
        directory = Path(temporary)
        overrides, environment = launch_settings(executable, directory, mcp_command)
        # Codex requires an explicitly configured CODEX_HOME to already exist.
        Path(environment["CODEX_HOME"]).mkdir()
        client = None
        phase = "import"
        try:
            client_type, config_type, *types = _sdk()
            phase = "construction"
            client = client_type(
                config_type(
                    codex_bin=str(executable),
                    config_overrides=overrides,
                    env=environment,
                    cwd=str(directory),
                )
            )
            phase = "startup"
            client.start()
            phase = "initialization"
            client.initialize()
            session = FixedCodexSession(
                client, types, directory, environment["OPENAI_BASE_URL"], mcp_command
            )
            session.verify_configuration()
            phase = "test operation"
            yield session
        except CodexTestError:
            raise
        except Exception as error:
            raise CodexTestError(
                f"Codex SDK {phase} failed ({type(error).__name__}); raw diagnostics suppressed"
            ) from None
        finally:
            if client is not None:
                try:
                    client.close()
                except Exception:
                    raise CodexTestError("Codex SDK cleanup failed") from None
