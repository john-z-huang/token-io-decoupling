"""持久化、读取和分类输出物化回执。"""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING

from pydantic import (
    ValidationError,
)

from token_io_decoupling_core.materialization_models import (
    AbsentBaseline,
    MaterializationFileReceipt,
    MaterializationReceipt,
    PreparedMaterializationFile,
    PreparedMaterializationManifest,
    Sha256Baseline,
)

from .models import MaterializationReceiptStatus, _MaterializationFailure

if TYPE_CHECKING:
    from .service import OutputMaterializationService


def read_receipt(
    service: OutputMaterializationService,
    directory_fd: int,
    manifest: PreparedMaterializationManifest,
    manifest_hash: str,
) -> MaterializationReceipt | None:
    assert service._storage is not None
    raw, _ = service._storage.read_file(directory_fd, "receipt.json", limit=16_384)
    if raw is None:
        return None
    try:
        receipt = MaterializationReceipt.model_validate(
            service._loads_no_duplicates(raw), strict=True
        )
    except ValidationError as exc:
        raise _MaterializationFailure("materialization_receipt_invalid") from exc
    if (
        receipt.prepared_id != manifest.prepared_id
        or receipt.manifest_sha256 != manifest_hash
        or len(receipt.files) != len(manifest.files)
        or service._canonical_json(receipt.model_dump(mode="json")) != raw
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


def persist_receipt(
    service: OutputMaterializationService,
    directory_fd: int,
    manifest: PreparedMaterializationManifest,
    manifest_hash: str,
    files: list[MaterializationFileReceipt],
    *,
    final: bool,
    status: MaterializationReceiptStatus | None = None,
    prior_receipt: MaterializationReceipt | None = None,
) -> MaterializationReceipt:
    assert service._storage is not None
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
    encoded = service._canonical_json(receipt.model_dump(mode="json"))
    service._storage.write_receipt(directory_fd, encoded)
    return receipt


def blocked_apply(
    service: OutputMaterializationService,
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


def prior_requires_reconciliation(receipt: MaterializationReceipt | None, index: int) -> bool:
    return (
        receipt is not None
        and index < len(receipt.files)
        and receipt.files[index].status in {"applied", "already_identical", "uncertain"}
    )


def file_receipt(index: int, path: str, state: str) -> MaterializationFileReceipt:
    mapped = (
        state
        if state in {"applied", "already_identical", "conflict", "not_attempted", "uncertain"}
        else "conflict"
    )
    return MaterializationFileReceipt(
        file_index=index, path=path, status=mapped, actual_sha256=None
    )


def matches_baseline(item: PreparedMaterializationFile, current: bytes | None) -> bool:
    if item.operation == "create":
        return current is None and isinstance(item.baseline, AbsentBaseline)
    return (
        current is not None
        and isinstance(item.baseline, Sha256Baseline)
        and hashlib.sha256(current).hexdigest() == item.baseline.value
    )
