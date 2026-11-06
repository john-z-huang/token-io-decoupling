from typing import Any, cast

from token_io_decoupling.server import create_tools_server, create_workflow_server
from token_io_decoupling_core.server_tools import TOOLS_SERVER_TOOLS, WORKFLOW_TOOLS


def _names(server: object) -> set[str]:
    return {tool.name for tool in cast(Any, server)._tool_manager.list_tools()}


def test_fixed_servers_expose_only_current_stateless_contracts() -> None:
    workflow = create_workflow_server()
    tools = create_tools_server()

    assert _names(workflow) == set(WORKFLOW_TOOLS)
    assert _names(tools) == set(TOOLS_SERVER_TOOLS)
    assert len(WORKFLOW_TOOLS) == 11
    assert len(TOOLS_SERVER_TOOLS) == 41
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


def test_rule_metadata_describes_compiled_execution_without_owner_followup() -> None:
    from token_io_decoupling_workflow.tool_metadata import tool_description

    description = tool_description("rules_get_context")
    assert "context_version (integer 2" in description
    assert "Version 1 is retired and rejected" in description
    assert "fragments is empty" in description
    assert "not paths to read" in description
    routing = tool_description("decide_decoupling_workflow")
    assert "selected stage's executable text" in routing
    assert "shared_requirements" in routing
    assert "required before any action" in routing
    assert "required when prerequisites are missing" in routing
    assert "matching hash" in routing
    assert "only those units" in routing
    assert "Follow the referenced current route owners" not in routing
