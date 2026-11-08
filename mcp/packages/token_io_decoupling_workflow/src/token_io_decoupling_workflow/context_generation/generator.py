"""描述生成的单次请求、客户端清理与政策新鲜度检查。"""

from __future__ import annotations

import hashlib
import json
import os
from typing import Any, Literal, cast

from token_io_decoupling_workflow.api_recovery import (
    RecoveryGuidance,
    classify_provider_failure,
    recovery_for_provider_failure,
)
from token_io_decoupling_workflow.compiled_rules.contracts import (
    CompiledDelegationPolicy,
    RuleLoadError,
)
from token_io_decoupling_workflow.compiled_rules.loader import RuleLoader

from .models import (
    GENERATION_MODEL,
    GENERATION_TIMEOUT_SECONDS,
    ClientFactory,
    DecisionContextInput,
    DecisionContextResult,
    DecisionContextStructuredOutput,
    _blocked,
    _RequestFailureReason,
)
from .response import _validate_generated_response


class DecisionContextGenerator:
    """只生成一个有界问题或背景段落，不读取仓库状态或触发下游操作。"""

    def __init__(self, *, rules: RuleLoader, client_factory: ClientFactory | None = None) -> None:
        self._rules = rules
        self._client_factory = client_factory

    def generate(self, payload: DecisionContextInput) -> DecisionContextResult:
        """核对政策与外发许可后请求一次描述，并将陈旧或无效结果安全阻止。"""
        input_hash = _input_hash(payload)
        if not payload.outbound_data_permitted:
            return _blocked("outbound_data_not_permitted", input_hash, payload.output_kind)
        try:
            policy = self._rules.load_delegation_policy("decision-context-generation")
            source_policy_hash = policy.content_sha256
        except (RuleLoadError, OSError, ValueError):
            return _blocked("policy_unavailable", input_hash, payload.output_kind)

        response, failure = self._request_description(payload, policy, input_hash)
        if failure is not None:
            return failure
        parsed = _validate_generated_response(
            response, payload.output_kind, input_hash, source_policy_hash
        )
        if isinstance(parsed, DecisionContextResult):
            return parsed
        description = parsed.description
        if not self._policy_is_current(source_policy_hash):
            return _blocked(
                "stale_policy",
                input_hash,
                payload.output_kind,
                source_policy_hash=source_policy_hash,
            )
        usage = getattr(response, "usage", None)
        total_tokens = getattr(usage, "total_tokens", None)
        if type(total_tokens) is not int or total_tokens < 0:
            total_tokens = None
        return DecisionContextResult(
            status="available",
            reason="description_generated",
            description=description,
            input_hash=input_hash,
            output_kind=payload.output_kind,
            model=GENERATION_MODEL,
            source_policy_hash=source_policy_hash,
            total_tokens=total_tokens,
        )

    def _request_description(
        self, payload: DecisionContextInput, policy: CompiledDelegationPolicy, input_hash: str
    ) -> tuple[object | None, DecisionContextResult | None]:
        """执行单次请求并清理客户端；失败结果在清理前构建，不让清理错误覆盖它。"""

        def blocked(
            reason: _RequestFailureReason, recovery: RecoveryGuidance | None = None
        ) -> DecisionContextResult:
            return _blocked(
                reason,
                input_hash,
                payload.output_kind,
                source_policy_hash=policy.content_sha256,
                recovery=recovery,
            )

        api_key = os.environ.get("OPENAI_API_KEY")
        base_url = os.environ.get("OPENAI_BASE_URL")
        if not api_key or not api_key.strip() or not base_url or not base_url.strip():
            return None, blocked("missing_credentials")
        request = _request_input(payload)
        client: object | None = None
        try:
            client = self._make_client(api_key, base_url)
            response = cast(Any, client).responses.parse(
                model=GENERATION_MODEL,
                input=request,
                instructions=policy.text,
                text_format=DecisionContextStructuredOutput,
                store=False,
                reasoning={"effort": "medium"},
                max_output_tokens=4096,
                truncation="disabled",
                tools=[],
            )
        except Exception as exc:
            failure = classify_provider_failure(exc)
            return None, blocked(_failure_reason(exc), recovery_for_provider_failure(failure))
        finally:
            _close_generation_client(client)
        return response, None

    def _policy_is_current(self, source_policy_hash: str) -> bool:
        try:
            current_policy_hash = self._rules.load_delegation_policy(
                "decision-context-generation"
            ).content_sha256
        except (RuleLoadError, OSError, ValueError):
            return False
        return current_policy_hash == source_policy_hash

    def _make_client(self, api_key: str, base_url: str) -> object:
        if self._client_factory is not None:
            return self._client_factory(api_key, base_url)
        from token_io_decoupling_workflow.openai_client import make_openai_client

        return make_openai_client(api_key, base_url, timeout=GENERATION_TIMEOUT_SECONDS)


def _close_generation_client(client: object | None) -> None:
    close = getattr(client, "close", None)
    if callable(close):
        try:
            close()
        except Exception:
            # 清理失败不能替换已经生成的结果或已分类的供应商故障。
            pass


def _request_input(payload: DecisionContextInput) -> str:
    request = payload.model_dump(mode="json", exclude={"outbound_data_permitted"})
    return json.dumps(
        {"request": request},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _input_hash(payload: DecisionContextInput) -> str:
    content = payload.model_dump(mode="json", exclude={"outbound_data_permitted"})
    return hashlib.sha256(
        json.dumps(content, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode(
            "utf-8"
        )
    ).hexdigest()


def _failure_reason(exc: Exception) -> Literal["provider_error", "timeout", "invalid_response"]:
    name = type(exc).__name__.lower()
    if "timeout" in name:
        return "timeout"
    if "validation" in name or "parsing" in name or "parse" in name:
        return "invalid_response"
    return "provider_error"
