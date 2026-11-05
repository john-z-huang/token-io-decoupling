"""Local stdio request routing; not host or process authentication."""

from __future__ import annotations

import hashlib
import sqlite3
from collections.abc import Generator
from contextlib import closing, contextmanager
from contextvars import ContextVar
from pathlib import Path

from token_io_decoupling_core.binding import BindingError
from token_io_decoupling_core.codex_context import parse_codex_request_context
from token_io_decoupling_core.state_models import (
    BindingIdentity,
    HostCapability,
    SessionRole,
    VerifiedChildBinding,
)

from token_io_decoupling_state.state.identity import (
    _ensure_derived_directory_chain,
    _safe_component,
)


class LocalSessionContext:
    """Use startup cwd and request metadata to scope existing local state.

    Root explicitly registers children with delegation_bind. Fixed server executables
    determine discovery inventories; per-call role and operation guards authorize use.
    They do not prove a role. Same-user code can impersonate metadata or edit local
    files: this is application scoping, not an OS isolation or authentication service.
    """

    def __init__(self, project_root: Path, state_root: Path) -> None:
        self.project_id = hashlib.sha256(str(project_root.resolve()).encode()).hexdigest()
        self.state_root = state_root.resolve()
        self._thread: ContextVar[str | None] = ContextVar("local_codex_thread", default=None)

    @contextmanager
    def request_scope(self, meta: object) -> Generator[None, None, None]:
        caller = parse_codex_request_context(meta)
        thread = _safe_component(caller.thread_id, "threadId")
        token = self._thread.set(thread)
        try:
            yield
        finally:
            self._thread.reset(token)

    def _parent_for(self, thread: str) -> str | None:
        project = self.state_root / self.project_id
        _ensure_derived_directory_chain(self.state_root, project, create=False)
        if not project.exists():
            return None
        parents: list[str] = []
        for root in project.iterdir():
            _safe_component(root.name, "root_session_id")
            _ensure_derived_directory_chain(self.state_root, root, create=False)
            database = root / "workflow.sqlite3"
            worker = root / "subagents" / thread / "worker.sqlite3"
            if not database.exists() and not database.is_symlink():
                continue
            if database.is_symlink():
                raise BindingError("symlink in local session state")
            try:
                with closing(
                    sqlite3.connect(database.as_uri() + "?mode=ro", uri=True)
                ) as connection:
                    row = connection.execute(
                        "SELECT status FROM allocations WHERE worker_session_id=?", (thread,)
                    ).fetchone()
                if row is None:
                    continue
                if row[0] not in {"bound", "initialized"}:
                    raise BindingError("Worker has no active Root allocation")
                _ensure_derived_directory_chain(self.state_root, worker.parent, create=False)
                if worker.is_symlink() or not worker.is_file():
                    raise BindingError("Worker state is missing or unsafe")
                with closing(sqlite3.connect(worker.as_uri() + "?mode=ro", uri=True)) as connection:
                    identity = connection.execute(
                        "SELECT project_id,root_session_id,worker_session_id "
                        "FROM worker_identity WHERE singleton=1"
                    ).fetchone()
                if identity != (self.project_id, root.name, thread):
                    raise BindingError("Worker state identity does not match its local path")
            except sqlite3.Error as exc:
                raise BindingError("local session state cannot be read") from exc
            parents.append(root.name)
        if len(parents) > 1:
            raise BindingError("Worker is registered under multiple Roots")
        return parents[0] if parents else None

    def current_binding(self) -> BindingIdentity:
        thread = self._thread.get()
        if thread is None:
            raise BindingError("local Codex request context is required")
        parent = self._parent_for(thread)
        role = SessionRole.WORKER if parent is not None else SessionRole.PARENT
        capabilities = (
            {HostCapability.WORKER_READ, HostCapability.WORKER_WRITE}
            if parent is not None
            else set(HostCapability) - {HostCapability.WORKER_READ, HostCapability.WORKER_WRITE}
        )
        return BindingIdentity(
            project_id=self.project_id,
            root_session_id=parent or thread,
            current_session_id=thread,
            parent_session_id=parent,
            role=role,
            capabilities=frozenset(capabilities),
            guards=frozenset(),
        )

    def verify_child_binding(
        self, parent: BindingIdentity, child_session_id: str
    ) -> VerifiedChildBinding:
        child = _safe_component(child_session_id, "child_session_id")
        if parent != self.current_binding() or parent.role is not SessionRole.PARENT:
            raise BindingError("child registration requires the current Root")
        if child == parent.current_session_id:
            raise BindingError("a Root cannot register itself as a Worker")
        previous = self._parent_for(child)
        if previous is not None and previous != parent.current_session_id:
            raise BindingError("Worker already belongs to a different Root")
        root_path = self.state_root / self.project_id / child
        _ensure_derived_directory_chain(self.state_root, root_path, create=False)
        if (root_path / "workflow.sqlite3").exists():
            raise BindingError("an existing Root cannot be registered as a Worker")
        return VerifiedChildBinding(
            project_id=self.project_id,
            root_session_id=parent.root_session_id,
            parent_session_id=parent.current_session_id,
            child_session_id=child,
            capabilities=frozenset(
                {
                    HostCapability.WORKER_READ,
                    HostCapability.WORKER_WRITE,
                    HostCapability.WORKER_STORE_CREATE,
                    HostCapability.PARENT_SUMMARY_READ,
                }
            ),
            guards=frozenset(),
        )
