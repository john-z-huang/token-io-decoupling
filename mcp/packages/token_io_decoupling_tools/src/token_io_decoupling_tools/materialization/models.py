"""物化分配、启动配置、独立授权提供者与调用绑定。"""

from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Mapping
from contextvars import ContextVar
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Annotated, Literal, Protocol, TypeAlias

from pydantic import (
    ConfigDict,
    Field,
    StringConstraints,
    TypeAdapter,
    field_validator,
)

from token_io_decoupling_core.materialization_models import (
    MaterializationRequest,
    OutputMaterializationGrant,
)
from token_io_decoupling_core.models import NonEmptyString, StrictModel
from token_io_decoupling_core.workflow_contracts.vocabulary import BindingIdentity


class MaterializationGrantProvider(Protocol):
    """Trusted operator source for a fresh, independently revocable grant."""

    def current_grant(self) -> OutputMaterializationGrant | Mapping[str, object] | None: ...


class MaterializationAssignment(StrictModel):
    """Finite current assignment facts returned by a trusted startup provider."""

    model_config = ConfigDict(frozen=True)

    project_id: NonEmptyString
    root_session_id: NonEmptyString
    worker_session_id: NonEmptyString
    allocation_id: NonEmptyString
    role: Literal["Primary Output"]
    output_class: Literal["code_configuration"]
    slice_id: NonEmptyString
    authorized_paths: Annotated[
        tuple[Annotated[str, StringConstraints(min_length=1, max_length=512)], ...],
        Field(min_length=1, max_length=128),
    ]

    @field_validator("authorized_paths")
    @classmethod
    def validate_paths(cls, paths: tuple[str, ...]) -> tuple[str, ...]:
        if len(paths) != len(set(paths)):
            raise ValueError("assignment_paths_must_be_unique")
        for path in paths:
            parsed = PurePosixPath(path)
            if (
                path.startswith("/")
                or "\\" in path
                or parsed.is_absolute()
                or parsed.as_posix() != path
                or any(part in {"", ".", ".."} for part in path.split("/"))
            ):
                raise ValueError("assignment_path_invalid")
        return paths


def materialization_assignment_hash(assignment: MaterializationAssignment) -> str:
    canonical = json.dumps(
        assignment.model_dump(mode="json"),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class MaterializationAuthorizationContext:
    """Trusted startup supplied current binding and assignment; never a tool payload."""

    binding: BindingIdentity
    assignment: MaterializationAssignment
    assignment_hash: str


class MaterializationAuthorizationProvider(Protocol):
    """Trusted source for a freshly checked Worker assignment and identity."""

    def current_context(self) -> MaterializationAuthorizationContext: ...


MaterializationReceiptStatus: TypeAlias = Literal[
    "applied", "already_identical", "partial", "conflict", "uncertain"
]


@dataclass(frozen=True, slots=True)
class OutputMaterializerConfig:
    """Typed startup configuration returned only by an explicit trusted factory."""

    project_root: str | os.PathLike[str]
    artifact_root: str | os.PathLike[str]
    grant_provider: MaterializationGrantProvider
    authorization_provider: MaterializationAuthorizationProvider

    def __post_init__(self) -> None:
        project_root = Path(self.project_root)
        artifact_root = Path(self.artifact_root)
        if not project_root.is_absolute() or not artifact_root.is_absolute():
            raise ValueError("materialization_roots_must_be_absolute")
        if not callable(getattr(self.grant_provider, "current_grant", None)):
            raise ValueError("materialization_grant_provider_invalid")
        if not callable(getattr(self.authorization_provider, "current_context", None)):
            raise ValueError("materialization_authorization_provider_invalid")
        object.__setattr__(self, "project_root", project_root)
        object.__setattr__(self, "artifact_root", artifact_root)


class _MaterializationFailure(Exception):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


_REQUEST_ADAPTER = TypeAdapter(MaterializationRequest)


_CALLER_BINDING: ContextVar[BindingIdentity | None] = ContextVar(
    "materialization_caller_binding", default=None
)
