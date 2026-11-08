"""各委派判断的公共入口与依赖装配。"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from token_io_decoupling_core.workflow_contracts.vocabulary import AllocationRole
from token_io_decoupling_workflow.compiled_rules.contracts import (
    CompiledDelegationPolicy,
    RuleLoadError,
)
from token_io_decoupling_workflow.compiled_rules.loader import RuleLoader

from . import candidates as _candidates
from . import executors as _executors
from . import output_tokens as _output_tokens
from . import provider as _provider
from . import roles as _roles
from .models import (
    DECISIONS_TIMEOUT_SECONDS,
    ChildCandidate,
    ChildCandidateSelectionInput,
    ChildRoleSelectionInput,
    ClientFactory,
    DecisionInputBase,
    DelegationDecisionResult,
    ExecutorSelectionInput,
    OutputTokenRoutingInput,
)


class DelegationDecisionSelector:
    """对当前会话事实作固定选项建议，不读取或修改父级 workflow 状态。"""

    def __init__(
        self,
        rules: RuleLoader,
        *,
        client_factory: ClientFactory | None = None,
    ) -> None:
        self._rules = rules
        self._client_factory = client_factory

    @staticmethod
    def _explicit_role_result(
        payload: ChildRoleSelectionInput,
        base: DelegationDecisionResult,
        available_roles: list[AllocationRole],
    ) -> DelegationDecisionResult:
        return _roles.explicit_role_result(payload, base, available_roles)

    def select_child_role(self, payload: ChildRoleSelectionInput) -> DelegationDecisionResult:
        """先执行模式、显式创建和同职责守卫，需要语义选择时才请求模型。"""
        return _roles.select_child_role(self, payload)

    def select_executor(self, payload: ExecutorSelectionInput) -> DelegationDecisionResult:
        """结合锁定模式与明确用户指令判断执行者，不授予实际派发权限。"""
        return _executors.select_executor(self, payload)

    @staticmethod
    def _candidate_fallback(
        result: DelegationDecisionResult, eligible: list[ChildCandidate]
    ) -> DelegationDecisionResult:
        return _candidates.candidate_fallback(result, eligible)

    @staticmethod
    def _explicit_candidate_result(
        payload: ChildCandidateSelectionInput,
        base: DelegationDecisionResult,
        eligible: list[ChildCandidate],
    ) -> DelegationDecisionResult:
        return _candidates.explicit_candidate_result(payload, base, eligible)

    def select_child_candidate(
        self, payload: ChildCandidateSelectionInput
    ) -> DelegationDecisionResult:
        """先筛选当前合格候选，再判断复用或等待；返回前复核事实新鲜度。"""
        return _candidates.select_child_candidate(self, payload)

    @staticmethod
    def _output_token_action(
        result: DelegationDecisionResult, payload: OutputTokenRoutingInput
    ) -> DelegationDecisionResult:
        return _output_tokens.output_token_action(result, payload)

    def assess_output_tokens(self, payload: OutputTokenRoutingInput) -> DelegationDecisionResult:
        """独立判断大量输出与当前容量，不因候选繁忙而反转输出判断。"""
        return _output_tokens.assess_output_tokens(self, payload)

    def _load_policies(self, names: Sequence[str]) -> dict[str, CompiledDelegationPolicy] | None:
        try:
            return {name: self._rules.load_delegation_policy(name) for name in names}
        except (RuleLoadError, OSError, ValueError):
            return None

    @staticmethod
    def _validated_decision_result(
        response: object,
        kind: str,
        result_base: DelegationDecisionResult,
        accepted: dict[str, set[str]],
        eligible_ids: set[str] | None,
    ) -> DelegationDecisionResult:
        return _provider.validated_decision_result(
            response, kind, result_base, accepted, eligible_ids
        )

    def _decide(
        self,
        kind: str,
        payload: DecisionInputBase,
        policies: Mapping[str, CompiledDelegationPolicy],
        policy_names: Sequence[str],
        choices: Sequence[str],
        accepted: dict[str, set[str]],
        *,
        eligible_ids: set[str] | None = None,
    ) -> DelegationDecisionResult:
        return _provider.decide(
            self,
            kind,
            payload,
            policies,
            policy_names,
            choices,
            accepted,
            eligible_ids=eligible_ids,
        )

    def _make_client(self, api_key: str, base_url: str) -> object:
        if self._client_factory is not None:
            return self._client_factory(api_key, base_url)
        from token_io_decoupling_workflow.openai_client import make_openai_client

        return make_openai_client(api_key, base_url, timeout=DECISIONS_TIMEOUT_SECONDS)
