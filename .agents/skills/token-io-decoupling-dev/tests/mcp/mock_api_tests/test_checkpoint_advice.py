"""检查旧 checkpoint 建议的请求与资源释放故障，禁止把故障结果当作建议。"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from token_io_decoupling_core.workflow_models import CheckpointNode
from token_io_decoupling_workflow.decisions import (
    DECISIONS_MODEL,
    DecisionAdvice,
    DecisionsAdvisor,
    DecisionsRuntimeConfig,
    TaskIntentInput,
)
from token_io_decoupling_workflow.rules import RuleLoader


class CheckpointClient:
    """可控的旧检查点客户端，只替换模型边界并记录请求与关闭次数。"""

    def __init__(
        self, *, request_error: Exception | None = None, close_error: Exception | None = None
    ) -> None:
        """为请求或关闭阶段注入独立故障，不模拟规则加载或截断政策。"""
        self.request_error = request_error
        self.close_error = close_error
        self.close_calls = 0
        self.requests: list[dict[str, object]] = []
        self.decisions = self

    def create(self, **kwargs: object) -> SimpleNamespace:
        """记录一次真实构造的请求，再返回合法选择或抛出指定供应商故障。"""
        self.requests.append(kwargs)
        if self.request_error is not None:
            raise self.request_error
        return SimpleNamespace(
            model=DECISIONS_MODEL,
            answers=[SimpleNamespace(type="choice", name="task_intent", choice="coding")],
            usage=SimpleNamespace(total_tokens=13),
        )

    def close(self) -> None:
        """记录清理动作，允许验证关闭失败不会被包装成建议成功。"""
        self.close_calls += 1
        if self.close_error is not None:
            raise self.close_error


@pytest.fixture
def checkpoint_request(monkeypatch: pytest.MonkeyPatch) -> TaskIntentInput:
    """提供合法 task_intent 语义输入，避免失败原因被无关字段校验覆盖。"""
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-checkpoint-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://checkpoint.example.invalid/v1")
    return TaskIntentInput(
        node_id=CheckpointNode.TASK_INTENT,
        requested_outcome="Review a bounded source change.",
        task_signal="coding",
    )


def checkpoint_advice(client: CheckpointClient, request: TaskIntentInput) -> DecisionAdvice:
    """使用真实中文规则和当前哈希调用旧建议接口，只替换外部客户端。"""
    rules = RuleLoader()
    advisor = DecisionsAdvisor(
        rules,
        DecisionsRuntimeConfig(enabled=True, outbound_data_permitted=True),
        client_factory=lambda _key, _url: client,
    )
    return advisor.advise(
        request,
        current_facts={"user-requested outcome": request.requested_outcome, "task type": "coding"},
        checkpoint_source_input_hash="a" * 64,
        language="zh_cn",
        expected_rule_hash=rules.load_context("task_intent", language="zh_cn").context_hash,
    )


def test_successful_checkpoint_request_closes_client_before_advice(checkpoint_request):
    """合法选择只有在客户端正常关闭后才成为可用建议。"""
    client = CheckpointClient()

    result = checkpoint_advice(client, checkpoint_request)

    assert result.status == "available"
    assert result.suggested_choice == "coding"
    assert result.total_tokens == 13
    assert client.close_calls == 1
    assert len(client.requests) == 1


def test_checkpoint_request_failure_closes_client_and_preserves_recovery(checkpoint_request):
    """瞬态请求失败仍关闭客户端，并保留分类恢复建议而不自动重试。"""
    client = CheckpointClient(request_error=TimeoutError("private request timeout"))

    result = checkpoint_advice(client, checkpoint_request)

    assert result.status == "fallback"
    assert result.suggested_choice is None
    assert result.reason == "timeout"
    assert result.failure_class == "transport"
    assert result.recovery is not None
    assert result.recovery.action == "review_then_optionally_retry_same_request"
    assert result.recovery.total_attempt_limit == 3
    assert client.close_calls == 1
    assert len(client.requests) == 1
    assert "private request" not in result.model_dump_json()


def test_checkpoint_close_failure_cannot_return_successful_choice(checkpoint_request):
    """关闭阶段故障必须丢弃选择、要求人工审阅且不泄露原始异常。"""
    client = CheckpointClient(close_error=RuntimeError("private close failure"))

    result = checkpoint_advice(client, checkpoint_request)

    assert result.status == "fallback"
    assert result.suggested_choice is None
    assert result.reason == "provider_error"
    assert result.failure_class == "unknown"
    assert result.recovery is not None
    assert result.recovery.action == "stop_and_review"
    assert result.recovery.retry_eligible is False
    assert client.close_calls == 1
    assert "private close" not in result.model_dump_json()
