"""Trusted role diagnostics shared by the server factory and tool registrars."""

from __future__ import annotations

from token_io_decoupling_core.binding import BindingError, BindingProvider, DenyingBindingProvider
from token_io_decoupling_core.state_models import BindingIdentity, HostGuard, SessionRole
from token_io_decoupling_state.service import StateService


def binding_details(provider: BindingProvider) -> dict[str, str]:
    """Probe baseline binding once, returning only fixed, public diagnostic text."""

    def result(status: str, code: str, message: str, next_step: str) -> dict[str, str]:
        return {
            "status": status,
            "reason_code": code,
            "message": message,
            "source": "provider.current_binding/baseline_validation",
            "next_step": next_step,
        }

    if type(provider) is DenyingBindingProvider:
        diagnostic = result(
            "unverified",
            "provider_not_configured",
            "No trusted host binding provider is configured; no probe was attempted.",
            "Use Native, or configure a trusted host provider through the host integration.",
        )
        diagnostic["source"] = "server.default_provider"
        return diagnostic
    try:
        binding = provider.current_binding()
    except BindingError:
        return result(
            "unknown",
            "binding_unavailable",
            "The provider could not supply a binding; the underlying cause is unknown.",
            "Check trusted host diagnostics for the underlying cause; continue on Native.",
        )
    except PermissionError:
        return result(
            "unavailable",
            "permission_denied",
            "The binding probe was denied permission.",
            "Have the host integration owner check binding permissions; continue on Native.",
        )
    except Exception:
        return result(
            "unknown",
            "probe_failed",
            "The binding probe failed for an unspecified reason.",
            "Have the host integration owner inspect the provider; continue on Native.",
        )
    if not isinstance(binding, BindingIdentity):
        return result(
            "unknown",
            "invalid_binding_response",
            "The provider returned an invalid binding value.",
            "Repair the provider's typed binding response; continue on Native.",
        )
    baseline = {HostGuard.IDENTITY_BOUND, HostGuard.SESSION_BOUND, HostGuard.PATH_BOUNDARY}
    if binding.role is SessionRole.WORKER:
        baseline.add(HostGuard.WORKER_STORE_ISOLATION)
    relationship_valid = (
        binding.role is SessionRole.PARENT and binding.current_session_id == binding.root_session_id
    ) or (
        binding.role is SessionRole.WORKER and binding.parent_session_id == binding.root_session_id
    )
    if not relationship_valid:
        return result(
            "unavailable",
            "session_identity_mismatch",
            "The binding does not satisfy the role's session relationship.",
            "Correct the host's session/role binding; do not substitute caller-supplied identity.",
        )
    if not baseline <= binding.guards:
        return result(
            "unavailable",
            "required_guards_missing",
            "The binding lacks one or more baseline guards required for its role.",
            "Have the trusted host supply the required guards; do not bypass operation checks.",
        )
    diagnostic = result(
        "available",
        "baseline_verified",
        "Session relationship and baseline guards passed; operation-specific checks still apply.",
        "Check the intended operation's guards and caller context before protected access.",
    )
    diagnostic["role"] = "parent" if binding.role is SessionRole.PARENT else "worker"
    return diagnostic


def bound_role(provider: BindingProvider) -> str | None:
    return binding_details(provider).get("role")


def binding_diagnostic(provider: BindingProvider) -> str:
    return "available" if bound_role(provider) is not None else "unavailable"


def schema_status(service: StateService, trusted_role: bool) -> dict[str, object]:
    if not trusted_role:
        return {
            "available": False,
            "reason": "trusted session binding unavailable; no state path was inspected",
        }
    return service.database_schema_status().model_dump(mode="json")
