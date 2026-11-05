"""Fail-closed interface to a trusted embedding host's identity and guard data."""

from __future__ import annotations

from typing import Protocol

from token_io_decoupling_core.state_models import BindingIdentity, VerifiedChildBinding


class BindingError(PermissionError):
    """Current session scope or required operation permission is unavailable."""


class BindingProvider(Protocol):
    """Internal session-context seam; local CLI profiles configure request scope automatically."""

    def current_binding(self) -> BindingIdentity: ...

    def verify_child_binding(
        self, parent: BindingIdentity, child_session_id: str
    ) -> VerifiedChildBinding: ...


class DenyingBindingProvider:
    """Unavailable fallback for standalone use without a session context."""

    def current_binding(self) -> BindingIdentity:
        raise BindingError("enhanced state is unavailable without a trusted host binding")

    def verify_child_binding(
        self, parent: BindingIdentity, child_session_id: str
    ) -> VerifiedChildBinding:
        del parent, child_session_id
        raise BindingError("child identity verification is unavailable")
