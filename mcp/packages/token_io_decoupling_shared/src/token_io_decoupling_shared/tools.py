"""Registration for optional shared state and cross-role evidence tools."""

from __future__ import annotations

from typing import Any

from token_io_decoupling_core.binding import BindingError, BindingProvider
from token_io_decoupling_core.state_models import RecoveryIndexPageRequest
from token_io_decoupling_state.service import StateService
from token_io_decoupling_transport.payloads import _EVIDENCE, _GET_STATE
from token_io_decoupling_transport.registration import ToolRegistrar


def register_shared_tools(
    registrar: ToolRegistrar,
    *,
    service: StateService,
    provider: BindingProvider,
    profile: str | None,
    schema_status: Any,
    binding_diagnostic: Any,
    bound_role_for: Any,
) -> None:
    registrar.register_no_args(
        "database_schema_status",
        lambda: schema_status(service, binding_diagnostic(provider) == "available"),
        codex_guard=registrar.require_codex_context and registrar.embedded,
    )
    if profile != "share":
        return
    registrar.register(
        "state_get",
        _GET_STATE,
        lambda payload: _share_state_get(service, provider, payload.index_page, bound_role_for),
    )
    registrar.register(
        "record_evidence",
        _EVIDENCE,
        lambda payload: _share_record_evidence(service, provider, payload, bound_role_for),
    )


def _share_state_get(
    service: StateService,
    provider: BindingProvider,
    index_page: RecoveryIndexPageRequest | None,
    bound_role_for: Any,
) -> Any:
    role = bound_role_for(provider)
    if role == "parent":
        return service.workflow_get_state(index_page=index_page)
    if role == "worker":
        if index_page is not None:
            raise ValueError("worker state does not accept an index page")
        return service.worker_get_state()
    raise BindingError("usable host binding is unavailable")


def _share_record_evidence(
    service: StateService, provider: BindingProvider, payload: Any, bound_role_for: Any
) -> Any:
    role = bound_role_for(provider)
    if role == "parent":
        return service.workflow_record_evidence(
            payload.submission,
            expected_revision=payload.expected_revision,
            idempotency_key=payload.idempotency_key,
        )
    if role == "worker":
        return service.worker_record_evidence(
            payload.submission,
            expected_revision=payload.expected_revision,
            idempotency_key=payload.idempotency_key,
        )
    raise BindingError("usable host binding is unavailable")
