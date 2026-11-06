from mcp.server import MCPServer

from token_io_decoupling.server import create_tools_server, create_workflow_server
from token_io_decoupling_core.server_tools import TOOLS_SERVER_TOOLS, WORKFLOW_TOOLS


def _names(server: MCPServer[object]) -> set[str]:
    return {tool.name for tool in server._tool_manager.list_tools()}


def test_fixed_servers_expose_only_current_stateless_contracts() -> None:
    """真实注册清单必须精确为 workflow 11 项和 tools 41 项，且不复活已移除的状态 API。"""
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
    """默认实例没有可信物化配置，不能因为 tools 服务可用就获得写入能力。"""
    server = create_tools_server()
    assert server._output_materializer is None


def test_rule_metadata_describes_compiled_execution_without_owner_followup() -> None:
    """工具说明须准确暴露版本、完整交付和非权威边界，不能引导回读作者源。"""
    from token_io_decoupling_workflow.tool_metadata import tool_description

    description = tool_description("rules_get_context")
    assert "context_version（整数2" in description
    assert "版本1已退役并拒绝" in description
    assert "fragments=[]" in description
    assert "不是待打开路径" in description
    assert "language（仅 zh_cn，默认 zh_cn）" in description
    event = tool_description("workflow_check_event")
    assert "不保存状态" in event
    assert "结构" in event
    assert "continue 不表示验收完成" in event
    assert "阶段" in event
    assert "task_received" in event
