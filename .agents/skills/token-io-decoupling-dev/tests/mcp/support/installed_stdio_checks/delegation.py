"""对四个独立委派建议接口使用相同的外发拒绝契约。"""

from __future__ import annotations

import json
import re

from mcp import Client

from .protocol import result_text

COMMON_FACTS = {
    "task_id": "installed-stdio-delegation-smoke",
    "task_summary": "Synthetic smoke check for delegation advice.",
    "reviewed_context": ("Synthetic bounded facts only; no user data or repository content."),
    "context_input_hash": "a" * 64,
    "fact_revision": 0,
    "fact_fingerprint": "b" * 64,
    "forked_session": False,
    "mode_reselected_after_fork": True,
    "outbound_data_permitted": False,
    "mode": "Multi-Agent Coding",
}
DELEGATION_CALLS = (
    (
        "workflow_select_child_role",
        "child_role",
        {
            "created_roles": [],
            "reserved_roles": [],
            "available_slots": 1,
            "user_explicit_create_instruction": False,
        },
    ),
    (
        "workflow_select_executor",
        "executor",
        {"current_session_child_count": 1, "available_slots": 0},
    ),
    (
        "workflow_select_child",
        "child_candidate",
        {
            "candidates": [
                {
                    "candidate_ref": "primary-output-1",
                    "role": "Primary Output",
                    "responsibility_match": True,
                    "capability_match": True,
                    "permission_allows": True,
                    "same_current_session": True,
                    "availability": "idle",
                    "responsibility_summary": "Owns the released slice.",
                    "capability_summary": "Implementation tools are available.",
                    "permission_summary": "Slice permits the listed paths.",
                    "task_relevant_context": "Has the current task facts.",
                },
                {
                    "candidate_ref": "context-refresh-1",
                    "role": "Context Bootstrap/Refresh",
                    "responsibility_match": True,
                    "capability_match": True,
                    "permission_allows": True,
                    "same_current_session": True,
                    "availability": "idle",
                    "responsibility_summary": "Owns bounded context refresh.",
                    "capability_summary": "Context lookup tools are available.",
                    "permission_summary": "Slice permits the lookup paths.",
                    "task_relevant_context": "Has current source notes.",
                },
            ]
        },
    ),
    (
        "workflow_assess_output_tokens",
        "output_tokens",
        {
            "requested_output_shape": "A concise installed-launcher smoke result.",
            "expected_output_volume": "One short status summary.",
            "idle_suitable_child_count": 1,
            "busy_suitable_child_count": 0,
        },
    ),
)


async def check_delegation_denials(client: Client) -> None:
    """用真实 stdio 验证委派安全拒绝及政策身份，未知候选、容量和职责不能获得放行。"""
    for tool_name, expected_decision, specific_facts in DELEGATION_CALLS:
        result = await client.call_tool(
            tool_name,
            {"payload": {"request": {**COMMON_FACTS, **specific_facts}}},
        )
        if result.is_error:
            raise AssertionError(f"installed {tool_name} outbound denial returned a tool error")
        decision_data = json.loads(result_text(result))
        if (
            decision_data.get("status") != "blocked"
            or decision_data.get("reason") != "outbound_data_not_permitted"
            or decision_data.get("decision") != expected_decision
        ):
            raise AssertionError(
                f"installed {tool_name} did not return its expected outbound denial"
            )
        source_policy_hashes = decision_data.get("source_policy_hashes")
        if (
            not isinstance(source_policy_hashes, dict)
            or not source_policy_hashes
            or any(
                not isinstance(value, str) or not re.fullmatch(r"[0-9a-fA-F]{64}", value)
                for value in source_policy_hashes.values()
            )
        ):
            raise AssertionError(f"installed {tool_name} did not return loaded owner policy hashes")
