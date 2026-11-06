"""通过真实 SDK 与本地 MockTransport 验证单次事件建议协议。"""

from __future__ import annotations

import json

import httpx2
import pytest
from openai import OpenAI
from support.event_cases import checker, request

from token_io_decoupling_workflow import openai_client
from token_io_decoupling_workflow.decisions import DECISIONS_MODEL, DECISIONS_TIMEOUT_SECONDS


def mock_decision_http_response() -> httpx2.Response:
    """构造只有已审核选择与明确用量的外部协议响应。"""
    return httpx2.Response(
        200,
        json={
            "id": "decision_event_mock",
            "object": "decision",
            "created_at": 1,
            "status": "completed",
            "error": None,
            "incomplete_details": None,
            "answers": [
                {"type": "choice", "name": "workflow_event_outcome", "choice": "needs_evidence"}
            ],
            "model": DECISIONS_MODEL,
            "usage": {
                "input_tokens": 80,
                "input_tokens_details": {"cache_write_tokens": 0, "cached_tokens": 0},
                "output_tokens": 7,
                "output_tokens_details": {"reasoning_tokens": 0},
                "total_tokens": 87,
            },
        },
    )


@pytest.fixture
def event_api_call(monkeypatch):
    """通过真实 OpenAI SDK 与本地 MockTransport 完成一次建议，保留请求供两个合同场景检查。"""
    monkeypatch.setenv("OPENAI_API_KEY", "mock-event-secret")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://events.example.invalid/v1")
    requests = []

    def handler(http_request):
        """记录真实 SDK 构造的 HTTP 请求，并返回固定的合法 Decisions 响应。"""
        requests.append(http_request)
        return mock_decision_http_response()

    transport = httpx2.Client(transport=httpx2.MockTransport(handler))
    sdk = OpenAI(
        api_key="mock-event-secret",
        base_url="https://events.example.invalid/v1",
        timeout=20,
        max_retries=0,
        http_client=transport,
    )
    result = checker(enabled=True, outbound=True, client=sdk).check(
        request(
            "completion_requested",
            mode="single-agent",
            include_workflow=True,
            semantic_input={"outbound_data_permitted": True},
        )
    )
    return result, transport, requests


def test_event_advice_returns_bounded_usage_and_closes_single_request(event_api_call):
    """成功建议须保留精确用量、关闭传输且只发送一次请求，凭据不能混进正文。"""
    result, transport, requests = event_api_call
    assert result.advice.status == "available"
    assert result.advice.suggested_outcome == "needs_evidence"
    assert result.advice.total_tokens == 87
    assert transport.is_closed
    assert len(requests) == 1
    http_request = requests[0]
    assert http_request.method == "POST"
    assert http_request.url.path == "/v1/decisions"
    assert http_request.headers["authorization"] == "Bearer mock-event-secret"
    assert "mock-event-secret" not in http_request.content.decode()


def test_event_advice_uses_complete_current_rules_and_exact_documented_choices(event_api_call):
    """外发问题须包含完整批准规则与同批流程，只暴露文档定义的六个结果。"""
    result, _transport, requests = event_api_call
    assert len(requests) == 1
    body = json.loads(requests[0].content)
    assert body["model"] == DECISIONS_MODEL
    question = body["questions"][0]
    assert question["name"] == "workflow_event_outcome"
    assert [choice["value"] for choice in question["choices"]] == [
        "continue",
        "needs_evidence",
        "amend",
        "wait",
        "stop",
        "not_applicable",
    ]
    supplied = json.loads(body["input"])
    assert result.instructions is not None
    assert result.instructions.workflow is not None
    assert supplied["approved_hook_instructions"] == result.instructions.event.text
    assert supplied["selected_workflow_instructions"] == result.instructions.workflow.text
    assert supplied["event"] == "completion_requested"
    assert supplied["mode"] == "single-agent"


def test_event_default_client_uses_httpx2_environment_and_closes_transport(monkeypatch):
    """默认客户端须保留 httpx2 环境行为，并在正常建议后关闭真实传输对象。"""
    monkeypatch.setenv("OPENAI_API_KEY", "mock-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://example.invalid/v1")
    arguments = []

    class FakeOpenAI:
        """截获 OpenAI 构造参数，仅替换外部决策服务而保留实际 HTTP 客户端。"""

        def __init__(self, **kwargs):
            """记录实际传入的客户端与 SDK 选项，供环境行为断言使用。"""
            arguments.append(kwargs)
            self.decisions = self

        def create(self, **_kwargs):
            """返回合法选择，避免将请求格式错误混入传输生命周期场景。"""
            from support.event_cases import response

            return response("continue")

        def close(self):
            """按真实 SDK 生命周期关闭所持 HTTP 客户端。"""
            arguments[0]["http_client"].close()

    monkeypatch.setattr(openai_client, "OpenAI", FakeOpenAI)
    result = checker(enabled=True, outbound=True).check(
        request(semantic_input={"outbound_data_permitted": True})
    )
    assert result.advice.status == "available"
    assert len(arguments) == 1
    kwargs = arguments[0]
    assert {key: kwargs[key] for key in ("api_key", "base_url", "timeout", "max_retries")} == {
        "api_key": "mock-key",
        "base_url": "https://example.invalid/v1",
        "timeout": DECISIONS_TIMEOUT_SECONDS,
        "max_retries": 0,
    }
    transport = kwargs["http_client"]
    assert isinstance(transport, httpx2.Client)
    assert transport._trust_env is True
    assert transport.is_closed
