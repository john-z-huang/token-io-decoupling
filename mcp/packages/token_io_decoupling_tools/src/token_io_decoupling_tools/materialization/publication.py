"""发布单个候选前复核授权、清单、候选内容及项目基线。"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

from token_io_decoupling_core.materialization_models import (
    MAX_MATERIALIZATION_BATCH_UTF8_BYTES,
    MaterializationApplyRequest,
    MaterializationFileReceipt,
    MaterializationReceipt,
    PreparedMaterializationFile,
    PreparedMaterializationManifest,
    Sha256Baseline,
)
from token_io_decoupling_tools.artifact_storage.filesystem import MaterializationStorageError

from .models import MaterializationReceiptStatus, _MaterializationFailure

if TYPE_CHECKING:
    from .service import OutputMaterializationService


def reload_pending_candidate(
    service: OutputMaterializationService,
    request: MaterializationApplyRequest,
    manifest: PreparedMaterializationManifest,
    manifest_hash: str,
    item: PreparedMaterializationFile,
    expected_content: bytes,
) -> tuple[dict[str, Any], bytes]:
    authority = service._authorize()
    service._match_manifest(authority, manifest)
    latest_manifest, latest_hash, latest_dir_fd = service._load_prepared(
        request.prepared_id, request.expected_manifest_hash
    )
    try:
        service._match_manifest(authority, latest_manifest)
        if latest_hash != manifest_hash:
            raise _MaterializationFailure("prepared_manifest_changed")
        candidate = service._read_candidate(latest_dir_fd, item)
    finally:
        os.close(latest_dir_fd)
    if candidate != expected_content:
        raise _MaterializationFailure("prepared_candidate_changed")
    return authority, candidate


def publish_pending_file(
    service: OutputMaterializationService,
    authority: dict[str, Any],
    item: PreparedMaterializationFile,
    candidate: bytes,
    index: int,
    prior_receipt: MaterializationReceipt | None,
) -> MaterializationFileReceipt:
    assert service._storage is not None
    current = service._storage.read_project_file(
        item.path, limit=MAX_MATERIALIZATION_BATCH_UTF8_BYTES
    )
    if current is not None and service._sha256(current) == item.content_sha256:
        return MaterializationFileReceipt(
            file_index=index,
            path=item.path,
            status="already_identical",
            actual_sha256=item.content_sha256,
        )
    if service._prior_requires_reconciliation(prior_receipt, index):
        raise _MaterializationFailure("previously_applied_file_changed")
    if not service._matches_baseline(item, current):
        raise _MaterializationFailure("materialization_baseline_conflict")
    service._same_authority(authority, service._authorize())
    baseline_hash = item.baseline.value if isinstance(item.baseline, Sha256Baseline) else None
    status, actual_hash = service._storage.publish_project_file(
        item.path,
        candidate,
        operation=item.operation,
        baseline_state=item.baseline.state,
        baseline_sha256=baseline_hash,
        candidate_sha256=item.content_sha256,
        limit=MAX_MATERIALIZATION_BATCH_UTF8_BYTES,
    )
    return MaterializationFileReceipt(
        file_index=index,
        path=item.path,
        status=status,
        actual_sha256=actual_hash,
    )


def pending_receipt_status(
    receipts: list[MaterializationFileReceipt], applied_any: bool, stop: bool
) -> MaterializationReceiptStatus:
    receipt_status: MaterializationReceiptStatus
    if stop or any(item.status in {"conflict", "uncertain", "not_attempted"} for item in receipts):
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
    return receipt_status


def checkpoint_pending_receipts(
    service: OutputMaterializationService,
    directory_fd: int,
    manifest: PreparedMaterializationManifest,
    manifest_hash: str,
    receipts: list[MaterializationFileReceipt],
    prior_receipt: MaterializationReceipt | None,
) -> bool:
    failed = False
    try:
        service._persist_receipt(
            directory_fd,
            manifest,
            manifest_hash,
            receipts,
            final=False,
            prior_receipt=prior_receipt,
        )
    except MaterializationStorageError:
        failed = True
        if receipts:
            last = receipts[-1]
            if last.status == "applied":
                receipts[-1] = last.model_copy(update={"status": "uncertain"})
    return failed
