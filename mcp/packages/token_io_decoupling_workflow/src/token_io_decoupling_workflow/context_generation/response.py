"""按固定顺序校验供应商响应、缺失信息和正文预算。"""

from __future__ import annotations

from typing import Literal

from .models import (
    GENERATION_MODEL,
    DecisionContextResult,
    DecisionContextStructuredOutput,
    DecisionOutputKind,
    ShortText,
    _blocked,
    _ResponseFailureReason,
)


def _response_failure_reason(
    response: object,
) -> Literal["incomplete", "invalid_response", "refusal"] | None:
    if getattr(response, "status", None) != "completed":
        return "incomplete"
    if (
        getattr(response, "error", None) is not None
        or getattr(response, "incomplete_details", None) is not None
    ):
        return "invalid_response"
    if getattr(response, "model", None) != GENERATION_MODEL:
        return "invalid_response"
    if _is_refusal(response):
        return "refusal"
    return None


def _description_failure_reason(
    parsed: DecisionContextStructuredOutput, output_kind: DecisionOutputKind
) -> Literal["invalid_response", "insufficient_evidence"] | None:
    description = parsed.description
    missing = parsed.missing_information
    if any(not item.strip() for item in missing):
        return "invalid_response"
    if description is None:
        return "insufficient_evidence" if missing else "invalid_response"
    if not description.strip() or missing:
        return "invalid_response"
    output_limit = 1200 if output_kind == "decision_question" else 6000
    if len(description) > output_limit:
        return "invalid_response"
    return None


def _validate_generated_response(
    response: object, output_kind: DecisionOutputKind, input_hash: str, source_policy_hash: str
) -> DecisionContextStructuredOutput | DecisionContextResult:
    """先检查响应状态，再检查严格结构与正文；失败结果保留来源 Hash 和缺口。"""

    def blocked(
        reason: _ResponseFailureReason, missing_information: list[ShortText] | None = None
    ) -> DecisionContextResult:
        return _blocked(
            reason,
            input_hash,
            output_kind,
            source_policy_hash=source_policy_hash,
            missing_information=missing_information,
        )

    reason = _response_failure_reason(response)
    if reason is not None:
        return blocked(reason)
    parsed = getattr(response, "output_parsed", None)
    if type(parsed) is not DecisionContextStructuredOutput:
        return blocked("invalid_response")
    description_reason = _description_failure_reason(parsed, output_kind)
    if description_reason is not None:
        missing = (
            parsed.missing_information if description_reason == "insufficient_evidence" else None
        )
        return blocked(description_reason, missing)
    return parsed


def _is_refusal(response: object) -> bool:
    output = getattr(response, "output", None)
    if not isinstance(output, list):
        return False
    for item in output:
        content_items = getattr(item, "content", None)
        if not isinstance(content_items, list):
            continue
        for content in content_items:
            if getattr(content, "type", None) == "refusal" or getattr(content, "refusal", None):
                return True
    return False
