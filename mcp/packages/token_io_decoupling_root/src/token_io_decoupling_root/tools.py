"""Registration for parent-only workflow mutation and delegation tools."""

from __future__ import annotations

from token_io_decoupling_core.state_models import WorkflowOpenRequest
from token_io_decoupling_state.service import StateService
from token_io_decoupling_transport.payloads import (
    _ALLOCATION,
    _BIND,
    _EVIDENCE,
    _GET_STATE,
    _RECONCILE,
    _RESERVE,
    _SLICE,
    _SLICE_RELEASE,
    _TRANSITION,
)
from token_io_decoupling_transport.registration import ToolRegistrar


def register_root_tools(registrar: ToolRegistrar, service: StateService) -> None:
    registrar.register(
        "workflow_open",
        WorkflowOpenRequest,
        lambda payload: service.workflow_open(payload),
        role="parent",
    )
    registrar.register(
        "workflow_get_state",
        _GET_STATE,
        lambda payload: service.workflow_get_state(index_page=payload.index_page),
        role="parent",
    )
    registrar.register(
        "delegation_reserve",
        _RESERVE,
        lambda payload: service.delegation_reserve(
            payload.role,
            expected_revision=payload.expected_revision,
            idempotency_key=payload.idempotency_key,
        ),
        role="parent",
    )
    registrar.register(
        "delegation_bind",
        _BIND,
        lambda payload: service.delegation_bind(
            payload.allocation_id,
            payload.child_session_id,
            expected_revision=payload.expected_revision,
            idempotency_key=payload.idempotency_key,
        ),
        role="parent",
    )
    registrar.register(
        "slice_check",
        _SLICE,
        lambda payload: service.slice_check(payload.spec),
        role="parent",
    )
    registrar.register(
        "slice_release",
        _SLICE_RELEASE,
        lambda payload: service.slice_release(
            payload.spec,
            expected_revision=payload.expected_revision,
            idempotency_key=payload.idempotency_key,
        ),
        role="parent",
    )
    registrar.register(
        "workflow_record_evidence",
        _EVIDENCE,
        lambda payload: service.workflow_record_evidence(
            payload.submission,
            expected_revision=payload.expected_revision,
            idempotency_key=payload.idempotency_key,
        ),
        role="parent",
    )
    registrar.register(
        "workflow_transition",
        _TRANSITION,
        lambda payload: service.workflow_transition(payload.request),
        role="parent",
    )
    registrar.register(
        "parent_get_worker_summary",
        _ALLOCATION,
        lambda payload: service.parent_get_worker_summary(payload.allocation_id),
        role="parent",
    )
    registrar.register(
        "workflow_reconcile",
        _RECONCILE,
        lambda payload: service.workflow_reconcile(
            payload.snapshot,
            confirm=payload.confirm,
            expected_revision=payload.expected_revision,
            idempotency_key=payload.idempotency_key,
        ),
        role="parent",
    )
