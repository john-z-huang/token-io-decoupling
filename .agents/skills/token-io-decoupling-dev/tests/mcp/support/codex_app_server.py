"""仅测试使用的 Codex App Server 边界，固定模型、强度与凭据来源。"""

from __future__ import annotations

import json
import os
import tempfile
from contextlib import contextmanager
from pathlib import Path

if __package__:
    from . import compiled_instruction_checks
    from .codex_app_server_rpc import AppServerClient
else:
    import compiled_instruction_checks
    from codex_app_server_rpc import AppServerClient

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
RESOURCE_INSPECTION = """
import hashlib
import json
from importlib.resources import files
root = files('token_io_decoupling_workflow').joinpath('_resources')
raw = root.joinpath('instructions.json').read_bytes()
document = json.loads(raw)
manifest = json.loads(root.joinpath('manifest.json').read_bytes())
assert manifest['files']['instructions.json'] == hashlib.sha256(raw).hexdigest()
assert document['build_id'] == manifest['build_id']
assert document['schema_version'] == manifest['schema_version'] == 3
assert document['language'] == manifest['language'] == 'zh_cn'
print(json.dumps({key: document[key] for key in ('schema_version', 'language', 'build_id')}))
"""


class CodexTestError(RuntimeError):
    """安全错误不包含 App Server stderr、配置值或凭据。"""


def _standard_capability_diagnostics(report):
    """核对全新安装的未绑定身份与无状态诊断，文案和机器分类均须符合当前契约。"""
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
    if not all(isinstance(value, dict) for value in (identity, binding, server_mode)):
        raise CodexTestError("fresh CLI omitted default protection diagnostics")
    if (
        identity.get("status") != "unavailable"
        or identity.get("reason_code") != "workflow_has_no_identity_bound_operations"
        or binding.get("status") != "unverified"
        or binding.get("reason_code") != "provider_not_configured"
        or server_mode.get("status") != "public_only"
        or server_mode.get("reason_code") != "startup_binding_unverified"
        or "不建立调用方身份" not in server_mode.get("message", "")
        or "workflow 状态存储" not in server_mode.get("message", "")
        or "task_plan_tools" in configuration
        or "serena_memory_reads" in configuration
        or "output_materialization" in configuration
        or report.get("trusted_binding") != "unverified"
    ):
        raise CodexTestError("fresh CLI omitted stateless/default-protection diagnostics")
    return {
        "capability_schema_version": details["schema_version"],
        "trusted_binding": report["trusted_binding"],
        "binding_reason": binding["reason_code"],
        "server_mode": server_mode["status"],
        "materialization": "separate_service",
    }


def validate_compiled_rule_bundle(context, language):
    """把交付校验失败转换为App Server 检验边界错误。"""
    try:
        return compiled_instruction_checks.validate_compiled_rule_bundle(context, language)
    except compiled_instruction_checks.CompiledInstructionError as exc:
        raise CodexTestError(str(exc)) from exc


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
    # 子进程覆盖这些环境项，隔离配置、认证和插件状态。
    environment = {
        "OPENAI_API_KEY": key,
        "OPENAI_BASE_URL": base_url,
        "HOME": str(directory),
        "CODEX_HOME": str(directory / ".codex"),
        "PYTHONPATH": "",
    }
    return overrides, environment


class FixedCodexSession:
    """只在最终安装检验阶段使用的 App Server 会话，限制配置、工具清单与零模型轮次。"""

    def __init__(self, client, directory, base_url, bin_dir=None):
        self._client = client
        self._directory = directory
        self._base_url = base_url
        self._thread_id = None
        self._bin_dir = bin_dir

    def verify_configuration(self):
        config = self._client.request("config/read", {"includeLayers": False})["config"]
        if (
            config.get("model") != MODEL
            or config.get("model_provider") != PROVIDER
            or config.get("model_reasoning_effort") != EFFORT
        ):
            raise CodexTestError("effective model/provider/effort violates test policy")
        providers = config.get("model_providers", {})
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
        started = self._client.request(
            "thread/start",
            {
                "cwd": str(self._directory),
                "ephemeral": True,
                "model": MODEL,
                "modelProvider": PROVIDER,
                "config": {"model_reasoning_effort": EFFORT},
                "approvalPolicy": "never",
                "sandbox": "read-only",
            },
        )
        if (
            started.get("model") != MODEL
            or started.get("modelProvider") != PROVIDER
            or started.get("reasoningEffort") != EFFORT
        ):
            raise CodexTestError("thread model/provider/effort violates test policy")
        self._thread_id = started["thread"]["id"]

    def _check_version(self, executable):
        command = self._client.request(
            "command/exec",
            {
                "command": [str(executable), "--version"],
                "cwd": str(self._directory),
                "sandboxPolicy": {"type": "readOnly"},
                "timeoutMs": 10000,
            },
        )
        if command["exitCode"] != 0 or not command["stdout"].startswith(f"{executable.name} "):
            # Report only fixed classifications; App Server stdout/stderr can contain secrets.
            diagnostic = (command["stderr"] or "").lower()
            permission_denied = (
                "operation not permitted" in diagnostic or "permission denied" in diagnostic
            )
            import_error = "modulenotfounderror" in diagnostic or "importerror" in diagnostic
            raise CodexTestError(
                "installed MCP executable version check failed "
                f"(exit={command['exitCode']}, "
                f"permission_denied={permission_denied}, "
                f"missing_file={'no such file' in diagnostic}, "
                f"import_error={import_error})"
            )

    def _check_inventory(self):
        """逐服务核对实际 App Server 发现结果，不能只凭版本号推断工具已经可用。"""
        for name, expected in INVENTORIES.items():
            status = self._client.request(
                "mcpServerStatus/list",
                {"threadId": self._thread_id, "serverName": name, "detail": "toolsAndAuthOnly"},
            )
            servers = [server for server in status["data"] if server["name"] == name]
            if len(servers) != 1 or set(servers[0]["tools"]) != expected:
                raise CodexTestError(f"installed MCP inventory mismatch: {name}")

    def _capability_report(self):
        """只调用固定的无副作用能力诊断，不暴露任意工具调用通道。"""
        result = self._client.request(
            "mcpServer/tool/call",
            {
                "threadId": self._thread_id,
                "server": WORKFLOW_SERVER_NAME,
                "tool": "workflow_capabilities",
                "arguments": {},
            },
        )
        if result.get("isError"):
            raise CodexTestError("packaged MCP capabilities inspection failed")
        return json.loads(result["content"][0]["text"])

    def _contract_bundle(self):
        """通过实际安装的 MCP 读取中文 Contract，保持外部 context_version 为2。"""
        result = self._client.request(
            "mcpServer/tool/call",
            {
                "threadId": self._thread_id,
                "server": WORKFLOW_SERVER_NAME,
                "tool": "rules_get_context",
                "arguments": {
                    "payload": {"node_id": "contract", "language": "zh_cn", "context_version": 2}
                },
            },
        )
        if result.get("isError"):
            raise CodexTestError("packaged MCP Contract inspection failed")
        return json.loads(result["content"][0]["text"])

    def _check_resource_identity(self, build_id):
        """核对实际安装资源的哈希、schema 3 与同批 build，区分外部 bundle 2。"""
        if self._bin_dir is None:
            raise CodexTestError("newly installed MCP bin directory is required")
        python = (self._bin_dir / WORKFLOW_SERVER_NAME).resolve().parent / "python"
        command = self._client.request(
            "command/exec",
            {
                "command": [str(python), "-c", RESOURCE_INSPECTION],
                "cwd": str(self._directory),
                "sandboxPolicy": {"type": "readOnly"},
                "timeoutMs": 10000,
            },
        )
        if command["exitCode"] != 0:
            raise CodexTestError("installed instruction resource inspection failed")
        identity = json.loads(command["stdout"])
        if identity != {"schema_version": 3, "language": "zh_cn", "build_id": build_id}:
            raise CodexTestError("installed instruction resource identity mismatch")

    def check_mcp(self):
        """先验证固定配置与发现，再核对交付正文和安装资源；全过程不启动模型轮次。"""
        self.verify_configuration()
        if self._bin_dir is None:
            raise CodexTestError("newly installed MCP bin directory is required")
        for name in INVENTORIES:
            self._check_version(self._bin_dir / name)
        self.start_thread()
        self._check_inventory()
        diagnostics = _standard_capability_diagnostics(self._capability_report())
        context = self._contract_bundle()
        instruction_build_id = validate_compiled_rule_bundle(context, "zh_cn")
        self._check_resource_identity(instruction_build_id)
        return {
            "model": MODEL,
            "effort": EFFORT,
            "mcp": "passed",
            "inventories": {name: len(tools) for name, tools in INVENTORIES.items()},
            "model_turns": 0,
            "context_schema_version": 2,
            "resource_schema_version": 3,
            "instruction_build_id": instruction_build_id,
            **diagnostics,
        }


@contextmanager
def fixed_codex_session(executable: Path, bin_dir: Path, *, phase=None):
    if phase is not _FINAL_INSPECTION:
        raise CodexTestError(
            "App Server launch is restricted to the final post-install inspection phase"
        )
    # 在校验必需进程变量之前，不启动 App Server。
    with tempfile.TemporaryDirectory(prefix="token-io-app-server-test-") as temporary:
        directory = Path(temporary)
        overrides, environment = launch_settings(executable, directory, bin_dir)
        # Codex requires an explicitly configured CODEX_HOME to already exist.
        Path(environment["CODEX_HOME"]).mkdir()
        client = None
        phase = "configuration"
        try:
            phase = "startup"
            client = AppServerClient(executable, overrides, environment, directory)
            phase = "initialization"
            client.initialize()
            session = FixedCodexSession(client, directory, environment["OPENAI_BASE_URL"], bin_dir)
            session.verify_configuration()
            phase = "test operation"
            yield session
        except CodexTestError:
            raise
        except Exception as error:
            raise CodexTestError(
                f"Codex App Server {phase} failed ({type(error).__name__}); "
                "raw diagnostics suppressed"
            ) from None
        finally:
            if client is not None:
                try:
                    client.close()
                except Exception:
                    raise CodexTestError("Codex App Server cleanup failed") from None
