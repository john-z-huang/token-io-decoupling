"""Safe, advisory recovery classification for one-shot API calls."""

from __future__ import annotations

from typing import Annotated, Literal, TypeAlias

from pydantic import Field
from token_io_decoupling_core.models import StrictModel

FailureClass: TypeAlias = Literal[
    "transport",
    "authentication",
    "authorization",
    "not_found",
    "rate_limit",
    "quota",
    "api",
    "sdk_contract",
    "configuration",
    "unknown",
]
ProviderErrorCode: TypeAlias = Literal[
    "invalid_api_key",
    "model_not_found",
    "insufficient_quota",
    "rate_limit_exceeded",
    "other",
]
RecoveryAction: TypeAlias = Literal[
    "no_action",
    "review_then_optionally_retry_same_request",
    "refresh_current_facts_and_policy",
    "continue_without_advice_or_review",
    "correct_input_or_review_evidence",
    "resolve_credentials_or_configuration",
    "resolve_permission",
    "resolve_quota_or_access",
    "restore_fixed_api_access",
    "stop_and_review",
]


class RecoveryGuidance(StrictModel):
    """Caller guidance only; the server never tracks attempts or invokes another request."""

    retry_eligible: bool = Field(
        description="A bounded retry candidate, not an instruction or automatic retry."
    )
    action: RecoveryAction
    failure_class: FailureClass | None = None
    total_attempt_limit: Annotated[int, Field(ge=1, le=3)] | None = Field(
        default=None,
        description=(
            "Maximum calls in the caller-tracked recovery process, including the first call."
        ),
    )


class ProviderFailure(StrictModel):
    """Allowlisted, non-sensitive classification of an SDK exception."""

    reason: Literal["provider_error", "timeout"]
    failure_class: FailureClass
    http_status: Annotated[int, Field(ge=100, le=599)] | None = None
    provider_error_code: ProviderErrorCode | None = None


def _safe_attribute(value: object, name: str) -> tuple[object | None, bool]:
    try:
        return getattr(value, name, None), True
    except Exception:
        return None, False


def _safe_error_code(exc: Exception) -> tuple[str | None, bool]:
    raw_code, safe_code = _safe_attribute(exc, "code")
    if not safe_code:
        return None, False
    if isinstance(raw_code, str):
        return raw_code, True
    body, safe_body = _safe_attribute(exc, "body")
    if not safe_body:
        return None, False
    try:
        error = body.get("error") if isinstance(body, dict) else None
        if isinstance(error, dict):
            code = error.get("code")
            if isinstance(code, str):
                return code, True
            kind = error.get("type")
            return (kind if isinstance(kind, str) else None), True
    except Exception:
        return None, False
    return None, True


def classify_provider_failure(exc: Exception) -> ProviderFailure:
    """Classify only known exception names and validated status/code fields; never echo input."""
    error_name = type(exc).__name__
    raw_status, safe_status = _safe_attribute(exc, "status_code")
    if raw_status is not None and (type(raw_status) is not int or not 100 <= raw_status <= 599):
        return ProviderFailure(reason="provider_error", failure_class="unknown")
    status = raw_status if type(raw_status) is int and 100 <= raw_status <= 599 else None
    raw_code, safe_code = _safe_error_code(exc)
    if not safe_status or not safe_code:
        return ProviderFailure(reason="provider_error", failure_class="unknown")
    allowed_codes: dict[str, ProviderErrorCode] = {
        "invalid_api_key": "invalid_api_key",
        "model_not_found": "model_not_found",
        "insufficient_quota": "insufficient_quota",
        "rate_limit_exceeded": "rate_limit_exceeded",
    }
    code = allowed_codes.get(raw_code) if raw_code is not None else None

    # Explicit hard failures win over broad transport names or server-status candidates.
    if status == 401 or code == "invalid_api_key":
        category: FailureClass = "authentication"
        code = "invalid_api_key" if code == "invalid_api_key" else None
    elif status == 403:
        category = "authorization"
        code = "other" if raw_code is not None and code is None else code
    elif code == "insufficient_quota":
        category = "quota"
    elif status == 404 or code == "model_not_found":
        category = "not_found"
        code = "model_not_found" if code == "model_not_found" else None
    elif code == "rate_limit_exceeded" and status not in (None, 429):
        category = "unknown"
        code = None
    elif status == 429 or (status is None and code == "rate_limit_exceeded"):
        category = "rate_limit"
        code = (
            "rate_limit_exceeded"
            if code == "rate_limit_exceeded"
            else ("other" if raw_code is not None else None)
        )
    elif isinstance(exc, (TypeError, ValueError)):
        category = "configuration"
    elif error_name == "APIResponseValidationError":
        category = "sdk_contract"
    elif status is not None and status >= 500:
        category = "api"
        code = "other" if raw_code is not None and code is None else code
    elif status is not None:
        category = "api"
        code = "other" if raw_code is not None and code is None else code
    elif error_name in {
        "APITimeoutError",
        "APIConnectionError",
        "APIConnectionTimeoutError",
        "TimeoutError",
    }:
        category = "transport"
    else:
        category = "unknown"

    reason: Literal["provider_error", "timeout"] = (
        "timeout"
        if category == "transport" and error_name in {"APITimeoutError", "TimeoutError"}
        else "provider_error"
    )
    return ProviderFailure(
        reason=reason,
        failure_class=category,
        http_status=status,
        provider_error_code=code,
    )


def recovery_for_provider_failure(failure: ProviderFailure) -> RecoveryGuidance:
    """Permit only a narrow set of explicitly transient failures to be considered for retry."""
    retry_eligible = failure.failure_class in {"transport", "api"} and (
        failure.failure_class == "transport"
        or failure.http_status is not None
        and failure.http_status >= 500
    )
    retry_eligible = retry_eligible or (
        failure.failure_class == "rate_limit"
        and failure.provider_error_code == "rate_limit_exceeded"
    )
    if retry_eligible:
        action: RecoveryAction = "review_then_optionally_retry_same_request"
        limit: int | None = 3
    else:
        action = {
            "authentication": "resolve_credentials_or_configuration",
            "authorization": "resolve_permission",
            "configuration": "resolve_credentials_or_configuration",
            "quota": "resolve_quota_or_access",
            "not_found": "restore_fixed_api_access",
            "sdk_contract": "stop_and_review",
            "rate_limit": "stop_and_review",
            "unknown": "stop_and_review",
            "api": "stop_and_review",
            "transport": "stop_and_review",
        }[failure.failure_class]
        limit = None
    return RecoveryGuidance(
        retry_eligible=retry_eligible,
        action=action,
        failure_class=failure.failure_class,
        total_attempt_limit=limit,
    )


def recovery_for_reason(reason: str) -> RecoveryGuidance:
    """Describe non-provider exits without promoting them to transient failures."""
    if reason in {"stale_policy", "stale_context", "source_policy_changed_during_request"}:
        action: RecoveryAction = "refresh_current_facts_and_policy"
    elif reason in {"missing_credentials", "policy_unavailable", "policy_contract_invalid"}:
        action = "resolve_credentials_or_configuration"
    elif reason in {"outbound_data_not_permitted", "binding_unavailable"}:
        action = "resolve_permission"
    elif reason in {
        "insufficient_evidence",
        "refusal",
        "invalid_response",
        "incomplete",
        "incomplete_response",
    }:
        action = "correct_input_or_review_evidence"
    elif reason in {"idempotent_replay", "disabled", "core_blocked", "not_started"}:
        action = "no_action"
    elif reason in {"unsupported_runtime_model", "unsupported_effort"}:
        action = "restore_fixed_api_access"
    else:
        action = "stop_and_review"
    return RecoveryGuidance(retry_eligible=False, action=action)
