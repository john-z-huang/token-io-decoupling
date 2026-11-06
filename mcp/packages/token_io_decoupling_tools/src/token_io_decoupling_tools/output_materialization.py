"""Trusted operator configuration and bounded Worker output materialization."""

from __future__ import annotations

import hashlib
import json
import os
import uuid
from collections.abc import Mapping
from contextvars import ContextVar
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Annotated, Any, Literal, Protocol, TypeAlias

from pydantic import (
    ConfigDict,
    Field,
    StringConstraints,
    TypeAdapter,
    ValidationError,
    field_validator,
)

from token_io_decoupling_core.materialization_models import (
    DEFAULT_INSPECT_CHARS,
    MAX_MATERIALIZATION_BATCH_UTF8_BYTES,
    MAX_MATERIALIZATION_TEXT_CHARS,
    AbsentBaseline,
    FactMarkdownTemplate,
    MaterializationApplyRequest,
    MaterializationBindingFingerprint,
    MaterializationFileReceipt,
    MaterializationFileSpec,
    MaterializationInspectRequest,
    MaterializationOperation,
    MaterializationPrepareRequest,
    MaterializationReceipt,
    MaterializationRequest,
    OutputMaterializationGrant,
    PreparedMaterializationFile,
    PreparedMaterializationManifest,
    Sha256Baseline,
)
from token_io_decoupling_core.models import NonEmptyString, StrictModel
from token_io_decoupling_core.workflow_models import (
    BindingIdentity,
    HostCapability,
    HostGuard,
    SessionRole,
)
from token_io_decoupling_tools.compliance_preflight import CompliancePreflightService
from token_io_decoupling_tools.materialization_storage import (
    MaterializationStorage,
    MaterializationStorageError,
)
from token_io_decoupling_tools.materialization_templates import (
    MaterializationTemplateError,
    MaterializationTemplateRenderer,
)


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


class OutputMaterializationService:
    """Coordinate current Worker authority, immutable artifacts, preflight, and writes."""

    def __init__(
        self,
        *,
        authorization_provider: MaterializationAuthorizationProvider,
        compliance_service: CompliancePreflightService,
        config: OutputMaterializerConfig,
    ) -> None:
        self._authorization_provider = authorization_provider
        self._compliance_service = compliance_service
        self._config = config
        self._renderer = MaterializationTemplateRenderer()
        self._storage: MaterializationStorage | None = None
        self._startup_reason: str | None = None
        try:
            self._storage = MaterializationStorage(
                config.project_root,
                config.artifact_root,
                expected_project_identity=compliance_service.root_identity(),
            )
        except MaterializationStorageError as exc:
            self._startup_reason = exc.reason
        except (OSError, ValueError, RuntimeError):
            self._startup_reason = "configured_roots_unavailable"

    def capability(self) -> dict[str, str]:
        if self._startup_reason is not None:
            return {"status": "unavailable", "reason_code": self._startup_reason}
        return {"status": "configured", "reason_code": "explicit_operator_factory_loaded"}

    def close(self) -> None:
        if self._storage is not None:
            self._storage.close()

    def execute(
        self,
        request: MaterializationRequest,
        *,
        expected_binding: BindingIdentity | None = None,
    ) -> dict[str, object]:
        token = _CALLER_BINDING.set(expected_binding)
        try:
            return self._execute_scoped(request)
        finally:
            _CALLER_BINDING.reset(token)

    def _execute_scoped(self, request: MaterializationRequest) -> dict[str, object]:
        if self._storage is None:
            return {
                "status": "unavailable",
                "reason_code": self._startup_reason or "materialization_store_unavailable",
            }
        try:
            parsed = _REQUEST_ADAPTER.validate_python(request, strict=True)
            if isinstance(parsed, MaterializationPrepareRequest):
                return self._prepare(parsed)
            if isinstance(parsed, MaterializationInspectRequest):
                return self._inspect(parsed)
            if isinstance(parsed, MaterializationApplyRequest):
                return self._apply(parsed)
            return {"status": "blocked", "reason_code": "materialization_action_invalid"}
        except _MaterializationFailure as exc:
            return {"status": "blocked", "reason_code": exc.reason}
        except MaterializationTemplateError as exc:
            return {"status": "blocked", "reason_code": exc.reason}
        except MaterializationStorageError as exc:
            return {"status": "blocked", "reason_code": exc.reason}
        except (OSError, ValidationError, ValueError, TypeError, json.JSONDecodeError):
            return {"status": "blocked", "reason_code": "materialization_request_unavailable"}

    def _prepare(self, request: MaterializationPrepareRequest) -> dict[str, object]:
        authority = self._authorize()
        templates: list[tuple[int, Any]] = []
        total_bytes = 0
        for index, spec in enumerate(request.files):
            self._authorize_file(spec, authority["grant"], authority["assignment"])
            templates.append((index, spec.template))
        rendered = self._renderer.render_all(
            templates,
            grant=authority["grant"],
            outbound_data_permitted=request.outbound_data_permitted,
        )
        contents: list[bytes] = []
        previews: list[str] = []
        file_rows: list[PreparedMaterializationFile] = []
        for index, spec in enumerate(request.files):
            content = rendered[index]
            encoded = self._bounded_content_bytes(content)
            total_bytes += len(encoded)
            if total_bytes > MAX_MATERIALIZATION_BATCH_UTF8_BYTES:
                raise _MaterializationFailure("candidate_batch_byte_limit_exceeded")
            contents.append(encoded)
            previews.append(content[:256])
            file_rows.append(
                PreparedMaterializationFile(
                    path=spec.path,
                    operation=spec.operation,
                    baseline=spec.baseline,
                    template=spec.template.kind,
                    content_sha256=self._sha256(encoded),
                    content_bytes=len(encoded),
                    content_chars=len(content),
                    artifact_name=f"candidate-{index:02d}.bin",
                )
            )
        self._same_authority(authority, self._authorize())
        prepared_id = uuid.uuid4().hex
        manifest = PreparedMaterializationManifest(
            version=1,
            prepared_id=prepared_id,
            policy_version=2,
            binding=authority["binding_fingerprint"],
            grant_id=authority["grant"].grant_id,
            grant_revision=authority["grant"].revision,
            grant_sha256=authority["grant_sha256"],
            project_root=authority["project_identity"],
            artifact_root=authority["artifact_identity"],
            policy_scope=authority["grant"].policy_scope,
            files=file_rows,
        )
        manifest_bytes = self._canonical_json(manifest.model_dump(mode="json"))
        manifest_hash = self._sha256(manifest_bytes)
        assert self._storage is not None
        self._storage.persist_prepared(prepared_id, contents, manifest_bytes)
        verified_manifest, verified_hash, verified_fd = self._load_prepared(
            prepared_id, manifest_hash
        )
        try:
            if verified_manifest != manifest or verified_hash != manifest_hash:
                raise _MaterializationFailure("prepared_manifest_readback_mismatch")
        finally:
            os.close(verified_fd)
        return {
            "status": "prepared",
            "prepared_id": prepared_id,
            "manifest_sha256": manifest_hash,
            "policy_version": 2,
            "files": [
                {
                    "file_index": index,
                    "path": row.path,
                    "operation": row.operation,
                    "template": row.template,
                    "content_sha256": row.content_sha256,
                    "content_chars": row.content_chars,
                    "content_bytes": row.content_bytes,
                    "preview": previews[index],
                }
                for index, row in enumerate(file_rows)
            ],
            "inspect": {
                "tool": "materialize_decoupled_output",
                "action": "inspect",
                "expected_manifest_hash": manifest_hash,
                "max_chars_default": DEFAULT_INSPECT_CHARS,
                "max_chars_limit": 8192,
            },
        }

    def _inspect(self, request: MaterializationInspectRequest) -> dict[str, object]:
        authority = self._authorize()
        manifest, manifest_hash, directory_fd = self._load_prepared(
            request.prepared_id, request.expected_manifest_hash
        )
        assert self._storage is not None
        try:
            self._match_manifest(authority, manifest)
            if request.file_index >= len(manifest.files):
                raise _MaterializationFailure("prepared_file_index_out_of_range")
            file = manifest.files[request.file_index]
            content = self._read_candidate(directory_fd, file)
            text = self._decode_content(content)
            chunk = text[request.offset : request.offset + request.max_chars]
            next_offset = request.offset + len(chunk)
            return {
                "status": "inspected",
                "prepared_id": request.prepared_id,
                "manifest_sha256": manifest_hash,
                "file_index": request.file_index,
                "path": file.path,
                "offset": request.offset,
                "max_chars": request.max_chars,
                "content_chars": file.content_chars,
                "content_bytes": file.content_bytes,
                "content_sha256": file.content_sha256,
                "content": chunk,
                "next_offset": next_offset,
                "complete": next_offset >= len(text),
            }
        finally:
            os.close(directory_fd)

    def _apply(self, request: MaterializationApplyRequest) -> dict[str, object]:
        assert self._storage is not None
        with self._storage.locked():
            authority = self._authorize()
            manifest, manifest_hash, directory_fd = self._load_prepared(
                request.prepared_id, request.expected_manifest_hash
            )
            try:
                self._match_manifest(authority, manifest)
                contents = {
                    index: self._read_candidate(directory_fd, item)
                    for index, item in enumerate(manifest.files)
                }
                prior_receipt = self._read_receipt(directory_fd, manifest, manifest_hash)
                initial_states = self._classify_current_files(manifest, contents, prior_receipt)
                if any(state == "conflict" for state in initial_states):
                    files = [
                        self._file_receipt(index, item.path, state)
                        for index, (item, state) in enumerate(
                            zip(manifest.files, initial_states, strict=True)
                        )
                    ]
                    return self._blocked_apply(
                        "materialization_baseline_conflict",
                        request.prepared_id,
                        manifest_hash,
                        files,
                        identical_projection_count=sum(
                            state == "already_identical" for state in initial_states
                        ),
                    )
                projection = self._preflight_projection(manifest, contents, initial_states)
                preflight = self._compliance_service.validate(
                    {"policy_scope": manifest.policy_scope, "candidates": projection}
                )
                if (
                    type(preflight.get("policy_version")) is not int
                    or preflight.get("policy_version") != 2
                    or preflight.get("status") != "pass"
                    or self._compliance_service.root_identity()
                    != (
                        self._storage.project_identity.device,
                        self._storage.project_identity.inode,
                    )
                ):
                    files = [
                        self._file_receipt(index, item.path, state)
                        for index, (item, state) in enumerate(
                            zip(manifest.files, initial_states, strict=True)
                        )
                    ]
                    return self._blocked_apply(
                        "fresh_preflight_not_passed",
                        request.prepared_id,
                        manifest_hash,
                        files,
                        preflight_status=str(preflight.get("status", "unknown")),
                        identical_projection_count=sum(
                            state == "already_identical" for state in initial_states
                        ),
                    )
                return self._apply_pending(
                    request,
                    manifest,
                    manifest_hash,
                    directory_fd,
                    contents,
                    prior_receipt,
                )
            finally:
                os.close(directory_fd)

    def _apply_pending(
        self,
        request: MaterializationApplyRequest,
        manifest: PreparedMaterializationManifest,
        manifest_hash: str,
        directory_fd: int,
        contents: dict[int, bytes],
        prior_receipt: MaterializationReceipt | None,
    ) -> dict[str, object]:
        assert self._storage is not None
        receipts: list[MaterializationFileReceipt] = []
        applied_any = False
        stop = False
        for index, item in enumerate(manifest.files):
            if stop:
                receipts.append(
                    MaterializationFileReceipt(
                        file_index=index, path=item.path, status="not_attempted"
                    )
                )
                continue
            try:
                authority = self._authorize()
                self._match_manifest(authority, manifest)
                latest_manifest, latest_hash, latest_dir_fd = self._load_prepared(
                    request.prepared_id, request.expected_manifest_hash
                )
                try:
                    self._match_manifest(authority, latest_manifest)
                    if latest_hash != manifest_hash:
                        raise _MaterializationFailure("prepared_manifest_changed")
                    candidate = self._read_candidate(latest_dir_fd, item)
                finally:
                    os.close(latest_dir_fd)
                if candidate != contents[index]:
                    raise _MaterializationFailure("prepared_candidate_changed")
                current = self._storage.read_project_file(
                    item.path, limit=MAX_MATERIALIZATION_BATCH_UTF8_BYTES
                )
                if current is not None and self._sha256(current) == item.content_sha256:
                    receipts.append(
                        MaterializationFileReceipt(
                            file_index=index,
                            path=item.path,
                            status="already_identical",
                            actual_sha256=item.content_sha256,
                        )
                    )
                    self._persist_receipt(
                        directory_fd,
                        manifest,
                        manifest_hash,
                        receipts,
                        final=False,
                        prior_receipt=prior_receipt,
                    )
                    continue
                if self._prior_requires_reconciliation(prior_receipt, index):
                    raise _MaterializationFailure("previously_applied_file_changed")
                if not self._matches_baseline(item, current):
                    raise _MaterializationFailure("materialization_baseline_conflict")
                self._same_authority(authority, self._authorize())
                status, actual_hash = self._storage.publish_project_file(
                    item.path,
                    candidate,
                    operation=item.operation,
                    baseline_state=item.baseline.state,
                    baseline_sha256=(
                        item.baseline.value if isinstance(item.baseline, Sha256Baseline) else None
                    ),
                    candidate_sha256=item.content_sha256,
                    limit=MAX_MATERIALIZATION_BATCH_UTF8_BYTES,
                )
                receipts.append(
                    MaterializationFileReceipt(
                        file_index=index,
                        path=item.path,
                        status=status,
                        actual_sha256=actual_hash,
                    )
                )
                applied_any = applied_any or status == "applied"
                if status in {"conflict", "uncertain"}:
                    stop = True
            except _MaterializationFailure as exc:
                conflict = MaterializationFileReceipt(
                    file_index=index, path=item.path, status="conflict"
                )
                if exc.reason == "worker_or_operator_grant_changed" and not applied_any:
                    blocked_files = [*receipts, conflict]
                    return self._blocked_apply(
                        exc.reason,
                        request.prepared_id,
                        manifest_hash,
                        blocked_files,
                        preflight_status="pass",
                        identical_projection_count=sum(
                            file_receipt.status == "already_identical"
                            for file_receipt in blocked_files
                        ),
                    )
                receipts.append(conflict)
                stop = True
            except MaterializationStorageError:
                receipts.append(
                    MaterializationFileReceipt(file_index=index, path=item.path, status="conflict")
                )
                stop = True
            except (OSError, ValueError):
                receipts.append(
                    MaterializationFileReceipt(file_index=index, path=item.path, status="uncertain")
                )
                stop = True
            try:
                self._persist_receipt(
                    directory_fd,
                    manifest,
                    manifest_hash,
                    receipts,
                    final=False,
                    prior_receipt=prior_receipt,
                )
            except MaterializationStorageError:
                stop = True
                if receipts:
                    last = receipts[-1]
                    if last.status == "applied":
                        receipts[-1] = last.model_copy(update={"status": "uncertain"})
        receipt_status: MaterializationReceiptStatus
        if stop or any(
            item.status in {"conflict", "uncertain", "not_attempted"} for item in receipts
        ):
            receipt_status = (
                "partial"
                if applied_any
                else "uncertain"
                if any(item.status == "uncertain" for item in receipts)
                else "conflict"
            )
        elif applied_any:
            receipt_status = "applied"
        else:
            receipt_status = "already_identical"
        try:
            self._persist_receipt(
                directory_fd,
                manifest,
                manifest_hash,
                receipts,
                final=True,
                status=receipt_status,
                prior_receipt=prior_receipt,
            )
        except MaterializationStorageError:
            return self._blocked_apply(
                "materialization_receipt_write_uncertain",
                request.prepared_id,
                manifest_hash,
                receipts,
                identical_projection_count=sum(
                    item.status == "already_identical" for item in receipts
                ),
            )
        response_receipt = MaterializationReceipt(
            version=1,
            prepared_id=manifest.prepared_id,
            manifest_sha256=manifest_hash,
            status=receipt_status,
            files=receipts,
        )
        return {
            **response_receipt.model_dump(mode="json"),
            "fresh_preflight": "pass",
            "preflight_projection": "already_identical_files_use_candidate_sha256_baseline",
            "identical_projection_count": sum(
                item.status == "already_identical" for item in receipts
            ),
        }

    def _authorize(self) -> dict[str, Any]:
        assert self._storage is not None
        try:
            context = self._authorization_provider.current_context()
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
        project_id = self._required_assignment_text(assignment, "project_id")
        root_session_id = self._required_assignment_text(assignment, "root_session_id")
        worker_session_id = self._required_assignment_text(assignment, "worker_session_id")
        allocation_id = self._required_assignment_text(assignment, "allocation_id")
        role = self._required_assignment_text(assignment, "role")
        output_class = self._required_assignment_text(assignment, "output_class")
        slice_id = self._required_assignment_text(assignment, "slice_id")
        if (
            self._identity_value(binding, "project_id") != project_id
            or self._identity_value(binding, "root_session_id") != root_session_id
            or self._identity_value(binding, "current_session_id") != worker_session_id
            or self._identity_value(binding, "parent_session_id") != root_session_id
        ):
            raise _MaterializationFailure("worker_assignment_binding_mismatch")
        if role != "Primary Output" or output_class not in {
            "code_configuration",
        }:
            raise _MaterializationFailure("worker_role_output_class_unsupported")
        try:
            self._storage.verify_roots(self._compliance_service.root_identity())
            project_identity = self._storage.project_identity
            artifact_identity = self._storage.artifact_identity
        except MaterializationStorageError as exc:
            raise _MaterializationFailure(exc.reason) from exc
        try:
            grant_raw = self._config.grant_provider.current_grant()
            if isinstance(grant_raw, OutputMaterializationGrant):
                grant = OutputMaterializationGrant.model_validate(grant_raw, strict=True)
            elif isinstance(grant_raw, Mapping):
                grant = OutputMaterializationGrant.model_validate(dict(grant_raw), strict=True)
            else:
                raise ValueError("operator_grant_missing")
        except Exception as exc:
            raise _MaterializationFailure("operator_grant_unavailable_or_invalid") from exc
        if (
            grant.project_id != project_id
            or grant.root_session_id != root_session_id
            or grant.worker_session_id != worker_session_id
            or grant.allocation_id != allocation_id
            or grant.role != role
            or grant.output_class != output_class
            or grant.slice_id != slice_id
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
            project_id=project_id,
            root_session_id=root_session_id,
            worker_session_id=worker_session_id,
            allocation_id=allocation_id,
            role=role,
            output_class=output_class,
            slice_id=slice_id,
            assignment_hash=assignment_hash,
        )
        return {
            "binding": binding,
            "assignment": assignment,
            "assignment_hash": assignment_hash,
            "grant": grant,
            "grant_sha256": self._sha256(self._canonical_json(grant.model_dump(mode="json"))),
            "binding_fingerprint": fingerprint,
            "project_identity": project_identity,
            "artifact_identity": artifact_identity,
            "authorized_paths": frozenset(authorized_paths),
        }

    def _authorize_file(
        self,
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

    def _same_authority(self, before: dict[str, Any], after: dict[str, Any]) -> None:
        if (
            before["binding_fingerprint"] != after["binding_fingerprint"]
            or before["grant"].grant_id != after["grant"].grant_id
            or before["grant"].revision != after["grant"].revision
            or before["grant_sha256"] != after["grant_sha256"]
        ):
            raise _MaterializationFailure("worker_or_operator_grant_changed")

    def _match_manifest(
        self, authority: dict[str, Any], manifest: PreparedMaterializationManifest
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

    def _load_prepared(
        self, prepared_id: str, expected_hash: str
    ) -> tuple[PreparedMaterializationManifest, str, int]:
        assert self._storage is not None
        directory_fd = self._storage.open_prepared(prepared_id)
        try:
            raw, _ = self._storage.read_file(directory_fd, "manifest.json", limit=32_768)
            if raw is None:
                raise _MaterializationFailure("prepared_manifest_unavailable")
            parsed_json = self._loads_no_duplicates(raw)
            try:
                manifest = PreparedMaterializationManifest.model_validate(parsed_json, strict=True)
            except ValidationError as exc:
                raise _MaterializationFailure("prepared_manifest_invalid") from exc
            canonical = self._canonical_json(manifest.model_dump(mode="json"))
            manifest_hash = self._sha256(canonical)
            if (
                raw != canonical
                or manifest_hash != expected_hash
                or manifest.prepared_id != prepared_id
            ):
                raise _MaterializationFailure("prepared_manifest_hash_mismatch")
            actual_batch_bytes = 0
            for item in manifest.files:
                content = self._read_candidate(directory_fd, item)
                actual_batch_bytes += len(content)
                if actual_batch_bytes > MAX_MATERIALIZATION_BATCH_UTF8_BYTES:
                    raise _MaterializationFailure("candidate_batch_byte_limit_exceeded")
            return manifest, manifest_hash, directory_fd
        except Exception:
            os.close(directory_fd)
            raise

    def _read_candidate(self, directory_fd: int, item: PreparedMaterializationFile) -> bytes:
        assert self._storage is not None
        raw, _ = self._storage.read_file(
            directory_fd,
            item.artifact_name,
            limit=MAX_MATERIALIZATION_BATCH_UTF8_BYTES,
        )
        if (
            raw is None
            or self._sha256(raw) != item.content_sha256
            or len(raw) != item.content_bytes
        ):
            raise _MaterializationFailure("prepared_candidate_hash_mismatch")
        text = self._decode_content(raw)
        if len(text) != item.content_chars:
            raise _MaterializationFailure("prepared_candidate_metadata_mismatch")
        return raw

    def _read_receipt(
        self,
        directory_fd: int,
        manifest: PreparedMaterializationManifest,
        manifest_hash: str,
    ) -> MaterializationReceipt | None:
        assert self._storage is not None
        raw, _ = self._storage.read_file(directory_fd, "receipt.json", limit=16_384)
        if raw is None:
            return None
        try:
            receipt = MaterializationReceipt.model_validate(
                self._loads_no_duplicates(raw), strict=True
            )
        except ValidationError as exc:
            raise _MaterializationFailure("materialization_receipt_invalid") from exc
        if (
            receipt.prepared_id != manifest.prepared_id
            or receipt.manifest_sha256 != manifest_hash
            or len(receipt.files) != len(manifest.files)
            or self._canonical_json(receipt.model_dump(mode="json")) != raw
        ):
            raise _MaterializationFailure("materialization_receipt_invalid")
        for index, (file_receipt, manifest_file) in enumerate(
            zip(receipt.files, manifest.files, strict=True)
        ):
            if file_receipt.file_index != index or file_receipt.path != manifest_file.path:
                raise _MaterializationFailure("materialization_receipt_invalid")
            if (
                file_receipt.status in {"applied", "already_identical"}
                and file_receipt.actual_sha256 != manifest_file.content_sha256
            ):
                raise _MaterializationFailure("materialization_receipt_invalid")
        return receipt

    def _persist_receipt(
        self,
        directory_fd: int,
        manifest: PreparedMaterializationManifest,
        manifest_hash: str,
        files: list[MaterializationFileReceipt],
        *,
        final: bool,
        status: MaterializationReceiptStatus | None = None,
        prior_receipt: MaterializationReceipt | None = None,
    ) -> MaterializationReceipt:
        assert self._storage is not None
        if status is None:
            status = "partial" if not final else "applied"
        complete_files = list(files)
        if len(complete_files) < len(manifest.files):
            complete_files.extend(
                MaterializationFileReceipt(file_index=index, path=item.path, status="not_attempted")
                for index, item in enumerate(
                    manifest.files[len(complete_files) :], start=len(complete_files)
                )
            )
        if prior_receipt is not None:
            for index, previous in enumerate(prior_receipt.files):
                if previous.status == "applied" and index < len(complete_files):
                    current = complete_files[index]
                    complete_files[index] = current.model_copy(
                        update={
                            "status": "applied",
                            "actual_sha256": previous.actual_sha256 or current.actual_sha256,
                        }
                    )
                elif (
                    previous.status == "uncertain"
                    and index < len(complete_files)
                    and complete_files[index].status == "already_identical"
                ):
                    # Preserve the possible-write record so a later undo cannot be replayed.
                    complete_files[index] = previous
        receipt = MaterializationReceipt(
            version=1,
            prepared_id=manifest.prepared_id,
            manifest_sha256=manifest_hash,
            status=status,
            files=complete_files,
        )
        encoded = self._canonical_json(receipt.model_dump(mode="json"))
        self._storage.write_receipt(directory_fd, encoded)
        return receipt

    def _classify_current_files(
        self,
        manifest: PreparedMaterializationManifest,
        contents: dict[int, bytes],
        prior_receipt: MaterializationReceipt | None,
    ) -> list[str]:
        states: list[str] = []
        assert self._storage is not None
        for index, item in enumerate(manifest.files):
            try:
                current = self._storage.read_project_file(
                    item.path, limit=MAX_MATERIALIZATION_BATCH_UTF8_BYTES
                )
            except MaterializationStorageError:
                states.append("conflict")
                continue
            if current is not None and self._sha256(current) == self._sha256(contents[index]):
                states.append("already_identical")
            elif self._prior_requires_reconciliation(prior_receipt, index):
                states.append("conflict")
            elif self._matches_baseline(item, current):
                states.append("pending")
            else:
                states.append("conflict")
        return states

    def _preflight_projection(
        self,
        manifest: PreparedMaterializationManifest,
        contents: dict[int, bytes],
        states: list[str],
    ) -> list[dict[str, object]]:
        candidates: list[dict[str, object]] = []
        for index, (item, state) in enumerate(zip(manifest.files, states, strict=True)):
            content = self._decode_content(contents[index])
            if state == "already_identical":
                operation: MaterializationOperation = "replace"
                baseline = {"state": "sha256", "value": item.content_sha256}
            else:
                operation = item.operation
                baseline = item.baseline.model_dump(mode="json")
            candidates.append(
                {
                    "path": item.path,
                    "operation": operation,
                    "baseline": baseline,
                    "content": content,
                }
            )
        return candidates

    def _blocked_apply(
        self,
        reason: str,
        prepared_id: str,
        manifest_hash: str,
        files: list[MaterializationFileReceipt],
        *,
        preflight_status: str | None = None,
        identical_projection_count: int = 0,
    ) -> dict[str, object]:
        result: dict[str, object] = {
            "status": "blocked",
            "reason_code": reason,
            "prepared_id": prepared_id,
            "manifest_sha256": manifest_hash,
            "files": [item.model_dump(mode="json") for item in files],
            "fresh_preflight": preflight_status or "not_passed",
            "preflight_projection": "already_identical_files_use_candidate_sha256_baseline",
            "identical_projection_count": identical_projection_count,
        }
        if preflight_status is not None:
            result["preflight_status"] = preflight_status
        return result

    @staticmethod
    def _prior_requires_reconciliation(receipt: MaterializationReceipt | None, index: int) -> bool:
        return (
            receipt is not None
            and index < len(receipt.files)
            and receipt.files[index].status in {"applied", "already_identical", "uncertain"}
        )

    @staticmethod
    def _file_receipt(index: int, path: str, state: str) -> MaterializationFileReceipt:
        mapped = (
            state
            if state in {"applied", "already_identical", "conflict", "not_attempted", "uncertain"}
            else "conflict"
        )
        return MaterializationFileReceipt(
            file_index=index, path=path, status=mapped, actual_sha256=None
        )

    @staticmethod
    def _matches_baseline(item: PreparedMaterializationFile, current: bytes | None) -> bool:
        if item.operation == "create":
            return current is None and isinstance(item.baseline, AbsentBaseline)
        return (
            current is not None
            and isinstance(item.baseline, Sha256Baseline)
            and hashlib.sha256(current).hexdigest() == item.baseline.value
        )

    @staticmethod
    def _bounded_content_bytes(content: str) -> bytes:
        if len(content) > MAX_MATERIALIZATION_TEXT_CHARS:
            raise _MaterializationFailure("candidate_file_char_limit_exceeded")
        try:
            return content.encode("utf-8", errors="strict")
        except UnicodeEncodeError as exc:
            raise _MaterializationFailure("candidate_content_not_valid_utf8") from exc

    @staticmethod
    def _canonical_json(value: object) -> bytes:
        try:
            return json.dumps(
                value,
                ensure_ascii=False,
                allow_nan=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8", errors="strict")
        except (TypeError, ValueError, UnicodeEncodeError) as exc:
            raise _MaterializationFailure("canonical_manifest_invalid") from exc

    @staticmethod
    def _loads_no_duplicates(raw: bytes) -> object:
        def pairs_to_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
            result: dict[str, object] = {}
            for key, value in pairs:
                if key in result:
                    raise _MaterializationFailure("artifact_duplicate_json_key")
                result[key] = value
            return result

        def reject_constant(_value: str) -> None:
            raise _MaterializationFailure("artifact_non_finite_number")

        try:
            return json.loads(
                raw.decode("utf-8", errors="strict"),
                object_pairs_hook=pairs_to_object,
                parse_constant=reject_constant,
            )
        except _MaterializationFailure:
            raise
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
            raise _MaterializationFailure("artifact_json_invalid") from exc

    @staticmethod
    def _decode_content(raw: bytes) -> str:
        try:
            return raw.decode("utf-8", errors="strict")
        except UnicodeDecodeError as exc:
            raise _MaterializationFailure("materialization_content_not_utf8") from exc

    @staticmethod
    def _sha256(raw: bytes) -> str:
        return hashlib.sha256(raw).hexdigest()

    @staticmethod
    def _identity_value(binding: object, key: str) -> str | None:
        value = getattr(binding, key, None)
        if hasattr(value, "value"):
            value = value.value
        return value if isinstance(value, str) else None

    @staticmethod
    def _required_assignment_text(assignment: dict[str, object], key: str) -> str:
        value = assignment.get(key)
        if not isinstance(value, str) or not value:
            raise _MaterializationFailure("worker_assignment_invalid")
        return value
