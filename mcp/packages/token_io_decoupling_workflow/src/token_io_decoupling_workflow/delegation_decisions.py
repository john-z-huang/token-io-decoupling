"""兼容原有导入路径；实现分别归属 delegation 包中的职责模块。"""

from .delegation.candidates import (
    _candidate_result as _candidate_result,
)
from .delegation.executors import (
    _executor_sub_action as _executor_sub_action,
)
from .delegation.models import (
    _CHOICE_HEADINGS as _CHOICE_HEADINGS,
)
from .delegation.models import (
    _GENERIC_BOUNDARY_INSTRUCTIONS as _GENERIC_BOUNDARY_INSTRUCTIONS,
)
from .delegation.models import (
    _INSTRUCTION_HEADINGS as _INSTRUCTION_HEADINGS,
)
from .delegation.models import (
    _OUTPUT_POLICY as _OUTPUT_POLICY,
)
from .delegation.models import (
    _PRIMARY as _PRIMARY,
)
from .delegation.models import (
    _ROLE_CHOICES as _ROLE_CHOICES,
)
from .delegation.models import (
    _ROLE_POLICY as _ROLE_POLICY,
)
from .delegation.models import (
    _SESSION_POLICY as _SESSION_POLICY,
)
from .delegation.models import (
    _TASK_POLICY as _TASK_POLICY,
)
from .delegation.models import (
    DECISIONS_MODEL as DECISIONS_MODEL,
)
from .delegation.models import (
    DECISIONS_TIMEOUT_SECONDS as DECISIONS_TIMEOUT_SECONDS,
)
from .delegation.models import (
    MAX_CANDIDATES as MAX_CANDIDATES,
)
from .delegation.models import (
    MAX_CONTEXT_TEXT as MAX_CONTEXT_TEXT,
)
from .delegation.models import (
    MAX_FACT_TEXT as MAX_FACT_TEXT,
)
from .delegation.models import (
    MAX_REQUEST_CHARS as MAX_REQUEST_CHARS,
)
from .delegation.models import (
    MAX_TASK_TEXT as MAX_TASK_TEXT,
)
from .delegation.models import (
    CandidateRef as CandidateRef,
)
from .delegation.models import (
    ChildCandidate as ChildCandidate,
)
from .delegation.models import (
    ChildCandidateSelectionInput as ChildCandidateSelectionInput,
)
from .delegation.models import (
    ChildCandidateSelectionPayload as ChildCandidateSelectionPayload,
)
from .delegation.models import (
    ChildRoleSelectionInput as ChildRoleSelectionInput,
)
from .delegation.models import (
    ChildRoleSelectionPayload as ChildRoleSelectionPayload,
)
from .delegation.models import (
    Choice as Choice,
)
from .delegation.models import (
    ClientFactory as ClientFactory,
)
from .delegation.models import (
    ContextText as ContextText,
)
from .delegation.models import (
    DecisionInputBase as DecisionInputBase,
)
from .delegation.models import (
    DecisionPayload as DecisionPayload,
)
from .delegation.models import (
    DelegationDecisionResult as DelegationDecisionResult,
)
from .delegation.models import (
    ExecutorSelectionInput as ExecutorSelectionInput,
)
from .delegation.models import (
    ExecutorSelectionPayload as ExecutorSelectionPayload,
)
from .delegation.models import (
    FactText as FactText,
)
from .delegation.models import (
    OutputTokenRoutingInput as OutputTokenRoutingInput,
)
from .delegation.models import (
    OutputTokenRoutingPayload as OutputTokenRoutingPayload,
)
from .delegation.models import (
    RoleValue as RoleValue,
)
from .delegation.models import (
    Sha256 as Sha256,
)
from .delegation.models import (
    ShortText as ShortText,
)
from .delegation.models import (
    _fallback_is_allowed as _fallback_is_allowed,
)
from .delegation.models import (
    _result_base as _result_base,
)
from .delegation.models import (
    _session_guard as _session_guard,
)
from .delegation.provider import (
    _blocked_decision_result as _blocked_decision_result,
)
from .delegation.provider import (
    _choice_payload as _choice_payload,
)
from .delegation.provider import (
    _decision_instructions as _decision_instructions,
)
from .delegation.provider import (
    _decision_response_failure as _decision_response_failure,
)
from .delegation.provider import (
    _invalid_decision_choice_result as _invalid_decision_choice_result,
)
from .delegation.provider import (
    _is_refusal as _is_refusal,
)
from .delegation.provider import (
    _request_input as _request_input,
)
from .delegation.provider import (
    _validated_choice as _validated_choice,
)
from .delegation.roles import (
    _role_guard as _role_guard,
)
from .delegation.selector import (
    DelegationDecisionSelector as DelegationDecisionSelector,
)
