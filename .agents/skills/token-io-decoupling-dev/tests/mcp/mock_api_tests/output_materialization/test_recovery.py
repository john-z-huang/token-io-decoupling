"""物化回执、部分成功及不确定写入的恢复边界。"""

from __future__ import annotations

import json

import pytest
from support.materialization_workspace import (
    _apply,
    _literal_file,
    _literal_prepare,
    _workspace,
)

from token_io_decoupling_core.materialization_models import (
    MaterializationPrepareRequest,
)
from token_io_decoupling_tools.materialization_storage import MaterializationStorageError


def test_partial_apply_replay_resumes_pending_file_and_blocks_reverted_applied_file(
    tmp_path, monkeypatch
) -> None:
    paths = ["src/first.txt", "src/second.txt"]
    project, _artifacts, _state, _provider, preflight, _grant_provider, _config, materializer = (
        _workspace(tmp_path, paths)
    )
    try:
        request = MaterializationPrepareRequest(
            action="prepare",
            files=[_literal_file(path, f"candidate {index}\n") for index, path in enumerate(paths)],
        )
        prepared = materializer.execute(request)
        store = materializer._storage
        assert store is not None
        original_publish = store.publish_project_file

        def fail_second(path: str, content: bytes, **kwargs):
            if path == paths[1]:
                return "conflict", None
            return original_publish(path, content, **kwargs)

        monkeypatch.setattr(store, "publish_project_file", fail_second)
        first = _apply(materializer, prepared)
        assert first["status"] == "partial"
        assert [item["status"] for item in first["files"]] == ["applied", "conflict"]

        monkeypatch.setattr(store, "publish_project_file", original_publish)
        resumed = _apply(materializer, prepared)
        assert resumed["status"] == "applied"
        assert [item["status"] for item in resumed["files"]] == [
            "already_identical",
            "applied",
        ]

        (project / paths[0]).unlink()
        reverted = _apply(materializer, prepared)
        assert reverted["status"] == "blocked"
        assert reverted["reason_code"] == "materialization_baseline_conflict"
        assert not (project / paths[0]).exists()
    finally:
        materializer.close()
        preflight.close()


def test_successful_replay_then_undo_is_not_reapplied(tmp_path) -> None:
    path = "src/output.txt"
    project, _artifacts, _state, _provider, preflight, _grant_provider, _config, materializer = (
        _workspace(tmp_path, [path])
    )
    try:
        prepared = materializer.execute(_literal_prepare(path, "candidate\n"))
        assert _apply(materializer, prepared)["status"] == "applied"
        assert _apply(materializer, prepared)["status"] == "already_identical"

        (project / path).unlink()
        replay = _apply(materializer, prepared)
        assert replay["status"] == "blocked"
        assert replay["reason_code"] == "materialization_baseline_conflict"
        assert not (project / path).exists()
    finally:
        materializer.close()
        preflight.close()


def test_uncertain_publish_then_confirmed_candidate_undo_is_not_reapplied(
    tmp_path, monkeypatch
) -> None:
    path = "src/output.txt"
    project, _artifacts, _state, _provider, preflight, _grant_provider, _config, materializer = (
        _workspace(tmp_path, [path])
    )
    try:
        prepared = materializer.execute(_literal_prepare(path, "candidate\n"))
        store = materializer._storage
        assert store is not None
        publish = store.publish_project_file

        def publish_but_report_uncertain(*args, **kwargs):
            publish(*args, **kwargs)
            return "uncertain", None

        monkeypatch.setattr(store, "publish_project_file", publish_but_report_uncertain)
        uncertain = _apply(materializer, prepared)
        assert uncertain["files"][0]["status"] == "uncertain"
        assert (project / path).read_text() == "candidate\n"

        monkeypatch.setattr(store, "publish_project_file", publish)
        confirmed = _apply(materializer, prepared)
        assert confirmed["status"] == "already_identical"

        (project / path).unlink()
        replay = _apply(materializer, prepared)
        assert replay["status"] == "blocked"
        assert replay["reason_code"] == "materialization_baseline_conflict"
        assert not (project / path).exists()
    finally:
        materializer.close()
        preflight.close()


def test_project_readback_failure_returns_uncertain_and_blocks_undo_replay(
    tmp_path, monkeypatch
) -> None:
    paths = ["src/first.txt", "src/second.txt"]
    project, _artifacts, _state, _provider, preflight, _grant_provider, _config, materializer = (
        _workspace(tmp_path, paths)
    )
    try:
        prepared = materializer.execute(
            MaterializationPrepareRequest(
                action="prepare",
                files=[
                    _literal_file(path, f"candidate {index}\n") for index, path in enumerate(paths)
                ],
            )
        )
        store = materializer._storage
        assert store is not None
        atomic_write = store._atomic_project_write

        def write_then_break_readback(*args, **kwargs):
            result = atomic_write(*args, **kwargs)
            read_file = store.read_file

            def fail_first_target_read(directory_fd, name, *, limit):
                if name == "first.txt":
                    raise MaterializationStorageError("project_readback_unavailable")
                return read_file(directory_fd, name, limit=limit)

            monkeypatch.setattr(store, "read_file", fail_first_target_read)
            return result

        monkeypatch.setattr(store, "_atomic_project_write", write_then_break_readback)
        uncertain = _apply(materializer, prepared)
        assert uncertain["status"] == "uncertain"
        assert [item["status"] for item in uncertain["files"]] == [
            "uncertain",
            "not_attempted",
        ]
        assert (project / paths[0]).read_text() == "candidate 0\n"

        (project / paths[0]).unlink()
        replay = _apply(materializer, prepared)
        assert replay["status"] == "blocked"
        assert replay["reason_code"] == "materialization_baseline_conflict"
        assert not any((project / path).exists() for path in paths)
    finally:
        materializer.close()
        preflight.close()


@pytest.mark.parametrize("tamper", ["order", "path", "length", "success_hash"])
def test_apply_rejects_receipts_that_do_not_match_manifest_files(tmp_path, tamper: str) -> None:
    paths = ["src/first.txt", "src/second.txt"]
    project, artifacts, _state, _provider, preflight, _grant_provider, _config, materializer = (
        _workspace(tmp_path, paths)
    )
    try:
        request = MaterializationPrepareRequest(
            action="prepare",
            files=[
                _literal_prepare(path, f"candidate {index}\n").files[0]
                for index, path in enumerate(paths)
            ],
        )
        prepared = materializer.execute(request)
        prepared_id = str(prepared["prepared_id"])
        manifest_hash = str(prepared["manifest_sha256"])
        manifest = json.loads((artifacts / prepared_id / "manifest.json").read_text())
        files = [
            {
                "file_index": index,
                "path": item["path"],
                "status": "already_identical",
                "actual_sha256": item["content_sha256"],
            }
            for index, item in enumerate(manifest["files"])
        ]
        if tamper == "order":
            files.reverse()
        elif tamper == "path":
            files[0]["path"] = "src/unrelated.txt"
        elif tamper == "length":
            files.pop()
        else:
            files[0]["actual_sha256"] = "0" * 64
        receipt = {
            "version": 1,
            "prepared_id": prepared_id,
            "manifest_sha256": manifest_hash,
            "status": "already_identical",
            "files": files,
        }
        canonical_receipt = (
            json.dumps(receipt, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
                "utf-8"
            )
            + b"\n"
        )
        (artifacts / prepared_id / "receipt.json").write_bytes(canonical_receipt)

        result = _apply(materializer, prepared)
        assert result["status"] == "blocked"
        assert result["reason_code"] == "materialization_receipt_invalid"
        assert not any((project / path).exists() for path in paths)
    finally:
        materializer.close()
        preflight.close()
