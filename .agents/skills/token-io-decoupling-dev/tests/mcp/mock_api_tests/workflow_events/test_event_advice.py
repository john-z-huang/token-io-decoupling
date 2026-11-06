"""验证可选模型建议的权限、失败与新鲜度边界。"""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest
from support.event_cases import FakeClient, checker, request, response

from token_io_decoupling_workflow.decisions import DECISIONS_MODEL
from token_io_decoupling_workflow.rules import RuleLoader


@pytest.fixture
def mock_credentials(monkeypatch):
    """仅提供合成凭据，所有模型边界由测试客户端接管。"""
    monkeypatch.setenv("OPENAI_API_KEY", "test-event-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://events.example.invalid/v1")


@pytest.mark.usefixtures("mock_credentials")
@pytest.mark.parametrize(
    "outcome", ["continue", "needs_evidence", "amend", "wait", "stop", "not_applicable"]
)
def test_documented_model_outcomes_are_advice_without_authority_or_stage(outcome):
    """每个文档允许结果都只是建议，不授予权限、不推进阶段且不伪造语义理由。"""
    client = FakeClient(response(outcome))
    result = checker(enabled=True, outbound=True, client=client).check(
        request("completion_requested", semantic_input={"outbound_data_permitted": True})
    )
    assert result.status == "checked"
    assert result.advice.status == "available"
    assert result.advice.suggested_outcome == outcome
    assert result.advice.authority == "advisory_only"
    assert result.advice.total_tokens == 17
    assert result.advice.input_hash
    assert result.advice.rule_hash
    assert "stage" not in result.model_dump()
    assert len(client.calls) == 1
    assert client.closed
    call = client.calls[0]
    assert call["model"] == DECISIONS_MODEL
    supplied = json.loads(call["input"])
    assert supplied["approved_hook_instructions"] == result.instructions.event.text
    assert supplied["selected_workflow_instructions"] is None
    assert "未核实数据" in call["questions"][0]["instructions"]
    assert "test-event-key" not in call["input"]


@pytest.mark.usefixtures("mock_credentials")
@pytest.mark.parametrize(
    "enabled,outbound,permission,reason",
    [
        (False, True, True, "disabled"),
        (True, True, False, "outbound_data_not_permitted"),
    ],
)
def test_both_host_and_per_call_permissions_are_required(enabled, outbound, permission, reason):
    """宿主开关与当次外发许可缺一不可，未满足时不能创建模型请求。"""
    client = FakeClient()
    result = checker(enabled=enabled, outbound=outbound, client=client).check(
        request(semantic_input={"outbound_data_permitted": permission})
    )
    assert result.instructions.complete
    assert result.advice.status == "unavailable"
    assert result.advice.reason == reason
    assert result.advice.suggested_outcome is None
    assert client.calls == []
    assert not client.closed


@pytest.mark.parametrize("missing", ["OPENAI_API_KEY", "OPENAI_BASE_URL"])
def test_empty_credentials_do_not_create_client(monkeypatch, missing):
    """空白凭据应在客户端构造前拒绝，静态指令仍可交付。"""
    monkeypatch.setenv("OPENAI_API_KEY", "mock-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://example.invalid/v1")
    monkeypatch.setenv(missing, "  ")
    client = FakeClient()
    result = checker(enabled=True, outbound=True, client=client).check(
        request(semantic_input={"outbound_data_permitted": True})
    )
    assert result.advice.reason == "missing_credentials"
    assert result.advice.suggested_outcome is None
    assert client.calls == []


@pytest.mark.usefixtures("mock_credentials")
@pytest.mark.parametrize(
    "invalid_response",
    [
        response("invented_success"),
        response(model="another-model"),
        response(status="incomplete"),
        response(status=None),
        response(status="invented_success"),
        response(error={"code": "mock_failure"}),
        response(incomplete_details={"reason": "limit"}),
        response(usage=SimpleNamespace(total_tokens=-1)),
        response(usage=SimpleNamespace(total_tokens=True)),
        response(answers=[]),
        response(answers=[SimpleNamespace(type="refusal", name="workflow_event_outcome")]),
        response(
            answers=[SimpleNamespace(type="choice", name="wrong-question", choice="continue")]
        ),
        response(
            answers=[
                SimpleNamespace(type="choice", name="workflow_event_outcome", choice="continue")
            ]
            * 2
        ),
    ],
)
def test_invalid_or_refused_model_responses_never_become_continue(invalid_response):
    """拒绝或格式错误的模型返回不能退化成 continue。"""
    client = FakeClient(invalid_response)
    result = checker(enabled=True, outbound=True, client=client).check(
        request(semantic_input={"outbound_data_permitted": True})
    )
    assert result.advice.status == "unavailable"
    assert result.advice.reason in {"invalid_response", "refusal"}
    assert result.advice.suggested_outcome is None
    assert client.closed


@pytest.mark.usefixtures("mock_credentials")
def test_provider_failure_keeps_static_rules_and_names_recovery_without_fake_pass():
    """模型故障保留静态规则并说明恢复方式，不能把不可用建议当成通过。"""
    client = FakeClient(error=TimeoutError("mock timeout"))
    result = checker(enabled=True, outbound=True, client=client).check(
        request(semantic_input={"outbound_data_permitted": True})
    )
    assert result.status == "checked"
    assert result.instructions.complete
    assert result.advice.status == "unavailable"
    assert result.advice.suggested_outcome is None
    assert result.advice.failure_class is not None
    assert result.advice.recovery is not None
    assert client.closed


@pytest.mark.usefixtures("mock_credentials")
def test_rule_change_during_model_call_invalidates_advice(monkeypatch):
    """请求期间批准规则改变时，旧输入上的建议必须标为陈旧。"""
    rules = RuleLoader()
    original = rules.load_event

    def change_rules():
        """在模型边界注入一次规则变化，模拟请求与采纳之间的版本竞争。"""

        def changed(*args, **kwargs):
            """返回变更后的规则身份，让采纳前的新鲜度检查观察到差异。"""
            return original(*args, **kwargs).model_copy(update={"rule_hash": "0" * 64})

        monkeypatch.setattr(rules, "load_event", changed)

    client = FakeClient(callback=change_rules)
    result = checker(rules=rules, enabled=True, outbound=True, client=client).check(
        request(semantic_input={"outbound_data_permitted": True})
    )
    assert result.advice.status == "stale"
    assert result.advice.suggested_outcome is None
    assert client.closed


@pytest.mark.usefixtures("mock_credentials")
def test_restored_context_gap_is_sent_to_the_model_as_a_gap():
    """恢复场景中的未知上下文必须如实传给模型，不能补成已通过状态。"""
    client = FakeClient(response("needs_evidence"))
    result = checker(enabled=True, outbound=True, client=client).check(
        request("session_resumed", facts={}, semantic_input={"outbound_data_permitted": True})
    )
    supplied = json.loads(client.calls[0]["input"])
    assert supplied["supplied_facts"] == {}
    assert supplied["structural_check"]["missing_facts"] == [
        "retained_context",
        "pending_work",
        "effect_status",
    ]
    assert result.structural_check.status == "incomplete_for_agent_review"
    assert result.advice.suggested_outcome == "needs_evidence"


@pytest.mark.usefixtures("mock_credentials")
def test_advice_request_larger_than_documented_bound_makes_no_client_call():
    """合法有界事实合成后超过建议请求上限时，必须在外发前拒绝。"""
    client = FakeClient()
    result = checker(enabled=True, outbound=True, client=client).check(
        request(
            "boundary_requested",
            context_summary="x" * 8000,
            facts={"objective": {"value": "y" * 15000}, "constraint": {"value": "z" * 7000}},
            semantic_input={"outbound_data_permitted": True},
        )
    )
    assert result.advice.reason == "request_exceeds_supported_bound"
    assert result.advice.suggested_outcome is None
    assert client.calls == []


def test_enabling_host_advice_without_outbound_permission_is_rejected():
    """不能配置成建议已启用但缺少宿主外发许可的矛盾状态。"""
    from pydantic import ValidationError

    from token_io_decoupling_workflow.decisions import DecisionsRuntimeConfig

    with pytest.raises(ValidationError, match="explicit outbound data permission"):
        DecisionsRuntimeConfig(enabled=True, outbound_data_permitted=False)


@pytest.mark.usefixtures("mock_credentials")
def test_sdk_response_without_optional_status_is_accepted():
    """第三方响应的可选 status 缺失时，仍按实际选择内容判定合法性。"""
    sdk_response = response("wait")
    del sdk_response.status
    del sdk_response.error
    del sdk_response.incomplete_details
    client = FakeClient(sdk_response)
    result = checker(enabled=True, outbound=True, client=client).check(
        request(semantic_input={"outbound_data_permitted": True})
    )
    assert result.advice.status == "available"
    assert result.advice.suggested_outcome == "wait"
    assert client.closed


@pytest.mark.usefixtures("mock_credentials")
def test_client_close_failure_remains_observable_and_does_not_accept_advice():
    """即使模型已经返回选择，关闭异常也必须可见且使建议不可采纳。"""

    class BrokenCloseClient(FakeClient):
        """只在关闭阶段故障的替身，用于隔离清理失败与请求失败。"""

        def close(self):
            """抛出带私密诊断的关闭故障，验证外层只暴露固定分类。"""
            raise RuntimeError("mock private close failure")

    client = BrokenCloseClient()
    result = checker(enabled=True, outbound=True, client=client).check(
        request(semantic_input={"outbound_data_permitted": True})
    )
    assert result.advice.status == "unavailable"
    assert result.advice.suggested_outcome is None
    assert result.advice.reason == "provider_error"
    assert result.advice.recovery.action == "stop_and_review"
    assert "mock private" not in result.model_dump_json()
