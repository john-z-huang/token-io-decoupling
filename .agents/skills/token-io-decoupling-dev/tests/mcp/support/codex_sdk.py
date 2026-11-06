"""Test-only Codex SDK boundary. No configurable model, effort or credentials."""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from contextlib import contextmanager
from pathlib import Path

from token_io_decoupling_core.server_tools import (
    TOOLS_SERVER_NAME,
    TOOLS_SERVER_TOOLS,
    WORKFLOW_SERVER_NAME,
    WORKFLOW_TOOLS,
)

MODEL = "gpt-6-luna"
EFFORT = "medium"
PROVIDER = "token_io_test"
_FINAL_INSPECTION = object()
INVENTORIES = {WORKFLOW_SERVER_NAME: WORKFLOW_TOOLS, TOOLS_SERVER_NAME: TOOLS_SERVER_TOOLS}


class CodexTestError(RuntimeError):
    """Safe failure without SDK stderr, configuration values or credential data."""


def _standard_capability_diagnostics(report):
    details = report.get("capability_details")
    if (
        report.get("agent_runtime") != "codex_cli"
        or not isinstance(details, dict)
        or details.get("schema_version") != 3
    ):
        raise CodexTestError("fresh CLI returned an unsupported capability schema")
    support = details.get("support")
    runtime = details.get("runtime")
    configuration = details.get("configuration")
    if not all(isinstance(value, dict) for value in (support, runtime, configuration)):
        raise CodexTestError("fresh CLI omitted required capability sections")
    identity = support.get("identity_bound_operations")
    binding = runtime.get("binding")
    server_mode = runtime.get("server_mode")
    materialization = configuration.get("output_materialization")
    if not all(
        isinstance(value, dict) for value in (identity, binding, server_mode, materialization)
    ):
        raise CodexTestError("fresh CLI omitted default protection diagnostics")
    if (
        identity.get("status") != "unavailable"
        or identity.get("reason_code") != "trusted_provider_not_configured"
        or binding.get("status") != "unverified"
        or binding.get("reason_code") != "provider_not_configured"
        or server_mode.get("status") != "public_only"
        or server_mode.get("reason_code") != "startup_binding_unverified"
        or "no caller identity" not in server_mode.get("message", "").lower()
        or "workflow state store" not in server_mode.get("message", "").lower()
        or materialization.get("status") != "unavailable"
        or materialization.get("reason_code") != "output_materializer_not_configured"
        or report.get("trusted_binding") != "unverified"
    ):
        raise CodexTestError("fresh CLI omitted stateless/default-protection diagnostics")
    return {
        "capability_schema_version": details["schema_version"],
        "trusted_binding": report["trusted_binding"],
        "binding_reason": binding["reason_code"],
        "server_mode": server_mode["status"],
        "materialization": materialization["status"],
    }


def validate_compiled_rule_bundle(context, language):
    """Check bounded delivered instructions without accessing the author tree or SDK."""
    metadata = context.get("node_metadata")
    fragments = context.get("fragments")
    if (
        context.get("schema_version") != 2
        or context.get("node_id") != "contract"
        or context.get("language") != language
        or context.get("complete") is not True
        or context.get("status") != "complete"
        or context.get("remaining_owner_refs") != []
        or context.get("remaining_owner_refs_truncated") is not False
        or not isinstance(metadata, dict)
        or metadata.get("next_checkpoint_ids") != ["mode"]
        or not metadata.get("owner_path", "").startswith("compiled:")
        or not isinstance(fragments, list)
        or not fragments
    ):
        raise CodexTestError("unexpected compiled MCP instruction bundle")
    for field in ("build_id", "context_hash"):
        if not isinstance(context.get(field), str) or not re.fullmatch(
            r"[0-9a-f]{64}", context[field]
        ):
            raise CodexTestError("invalid compiled MCP instruction identity")
    for fragment in fragments:
        text = fragment.get("text")
        if (
            not isinstance(text, str)
            or not text.strip()
            or not fragment.get("owner_path", "").startswith("compiled:")
            or fragment.get("text_sha256") != hashlib.sha256(text.encode("utf-8")).hexdigest()
        ):
            raise CodexTestError("incomplete or corrupt compiled MCP instruction text")
    total = sum(len(fragment["text"]) for fragment in fragments)
    if (
        context.get("text_characters") != total
        or context.get("required_text_characters") != total
        or type(context.get("text_budget")) is not int
        or total > context["text_budget"]
        or context.get("required_fragment_ids")
        != [fragment.get("fragment_id") for fragment in fragments]
    ):
        raise CodexTestError("compiled MCP instruction budget/completeness mismatch")
    return context["build_id"]


def launch_settings(executable: Path, directory: Path, bin_dir: Path):
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
        + ",".join(
            f"{name}={{command={json.dumps(str(bin_dir / name))},"
            "args=[],env_vars=[],startup_timeout_sec=30}"
            for name in INVENTORIES
        )
        + "}",
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
    def __init__(self, client, types, directory, base_url, bin_dir=None):
        self._client = client
        self._types = types
        self._directory = directory
        self._base_url = base_url
        self._thread_id = None
        self._bin_dir = bin_dir

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

    def _check_version(self, executable):
        command = self._client.request(
            "command/exec",
            {
                "command": [str(executable), "--version"],
                "cwd": str(self._directory),
                "sandboxPolicy": {"type": "readOnly"},
                "timeoutMs": 10000,
            },
            response_model=self._types[3],
        )
        if command.exit_code != 0 or not command.stdout.startswith(f"{executable.name} "):
            # Report only fixed classifications; SDK stdout/stderr can contain secrets.
            diagnostic = (command.stderr or "").lower()
            permission_denied = (
                "operation not permitted" in diagnostic or "permission denied" in diagnostic
            )
            import_error = "modulenotfounderror" in diagnostic or "importerror" in diagnostic
            raise CodexTestError(
                "installed MCP executable version check failed "
                f"(exit={command.exit_code}, "
                f"permission_denied={permission_denied}, "
                f"missing_file={'no such file' in diagnostic}, "
                f"import_error={import_error})"
            )

    def check_mcp(self):
        self.verify_configuration()
        if self._bin_dir is None:
            raise CodexTestError("newly installed MCP bin directory is required")
        for name in INVENTORIES:
            self._check_version(self._bin_dir / name)
        self.start_thread()
        for name, expected in INVENTORIES.items():
            status = self._client.request(
                "mcpServerStatus/list",
                {
                    "threadId": self._thread_id,
                    "serverName": name,
                    "detail": "toolsAndAuthOnly",
                },
                response_model=self._types[1],
            )
            servers = [server for server in status.data if server.name == name]
            if len(servers) != 1 or set(servers[0].tools) != expected:
                raise CodexTestError(f"installed MCP inventory mismatch: {name}")
        result = self._client.request(
            "mcpServer/tool/call",
            {
                "threadId": self._thread_id,
                "server": WORKFLOW_SERVER_NAME,
                "tool": "workflow_capabilities",
                "arguments": {},
            },
            response_model=self._types[2],
        )
        if result.is_error:
            raise CodexTestError("MCP capabilities call failed")
        report = json.loads(result.content[0]["text"])
        diagnostics = _standard_capability_diagnostics(report)
        instruction_build_id = None
        for language in ("en", "zh_cn"):
            rules = self._client.request(
                "mcpServer/tool/call",
                {
                    "threadId": self._thread_id,
                    "server": WORKFLOW_SERVER_NAME,
                    "tool": "rules_get_context",
                    "arguments": {
                        "payload": {
                            "node_id": "contract",
                            "language": language,
                            "context_version": 2,
                        }
                    },
                },
                response_model=self._types[2],
            )
            if rules.is_error:
                raise CodexTestError("packaged MCP rule lookup failed")
            context = json.loads(rules.content[0]["text"])
            build_id = validate_compiled_rule_bundle(context, language)
            if instruction_build_id is not None and build_id != instruction_build_id:
                raise CodexTestError("mixed-build bilingual MCP instruction resources")
            instruction_build_id = build_id
        return {
            "model": MODEL,
            "effort": EFFORT,
            "mcp": "passed",
            "inventories": {name: len(tools) for name, tools in INVENTORIES.items()},
            "model_turns": 0,
            "instruction_schema_version": 2,
            "instruction_build_id": instruction_build_id,
            **diagnostics,
        }


@contextmanager
def fixed_codex_session(executable: Path, bin_dir: Path, *, phase=None):
    if phase is not _FINAL_INSPECTION:
        raise CodexTestError("SDK launch is restricted to the final post-install inspection phase")
    # No SDK launch or dependency import until both existing values are verified.
    with tempfile.TemporaryDirectory(prefix="token-io-sdk-test-") as temporary:
        directory = Path(temporary)
        overrides, environment = launch_settings(executable, directory, bin_dir)
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
                client, types, directory, environment["OPENAI_BASE_URL"], bin_dir
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
