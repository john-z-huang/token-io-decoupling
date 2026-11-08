"""检查已准备候选和当前项目文件，生成预检投影。"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from token_io_decoupling_core.materialization_models import (
    MAX_MATERIALIZATION_BATCH_UTF8_BYTES,
    MaterializationInspectRequest,
    MaterializationOperation,
    MaterializationReceipt,
    PreparedMaterializationFile,
    PreparedMaterializationManifest,
)
from token_io_decoupling_tools.artifact_storage.filesystem import MaterializationStorageError

from .models import _MaterializationFailure

if TYPE_CHECKING:
    from .service import OutputMaterializationService


def inspect(
    service: OutputMaterializationService, request: MaterializationInspectRequest
) -> dict[str, object]:
    authority = service._authorize()
    manifest, manifest_hash, directory_fd = service._load_prepared(
        request.prepared_id, request.expected_manifest_hash
    )
    assert service._storage is not None
    try:
        service._match_manifest(authority, manifest)
        if request.file_index >= len(manifest.files):
            raise _MaterializationFailure("prepared_file_index_out_of_range")
        file = manifest.files[request.file_index]
        content = service._read_candidate(directory_fd, file)
        text = service._decode_content(content)
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


def read_candidate(
    service: OutputMaterializationService, directory_fd: int, item: PreparedMaterializationFile
) -> bytes:
    assert service._storage is not None
    raw, _ = service._storage.read_file(
        directory_fd,
        item.artifact_name,
        limit=MAX_MATERIALIZATION_BATCH_UTF8_BYTES,
    )
    if raw is None or service._sha256(raw) != item.content_sha256 or len(raw) != item.content_bytes:
        raise _MaterializationFailure("prepared_candidate_hash_mismatch")
    text = service._decode_content(raw)
    if len(text) != item.content_chars:
        raise _MaterializationFailure("prepared_candidate_metadata_mismatch")
    return raw


def classify_current_files(
    service: OutputMaterializationService,
    manifest: PreparedMaterializationManifest,
    contents: dict[int, bytes],
    prior_receipt: MaterializationReceipt | None,
) -> list[str]:
    states: list[str] = []
    assert service._storage is not None
    for index, item in enumerate(manifest.files):
        try:
            current = service._storage.read_project_file(
                item.path, limit=MAX_MATERIALIZATION_BATCH_UTF8_BYTES
            )
        except MaterializationStorageError:
            states.append("conflict")
            continue
        if current is not None and service._sha256(current) == service._sha256(contents[index]):
            states.append("already_identical")
        elif service._prior_requires_reconciliation(prior_receipt, index):
            states.append("conflict")
        elif service._matches_baseline(item, current):
            states.append("pending")
        else:
            states.append("conflict")
    return states


def preflight_projection(
    service: OutputMaterializationService,
    manifest: PreparedMaterializationManifest,
    contents: dict[int, bytes],
    states: list[str],
) -> list[dict[str, object]]:
    candidates: list[dict[str, object]] = []
    for index, (item, state) in enumerate(zip(manifest.files, states, strict=True)):
        content = service._decode_content(contents[index])
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
