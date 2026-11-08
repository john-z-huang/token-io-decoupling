"""在外发许可和规则新鲜度约束下请求一次工作流建议。"""

from __future__ import annotations

import os
from contextlib import closing
from typing import Literal

from token_io_decoupling_workflow.api_recovery import (
    classify_provider_failure,
)
from token_io_decoupling_workflow.compiled_rules.contracts import RuleLoadError
from token_io_decoupling_workflow.compiled_rules.loader import RuleLoader
from token_io_decoupling_workflow.decision_prompts import reviewed_prompt

from .models import (
    DECISIONS_MODEL,
    DECISIONS_TIMEOUT_SECONDS,
    MAX_REQUEST_CHARS,
    SUPPORTED_ADVISORY_NODES,
    ClientFactory,
    DecisionAdvice,
    DecisionAdvisoryInput,
    DecisionsRuntimeConfig,
    _CheckpointSource,
    _ClosableClient,
    _DecisionsResource,
    _PreparedAdvice,
)
from .requests import (
    _basis_hash,
    _checkpoint_response,
    _decision_question,
    _fallback,
    _request_input,
)


class DecisionsAdvisor:
    """提供检查点的单次建议；规则和结构检查不依赖网络建议成功。"""

    def __init__(
        self,
        rule_loader: RuleLoader,
        config: DecisionsRuntimeConfig,
        *,
        client_factory: ClientFactory | None = None,
    ) -> None:
        self._rule_loader = rule_loader
        self._config = config
        self._client_factory = client_factory

    def advise(
        self,
        advisory_input: DecisionAdvisoryInput,
        *,
        current_facts: dict[str, str],
        checkpoint_source_input_hash: str,
        language: Literal["zh_cn"] = "zh_cn",
        expected_rule_hash: str,
    ) -> DecisionAdvice:
        """保留现有调用接口；外部请求或释放故障均返回安全 fallback。"""
        if not self._config.enabled:
            return DecisionAdvice(
                status="fallback", reason="disabled", node_id=advisory_input.node_id
            )
        source = _CheckpointSource(current_facts, checkpoint_source_input_hash, language)
        prepared = self._prepare(advisory_input, source, expected_rule_hash)
        if isinstance(prepared, DecisionAdvice):
            return prepared
        api_key, base_url = os.environ.get("OPENAI_API_KEY"), os.environ.get("OPENAI_BASE_URL")
        if not api_key or not api_key.strip() or not base_url or not base_url.strip():
            return _fallback(
                "missing_credentials", prepared.node_id, prepared.basis_hash, prepared.rules
            )
        try:
            response = self._request_decision(api_key, base_url, prepared)
        except Exception as exc:
            # SDK 请求与释放是外部边界；失败不采纳选项且不泄露供应商原始消息。
            failure = classify_provider_failure(exc)
            return _fallback(
                failure.reason,
                prepared.node_id,
                prepared.basis_hash,
                prepared.rules,
                failure=failure,
            )
        return self._finish(response, advisory_input, source, prepared)

    def _prepare(
        self,
        advisory_input: DecisionAdvisoryInput,
        source: _CheckpointSource,
        expected_rule_hash: str,
    ) -> _PreparedAdvice | DecisionAdvice:
        """在外发前绑定当前规则、已审阅问题与来源指纹，缺失或超限时直接返回。"""
        node_id = advisory_input.node_id
        if node_id not in SUPPORTED_ADVISORY_NODES:
            return DecisionAdvice(status="fallback", reason="invalid_response", node_id=node_id)
        try:
            rules = self._rule_loader.load_context(node_id.value, language=source.language)
        except (RuleLoadError, OSError, ValueError):
            return DecisionAdvice(
                status="fallback", reason="rule_context_unavailable", node_id=node_id
            )
        if rules.context_hash != expected_rule_hash:
            return DecisionAdvice(status="stale", reason="stale_context", node_id=node_id)
        prompt = reviewed_prompt(node_id, list(rules.legal_branches))
        if not rules.legal_branches or prompt is None:
            return DecisionAdvice(status="fallback", reason="invalid_response", node_id=node_id)
        request_input = _request_input(advisory_input, rules, prompt, source)
        if len(request_input) > MAX_REQUEST_CHARS:
            return _fallback("rule_context_too_large", node_id, "", rules)
        return _PreparedAdvice(
            node_id,
            rules,
            prompt,
            request_input,
            _basis_hash(advisory_input, source, rules.context_hash),
        )

    def _request_decision(self, api_key: str, base_url: str, prepared: _PreparedAdvice) -> object:
        """返回响应前释放客户端；请求或关闭异常都交给上层阻止采纳。"""
        client = self._make_client(api_key, base_url)
        if not isinstance(client, _ClosableClient):
            raise TypeError("checkpoint advice client must support close")
        with closing(client):
            resource = getattr(client, "decisions", None)
            if not isinstance(resource, _DecisionsResource):
                raise TypeError("checkpoint advice client must support decisions.create")
            return resource.create(
                model=DECISIONS_MODEL,
                input=prepared.request_input,
                questions=[_decision_question(prepared)],
            )

    def _finish(
        self,
        response: object,
        advisory_input: DecisionAdvisoryInput,
        source: _CheckpointSource,
        prepared: _PreparedAdvice,
    ) -> DecisionAdvice:
        """仅在响应可用且规则仍新鲜时保留选项，变化时移除选择并返回 stale。"""
        advice = _checkpoint_response(response, prepared)
        if advice.status != "available":
            return advice
        if not self._rules_unchanged(advisory_input, source, prepared):
            return DecisionAdvice(
                status="stale",
                reason="stale_context",
                node_id=prepared.node_id,
                input_hash=prepared.basis_hash,
                rule_hash=prepared.rules.context_hash,
            )
        return advice

    def _rules_unchanged(
        self,
        advisory_input: DecisionAdvisoryInput,
        source: _CheckpointSource,
        prepared: _PreparedAdvice,
    ) -> bool:
        """请求后重读同一规则并重算事实依据；读回失败也不能继续采纳建议。"""
        try:
            current = self._rule_loader.load_context(
                prepared.node_id.value, language=source.language
            )
        except (RuleLoadError, OSError, ValueError):
            return False
        return (
            current.context_hash == prepared.rules.context_hash
            and _basis_hash(advisory_input, source, current.context_hash) == prepared.basis_hash
        )

    def _make_client(self, api_key: str, base_url: str) -> object:
        if self._client_factory is not None:
            return self._client_factory(api_key, base_url)
        from token_io_decoupling_workflow.openai_client import make_openai_client

        return make_openai_client(api_key, base_url, timeout=DECISIONS_TIMEOUT_SECONDS)
