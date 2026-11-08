"""复核 Worker 绑定、分配、根目录身份与操作员 grant。"""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

from token_io_decoupling_core.materialization_models import (
    FactMarkdownTemplate,
    MaterializationBindingFingerprint,
    MaterializationFileSpec,
    OutputMaterializationGrant,
    PreparedMaterializationManifest,
)
from token_io_decoupling_core.workflow_contracts.vocabulary import (
    BindingIdentity,
    HostCapability,
    HostGuard,
    SessionRole,
)
from token_io_decoupling_tools.artifact_storage.filesystem import MaterializationStorageError

from .models import (
    _CALLER_BINDING,
    MaterializationAssignment,
    MaterializationAuthorizationContext,
    _MaterializationFailure,
    materialization_assignment_hash,
)

if TYPE_CHECKING:
    from .service import OutputMaterializationService


def validate_worker_binding(
    service: OutputMaterializationService,
    context: MaterializationAuthorizationContext,
    binding: BindingIdentity,
) -> None:
    if _CALLER_BINDING.get() is None or context.binding != _CALLER_BINDING.get():
        raise _MaterializationFailure("caller_binding_assignment_mismatch")
    if not isinstance(binding, BindingIdentity) or binding.role is not SessionRole.WORKER:
        raise _MaterializationFailure("worker_binding_invalid")
    if HostCapability.WORKER_WRITE not in binding.capabilities:
        raise _MaterializationFailure("worker_write_capability_missing")
    required_guards = {
        HostGuard.IDENTITY_BOUND,
        HostGuard.SESSION_BOUND,
        HostGuard.PATH_BOUNDARY,
        HostGuard.PARENT_CHILD_RELATION,
    }
    if not required_guards <= binding.guards:
        raise _MaterializationFailure("worker_binding_guards_missing")


def validate_assignment_binding(
    service: OutputMaterializationService, binding: BindingIdentity, assignment: dict[str, Any]
) -> None:
    project_id = service._required_assignment_text(assignment, "project_id")
    root_session_id = service._required_assignment_text(assignment, "root_session_id")
    worker_session_id = service._required_assignment_text(assignment, "worker_session_id")
    service._required_assignment_text(assignment, "allocation_id")
    role = service._required_assignment_text(assignment, "role")
    output_class = service._required_assignment_text(assignment, "output_class")
    service._required_assignment_text(assignment, "slice_id")
    if (
        service._identity_value(binding, "project_id") != project_id
        or service._identity_value(binding, "root_session_id") != root_session_id
        or service._identity_value(binding, "current_session_id") != worker_session_id
        or service._identity_value(binding, "parent_session_id") != root_session_id
    ):
        raise _MaterializationFailure("worker_assignment_binding_mismatch")
    if role != "Primary Output" or output_class not in {
        "code_configuration",
    }:
        raise _MaterializationFailure("worker_role_output_class_unsupported")


def current_operator_grant(service: OutputMaterializationService) -> OutputMaterializationGrant:
    try:
        grant_raw = service._config.grant_provider.current_grant()
        if isinstance(grant_raw, OutputMaterializationGrant):
            grant = OutputMaterializationGrant.model_validate(grant_raw, strict=True)
        elif isinstance(grant_raw, Mapping):
            grant = OutputMaterializationGrant.model_validate(dict(grant_raw), strict=True)
        else:
            raise ValueError("operator_grant_missing")
    except Exception as exc:
        raise _MaterializationFailure("operator_grant_unavailable_or_invalid") from exc
    return grant


def authorize(service: OutputMaterializationService) -> dict[str, Any]:
    assert service._storage is not None
    try:
        context = service._authorization_provider.current_context()
        if not isinstance(context.assignment, MaterializationAssignment):
            raise ValueError("worker_assignment_invalid")
        assignment_model = MaterializationAssignment.model_validate_json(
            context.assignment.model_dump_json()
        )
        assignment_hash = materialization_assignment_hash(assignment_model)
        if context.assignment_hash != assignment_hash:
            raise ValueError("worker_assignment_hash_mismatch")
        binding = context.binding
        assignment = assignment_model.model_dump(mode="json")
    except Exception as exc:
        reason = (
            str(exc)
            if str(exc) in {"worker_assignment_invalid", "worker_assignment_hash_mismatch"}
            else "worker_assignment_unavailable"
        )
        raise _MaterializationFailure(reason) from exc
    if not isinstance(assignment, dict):
        raise _MaterializationFailure("worker_assignment_unavailable")
    service._validate_worker_binding(context, binding)
    service._validate_assignment_binding(binding, assignment)
    try:
        service._storage.verify_roots(service._compliance_service.root_identity())
        project_identity = service._storage.project_identity
        artifact_identity = service._storage.artifact_identity
    except MaterializationStorageError as exc:
        raise _MaterializationFailure(exc.reason) from exc
    grant = service._current_operator_grant()
    if (
        grant.project_id != assignment["project_id"]
        or grant.root_session_id != assignment["root_session_id"]
        or grant.worker_session_id != assignment["worker_session_id"]
        or grant.allocation_id != assignment["allocation_id"]
        or grant.role != assignment["role"]
        or grant.output_class != assignment["output_class"]
        or grant.slice_id != assignment["slice_id"]
        or grant.assignment_hash != assignment_hash
        or grant.project_root != project_identity
        or grant.artifact_root != artifact_identity
    ):
        raise _MaterializationFailure("operator_grant_assignment_mismatch")
    authorized_paths = assignment.get("authorized_paths")
    if not isinstance(authorized_paths, list) or not all(
        isinstance(path, str) for path in authorized_paths
    ):
        raise _MaterializationFailure("worker_assignment_paths_invalid")
    fingerprint = MaterializationBindingFingerprint(
        project_id=assignment["project_id"],
        root_session_id=assignment["root_session_id"],
        worker_session_id=assignment["worker_session_id"],
        allocation_id=assignment["allocation_id"],
        role=assignment["role"],
        output_class=assignment["output_class"],
        slice_id=assignment["slice_id"],
        assignment_hash=assignment_hash,
    )
    return {
        "binding": binding,
        "assignment": assignment,
        "assignment_hash": assignment_hash,
        "grant": grant,
        "grant_sha256": service._sha256(service._canonical_json(grant.model_dump(mode="json"))),
        "binding_fingerprint": fingerprint,
        "project_identity": project_identity,
        "artifact_identity": artifact_identity,
        "authorized_paths": frozenset(authorized_paths),
    }


def authorize_file(
    service: OutputMaterializationService,
    spec: MaterializationFileSpec,
    grant: OutputMaterializationGrant,
    assignment: dict[str, object],
) -> None:
    allowed_paths = set(grant.allowed_paths)
    assignment_paths = assignment.get("authorized_paths")
    if (
        not isinstance(assignment_paths, list)
        or spec.path not in allowed_paths
        or spec.path not in assignment_paths
    ):
        raise _MaterializationFailure("materialization_path_not_authorized")
    if spec.operation not in grant.allowed_operations:
        raise _MaterializationFailure("materialization_operation_not_authorized")
    if spec.template.kind not in grant.allowed_templates:
        raise _MaterializationFailure("materialization_template_not_authorized")
    if (
        isinstance(spec.template, FactMarkdownTemplate)
        and spec.template.ordering == "responses"
        and not grant.allow_responses_ordering
    ):
        raise _MaterializationFailure("responses_ordering_not_granted")


def same_authority(
    service: OutputMaterializationService, before: dict[str, Any], after: dict[str, Any]
) -> None:
    if (
        before["binding_fingerprint"] != after["binding_fingerprint"]
        or before["grant"].grant_id != after["grant"].grant_id
        or before["grant"].revision != after["grant"].revision
        or before["grant_sha256"] != after["grant_sha256"]
    ):
        raise _MaterializationFailure("worker_or_operator_grant_changed")


def match_manifest(
    service: OutputMaterializationService,
    authority: dict[str, Any],
    manifest: PreparedMaterializationManifest,
) -> None:
    grant: OutputMaterializationGrant = authority["grant"]
    if (
        manifest.binding != authority["binding_fingerprint"]
        or manifest.grant_id != grant.grant_id
        or manifest.grant_revision != grant.revision
        or manifest.grant_sha256 != authority["grant_sha256"]
        or manifest.project_root != authority["project_identity"]
        or manifest.artifact_root != authority["artifact_identity"]
        or manifest.policy_version != grant.policy_version
        or manifest.policy_scope != grant.policy_scope
    ):
        raise _MaterializationFailure("prepared_manifest_authority_mismatch")
    for item in manifest.files:
        if (
            item.path not in grant.allowed_paths
            or item.path not in authority["authorized_paths"]
            or item.operation not in grant.allowed_operations
            or item.template not in grant.allowed_templates
        ):
            raise _MaterializationFailure("prepared_manifest_exceeds_current_grant")


def identity_value(binding: object, key: str) -> str | None:
    value = getattr(binding, key, None)
    if hasattr(value, "value"):
        value = value.value
    return value if isinstance(value, str) else None


def required_assignment_text(assignment: dict[str, object], key: str) -> str:
    value = assignment.get(key)
    if not isinstance(value, str) or not value:
        raise _MaterializationFailure("worker_assignment_invalid")
    return value
