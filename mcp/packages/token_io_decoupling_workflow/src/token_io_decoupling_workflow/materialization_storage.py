"""No-follow filesystem primitives for prepared output artifacts and project files."""

from __future__ import annotations

import errno
import fcntl
import os
import secrets
import stat
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from typing import Literal

from token_io_decoupling_core.materialization_models import DirectoryIdentity


class MaterializationStorageError(Exception):
    """Sanitized storage failure with a stable reason code."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


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
        flags = os.O_RDONLY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0)
        flags |= getattr(os, "O_NONBLOCK", 0)
        try:
            fd = os.open(leaf, flags, dir_fd=directory_fd)
        except FileNotFoundError:
            return None, None
        except OSError as exc:
            raise MaterializationStorageError("materialization_target_unavailable") from exc
        try:
            before = os.fstat(fd)
            if not stat.S_ISREG(before.st_mode) or before.st_size > limit:
                raise MaterializationStorageError("materialization_target_not_bounded_regular_file")
            chunks: list[bytes] = []
            remaining = limit + 1
            while remaining > 0:
                chunk = os.read(fd, min(65_536, remaining))
                if not chunk:
                    break
                chunks.append(chunk)
                remaining -= len(chunk)
            content = b"".join(chunks)
            after = os.fstat(fd)
            linked = os.stat(leaf, dir_fd=directory_fd, follow_symlinks=False)
            if (
                len(content) > limit
                or not self._same_file_state(before, after)
                or not self._same_file_state(after, linked)
            ):
                raise MaterializationStorageError("materialization_target_changed_during_read")
            return content, stat.S_IMODE(after.st_mode)
        except OSError as exc:
            raise MaterializationStorageError("materialization_target_unavailable") from exc
        finally:
            os.close(fd)

    def read_project_file(self, path: str, *, limit: int) -> bytes | None:
        parent_fd, leaf = self.open_project_parent(path)
        try:
            content, _ = self.read_file(parent_fd, leaf, limit=limit)
            return content
        finally:
            os.close(parent_fd)

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
        parent_fd, leaf = self.open_project_parent(path)
        try:
            try:
                current, current_mode = self.read_file(parent_fd, leaf, limit=limit)
            except MaterializationStorageError:
                return "conflict", None
            if current is not None and self._sha256(current) == candidate_sha256:
                return "already_identical", candidate_sha256
            if not self._matches_baseline(current, baseline_state, baseline_sha256):
                return "conflict", self._sha256(current) if current is not None else None
            try:
                published = self._atomic_project_write(
                    parent_fd,
                    leaf,
                    content,
                    operation=operation,
                    baseline_state=baseline_state,
                    baseline_sha256=baseline_sha256,
                    candidate_sha256=candidate_sha256,
                    existing_mode=current_mode,
                    limit=limit,
                )
            except MaterializationStorageError as exc:
                if exc.reason == "materialization_write_uncertain":
                    return "uncertain", None
                raise
            if not published:
                return "already_identical", candidate_sha256
            try:
                readback, _ = self.read_file(parent_fd, leaf, limit=limit)
            except MaterializationStorageError:
                return "uncertain", None
            if readback is None:
                return "uncertain", None
            actual_hash = self._sha256(readback)
            if actual_hash != candidate_sha256:
                return "uncertain", actual_hash
            return "applied", actual_hash
        finally:
            os.close(parent_fd)

    def write_receipt(self, directory_fd: int, raw: bytes) -> None:
        self._atomic_replace(directory_fd, "receipt.json", raw, 0o600)

    def open_project_parent(self, path: str) -> tuple[int, str]:
        parts = path.split("/")
        if not parts or any(part in {"", ".", ".."} for part in parts):
            raise MaterializationStorageError("materialization_path_invalid")
        current_fd = os.dup(self.project_fd)
        flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0)
        try:
            for part in parts[:-1]:
                next_fd = os.open(part, flags, dir_fd=current_fd)
                os.close(current_fd)
                current_fd = next_fd
            return current_fd, parts[-1]
        except OSError as exc:
            os.close(current_fd)
            raise MaterializationStorageError("materialization_parent_unavailable") from exc

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
        temp_name, temp_fd = self._new_temp_file(
            parent_fd, 0o666 if operation == "create" else 0o600
        )
        try:
            self._write_all(temp_fd, content)
            if operation == "replace":
                safe_mode = existing_mode if existing_mode is not None else 0o600
                os.fchmod(temp_fd, safe_mode & 0o777)
            os.fsync(temp_fd)
            os.close(temp_fd)
            temp_fd = -1
            current, _ = self.read_file(parent_fd, leaf, limit=limit)
            if current is not None and self._sha256(current) == candidate_sha256:
                return False
            if not self._matches_baseline(current, baseline_state, baseline_sha256):
                raise MaterializationStorageError("materialization_baseline_conflict")
            if operation == "create":
                os.link(
                    temp_name,
                    leaf,
                    src_dir_fd=parent_fd,
                    dst_dir_fd=parent_fd,
                    follow_symlinks=False,
                )
                os.unlink(temp_name, dir_fd=parent_fd)
            else:
                os.replace(temp_name, leaf, src_dir_fd=parent_fd, dst_dir_fd=parent_fd)
            os.fsync(parent_fd)
            return True
        except MaterializationStorageError:
            raise
        except OSError as exc:
            if operation == "create" and exc.errno == errno.EEXIST:
                current, _ = self.read_file(parent_fd, leaf, limit=limit)
                if current is not None and self._sha256(current) == candidate_sha256:
                    return False
                raise MaterializationStorageError("materialization_create_target_occupied") from exc
            raise MaterializationStorageError("materialization_write_uncertain") from exc
        finally:
            if temp_fd >= 0:
                os.close(temp_fd)
            try:
                os.unlink(temp_name, dir_fd=parent_fd)
            except OSError:
                pass

    def _write_once(self, directory_fd: int, target: str, content: bytes, mode: int) -> None:
        temp_name, fd = self._new_temp_file(directory_fd, 0o600)
        try:
            self._write_all(fd, content)
            os.fchmod(fd, mode)
            os.fsync(fd)
            os.close(fd)
            fd = -1
            os.link(
                temp_name,
                target,
                src_dir_fd=directory_fd,
                dst_dir_fd=directory_fd,
                follow_symlinks=False,
            )
            os.unlink(temp_name, dir_fd=directory_fd)
            os.fsync(directory_fd)
        except OSError as exc:
            raise MaterializationStorageError("artifact_write_failed") from exc
        finally:
            if fd >= 0:
                os.close(fd)
            try:
                os.unlink(temp_name, dir_fd=directory_fd)
            except OSError:
                pass

    def _atomic_replace(self, directory_fd: int, target: str, content: bytes, mode: int) -> None:
        temp_name, fd = self._new_temp_file(directory_fd, 0o600)
        try:
            self._write_all(fd, content)
            os.fchmod(fd, mode)
            os.fsync(fd)
            os.close(fd)
            fd = -1
            os.replace(temp_name, target, src_dir_fd=directory_fd, dst_dir_fd=directory_fd)
            os.fsync(directory_fd)
        except OSError as exc:
            raise MaterializationStorageError("artifact_receipt_write_failed") from exc
        finally:
            if fd >= 0:
                os.close(fd)
            try:
                os.unlink(temp_name, dir_fd=directory_fd)
            except OSError:
                pass

    @staticmethod
    def _new_temp_file(directory_fd: int, mode: int) -> tuple[str, int]:
        for _ in range(5):
            name = f".tmp-{secrets.token_hex(16)}"
            try:
                fd = os.open(
                    name,
                    os.O_WRONLY
                    | os.O_CREAT
                    | os.O_EXCL
                    | os.O_NOFOLLOW
                    | getattr(os, "O_CLOEXEC", 0),
                    mode,
                    dir_fd=directory_fd,
                )
                return name, fd
            except FileExistsError:
                continue
        raise MaterializationStorageError("temporary_name_collision")

    @staticmethod
    def _write_all(fd: int, content: bytes) -> None:
        view = memoryview(content)
        while view:
            written = os.write(fd, view)
            if written <= 0:
                raise OSError("short_write")
            view = view[written:]

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
