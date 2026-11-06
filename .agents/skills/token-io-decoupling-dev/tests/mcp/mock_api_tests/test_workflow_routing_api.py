from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import httpx2
import pytest
from openai import OpenAI

import token_io_decoupling_workflow.openai_client as openai_client
from token_io_decoupling_workflow.decisions import (
    DECISIONS_MODEL,
    DECISIONS_TIMEOUT_SECONDS,
    DecisionsRuntimeConfig,
)
from token_io_decoupling_workflow.rules import RuleLoader
from token_io_decoupling_workflow.workflow_routing import (
    DecouplingWorkflowRequest,
    WorkflowRouter,
    canonical_json,
)

_REPOSITORY_ROOT = Path(__file__).resolve().parents[6]


def _request(**overrides: object) -> dict[str, object]:
    facts = [
        {
            "fact_id": "observed-change",
            "source_ref": "reviewed-diff:1",
            "statement": "A scoped parser fix is implemented and needs verification.",
        }
    ]
    request: dict[str, object] = {
        "task_id": "parser-fix",
        "task_summary": "Finish verification for a bounded parser correction.",
        "stage": "auto",
        "language": "en",
        "mode_locked": True,
        "mode_count": {"mode": "Single-Agent Coding", "child_count": 0},
        "capabilities": [
            {"capability_id": "verification", "status": "available", "source_ref": "host:verified"}
        ],
        "hard_constraints": [],
        "source_facts": facts,
        "source_facts_hash": source_facts_hash_from_payload(facts),
        "outbound_data_permitted": True,
    }
    request.update(overrides)
    return request


def source_facts_hash_from_payload(facts: list[dict[str, str]]) -> str:
    return hashlib.sha256(canonical_json(facts).encode("utf-8")).hexdigest()


def test_decisions_call_uses_fixed_model_facts_and_closed_choice_set_over_mock_http(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "canary-secret-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://canary.example.invalid/v1")
    requests: list[httpx2.Request] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        requests.append(request)
        return httpx2.Response(
            200,
            json={
                "answers": [
                    {
                        "type": "choice",
                        "name": "workflow_stage",
                        "choice": "verification_repair",
                        "confidence": 1.0,
                        "probabilities": [{"value": "verification_repair", "probability": 1.0}],
                    }
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

    transport = httpx2.Client(transport=httpx2.MockTransport(handler))
    sdk_client = OpenAI(
        api_key="canary-secret-key",
        base_url="https://canary.example.invalid/v1",
        timeout=20,
        max_retries=0,
        http_client=transport,
    )
    router = WorkflowRouter(
        RuleLoader(repository_root=_REPOSITORY_ROOT),
        DecisionsRuntimeConfig(enabled=True, outbound_data_permitted=True),
        client_factory=lambda key, url: sdk_client,
    )

    result = router.decide(
        DecouplingWorkflowRequest.model_validate_json(json.dumps(_request(), ensure_ascii=False))
    )

    assert (result.status, result.reason) == ("available", "stage_selected")
    assert result.selected_stage == "verification_repair"
    assert result.module_id == "SM05"
    assert result.model == DECISIONS_MODEL
    assert result.total_tokens == 87
    assert result.advisory_only is True
    assert (
        result.route_reference is not None
        and result.route_reference.route_id == "coding-single-agent"
    )
    assert len(requests) == 1
    request = requests[0]
    assert request.method == "POST" and request.url.path == "/v1/decisions"
    assert request.headers["authorization"] == "Bearer canary-secret-key"
    body = json.loads(request.content)
    assert body["model"] == DECISIONS_MODEL
    assert len(body["questions"]) == 1
    question = body["questions"][0]
    assert question["name"] == "workflow_stage"
    choice_values = [choice["value"] for choice in question["choices"]]
    assert choice_values == [
        "entry_readiness",
        "session_readiness",
        "work_definition",
        "execution",
        "verification_repair",
        "documentation",
        "delivery_acceptance",
        "insufficient_evidence",
    ]
    assert "Single-Agent Coding" in question["instructions"]
    encoded_input = body["input"]
    assert isinstance(encoded_input, str)
    decision = json.loads(encoded_input)
    assert decision["caller_facts"]["mode_locked"] is True
    assert decision["caller_facts"]["mode_count"] == {
        "mode": "Single-Agent Coding",
        "child_count": 0,
    }
    assert decision["caller_facts"]["task_id"] == "parser-fix"
    assert decision["current_rule_context"]
    assert "canary-secret-key" not in request.content.decode()
    assert transport.is_closed


def test_router_default_factory_passes_environment_and_httpx2_options(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://example.invalid/v1")
    arguments: list[dict[str, object]] = []
    closed = False

    class FakeDecisions:
        def create(self, **_kwargs: object) -> object:
            return SimpleNamespace(
                answers=[SimpleNamespace(type="choice", name="workflow_stage", choice="execution")],
                model=DECISIONS_MODEL,
                status="completed",
                error=None,
                incomplete_details=None,
                usage=SimpleNamespace(total_tokens=17),
            )

    class FakeOpenAI:
        def __init__(self, **kwargs: object) -> None:
            arguments.append(kwargs)
            self.decisions = FakeDecisions()

        def close(self) -> None:
            nonlocal closed
            closed = True
            http_client = arguments[0]["http_client"]
            assert isinstance(http_client, httpx2.Client)
            http_client.close()

    monkeypatch.setattr(openai_client, "OpenAI", FakeOpenAI)
    router = WorkflowRouter(
        RuleLoader(repository_root=_REPOSITORY_ROOT),
        DecisionsRuntimeConfig(enabled=True, outbound_data_permitted=True),
    )
    request = DecouplingWorkflowRequest.model_validate_json(
        json.dumps(_request(), ensure_ascii=False)
    )
    result = router.decide(request)

    assert (result.status, result.reason) == ("available", "stage_selected")
    assert len(arguments) == 1
    kwargs = arguments[0]
    assert {key: kwargs[key] for key in ("api_key", "base_url", "timeout", "max_retries")} == {
        "api_key": "test-key",
        "base_url": "https://example.invalid/v1",
        "timeout": DECISIONS_TIMEOUT_SECONDS,
        "max_retries": 0,
    }
    http_client = kwargs["http_client"]
    assert isinstance(http_client, httpx2.Client)
    assert http_client._trust_env is True
    assert http_client.timeout.as_dict() == {
        "connect": DECISIONS_TIMEOUT_SECONDS,
        "read": DECISIONS_TIMEOUT_SECONDS,
        "write": DECISIONS_TIMEOUT_SECONDS,
        "pool": DECISIONS_TIMEOUT_SECONDS,
    }
    assert closed
    assert http_client.is_closed
