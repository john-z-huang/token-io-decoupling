"""生成、持久化并读取待审阅的候选内容及清单。"""

from __future__ import annotations

import hashlib
import json
import os
import uuid
from typing import TYPE_CHECKING, Any

from pydantic import (
    ValidationError,
)

from token_io_decoupling_core.materialization_models import (
    DEFAULT_INSPECT_CHARS,
    MAX_MATERIALIZATION_BATCH_UTF8_BYTES,
    MAX_MATERIALIZATION_TEXT_CHARS,
    MaterializationPrepareRequest,
    PreparedMaterializationFile,
    PreparedMaterializationManifest,
)

from .models import _MaterializationFailure

if TYPE_CHECKING:
    from .service import OutputMaterializationService


def prepare(
    service: OutputMaterializationService, request: MaterializationPrepareRequest
) -> dict[str, object]:
    authority = service._authorize()
    templates: list[tuple[int, Any]] = []
    total_bytes = 0
    for index, spec in enumerate(request.files):
        service._authorize_file(spec, authority["grant"], authority["assignment"])
        templates.append((index, spec.template))
    rendered = service._renderer.render_all(
        templates,
        grant=authority["grant"],
        outbound_data_permitted=request.outbound_data_permitted,
    )
    contents: list[bytes] = []
    previews: list[str] = []
    file_rows: list[PreparedMaterializationFile] = []
    for index, spec in enumerate(request.files):
        content = rendered[index]
        encoded = service._bounded_content_bytes(content)
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
                content_sha256=service._sha256(encoded),
                content_bytes=len(encoded),
                content_chars=len(content),
                artifact_name=f"candidate-{index:02d}.bin",
            )
        )
    service._same_authority(authority, service._authorize())
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
    manifest_bytes = service._canonical_json(manifest.model_dump(mode="json"))
    manifest_hash = service._sha256(manifest_bytes)
    assert service._storage is not None
    service._storage.persist_prepared(prepared_id, contents, manifest_bytes)
    verified_manifest, verified_hash, verified_fd = service._load_prepared(
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


def load_prepared(
    service: OutputMaterializationService, prepared_id: str, expected_hash: str
) -> tuple[PreparedMaterializationManifest, str, int]:
    assert service._storage is not None
    directory_fd = service._storage.open_prepared(prepared_id)
    try:
        raw, _ = service._storage.read_file(directory_fd, "manifest.json", limit=32_768)
        if raw is None:
            raise _MaterializationFailure("prepared_manifest_unavailable")
        parsed_json = service._loads_no_duplicates(raw)
        try:
            manifest = PreparedMaterializationManifest.model_validate(parsed_json, strict=True)
        except ValidationError as exc:
            raise _MaterializationFailure("prepared_manifest_invalid") from exc
        canonical = service._canonical_json(manifest.model_dump(mode="json"))
        manifest_hash = service._sha256(canonical)
        if (
            raw != canonical
            or manifest_hash != expected_hash
            or manifest.prepared_id != prepared_id
        ):
            raise _MaterializationFailure("prepared_manifest_hash_mismatch")
        actual_batch_bytes = 0
        for item in manifest.files:
            content = service._read_candidate(directory_fd, item)
            actual_batch_bytes += len(content)
            if actual_batch_bytes > MAX_MATERIALIZATION_BATCH_UTF8_BYTES:
                raise _MaterializationFailure("candidate_batch_byte_limit_exceeded")
        return manifest, manifest_hash, directory_fd
    except Exception:
        os.close(directory_fd)
        raise


def bounded_content_bytes(content: str) -> bytes:
    if len(content) > MAX_MATERIALIZATION_TEXT_CHARS:
        raise _MaterializationFailure("candidate_file_char_limit_exceeded")
    try:
        return content.encode("utf-8", errors="strict")
    except UnicodeEncodeError as exc:
        raise _MaterializationFailure("candidate_content_not_valid_utf8") from exc


def canonical_json(value: object) -> bytes:
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


def loads_no_duplicates(raw: bytes) -> object:
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


def decode_content(raw: bytes) -> str:
    try:
        return raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise _MaterializationFailure("materialization_content_not_utf8") from exc


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()
