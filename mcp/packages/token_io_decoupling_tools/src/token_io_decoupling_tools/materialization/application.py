"""应用已预检候选，按文件生成回执并处理部分完成。"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from token_io_decoupling_core.materialization_models import (
    MaterializationApplyRequest,
    MaterializationFileReceipt,
    MaterializationReceipt,
    PreparedMaterializationManifest,
)
from token_io_decoupling_tools.artifact_storage.filesystem import MaterializationStorageError

from .models import _MaterializationFailure

if TYPE_CHECKING:
    from .service import OutputMaterializationService


def apply(
    service: OutputMaterializationService, request: MaterializationApplyRequest
) -> dict[str, object]:
    assert service._storage is not None
    with service._storage.locked():
        authority = service._authorize()
        manifest, manifest_hash, directory_fd = service._load_prepared(
            request.prepared_id, request.expected_manifest_hash
        )
        try:
            service._match_manifest(authority, manifest)
            contents = {
                index: service._read_candidate(directory_fd, item)
                for index, item in enumerate(manifest.files)
            }
            prior_receipt = service._read_receipt(directory_fd, manifest, manifest_hash)
            initial_states = service._classify_current_files(manifest, contents, prior_receipt)
            if any(state == "conflict" for state in initial_states):
                files = [
                    service._file_receipt(index, item.path, state)
                    for index, (item, state) in enumerate(
                        zip(manifest.files, initial_states, strict=True)
                    )
                ]
                return service._blocked_apply(
                    "materialization_baseline_conflict",
                    request.prepared_id,
                    manifest_hash,
                    files,
                    identical_projection_count=sum(
                        state == "already_identical" for state in initial_states
                    ),
                )
            projection = service._preflight_projection(manifest, contents, initial_states)
            preflight = service._compliance_service.validate(
                {"policy_scope": manifest.policy_scope, "candidates": projection}
            )
            if (
                type(preflight.get("policy_version")) is not int
                or preflight.get("policy_version") != 2
                or preflight.get("status") != "pass"
                or service._compliance_service.root_identity()
                != (
                    service._storage.project_identity.device,
                    service._storage.project_identity.inode,
                )
            ):
                files = [
                    service._file_receipt(index, item.path, state)
                    for index, (item, state) in enumerate(
                        zip(manifest.files, initial_states, strict=True)
                    )
                ]
                return service._blocked_apply(
                    "fresh_preflight_not_passed",
                    request.prepared_id,
                    manifest_hash,
                    files,
                    preflight_status=str(preflight.get("status", "unknown")),
                    identical_projection_count=sum(
                        state == "already_identical" for state in initial_states
                    ),
                )
            return service._apply_pending(
                request,
                manifest,
                manifest_hash,
                directory_fd,
                contents,
                prior_receipt,
            )
        finally:
            os.close(directory_fd)


def apply_pending(
    service: OutputMaterializationService,
    request: MaterializationApplyRequest,
    manifest: PreparedMaterializationManifest,
    manifest_hash: str,
    directory_fd: int,
    contents: dict[int, bytes],
    prior_receipt: MaterializationReceipt | None,
) -> dict[str, object]:
    assert service._storage is not None
    receipts: list[MaterializationFileReceipt] = []
    applied_any = False
    stop = False
    for index, item in enumerate(manifest.files):
        if stop:
            receipts.append(
                MaterializationFileReceipt(file_index=index, path=item.path, status="not_attempted")
            )
            continue
        try:
            authority, candidate = service._reload_pending_candidate(
                request, manifest, manifest_hash, item, contents[index]
            )
            file_receipt = service._publish_pending_file(
                authority, item, candidate, index, prior_receipt
            )
            receipts.append(file_receipt)
            status = file_receipt.status
            if status == "already_identical":
                service._persist_receipt(
                    directory_fd,
                    manifest,
                    manifest_hash,
                    receipts,
                    final=False,
                    prior_receipt=prior_receipt,
                )
                continue
            applied_any = applied_any or status == "applied"
            stop = status in {"conflict", "uncertain"}
        except _MaterializationFailure as exc:
            conflict = MaterializationFileReceipt(
                file_index=index, path=item.path, status="conflict"
            )
            if exc.reason == "worker_or_operator_grant_changed" and not applied_any:
                blocked_files = [*receipts, conflict]
                return service._blocked_apply(
                    exc.reason,
                    request.prepared_id,
                    manifest_hash,
                    blocked_files,
                    preflight_status="pass",
                    identical_projection_count=sum(
                        file_receipt.status == "already_identical" for file_receipt in blocked_files
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
        if service._checkpoint_pending_receipts(
            directory_fd, manifest, manifest_hash, receipts, prior_receipt
        ):
            stop = True
    receipt_status = service._pending_receipt_status(receipts, applied_any, stop)
    try:
        service._persist_receipt(
            directory_fd,
            manifest,
            manifest_hash,
            receipts,
            final=True,
            status=receipt_status,
            prior_receipt=prior_receipt,
        )
    except MaterializationStorageError:
        return service._blocked_apply(
            "materialization_receipt_write_uncertain",
            request.prepared_id,
            manifest_hash,
            receipts,
            identical_projection_count=sum(item.status == "already_identical" for item in receipts),
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
        "identical_projection_count": sum(item.status == "already_identical" for item in receipts),
    }
