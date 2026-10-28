"""Opt-in live API integration tests; never run from credentials alone."""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
from pathlib import Path
from typing import Any, cast

import pytest
from mcp import Client
from mcp.types import TextContent
from token_io_decoupling_workflow.child_effort import (
    DECISIONS_MODEL,
    ChildEffortInput,
    ChildEffortSelector,
    Effort,
)
from token_io_decoupling_workflow.decision_context import (
    GENERATION_MODEL,
    DecisionContextGenerator,
    DecisionContextInput,
    DecisionOutputKind,
)

from token_io_decoupling.server import create_server

_OPT_IN_NAME = "TOKEN_IO_RUN_REAL_API"
_OPTED_IN = os.environ.get(_OPT_IN_NAME) == "1"
pytestmark = [
    pytest.mark.real_api,
    pytest.mark.skipif(
        not _OPTED_IN,
        reason=f"set {_OPT_IN_NAME}=1 to enable live OpenAI API tests",
    ),
]
_RAW_CONTENT = """Synthetic, released mechanical task fixture; it contains no real repository,
Git, LSP, host-session, or Agent observations and must not be treated as such.

User goal (synthetic): Add exactly one integer constant named MAX_RETRIES with value 0 above the
target function in src/sample.py. No other code changes are requested.
Current diff (synthetic): +# Retry policy constants
LSP observation (synthetic): src/sample.py has a module-level constants section directly above the
target function. MAX_RETRIES does not exist yet and has no existing references.
Scope (synthetic): One module-level constant in src/sample.py.
Dependencies (synthetic): none.
Risk (synthetic): A wrong value would affect only the new constant; no other behavior changes.
Uncertainty (synthetic): none.
Verification (synthetic): Confirm the exact constant value and run its direct assertion.
Previous failure evidence (synthetic): none.
Supported reasoning efforts (synthetic): low, medium.
"""
_QUESTION_GOAL = (
    "Write one concise question asking which lowest sufficient supported reasoning effort fits "
    "this exact released mechanical task."
)
_CONTEXT_GOAL = (
    "Summarize the supplied released mechanical task facts relevant to choosing the lowest "
    "sufficient supported reasoning effort, without making the choice."
)
_SUPPORTED_EFFORTS: list[Effort] = ["low", "medium"]
_SLICE_FINGERPRINT = "a" * 64


@pytest.fixture(scope="module", autouse=True)
def suppress_provider_logs():
    """Silence all logging during opt-in calls and restore the prior global threshold."""
    previous_disable = logging.root.manager.disable
    logging.disable(logging.CRITICAL)
    try:
        yield
    finally:
        logging.disable(previous_disable)


@pytest.fixture(scope="module")
def real_api_configuration() -> None:
    """Require explicit opt-in and report only missing variable names."""
    missing = [
        name
        for name in ("OPENAI_API_KEY", "OPENAI_BASE_URL")
        if not os.environ.get(name, "").strip()
    ]
    if missing:
        cast(Any, pytest).fail(
            (
                f"{_OPT_IN_NAME}=1 but required environment variable(s) are missing: "
                + ", ".join(missing)
            ),
            pytrace=False,
        )


def _canonical_hash(facts: dict[str, Any]) -> str:
    canonical = json.dumps(
        facts,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _generation_input(
    output_kind: DecisionOutputKind = "decision_question",
) -> DecisionContextInput:
    return DecisionContextInput(
        raw_content=_RAW_CONTENT,
        decision_goal=(_CONTEXT_GOAL if output_kind == "decision_context" else _QUESTION_GOAL),
        output_kind=output_kind,
        outbound_data_permitted=True,
    )


def _child_input(decision_question: str) -> ChildEffortInput:
    return ChildEffortInput(
        slice_id="real-api-synthetic-slice-1",
        role="Primary Output",
        objective=(
            "Add exactly one integer constant named MAX_RETRIES with value 0 at the stated "
            "location."
        ),
        decision_question=decision_question,
        task_complexity="mechanical",
        uncertainty="none",
        scope="One module-level constant in src/sample.py.",
        dependencies="none",
        risk="A wrong value would affect only the new constant; no other behavior is changed.",
        verification_demands="Confirm the exact constant value and run its direct assertion.",
        previous_failure_evidence="none",
        slice_fingerprint=_SLICE_FINGERPRINT,
        runtime="codex",
        child_model=DECISIONS_MODEL,
        supported_efforts=_SUPPORTED_EFFORTS,
        outbound_data_permitted=True,
    )


def _assert_generated(
    result: dict[str, Any],
    expected_hash: str,
    output_kind: DecisionOutputKind = "decision_question",
) -> str:
    assert result.get("status") == "available", (
        f"decision context unavailable: status={result.get('status')} reason={result.get('reason')}"
    )
    assert result.get("reason") == "description_generated"
    assert result.get("model") == GENERATION_MODEL
    assert result.get("output_kind") == output_kind
    assert result.get("input_hash") == expected_hash
    assert result.get("missing_information") == []
    description = result.get("description")
    assert isinstance(description, str) and description.strip()
    assert len(description) <= (6000 if output_kind == "decision_context" else 1200)
    return description


def _assert_effort_result(
    result: dict[str, Any],
    request: ChildEffortInput,
    expected_hash: str,
) -> None:
    assert result.get("status") == "available", (
        f"child effort unavailable: status={result.get('status')} reason={result.get('reason')}"
    )
    assert result.get("reason") == "effort_selected"
    assert result.get("selected_effort") in request.supported_efforts
    assert result.get("model") == DECISIONS_MODEL
    assert result.get("input_hash") == expected_hash
    assert result.get("slice_fingerprint") == request.slice_fingerprint


def _tool_json(result: Any) -> dict[str, Any]:
    assert not result.is_error, "workflow tool returned an MCP error"
    text_content = next((item for item in result.content if isinstance(item, TextContent)), None)
    assert text_content is not None, "workflow tool returned no text content"
    decoded = json.loads(text_content.text)
    assert isinstance(decoded, dict), "workflow tool returned an unexpected result shape"
    return decoded


def test_real_api_generates_decision_context(real_api_configuration: None) -> None:
    del real_api_configuration
    payload = _generation_input(output_kind="decision_context")
    expected_generation_hash = _canonical_hash(
        {
            "raw_content": payload.raw_content,
            "decision_goal": payload.decision_goal,
            "output_kind": payload.output_kind,
        }
    )
    result = DecisionContextGenerator().generate(payload).model_dump(mode="json")
    _assert_generated(result, expected_generation_hash, output_kind="decision_context")


def test_real_api_selects_child_effort(real_api_configuration: None) -> None:
    del real_api_configuration
    request = _child_input(
        "Which lowest sufficient supported reasoning effort fits this released task?"
    )
    expected_effort_hash = _canonical_hash(
        request.model_dump(
            mode="json",
            exclude={"outbound_data_permitted", "slice_fingerprint"},
        )
    )
    result = ChildEffortSelector().select(request).model_dump(mode="json")
    _assert_effort_result(result, request, expected_effort_hash)


def test_real_api_mcp_generation_to_effort_decision_chain(
    real_api_configuration: None, tmp_path: Path
) -> None:
    del real_api_configuration
    generation_payload = _generation_input()
    expected_generation_hash = _canonical_hash(
        {
            "raw_content": generation_payload.raw_content,
            "decision_goal": generation_payload.decision_goal,
            "output_kind": generation_payload.output_kind,
        }
    )
    server = create_server(profile="workflow", state_root=tmp_path)

    async def call_chain() -> tuple[dict[str, Any], dict[str, Any], ChildEffortInput, str]:
        async with Client(server, mode="auto") as client:
            generated = _tool_json(
                await client.call_tool(
                    "workflow_generate_decision_context",
                    {
                        "payload": {
                            "request": generation_payload.model_dump(mode="json"),
                        }
                    },
                )
            )
            question = _assert_generated(generated, expected_generation_hash)
            child_request = _child_input(question)
            assert child_request.decision_question == generated["description"]
            expected_effort_hash = _canonical_hash(
                child_request.model_dump(
                    mode="json",
                    exclude={"outbound_data_permitted", "slice_fingerprint"},
                )
            )
            effort = _tool_json(
                await client.call_tool(
                    "workflow_select_child_effort",
                    {"payload": {"request": child_request.model_dump(mode="json")}},
                )
            )
            return generated, effort, child_request, expected_effort_hash

    generated, effort, child_request, expected_effort_hash = asyncio.run(call_chain())
    _assert_effort_result(effort, child_request, expected_effort_hash)
    assert generated["input_hash"] != effort["input_hash"]
