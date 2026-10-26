"""Trusted role diagnostics shared by the server factory and tool registrars."""

from __future__ import annotations

from token_io_decoupling_core.binding import BindingProvider
from token_io_decoupling_core.state_models import HostGuard, SessionRole
from token_io_decoupling_state.service import StateService


def bound_role(provider: BindingProvider) -> str | None:
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


def binding_diagnostic(provider: BindingProvider) -> str:
    return "available" if bound_role(provider) is not None else "unavailable"


def schema_status(service: StateService, trusted_role: bool) -> dict[str, object]:
    if not trusted_role:
        return {
            "available": False,
            "reason": "trusted session binding unavailable; no state path was inspected",
        }
    return service.database_schema_status().model_dump(mode="json")
