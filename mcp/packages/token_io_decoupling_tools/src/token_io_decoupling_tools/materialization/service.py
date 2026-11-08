"""输出物化服务的公共请求入口与受限执行环境。"""

from __future__ import annotations

import json
from typing import Any

from pydantic import (
    ValidationError,
)

from token_io_decoupling_core.materialization_models import (
    MaterializationApplyRequest,
    MaterializationFileReceipt,
    MaterializationFileSpec,
    MaterializationInspectRequest,
    MaterializationPrepareRequest,
    MaterializationReceipt,
    MaterializationRequest,
    OutputMaterializationGrant,
    PreparedMaterializationFile,
    PreparedMaterializationManifest,
)
from token_io_decoupling_core.workflow_contracts.vocabulary import BindingIdentity
from token_io_decoupling_tools.artifact_storage.filesystem import MaterializationStorageError
from token_io_decoupling_tools.artifact_storage.service import MaterializationStorage
from token_io_decoupling_tools.compliance.service import CompliancePreflightService
from token_io_decoupling_tools.materialization_templates import (
    MaterializationTemplateError,
    MaterializationTemplateRenderer,
)

from . import application as _application
from . import authorization as _authorization
from . import inspection as _inspection
from . import preparation as _preparation
from . import publication as _publication
from . import receipts as _receipts
from .models import (
    _CALLER_BINDING,
    _REQUEST_ADAPTER,
    MaterializationAuthorizationContext,
    MaterializationAuthorizationProvider,
    MaterializationReceiptStatus,
    OutputMaterializerConfig,
    _MaterializationFailure,
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
        return _preparation.prepare(self, request)

    def _inspect(self, request: MaterializationInspectRequest) -> dict[str, object]:
        return _inspection.inspect(self, request)

    def _apply(self, request: MaterializationApplyRequest) -> dict[str, object]:
        return _application.apply(self, request)

    def _reload_pending_candidate(
        self,
        request: MaterializationApplyRequest,
        manifest: PreparedMaterializationManifest,
        manifest_hash: str,
        item: PreparedMaterializationFile,
        expected_content: bytes,
    ) -> tuple[dict[str, Any], bytes]:
        return _publication.reload_pending_candidate(
            self, request, manifest, manifest_hash, item, expected_content
        )

    def _publish_pending_file(
        self,
        authority: dict[str, Any],
        item: PreparedMaterializationFile,
        candidate: bytes,
        index: int,
        prior_receipt: MaterializationReceipt | None,
    ) -> MaterializationFileReceipt:
        return _publication.publish_pending_file(
            self, authority, item, candidate, index, prior_receipt
        )

    @staticmethod
    def _pending_receipt_status(
        receipts: list[MaterializationFileReceipt], applied_any: bool, stop: bool
    ) -> MaterializationReceiptStatus:
        return _publication.pending_receipt_status(receipts, applied_any, stop)

    def _checkpoint_pending_receipts(
        self,
        directory_fd: int,
        manifest: PreparedMaterializationManifest,
        manifest_hash: str,
        receipts: list[MaterializationFileReceipt],
        prior_receipt: MaterializationReceipt | None,
    ) -> bool:
        return _publication.checkpoint_pending_receipts(
            self, directory_fd, manifest, manifest_hash, receipts, prior_receipt
        )

    def _apply_pending(
        self,
        request: MaterializationApplyRequest,
        manifest: PreparedMaterializationManifest,
        manifest_hash: str,
        directory_fd: int,
        contents: dict[int, bytes],
        prior_receipt: MaterializationReceipt | None,
    ) -> dict[str, object]:
        return _application.apply_pending(
            self, request, manifest, manifest_hash, directory_fd, contents, prior_receipt
        )

    def _validate_worker_binding(
        self, context: MaterializationAuthorizationContext, binding: BindingIdentity
    ) -> None:
        return _authorization.validate_worker_binding(self, context, binding)

    def _validate_assignment_binding(
        self, binding: BindingIdentity, assignment: dict[str, Any]
    ) -> None:
        return _authorization.validate_assignment_binding(self, binding, assignment)

    def _current_operator_grant(self) -> OutputMaterializationGrant:
        return _authorization.current_operator_grant(self)

    def _authorize(self) -> dict[str, Any]:
        return _authorization.authorize(self)

    def _authorize_file(
        self,
        spec: MaterializationFileSpec,
        grant: OutputMaterializationGrant,
        assignment: dict[str, object],
    ) -> None:
        return _authorization.authorize_file(self, spec, grant, assignment)

    def _same_authority(self, before: dict[str, Any], after: dict[str, Any]) -> None:
        return _authorization.same_authority(self, before, after)

    def _match_manifest(
        self, authority: dict[str, Any], manifest: PreparedMaterializationManifest
    ) -> None:
        return _authorization.match_manifest(self, authority, manifest)

    def _load_prepared(
        self, prepared_id: str, expected_hash: str
    ) -> tuple[PreparedMaterializationManifest, str, int]:
        return _preparation.load_prepared(self, prepared_id, expected_hash)

    def _read_candidate(self, directory_fd: int, item: PreparedMaterializationFile) -> bytes:
        return _inspection.read_candidate(self, directory_fd, item)

    def _read_receipt(
        self,
        directory_fd: int,
        manifest: PreparedMaterializationManifest,
        manifest_hash: str,
    ) -> MaterializationReceipt | None:
        return _receipts.read_receipt(self, directory_fd, manifest, manifest_hash)

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
        return _receipts.persist_receipt(
            self,
            directory_fd,
            manifest,
            manifest_hash,
            files,
            final=final,
            status=status,
            prior_receipt=prior_receipt,
        )

    def _classify_current_files(
        self,
        manifest: PreparedMaterializationManifest,
        contents: dict[int, bytes],
        prior_receipt: MaterializationReceipt | None,
    ) -> list[str]:
        return _inspection.classify_current_files(self, manifest, contents, prior_receipt)

    def _preflight_projection(
        self,
        manifest: PreparedMaterializationManifest,
        contents: dict[int, bytes],
        states: list[str],
    ) -> list[dict[str, object]]:
        return _inspection.preflight_projection(self, manifest, contents, states)

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
        return _receipts.blocked_apply(
            self,
            reason,
            prepared_id,
            manifest_hash,
            files,
            preflight_status=preflight_status,
            identical_projection_count=identical_projection_count,
        )

    @staticmethod
    def _prior_requires_reconciliation(receipt: MaterializationReceipt | None, index: int) -> bool:
        return _receipts.prior_requires_reconciliation(receipt, index)

    @staticmethod
    def _file_receipt(index: int, path: str, state: str) -> MaterializationFileReceipt:
        return _receipts.file_receipt(index, path, state)

    @staticmethod
    def _matches_baseline(item: PreparedMaterializationFile, current: bytes | None) -> bool:
        return _receipts.matches_baseline(item, current)

    @staticmethod
    def _bounded_content_bytes(content: str) -> bytes:
        return _preparation.bounded_content_bytes(content)

    @staticmethod
    def _canonical_json(value: object) -> bytes:
        return _preparation.canonical_json(value)

    @staticmethod
    def _loads_no_duplicates(raw: bytes) -> object:
        return _preparation.loads_no_duplicates(raw)

    @staticmethod
    def _decode_content(raw: bytes) -> str:
        return _preparation.decode_content(raw)

    @staticmethod
    def _sha256(raw: bytes) -> str:
        return _preparation.sha256(raw)

    @staticmethod
    def _identity_value(binding: object, key: str) -> str | None:
        return _authorization.identity_value(binding, key)

    @staticmethod
    def _required_assignment_text(assignment: dict[str, object], key: str) -> str:
        return _authorization.required_assignment_text(assignment, key)
