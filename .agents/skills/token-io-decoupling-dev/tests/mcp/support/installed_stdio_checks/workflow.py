"""验证安装后规则、公共能力边界及显式外发许可。"""

from __future__ import annotations

import json

from codex_app_server import validate_compiled_rule_bundle
from mcp import Client

from .protocol import result_text


async def check_capabilities(client: Client) -> None:
    """核对安装服务报告的固定宿主和默认未授权状态，不把发现当作可信运行时绑定。"""
    capabilities = await client.call_tool("workflow_capabilities", {})
    capability_data = json.loads(result_text(capabilities))
    if capabilities.is_error:
        raise AssertionError("installed unbound CLI did not return capability data")
    details = capability_data["capability_details"]
    if (
        details["schema_version"] != 3
        or details["support"]["agent_runtime"]["status"] != "available"
        or details["runtime"]["binding"]["reason_code"] != "provider_not_configured"
        or details["runtime"]["server_mode"]["status"] != "public_only"
        or details["configuration"]["public_interfaces"]["reason_code"]
        != "tool_dependencies_not_probed"
    ):
        raise AssertionError("installed CLI misstated capability boundaries")


async def check_context_denial(client: Client) -> None:
    """向缺少可信宿主绑定的服务请求上下文，必须得到有界拒绝而非可采纳背景。"""
    denied_context = await client.call_tool(
        "workflow_generate_decision_context",
        {
            "payload": {
                "request": {
                    "raw_content": "caller-composed material",
                    "decision_goal": "Create a short question.",
                    "output_kind": "decision_question",
                    "outbound_data_permitted": False,
                }
            }
        },
    )
    if denied_context.is_error:
        raise AssertionError("public decision-context denial returned a tool error")
    denied_data = json.loads(result_text(denied_context))
    if (
        denied_data.get("status") != "blocked"
        or denied_data.get("reason") != "outbound_data_not_permitted"
    ):
        raise AssertionError("unbound installed workflow called without permission")


async def check_rule_instructions(client: Client) -> None:
    """直接读取完整中文 Contract，并检查关键上下文、权限和子级创建约束真实存在。"""
    result = await client.call_tool(
        "rules_get_context",
        {"payload": {"node_id": "contract", "language": "zh_cn", "context_version": 2}},
    )
    if result.is_error:
        raise AssertionError("installed wheel did not return the Chinese Contract rule")
    context = json.loads(result_text(result))
    validate_compiled_rule_bundle(context, "zh_cn")
    delivered_text = "\n".join(fragment["text"] for fragment in context["fragments"])
    expected_actions = (
        "自身对话上下文",
        "任何结果都不独自授权或宣布完成",
        "任务开始不自动初始化子级",
    )
    if any(action not in delivered_text for action in expected_actions):
        raise AssertionError("installed wheel returned incomplete Chinese Contract Actions")
