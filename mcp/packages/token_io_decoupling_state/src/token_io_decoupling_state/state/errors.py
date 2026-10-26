"""Public exceptions for deterministic state operations."""

from __future__ import annotations


class StateServiceError(RuntimeError):
    """Base error for deterministic state operations."""


class WorkflowNotOpenError(StateServiceError):
    """No compatible workflow record exists for this trusted binding."""


class RevisionConflictError(StateServiceError):
    """The caller's expected Revision does not match current state."""


class StaleRecoveryCursorError(StateServiceError):
    """A recovery-index cursor refers to an older Root Revision."""


class IdempotencyConflictError(StateServiceError):
    """An idempotency key was reused with another operation or payload."""


class InvalidStateTransitionError(StateServiceError):
    """The requested operation violates the locked mode/allocation/slice state."""


class WorkerInitializationError(StateServiceError):
    """A committed Root event cannot safely initialize or recover its Worker store."""
