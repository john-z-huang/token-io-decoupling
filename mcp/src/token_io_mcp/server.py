"""Official MCP v2 stdio transport for the bounded Token I/O API."""

from __future__ import annotations

import json
from collections.abc import Callable
from importlib import resources
from pathlib import Path
from typing import Annotated, Any, Literal

from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import BaseModel, TypeAdapter, ValidationError, WithJsonSchema, create_model

from token_io_mcp.binding import BindingError, BindingProvider, DenyingBindingProvider
from token_io_mcp.decisions import (
    DecisionAdvice,
    DecisionAdvisoryInput,
    DecisionsAdvisor,
    DecisionsRuntimeConfig,
    EvaluationWithAdvice,
)
from token_io_mcp.models import NonEmptyString, StrictModel
from token_io_mcp.rules import RuleLoader
from token_io_mcp.state_models import (
    BlockerRecord,
    CheckpointNode,
    EvidenceSubmission,
    HostGuard,
    LegalBranch,
    NativeWorkflowSnapshot,
    ProgressRecord,
    RecoveryIndexPageRequest,
    SessionRole,
    SliceSpec,
    WorkflowOpenRequest,
    WorkflowTransitionRequest,
)
from token_io_mcp.state_service import StateService, StateServiceError


class ToolPayload(StrictModel):
    """Shared base for strict, extra-forbidden wire payload containers."""


def _payload_model(name: str, **fields: Any) -> type[BaseModel]:
    return create_model(name, __base__=ToolPayload, **fields)


def _inline_schema(model: type[BaseModel]) -> dict[str, Any]:
    schema = model.model_json_schema()
    definitions = schema.pop("$defs", {})

    def expand(value: Any) -> Any:
        if isinstance(value, dict):
            reference = value.get("$ref")
            if isinstance(reference, str) and reference.startswith("#/$defs/"):
                target = definitions[reference.rsplit("/", 1)[1]]
                siblings = {key: item for key, item in value.items() if key != "$ref"}
                return {**expand(target), **expand(siblings)}
            return {key: expand(item) for key, item in value.items()}
        if isinstance(value, list):
            return [expand(item) for item in value]
        return value

    return expand(schema)


_NO_ARGUMENTS = _payload_model("NoArguments")
_GET_STATE = _payload_model("GetStatePayload", index_page=(RecoveryIndexPageRequest | None, None))
_RESERVE = _payload_model(
    "ReservePayload",
    role=(NonEmptyString, ...),
    expected_revision=(int, ...),
    idempotency_key=(NonEmptyString, ...),
)
_BIND = _payload_model(
    "BindPayload",
    allocation_id=(NonEmptyString, ...),
    child_session_id=(NonEmptyString, ...),
    expected_revision=(int, ...),
    idempotency_key=(NonEmptyString, ...),
)
_SLICE = _payload_model("SlicePayload", spec=(SliceSpec, ...))
_SLICE_RELEASE = _payload_model(
    "SliceReleasePayload",
    spec=(SliceSpec, ...),
    expected_revision=(int, ...),
    idempotency_key=(NonEmptyString, ...),
)
_EVALUATE = _payload_model(
    "EvaluatePayload",
    node_id=(CheckpointNode, ...),
    expected_revision=(int, ...),
    idempotency_key=(NonEmptyString, ...),
    branch=(LegalBranch | None, None),
    input_hash=(str | None, None),
    slice_ids=(list[NonEmptyString] | None, None),
    semantic_input=(DecisionAdvisoryInput | None, None),
)
_CONTROL_EVALUATE = _payload_model(
    "ControlEvaluatePayload",
    expected_revision=(int, ...),
    idempotency_key=(NonEmptyString, ...),
    branch=(LegalBranch | None, None),
    input_hash=(str | None, None),
    slice_ids=(list[NonEmptyString] | None, None),
    semantic_input=(DecisionAdvisoryInput | None, None),
)
_EVIDENCE = _payload_model(
    "EvidencePayload",
    submission=(EvidenceSubmission, ...),
    expected_revision=(int, ...),
    idempotency_key=(NonEmptyString, ...),
)
_RECONCILE = _payload_model(
    "ReconcilePayload",
    snapshot=(NativeWorkflowSnapshot, ...),
    confirm=(bool, False),
    expected_revision=(int, ...),
    idempotency_key=(NonEmptyString, ...),
)
_ALLOCATION = _payload_model("AllocationPayload", allocation_id=(NonEmptyString, ...))
_EVIDENCE_ID = _payload_model("EvidenceIdPayload", evidence_id=(NonEmptyString, ...))
_PROGRESS = _payload_model(
    "ProgressPayload",
    record=(ProgressRecord, ...),
    expected_revision=(int, ...),
    idempotency_key=(NonEmptyString, ...),
)
_BLOCKER = _payload_model(
    "BlockerPayload",
    blocker=(BlockerRecord, ...),
    expected_revision=(int, ...),
    idempotency_key=(NonEmptyString, ...),
)
_RULE_CONTEXT = _payload_model(
    "RuleContextPayload",
    node_id=(CheckpointNode, ...),
    language=(Literal["en", "zh_cn"], "en"),
)


def _jsonable(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


def _call_safely(callback: Callable[[], Any]) -> Any:
    try:
        return _jsonable(callback())
    except BindingError as exc:
        raise ToolError("trusted host binding or required guard is unavailable") from exc
    except StateServiceError as exc:
        raise ToolError(str(exc)) from exc
    except (ValidationError, ValueError, TypeError) as exc:
        raise ToolError("request violates the typed operation contract") from exc


def _evaluate_with_advice(
    evaluation: Any,
    advisory_input: DecisionAdvisoryInput | None,
    advisor: DecisionsAdvisor,
    *,
    replayed: bool = False,
) -> Any:
    if advisory_input is None:
        return evaluation
    if advisory_input.node_id is not evaluation.node_id:
        return EvaluationWithAdvice(
            evaluation=evaluation,
            advice=DecisionAdvice(
                status="fallback",
                reason="invalid_response",
                node_id=advisory_input.node_id,
            ),
        )
    if replayed:
        advice = DecisionAdvice(
            status="fallback",
            reason="idempotent_replay",
            node_id=advisory_input.node_id,
        )
    else:
        advice = advisor.advise(advisory_input, core_evaluation=evaluation)
    return EvaluationWithAdvice(evaluation=evaluation, advice=advice)


def create_server(
    binding_provider: BindingProvider | None = None,
    *,
    state_root: Path | str | None = None,
    decisions_config: DecisionsRuntimeConfig | None = None,
    decisions_client_factory: Callable[[str, str], object] | None = None,
) -> MCPServer[Any]:
    """Create a public-only server by default or a trusted embedding server.

    Passing a provider is an embedding-only capability boundary. The production CLI
    never accepts or constructs one. Every enhanced operation still re-reads that
    provider through StateService, so revocation takes effect on the next call.
    """
    provider = binding_provider or DenyingBindingProvider()
    registry_resource = resources.files("token_io_mcp").joinpath("_resources", "registry.json")
    rules = (
        RuleLoader()
        if registry_resource.is_file()
        else RuleLoader(repository_root=Path(__file__).resolve().parents[3])
    )
    service = StateService(binding_provider=provider, state_root=state_root, rule_loader=rules)
    decisions = DecisionsAdvisor(
        service,
        rules,
        decisions_config or DecisionsRuntimeConfig(),
        client_factory=decisions_client_factory,
    )
    server = MCPServer(name="token-io-mcp", version="0.1.0")
    bound_role = _bound_role(provider) if binding_provider is not None else None
    embedded = bound_role is not None

    def register(
        name: str,
        payload_type: type[BaseModel],
        callback: Callable[[Any], Any],
        *,
        enhanced: bool = True,
        role: str | None = None,
    ) -> None:
        if role is not None and role != bound_role:
            return

        def handler(payload: dict[str, Any]) -> Any:
            if enhanced and not embedded:
                raise ToolError("enhanced operations are unavailable in the unbound CLI")
            return _call_safely(
                lambda: callback(
                    TypeAdapter(payload_type).validate_json(json.dumps(payload, ensure_ascii=False))
                )
            )

        handler.__name__ = name
        handler.__doc__ = f"Perform the typed {name} operation."
        handler.__annotations__ = {
            "payload": Annotated[dict[str, Any], WithJsonSchema(_inline_schema(payload_type))],
            "return": dict[str, Any],
        }
        server.tool(name=name, structured_output=False)(handler)

    def register_no_args(name: str, callback: Callable[[], Any]) -> None:
        def handler() -> Any:
            return _call_safely(callback)

        handler.__name__ = name
        handler.__doc__ = f"Return public {name} information."
        handler.__annotations__ = {"return": dict[str, Any]}
        server.tool(name=name, structured_output=False)(handler)

    register_no_args(
        "workflow_capabilities",
        lambda: {
            "subsystem": "token-io-mcp",
            "supported_transports": ["stdio"],
            "host_adapters": {
                "Codex Desktop": {
                    "identity_attestation": "unavailable",
                    "guard_binding": "unavailable",
                },
                "ChatGPT Desktop": {
                    "identity_attestation": "unavailable",
                    "guard_binding": "unavailable",
                },
            },
            "enhanced_binding": "unverified" if not embedded else _binding_diagnostic(provider),
            "mode_fallback": "Native",
            "api_decisions": "enabled"
            if decisions_config and decisions_config.enabled
            else "disabled",
            "protocol_target": "2026-07-28",
        },
    )
    register(
        "rules_get_context",
        _RULE_CONTEXT,
        lambda p: rules.load_context(p.node_id.value, language=p.language),
        enhanced=False,
    )
    register_no_args(
        "database_schema_status",
        lambda: _schema_status(service, bound_role in {"parent", "worker"}),
    )

    if not embedded:
        return server

    def register_enhanced_no_args(name: str, callback: Callable[[], Any], *, role: str) -> None:
        if role != bound_role:
            return

        def handler() -> Any:
            if not embedded:
                raise ToolError("enhanced operations are unavailable in the unbound CLI")
            return _call_safely(callback)

        handler.__name__ = name
        handler.__doc__ = f"Perform the bound {name} operation."
        handler.__annotations__ = {"return": dict[str, Any]}
        server.tool(name=name, structured_output=False)(handler)

    # Each callback is only a typed adapter; identity, roles and guards are resolved
    # and checked inside StateService for every invocation.
    register(
        "workflow_open", WorkflowOpenRequest, lambda p: service.workflow_open(p), role="parent"
    )
    register(
        "workflow_get_state",
        _GET_STATE,
        lambda p: service.workflow_get_state(index_page=p.index_page),
        role="parent",
    )
    register(
        "delegation_reserve",
        _RESERVE,
        lambda p: service.delegation_reserve(
            p.role,
            expected_revision=p.expected_revision,
            idempotency_key=p.idempotency_key,
        ),
        role="parent",
    )
    register(
        "delegation_bind",
        _BIND,
        lambda p: service.delegation_bind(
            p.allocation_id,
            p.child_session_id,
            expected_revision=p.expected_revision,
            idempotency_key=p.idempotency_key,
        ),
        role="parent",
    )
    register("slice_check", _SLICE, lambda p: service.slice_check(p.spec), role="parent")
    register(
        "slice_release",
        _SLICE_RELEASE,
        lambda p: service.slice_release(
            p.spec,
            expected_revision=p.expected_revision,
            idempotency_key=p.idempotency_key,
        ),
        role="parent",
    )

    def evaluate_node(p: Any) -> Any:
        if p.semantic_input is None:
            return service.workflow_evaluate(
                p.node_id,
                expected_revision=p.expected_revision,
                idempotency_key=p.idempotency_key,
                branch=p.branch.value if p.branch else None,
                input_hash=p.input_hash,
                slice_ids=p.slice_ids,
            )
        if p.semantic_input.node_id is not p.node_id:
            raise ValueError("semantic input node must match the evaluated checkpoint")
        evaluation, replayed = service.workflow_evaluate_with_replay(
            p.node_id,
            expected_revision=p.expected_revision,
            idempotency_key=p.idempotency_key,
            branch=p.branch.value if p.branch else None,
            input_hash=p.input_hash,
            slice_ids=p.slice_ids,
        )
        return _evaluate_with_advice(evaluation, p.semantic_input, decisions, replayed=replayed)

    def evaluate_control(p: Any) -> Any:
        if p.semantic_input is None:
            return service.evaluate_control_checkpoint(
                expected_revision=p.expected_revision,
                idempotency_key=p.idempotency_key,
                branch=p.branch.value if p.branch else None,
                input_hash=p.input_hash,
                slice_ids=p.slice_ids,
            )
        if p.semantic_input.node_id is not CheckpointNode.CONTROL:
            raise ValueError("control evaluation requires Control semantic input")
        evaluation, replayed = service.evaluate_control_checkpoint_with_replay(
            expected_revision=p.expected_revision,
            idempotency_key=p.idempotency_key,
            branch=p.branch.value if p.branch else None,
            input_hash=p.input_hash,
            slice_ids=p.slice_ids,
        )
        return _evaluate_with_advice(evaluation, p.semantic_input, decisions, replayed=replayed)

    register(
        "workflow_evaluate",
        _EVALUATE,
        evaluate_node,
        role="parent",
    )
    register(
        "evaluate_control_checkpoint",
        _CONTROL_EVALUATE,
        evaluate_control,
        role="parent",
    )
    register(
        "workflow_record_evidence",
        _EVIDENCE,
        lambda p: service.workflow_record_evidence(
            p.submission,
            expected_revision=p.expected_revision,
            idempotency_key=p.idempotency_key,
        ),
        role="parent",
    )
    register(
        "workflow_transition",
        _payload_model("TransitionPayload", request=(WorkflowTransitionRequest, ...)),
        lambda p: service.workflow_transition(p.request),
        role="parent",
    )
    register(
        "parent_get_worker_summary",
        _ALLOCATION,
        lambda p: service.parent_get_worker_summary(p.allocation_id),
        role="parent",
    )
    register(
        "workflow_reconcile",
        _RECONCILE,
        lambda p: service.workflow_reconcile(
            p.snapshot,
            confirm=p.confirm,
            expected_revision=p.expected_revision,
            idempotency_key=p.idempotency_key,
        ),
        role="parent",
    )
    register_enhanced_no_args("worker_get_assignment", service.worker_get_assignment, role="worker")
    register_enhanced_no_args("worker_get_state", service.worker_get_state, role="worker")
    register(
        "worker_record_progress",
        _PROGRESS,
        lambda p: service.worker_record_progress(
            p.record,
            expected_revision=p.expected_revision,
            idempotency_key=p.idempotency_key,
        ),
        role="worker",
    )
    register(
        "worker_record_evidence",
        _EVIDENCE,
        lambda p: service.worker_record_evidence(
            p.submission,
            expected_revision=p.expected_revision,
            idempotency_key=p.idempotency_key,
        ),
        role="worker",
    )
    register(
        "worker_get_evidence",
        _EVIDENCE_ID,
        lambda p: service.worker_get_evidence(p.evidence_id),
        role="worker",
    )
    register(
        "worker_report_blocker",
        _BLOCKER,
        lambda p: service.worker_report_blocker(
            p.blocker,
            expected_revision=p.expected_revision,
            idempotency_key=p.idempotency_key,
        ),
        role="worker",
    )
    register_enhanced_no_args(
        "worker_get_recovery_context", service.worker_get_recovery_context, role="worker"
    )
    return server


def _bound_role(provider: BindingProvider) -> str | None:
    try:
        binding = provider.current_binding()
    except Exception:
        return None
    baseline = {HostGuard.IDENTITY_BOUND, HostGuard.SESSION_BOUND, HostGuard.PATH_BOUNDARY}
    if binding.role is SessionRole.PARENT:
        if binding.current_session_id == binding.root_session_id and baseline <= binding.guards:
            return "parent"
    if binding.role is SessionRole.WORKER:
        if (
            binding.parent_session_id == binding.root_session_id
            and baseline | {HostGuard.WORKER_STORE_ISOLATION} <= binding.guards
        ):
            return "worker"
    return None


def _binding_diagnostic(provider: BindingProvider) -> str:
    return "available" if _bound_role(provider) is not None else "unavailable"


def _schema_status(service: StateService, trusted_role: bool) -> dict[str, object]:
    if not trusted_role:
        return {
            "available": False,
            "reason": "trusted session binding unavailable; no state path was inspected",
        }
    return service.database_schema_status().model_dump(mode="json")
