from __future__ import annotations

import hashlib
import os
import stat

import pytest
from token_io_decoupling_tools.materialization_storage import (
    MaterializationStorage,
    MaterializationStorageError,
)


def _storage(tmp_path):
    project = tmp_path / "project"
    artifacts = tmp_path / "artifacts"
    project.mkdir()
    artifacts.mkdir(mode=0o700)
    os.chmod(artifacts, 0o700)
    metadata = project.stat()
    storage = MaterializationStorage(
        project,
        artifacts,
        expected_project_identity=(metadata.st_dev, metadata.st_ino),
    )
    return project, artifacts, storage


def _digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def test_roots_are_pinned_and_artifact_root_must_be_private(tmp_path) -> None:
    project = tmp_path / "project"
    artifacts = tmp_path / "artifacts"
    project.mkdir()
    artifacts.mkdir(mode=0o755)
    os.chmod(artifacts, 0o755)

    with pytest.raises(MaterializationStorageError, match="artifact_root_must_be_private"):
        MaterializationStorage(
            project,
            artifacts,
            expected_project_identity=(project.stat().st_dev, project.stat().st_ino),
        )

    artifacts.chmod(0o700)
    storage = MaterializationStorage(
        project,
        artifacts,
        expected_project_identity=(project.stat().st_dev, project.stat().st_ino),
    )
    try:
        moved = tmp_path / "moved-project"
        project.rename(moved)
        project.mkdir()
        with pytest.raises(MaterializationStorageError, match="configured_project_root_changed"):
            storage.verify_roots((moved.stat().st_dev, moved.stat().st_ino))
    finally:
        storage.close()


def test_artifacts_are_published_immutably_and_read_with_bounds(tmp_path) -> None:
    _project, _artifacts, storage = _storage(tmp_path)
    try:
        storage.persist_prepared("a" * 32, [b"candidate"], b"manifest")
        with pytest.raises(MaterializationStorageError, match="prepared_artifact_id_invalid"):
            storage.open_prepared("a" * 31)
        with pytest.raises(MaterializationStorageError, match="prepared_artifact_id_invalid"):
            storage.open_prepared("A" * 32)
        directory_fd = storage.open_prepared("a" * 32)
        try:
            manifest, _ = storage.read_file(directory_fd, "manifest.json", limit=1024)
            candidate, mode = storage.read_file(directory_fd, "candidate-00.bin", limit=1024)
            assert manifest == b"manifest"
            assert candidate == b"candidate"
            assert mode == 0o400
            with pytest.raises(MaterializationStorageError, match="not_bounded_regular_file"):
                storage.read_file(directory_fd, "candidate-00.bin", limit=3)
        finally:
            os.close(directory_fd)
    finally:
        storage.close()


def test_create_is_no_clobber_and_identical_replay_does_not_rewrite(tmp_path) -> None:
    project, _artifacts, storage = _storage(tmp_path)
    try:
        (project / "src").mkdir()
        content = b"new output\n"
        digest = _digest(content)
        result = storage.publish_project_file(
            "src/output.py",
            content,
            operation="create",
            baseline_state="absent",
            baseline_sha256=None,
            candidate_sha256=digest,
            limit=1024,
        )
        assert result == ("applied", digest)
        file_path = project / "src" / "output.py"
        inode = file_path.stat().st_ino
        assert storage.publish_project_file(
            "src/output.py",
            content,
            operation="create",
            baseline_state="absent",
            baseline_sha256=None,
            candidate_sha256=digest,
            limit=1024,
        ) == ("already_identical", digest)
        assert file_path.stat().st_ino == inode
        assert (
            storage.publish_project_file(
                "src/output.py",
                b"different\n",
                operation="create",
                baseline_state="absent",
                baseline_sha256=None,
                candidate_sha256=_digest(b"different\n"),
                limit=1024,
            )[0]
            == "conflict"
        )
    finally:
        storage.close()


def test_replace_requires_expected_hash_and_preserves_ordinary_mode(tmp_path) -> None:
    project, _artifacts, storage = _storage(tmp_path)
    try:
        target = project / "config.txt"
        target.write_bytes(b"before")
        target.chmod(0o640)
        old_hash = _digest(b"before")
        new_hash = _digest(b"after")
        assert storage.publish_project_file(
            "config.txt",
            b"after",
            operation="replace",
            baseline_state="sha256",
            baseline_sha256=old_hash,
            candidate_sha256=new_hash,
            limit=1024,
        ) == ("applied", new_hash)
        assert target.read_bytes() == b"after"
        assert stat.S_IMODE(target.stat().st_mode) == 0o640
        assert (
            storage.publish_project_file(
                "config.txt",
                b"third",
                operation="replace",
                baseline_state="sha256",
                baseline_sha256=old_hash,
                candidate_sha256=_digest(b"third"),
                limit=1024,
            )[0]
            == "conflict"
        )
    finally:
        storage.close()


def test_replace_does_not_promote_an_existing_zero_mode(tmp_path, monkeypatch) -> None:
    project, _artifacts, storage = _storage(tmp_path)
    try:
        (project / "config.txt").write_bytes(b"before")
        reads = iter([(b"before", 0), (b"before", 0), (b"after", 0)])
        monkeypatch.setattr(storage, "read_file", lambda *_args, **_kwargs: next(reads))
        requested_modes = []
        monkeypatch.setattr(os, "fchmod", lambda _fd, mode: requested_modes.append(mode))
        assert storage.publish_project_file(
            "config.txt",
            b"after",
            operation="replace",
            baseline_state="sha256",
            baseline_sha256=_digest(b"before"),
            candidate_sha256=_digest(b"after"),
            limit=1024,
        ) == ("applied", _digest(b"after"))
        assert requested_modes == [0]
    finally:
        storage.close()


def test_project_reads_and_writes_reject_symlink_targets_and_parents(tmp_path) -> None:
    project, _artifacts, storage = _storage(tmp_path)
    try:
        (project / "outside.txt").write_text("safe")
        (project / "link.txt").symlink_to(project / "outside.txt")
        with pytest.raises(MaterializationStorageError):
            storage.read_project_file("link.txt", limit=1024)
        assert (
            storage.publish_project_file(
                "link.txt",
                b"candidate",
                operation="create",
                baseline_state="absent",
                baseline_sha256=None,
                candidate_sha256=_digest(b"candidate"),
                limit=1024,
            )[0]
            == "conflict"
        )
        with pytest.raises(MaterializationStorageError):
            storage.read_project_file("missing/output.txt", limit=1024)
    finally:
        storage.close()
