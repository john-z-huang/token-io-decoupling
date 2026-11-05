from typing import Any, cast

from token_io_decoupling_core.server_tools import TOOLS_SERVER_TOOLS, WORKFLOW_TOOLS

from token_io_decoupling.server import create_tools_server, create_workflow_server


def _names(server: object) -> set[str]:
    return {tool.name for tool in cast(Any, server)._tool_manager.list_tools()}


def test_fixed_servers_expose_only_current_stateless_contracts() -> None:
    workflow = create_workflow_server()
    tools = create_tools_server()

    assert _names(workflow) == set(WORKFLOW_TOOLS)
    assert _names(tools) == set(TOOLS_SERVER_TOOLS)
    assert len(WORKFLOW_TOOLS) == 17
    assert len(TOOLS_SERVER_TOOLS) == 34
    retired = {
        "database_schema_status",
        "state_get",
        "record_evidence",
        "workflow_get_state",
        "workflow_reconcile",
        "workflow_open",
    }
    assert not (retired & _names(tools))


def test_default_materialization_is_unavailable_without_trusted_context() -> None:
    server = create_tools_server()
    assert cast(Any, server)._output_materializer is None
