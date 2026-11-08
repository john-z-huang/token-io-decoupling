"""托管物化根目录描述符、锁与候选产物生命周期。"""

from __future__ import annotations

import fcntl
import os
import stat
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from typing import Literal

from token_io_decoupling_core.materialization_models import DirectoryIdentity

from . import filesystem as _filesystem
from . import publication as _publication
from .filesystem import MaterializationStorageError


class MaterializationStorage:
    """Pin configured roots and provide bounded, no-follow, atomic file operations."""

    def __init__(
        self,
        project_root: str | os.PathLike[str],
        artifact_root: str | os.PathLike[str],
        *,
        expected_project_identity: tuple[int, int],
    ) -> None:
        self.project_path = Path(project_root)
        self.artifact_path = Path(artifact_root)
        self.project_fd = -1
        self.artifact_fd = -1
        if not self._secure_dirfd_available():
            raise MaterializationStorageError("secure_dirfd_unavailable")
        if self._paths_overlap(self.project_path, self.artifact_path):
            raise MaterializationStorageError("materialization_roots_must_be_disjoint")
        try:
            self.project_fd = self._open_absolute_directory(self.project_path)
            self.artifact_fd = self._open_absolute_directory(self.artifact_path)
            self.project_identity = self.directory_identity(self.project_fd)
            self.artifact_identity = self.directory_identity(self.artifact_fd)
            if self.project_identity == self.artifact_identity:
                raise MaterializationStorageError("materialization_roots_must_be_disjoint")
            artifact_metadata = os.fstat(self.artifact_fd)
            if stat.S_IMODE(artifact_metadata.st_mode) & 0o077:
                raise MaterializationStorageError("artifact_root_must_be_private")
            if (
                self.project_identity.device,
                self.project_identity.inode,
            ) != expected_project_identity:
                raise MaterializationStorageError("preflight_project_root_mismatch")
        except Exception:
            self.close()
            raise

    @staticmethod
    def _secure_dirfd_available() -> bool:
        return (
            hasattr(os, "O_NOFOLLOW")
            and hasattr(os, "O_DIRECTORY")
            and hasattr(os, "supports_dir_fd")
            and os.open in os.supports_dir_fd
            and os.link in os.supports_dir_fd
            and os.rename in os.supports_dir_fd
            and os.stat in os.supports_dir_fd
        )

    @staticmethod
    def _open_absolute_directory(path: Path) -> int:
        if not path.is_absolute():
            raise MaterializationStorageError("materialization_roots_must_be_absolute")
        parts = path.parts
        if not parts or parts[0] != "/" or any(part in {"", ".", ".."} for part in parts[1:]):
            raise MaterializationStorageError("materialization_root_path_invalid")
        flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0)
        current_fd = os.open("/", flags)
        try:
            for part in parts[1:]:
                next_fd = os.open(part, flags, dir_fd=current_fd)
                os.close(current_fd)
                current_fd = next_fd
            return current_fd
        except Exception:
            os.close(current_fd)
            raise

    @staticmethod
    def _paths_overlap(first: Path, second: Path) -> bool:
        first_parts = first.parts
        second_parts = second.parts
        return (
            first_parts[: len(second_parts)] == second_parts
            or second_parts[: len(first_parts)] == first_parts
        )

    @staticmethod
    def directory_identity(fd: int) -> DirectoryIdentity:
        metadata = os.fstat(fd)
        if not stat.S_ISDIR(metadata.st_mode):
            raise MaterializationStorageError("configured_root_not_directory")
        return DirectoryIdentity(device=metadata.st_dev, inode=metadata.st_ino)

    def verify_roots(self, expected_project_identity: tuple[int, int]) -> None:
        fresh_project = -1
        fresh_artifact = -1
        try:
            fresh_project = self._open_absolute_directory(self.project_path)
            fresh_artifact = self._open_absolute_directory(self.artifact_path)
            if self.directory_identity(fresh_project) != self.project_identity:
                raise MaterializationStorageError("configured_project_root_changed")
            if self.directory_identity(fresh_artifact) != self.artifact_identity:
                raise MaterializationStorageError("configured_artifact_root_changed")
            if (
                self.project_identity.device,
                self.project_identity.inode,
            ) != expected_project_identity:
                raise MaterializationStorageError("preflight_project_root_mismatch")
            if stat.S_IMODE(os.fstat(fresh_artifact).st_mode) & 0o077:
                raise MaterializationStorageError("artifact_root_must_be_private")
        except MaterializationStorageError:
            raise
        except OSError as exc:
            raise MaterializationStorageError("configured_roots_unavailable") from exc
        finally:
            if fresh_project >= 0:
                os.close(fresh_project)
            if fresh_artifact >= 0:
                os.close(fresh_artifact)

    @contextmanager
    def locked(self) -> Generator[None, None, None]:
        try:
            fd = os.open(
                ".output-materialization.lock",
                os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0),
                0o600,
                dir_fd=self.artifact_fd,
            )
            if not stat.S_ISREG(os.fstat(fd).st_mode):
                os.close(fd)
                raise MaterializationStorageError("artifact_lock_invalid")
        except OSError as exc:
            raise MaterializationStorageError("artifact_lock_unavailable") from exc
        try:
            fcntl.flock(fd, fcntl.LOCK_EX)
            yield
        finally:
            try:
                fcntl.flock(fd, fcntl.LOCK_UN)
            finally:
                os.close(fd)

    def persist_prepared(
        self, prepared_id: str, candidate_contents: list[bytes], manifest: bytes
    ) -> None:
        try:
            os.mkdir(prepared_id, 0o700, dir_fd=self.artifact_fd)
            directory_fd = self.open_prepared(prepared_id)
        except OSError as exc:
            raise MaterializationStorageError("artifact_directory_create_failed") from exc
        try:
            for index, content in enumerate(candidate_contents):
                self._write_once(directory_fd, f"candidate-{index:02d}.bin", content, 0o400)
            self._write_once(directory_fd, "manifest.json", manifest, 0o400)
            os.fsync(directory_fd)
        except Exception:
            for name in [
                *(f"candidate-{index:02d}.bin" for index in range(len(candidate_contents))),
                "manifest.json",
            ]:
                try:
                    os.unlink(name, dir_fd=directory_fd)
                except OSError:
                    pass
            os.close(directory_fd)
            try:
                os.rmdir(prepared_id, dir_fd=self.artifact_fd)
            except OSError:
                pass
            raise
        else:
            os.close(directory_fd)

    def open_prepared(self, prepared_id: str) -> int:
        if len(prepared_id) != 32 or any(
            character not in "0123456789abcdef" for character in prepared_id
        ):
            raise MaterializationStorageError("prepared_artifact_id_invalid")
        try:
            fd = os.open(
                prepared_id,
                os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0),
                dir_fd=self.artifact_fd,
            )
        except OSError as exc:
            raise MaterializationStorageError("prepared_artifact_unavailable") from exc
        if not stat.S_ISDIR(os.fstat(fd).st_mode):
            os.close(fd)
            raise MaterializationStorageError("prepared_artifact_unavailable")
        return fd

    def read_file(
        self, directory_fd: int, leaf: str, *, limit: int
    ) -> tuple[bytes | None, int | None]:
        return _filesystem.read_file(self, directory_fd, leaf, limit=limit)

    def read_project_file(self, path: str, *, limit: int) -> bytes | None:
        return _filesystem.read_project_file(self, path, limit=limit)

    def publish_project_file(
        self,
        path: str,
        content: bytes,
        *,
        operation: Literal["create", "replace"],
        baseline_state: Literal["absent", "sha256"],
        baseline_sha256: str | None,
        candidate_sha256: str,
        limit: int,
    ) -> tuple[Literal["applied", "already_identical", "conflict", "uncertain"], str | None]:
        return _publication.publish_project_file(
            self,
            path,
            content,
            operation=operation,
            baseline_state=baseline_state,
            baseline_sha256=baseline_sha256,
            candidate_sha256=candidate_sha256,
            limit=limit,
        )

    def write_receipt(self, directory_fd: int, raw: bytes) -> None:
        self._atomic_replace(directory_fd, "receipt.json", raw, 0o600)

    def open_project_parent(self, path: str) -> tuple[int, str]:
        return _filesystem.open_project_parent(self, path)

    def _reconcile_create_collision(
        self, parent_fd: int, leaf: str, candidate_sha256: str, limit: int, exc: OSError
    ) -> bool:
        return _publication.reconcile_create_collision(
            self, parent_fd, leaf, candidate_sha256, limit, exc
        )

    def _atomic_project_write(
        self,
        parent_fd: int,
        leaf: str,
        content: bytes,
        *,
        operation: Literal["create", "replace"],
        baseline_state: Literal["absent", "sha256"],
        baseline_sha256: str | None,
        candidate_sha256: str,
        existing_mode: int | None,
        limit: int,
    ) -> bool:
        return _publication.atomic_project_write(
            self,
            parent_fd,
            leaf,
            content,
            operation=operation,
            baseline_state=baseline_state,
            baseline_sha256=baseline_sha256,
            candidate_sha256=candidate_sha256,
            existing_mode=existing_mode,
            limit=limit,
        )

    def _write_once(self, directory_fd: int, target: str, content: bytes, mode: int) -> None:
        return _publication.write_once(self, directory_fd, target, content, mode)

    def _atomic_replace(self, directory_fd: int, target: str, content: bytes, mode: int) -> None:
        return _publication.atomic_replace(self, directory_fd, target, content, mode)

    @staticmethod
    def _new_temp_file(directory_fd: int, mode: int) -> tuple[str, int]:
        return _publication.new_temp_file(directory_fd, mode)

    @staticmethod
    def _write_all(fd: int, content: bytes) -> None:
        return _publication.write_all(fd, content)

    @staticmethod
    def _matches_baseline(
        current: bytes | None, baseline_state: str, baseline_sha256: str | None
    ) -> bool:
        if baseline_state == "absent":
            return current is None
        return current is not None and MaterializationStorage._sha256(current) == baseline_sha256

    @staticmethod
    def _same_file_state(first: os.stat_result, second: os.stat_result) -> bool:
        return (
            first.st_dev,
            first.st_ino,
            first.st_mode,
            first.st_size,
            first.st_mtime_ns,
            first.st_ctime_ns,
        ) == (
            second.st_dev,
            second.st_ino,
            second.st_mode,
            second.st_size,
            second.st_mtime_ns,
            second.st_ctime_ns,
        )

    @staticmethod
    def _sha256(raw: bytes) -> str:
        import hashlib

        return hashlib.sha256(raw).hexdigest()

    def close(self) -> None:
        for fd_name in ("project_fd", "artifact_fd"):
            fd = getattr(self, fd_name, -1)
            if fd >= 0:
                try:
                    os.close(fd)
                except OSError:
                    pass
                setattr(self, fd_name, -1)
