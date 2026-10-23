"""Fail-closed interface to a trusted embedding host's identity and guard data."""

from __future__ import annotations

from typing import Protocol

from token_io_mcp.state_models import BindingIdentity, VerifiedChildBinding


class BindingError(PermissionError):
    """Trusted runtime identity or a required permission boundary is unavailable."""


class BindingProvider(Protocol):
    """The host supplies this provider; request parameters never establish identity."""

    def current_binding(self) -> BindingIdentity: ...

    def verify_child_binding(
        self, parent: BindingIdentity, child_session_id: str
    ) -> VerifiedChildBinding: ...


class DenyingBindingProvider:
    """Production default until a concrete trusted host adapter is implemented."""

    def current_binding(self) -> BindingIdentity:
        raise BindingError("enhanced state is unavailable without a trusted host binding")

    def verify_child_binding(
        self, parent: BindingIdentity, child_session_id: str
    ) -> VerifiedChildBinding:
        del parent, child_session_id
        raise BindingError("child identity verification is unavailable")
