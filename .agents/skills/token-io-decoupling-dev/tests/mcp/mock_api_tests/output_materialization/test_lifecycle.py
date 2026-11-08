"""物化产物的准备、检查、并发应用及完整性验证。"""

from __future__ import annotations

import hashlib
import json
import threading

import pytest
from pydantic import ValidationError
from support import materialization_workspace as fixture
from support.materialization_workspace import (
    _apply,
    _literal_file,
    _literal_prepare,
    _string_field,
    _workspace,
)

from token_io_decoupling_core.materialization_models import (
    MaterializationInspectRequest,
    MaterializationPrepareRequest,
    PreparedMaterializationManifest,
)


def test_prepare_inspect_apply_and_create_retry_use_real_confirmed_assignment(tmp_path) -> None:
    path = "src/output.txt"
    project, artifacts, _state, _provider, preflight, grant_provider, _config, materializer = (
        _workspace(tmp_path, [path], allowed_operations=["create"])
    )
    try:
        prepared = materializer.execute(_literal_prepare(path, "bounded result\n"))
        assert prepared["status"] == "prepared"
        assert not (project / path).exists()
        assert len(list(artifacts.iterdir())) == 1
        manifest_hash = prepared["manifest_sha256"]
        prepared_id = prepared["prepared_id"]
        inspected = materializer.execute(
            MaterializationInspectRequest(
                action="inspect",
                prepared_id=prepared_id,
                expected_manifest_hash=manifest_hash,
                file_index=0,
                max_chars=5,
            )
        )
        assert inspected["status"] == "inspected"
        assert inspected["content"] == "bound"
        assert inspected["next_offset"] == 5
        assert inspected["complete"] is False

        applied = _apply(materializer, prepared)
        assert applied["status"] == "applied"
        assert applied["fresh_preflight"] == "pass"
        assert (project / path).read_text() == "bounded result\n"
        replay = _apply(materializer, prepared)
        assert replay["status"] == "already_identical"
        assert replay["files"][0]["status"] == "already_identical"
        assert (
            replay["preflight_projection"]
            == "already_identical_files_use_candidate_sha256_baseline"
        )
        assert grant_provider.grant is not None
        assert grant_provider.grant.allowed_operations == ["create"]
    finally:
        materializer.close()
        preflight.close()


def test_concurrent_identical_apply_is_cooperatively_serialized(tmp_path) -> None:
    path = "src/output.txt"
    project, _artifacts, _state, _provider, preflight, _grant_provider, _config, materializer = (
        _workspace(tmp_path, [path])
    )
    try:
        prepared = materializer.execute(_literal_prepare(path, "candidate\n"))
        barrier = threading.Barrier(3)
        results: list[dict[str, object]] = []

        def apply_concurrently() -> None:
            barrier.wait()
            results.append(_apply(materializer, prepared))

        threads = [threading.Thread(target=apply_concurrently) for _ in range(2)]
        for thread in threads:
            thread.start()
        barrier.wait()
        for thread in threads:
            thread.join(timeout=5)

        assert all(not thread.is_alive() for thread in threads)
        assert sorted(str(result["status"]) for result in results) == [
            "already_identical",
            "applied",
        ], results
        assert (project / path).read_text() == "candidate\n"
    finally:
        materializer.close()
        preflight.close()


def test_apply_rejects_stale_baseline_and_tampered_candidate(tmp_path) -> None:
    path = "src/output.txt"
    project, artifacts, _state, _provider, preflight, _grant_provider, _config, materializer = (
        _workspace(tmp_path, [path])
    )
    try:
        prepared = materializer.execute(_literal_prepare(path, "candidate\n"))
        (project / path).write_text("external change\n")
        conflict = _apply(materializer, prepared)
        assert conflict["status"] == "blocked"
        assert conflict["reason_code"] == "materialization_baseline_conflict"
        (project / path).unlink()

        candidate = artifacts / str(prepared["prepared_id"]) / "candidate-00.bin"
        candidate.chmod(0o600)
        candidate.write_text("tampered\n")
        tampered = materializer.execute(
            MaterializationInspectRequest(
                action="inspect",
                prepared_id=_string_field(prepared, "prepared_id"),
                expected_manifest_hash=_string_field(prepared, "manifest_sha256"),
                file_index=0,
            )
        )
        assert tampered["status"] == "blocked"
        assert tampered["reason_code"] == "prepared_candidate_hash_mismatch"
        assert not (project / path).exists()
    finally:
        materializer.close()
        preflight.close()


def test_manifest_version_types_and_actual_artifact_batch_bytes_are_strict(tmp_path) -> None:
    paths = [f"src/output-{index}.txt" for index in range(5)]
    project, artifacts, _state, _provider, preflight, _grant_provider, _config, materializer = (
        _workspace(tmp_path, paths)
    )
    try:
        oversized = MaterializationPrepareRequest(
            action="prepare",
            files=[_literal_file(path, "x" * 131_072) for path in paths],
        )
        blocked_prepare = materializer.execute(oversized)
        assert blocked_prepare["status"] == "blocked"
        assert blocked_prepare["reason_code"] == "candidate_batch_byte_limit_exceeded"
        assert not list(artifacts.iterdir())

        unicode_oversized = MaterializationPrepareRequest(
            action="prepare",
            files=[_literal_file(path, "é" * 131_072) for path in paths[:3]],
        )
        blocked_unicode = materializer.execute(unicode_oversized)
        assert blocked_unicode["status"] == "blocked"
        assert blocked_unicode["reason_code"] == "candidate_batch_byte_limit_exceeded"
        assert not list(artifacts.iterdir())

        prepared = materializer.execute(
            MaterializationPrepareRequest(
                action="prepare",
                files=[_literal_file(path, "x") for path in paths],
            )
        )
        assert prepared["status"] == "prepared"
        prepared_dir = artifacts / str(prepared["prepared_id"])
        manifest_path = prepared_dir / "manifest.json"
        manifest_raw = json.loads(manifest_path.read_text())
        manifest_path.chmod(0o600)
        for version_field in ("version", "policy_version"):
            for invalid in (True, 1.0):
                altered = dict(manifest_raw)
                altered[version_field] = invalid
                with pytest.raises(ValidationError):
                    PreparedMaterializationManifest.model_validate(altered, strict=True)

        expanded = b"z" * 131_072
        for index, item in enumerate(manifest_raw["files"]):
            candidate_path = prepared_dir / f"candidate-{index:02d}.bin"
            candidate_path.chmod(0o600)
            candidate_path.write_bytes(expanded)
            item["content_sha256"] = hashlib.sha256(expanded).hexdigest()
            item["content_bytes"] = len(expanded)
            item["content_chars"] = len(expanded)
        canonical = json.dumps(
            manifest_raw,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        manifest_path.write_bytes(canonical)
        tampered_hash = hashlib.sha256(canonical).hexdigest()
        inspected = materializer.execute(
            MaterializationInspectRequest(
                action="inspect",
                prepared_id=_string_field(prepared, "prepared_id"),
                expected_manifest_hash=tampered_hash,
                file_index=0,
            )
        )
        assert inspected["status"] == "blocked"
        assert inspected["reason_code"] == "candidate_batch_byte_limit_exceeded"
        assert not any((project / path).exists() for path in paths)
    finally:
        materializer.close()
        preflight.close()


def test_current_generic_code_materialization_keeps_prepare_inspect_preflight_apply_guards(
    tmp_path,
):
    project, _artifacts, _binding, _provider, preflight, _grant, _config, materializer = (
        fixture._workspace(tmp_path, ["src/current.txt"])
    )
    try:
        prepared = materializer.execute(
            fixture._literal_prepare("src/current.txt", "current code output\n")
        )
        assert prepared["status"] == "prepared"
        assert not (project / "src/current.txt").exists()
        inspected = materializer.execute(
            MaterializationInspectRequest(
                action="inspect",
                prepared_id=prepared["prepared_id"],
                expected_manifest_hash=prepared["manifest_sha256"],
                file_index=0,
                max_chars=8192,
            )
        )
        assert inspected["complete"] is True
        assert inspected["content"] == "current code output\n"
        applied = fixture._apply(materializer, prepared)
        assert applied["status"] == "applied"
        assert applied["fresh_preflight"] == "pass"
        assert (project / "src/current.txt").read_text() == "current code output\n"
    finally:
        materializer.close()
        preflight.close()
