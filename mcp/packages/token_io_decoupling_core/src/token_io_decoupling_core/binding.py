"""Fail-closed interface to a trusted embedding host's identity and guard data."""

from __future__ import annotations

from typing import Protocol

from token_io_decoupling_core.workflow_contracts.vocabulary import BindingIdentity


class BindingError(PermissionError):
    """Current session scope or required operation permission is unavailable."""


class BindingProvider(Protocol):
    """Internal context seam; both local stdio servers scope calls from request metadata."""

    def current_binding(self) -> BindingIdentity: ...


class DenyingBindingProvider:
    """Unavailable fallback for standalone use without a session context."""

    def current_binding(self) -> BindingIdentity:
        raise BindingError("enhanced state is unavailable without a trusted host binding")
