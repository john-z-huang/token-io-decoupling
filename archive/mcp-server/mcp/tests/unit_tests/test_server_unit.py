from typing import Any, cast

from token_io_decoupling_core.server_tools import TOOLS_SERVER_TOOLS

from token_io_decoupling.server import create_tools_server


def _names(server: object) -> set[str]:
    return {tool.name for tool in cast(Any, server)._tool_manager.list_tools()}


def test_fixed_servers_expose_only_current_stateless_contracts() -> None:
    tools = create_tools_server()

    names = _names(tools)
    assert names == set(TOOLS_SERVER_TOOLS)
    assert len(TOOLS_SERVER_TOOLS) == 34
    assert not any(name.startswith(("workflow_", "task_plan_")) for name in names)
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
