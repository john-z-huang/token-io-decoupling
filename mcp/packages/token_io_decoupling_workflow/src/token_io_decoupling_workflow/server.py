"""Workflow-only composition root, independently installable from tools."""

from collections.abc import Callable
from typing import Any

from mcp.server import MCPServer

from token_io_decoupling_core.binding import BindingError, BindingProvider, DenyingBindingProvider
from token_io_decoupling_core.codex_context import CodexCallerBoundProvider
from token_io_decoupling_core.server_tools import WORKFLOW_SERVER_NAME, WORKFLOW_TOOLS
from token_io_decoupling_transport.identity import binding_details, bound_role
from token_io_decoupling_transport.tool import ToolRegistrar
from token_io_decoupling_workflow.capabilities import AdviceAvailability, capability_report
from token_io_decoupling_workflow.decisions import DecisionsAdvisor, DecisionsRuntimeConfig
from token_io_decoupling_workflow.events.advice import EventAdvisor
from token_io_decoupling_workflow.rules import RuleLoader
from token_io_decoupling_workflow.tool import register_tools
from token_io_decoupling_workflow.tool_metadata import (
    tool_description,
    workflow_server_description,
    workflow_server_instructions,
)


def _validate_workflow_inventory(server: MCPServer[Any]) -> None:
    """实际注册清单必须与固定公开契约严格相同。"""
    names = [tool.name for tool in server._tool_manager.list_tools()]
    if len(names) != len(set(names)) or set(names) != WORKFLOW_TOOLS:
        raise ValueError("workflow tool inventory differs from its manifest")


def create_workflow_server(
    binding_provider: BindingProvider | None = None,
    *,
    require_bound: bool = False,
    require_codex_context: bool = False,
    decisions_config: DecisionsRuntimeConfig | None = None,
    decisions_client_factory: Callable[[str, str], object] | None = None,
    event_advice_config: DecisionsRuntimeConfig | None = None,
) -> MCPServer[Any]:
    """在组合根装配静态服务和两个独立建议开关，不在启动时请求模型。"""
    provider = binding_provider or DenyingBindingProvider()
    role = bound_role(provider) if binding_provider is not None else None
    if require_bound and role is None:
        raise BindingError("trusted provider did not supply a usable bound identity")
    if require_codex_context and binding_provider is not None and role is None:
        raise BindingError("Codex caller matching requires a usable bound identity")
    server = MCPServer(
        name=WORKFLOW_SERVER_NAME,
        version="0.1.0",
        description=workflow_server_description(),
        instructions=workflow_server_instructions(),
    )
    rules = RuleLoader()
    config = decisions_config or DecisionsRuntimeConfig()
    event_config = event_advice_config or DecisionsRuntimeConfig()
    registrar = ToolRegistrar(
        server,
        provider=provider,
        state_provider=CodexCallerBoundProvider(provider) if require_codex_context else provider,
        allowed_tools=WORKFLOW_TOOLS,
        require_codex_context=require_codex_context,
        bound_role_for=bound_role,
        description_for=tool_description,
    )
    register_tools(
        registrar,
        rules=rules,
        advisor=DecisionsAdvisor(rules, config, client_factory=decisions_client_factory),
        event_advisor=EventAdvisor(rules, event_config, client_factory=decisions_client_factory),
        capability_callback=lambda: capability_report(
            provider,
            embedded=role is not None,
            require_codex_context=require_codex_context,
            advice=AdviceAvailability(checkpoint=config.enabled, event=event_config.enabled),
            diagnose_binding=binding_details,
        ),
    )
    _validate_workflow_inventory(server)
    return server
