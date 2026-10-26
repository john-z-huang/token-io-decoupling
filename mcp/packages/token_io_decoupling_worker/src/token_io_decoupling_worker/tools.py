"""Registration for worker assignment, progress, evidence, and blocker tools."""

from __future__ import annotations

from token_io_decoupling_state.service import StateService
from token_io_decoupling_transport.payloads import _BLOCKER, _EVIDENCE, _EVIDENCE_ID, _PROGRESS
from token_io_decoupling_transport.registration import ToolRegistrar


def register_worker_tools(registrar: ToolRegistrar, service: StateService) -> None:
    registrar.register_enhanced_no_args(
        "worker_get_assignment", service.worker_get_assignment, role="worker"
    )
    registrar.register_enhanced_no_args("worker_get_state", service.worker_get_state, role="worker")
    registrar.register(
        "worker_record_progress",
        _PROGRESS,
        lambda payload: service.worker_record_progress(
            payload.record,
            expected_revision=payload.expected_revision,
            idempotency_key=payload.idempotency_key,
        ),
        role="worker",
    )
    registrar.register(
        "worker_record_evidence",
        _EVIDENCE,
        lambda payload: service.worker_record_evidence(
            payload.submission,
            expected_revision=payload.expected_revision,
            idempotency_key=payload.idempotency_key,
        ),
        role="worker",
    )
    registrar.register(
        "worker_get_evidence",
        _EVIDENCE_ID,
        lambda payload: service.worker_get_evidence(payload.evidence_id),
        role="worker",
    )
    registrar.register(
        "worker_report_blocker",
        _BLOCKER,
        lambda payload: service.worker_report_blocker(
            payload.blocker,
            expected_revision=payload.expected_revision,
            idempotency_key=payload.idempotency_key,
        ),
        role="worker",
    )
    registrar.register_enhanced_no_args(
        "worker_get_recovery_context", service.worker_get_recovery_context, role="worker"
    )
