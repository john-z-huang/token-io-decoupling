"""Strict extraction of Codex caller context from MCP request metadata."""

from __future__ import annotations

import unicodedata
from collections.abc import Generator, Mapping
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass

from token_io_decoupling_core.binding import BindingError, BindingProvider
from token_io_decoupling_core.state_models import BindingIdentity, VerifiedChildBinding

_MAX_CONTEXT_VALUE = 256


@dataclass(frozen=True)
class CodexRequestContext:
    """Validated caller fields; session ID is opaque and never selects authority."""

    thread_id: str
    session_id: str


def parse_codex_request_context(meta: object) -> CodexRequestContext:
    """Read only threadId/sessionId from a request `_meta` mapping."""
    if not isinstance(meta, Mapping):
        raise BindingError("Codex caller context is missing or malformed")
    thread_id = _context_value(meta, "threadId")
    session_id = _context_value(meta, "sessionId")
    return CodexRequestContext(thread_id=thread_id, session_id=session_id)


class CodexCallerBoundProvider:
    """Apply request-thread matching to every identity read made by a state service."""

    def __init__(self, provider: BindingProvider) -> None:
        self._provider = provider
        self._request_thread_id: ContextVar[str | None] = ContextVar(
            f"token_io_codex_thread_{id(self)}", default=None
        )

    @contextmanager
    def request_scope(self, meta: object) -> Generator[None, None, None]:
        caller = parse_codex_request_context(meta)
        initial = self._provider.current_binding()
        if caller.thread_id != initial.current_session_id:
            raise BindingError("Codex caller thread does not match the verified session")
        token = self._request_thread_id.set(caller.thread_id)
        try:
            yield
        finally:
            self._request_thread_id.reset(token)

    def current_binding(self) -> BindingIdentity:
        binding = self._provider.current_binding()
        request_thread_id = self._request_thread_id.get()
        if request_thread_id is None or request_thread_id != binding.current_session_id:
            raise BindingError("Codex caller context is unavailable or mismatched")
        return binding

    def verify_child_binding(
        self, parent: BindingIdentity, child_session_id: str
    ) -> VerifiedChildBinding:
        binding = self.current_binding()
        if parent != binding:
            raise BindingError("requested parent does not match the verified session")
        return self._provider.verify_child_binding(binding, child_session_id)


def _context_value(meta: Mapping[object, object], key: str) -> str:
    value = meta.get(key)
    if (
        not isinstance(value, str)
        or not value.strip()
        or len(value) > _MAX_CONTEXT_VALUE
        or any(unicodedata.category(character) == "Cc" for character in value)
    ):
        raise BindingError("Codex caller context is missing or malformed")
    return value
