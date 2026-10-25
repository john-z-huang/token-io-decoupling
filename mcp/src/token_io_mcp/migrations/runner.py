"""Safe, bounded SQLite migration and recovery primitives."""

from __future__ import annotations

import fcntl
import hashlib
import importlib
import os
import sqlite3
import time
import uuid
from collections.abc import Callable, Generator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from types import ModuleType
from urllib.parse import quote

from token_io_mcp.models import DatabaseKind, SchemaStatus

SUPPORTED_DATABASE_KINDS = tuple(DatabaseKind)
DEFAULT_LOCK_TIMEOUT_SECONDS = 5.0


class StorageError(RuntimeError):
    """Base class for storage and migration failures."""


class UnsafeDatabasePathError(StorageError):
    """Raised when a database path is outside its trusted root or traverses a symlink."""


class MigrationLockTimeoutError(StorageError):
    """Raised when the bounded exclusive migration lock cannot be acquired."""


class UnknownDatabaseError(StorageError):
    """Raised when an existing file has no recognized application schema."""


class DatabaseKindMismatchError(StorageError):
    """Raised when a database is opened through the wrong Root/Worker path."""


class MigrationHistoryError(StorageError):
    """Raised when migration history is missing, discontinuous, or inconsistent."""


class MigrationChecksumError(MigrationHistoryError):
    """Raised when a recorded migration checksum differs from package source."""


class FutureSchemaError(MigrationHistoryError):
    """Raised when a database schema is newer than this package supports."""


class MigrationExecutionError(StorageError):
    """Raised when a migration fails and its transaction is rolled back."""


class DatabaseIdentityMismatchError(StorageError):
    """Raised when a stored logical identity differs from trusted host identity."""


@dataclass(frozen=True)
class _Migration:
    version: int
    name: str
    checksum: str
    upgrade: Callable[[sqlite3.Connection], None]


def _migration_from_module(module: ModuleType) -> _Migration:
    version = getattr(module, "VERSION", None)
    name = getattr(module, "NAME", None)
    upgrade = getattr(module, "upgrade", None)
    source_path = getattr(module, "__file__", None)
    if (
        type(version) is not int
        or version < 1
        or not isinstance(name, str)
        or not callable(upgrade)
    ):
        raise MigrationHistoryError(f"invalid package migration module: {module.__name__}")
    if not source_path:
        raise MigrationHistoryError(f"migration has no source file: {module.__name__}")
    checksum = hashlib.sha256(Path(source_path).read_bytes()).hexdigest()
    return _Migration(version=version, name=name, checksum=checksum, upgrade=upgrade)


def _package_migrations(kind: DatabaseKind) -> tuple[_Migration, ...]:
    if kind is DatabaseKind.WORKFLOW:
        module_names = (
            "token_io_mcp.migrations.workflow.v0001_initial",
            "token_io_mcp.migrations.workflow.v0002_control_state",
            "token_io_mcp.migrations.workflow.v0003_evidence_control",
            "token_io_mcp.migrations.workflow.v0004_session_metadata",
            "token_io_mcp.migrations.workflow.v0005_native_resolution",
        )
    else:
        module_names = (
            "token_io_mcp.migrations.worker.v0001_initial",
            "token_io_mcp.migrations.worker.v0002_worker_identity",
            "token_io_mcp.migrations.worker.v0003_evidence_dispatch",
        )
    migrations = tuple(
        _migration_from_module(importlib.import_module(name)) for name in module_names
    )
    _validate_migration_sequence(migrations)
    return migrations


def _validate_migration_sequence(migrations: Sequence[_Migration]) -> None:
    versions = [migration.version for migration in migrations]
    if versions != list(range(1, len(versions) + 1)):
        raise MigrationHistoryError(
            "package migration versions must be unique and contiguous from v0001"
        )
    if len({migration.name for migration in migrations}) != len(migrations):
        raise MigrationHistoryError("package migration names must be unique")


def open_database_for_authorized_write(
    database_path: Path | str,
    database_kind: DatabaseKind,
    *,
    trusted_root: Path | str,
    expected_identity: tuple[str, str, str | None] | None = None,
    lock_timeout_seconds: float = DEFAULT_LOCK_TIMEOUT_SECONDS,
) -> sqlite3.Connection:
    """Open after the caller has authorized a write; migrate with fixed package code only."""
    return _open_with_migrations(
        database_path,
        database_kind,
        trusted_root=trusted_root,
        migrations=_package_migrations(database_kind),
        expected_identity=expected_identity,
        lock_timeout_seconds=lock_timeout_seconds,
    )


def _open_with_migrations(
    database_path: Path | str,
    database_kind: DatabaseKind,
    *,
    trusted_root: Path | str,
    migrations: Sequence[_Migration],
    expected_identity: tuple[str, str, str | None] | None = None,
    lock_timeout_seconds: float = DEFAULT_LOCK_TIMEOUT_SECONDS,
) -> sqlite3.Connection:
    """Internal injection point for migration-runner tests; never exposed over MCP."""
    _validate_migration_sequence(migrations)
    path = _prepare_database_path(database_path, trusted_root, create_parent=True)
    if lock_timeout_seconds <= 0:
        raise ValueError("lock_timeout_seconds must be positive")

    with _migration_lock(path, trusted_root, lock_timeout_seconds):
        created = not path.exists()
        original_size = path.stat().st_size if path.exists() else 0
        if created:
            _create_empty_file(path)
        elif not path.is_file():
            raise UnknownDatabaseError("database path is not a regular file")

        connection = sqlite3.connect(path, timeout=lock_timeout_seconds, isolation_level=None)
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute(f"PRAGMA busy_timeout = {int(lock_timeout_seconds * 1000)}")
        try:
            initialized_from_empty = created or original_size == 0
            if not initialized_from_empty and expected_identity is not None:
                _validate_identity_before_migration(connection, database_kind, expected_identity)
            backup_created = False
            while True:
                current_version, has_catalog = _current_version(
                    connection,
                    database_kind,
                    migrations,
                    allow_empty=initialized_from_empty,
                )
                if not has_catalog:
                    migration = migrations[0]
                else:
                    if current_version >= migrations[-1].version:
                        break
                    if not backup_created:
                        _create_backup(connection, path, trusted_root)
                        backup_created = True
                    migration = migrations[current_version]

                connection.execute("BEGIN EXCLUSIVE")
                try:
                    locked_version, locked_catalog = _current_version(
                        connection,
                        database_kind,
                        migrations,
                        allow_empty=initialized_from_empty,
                    )
                    if locked_catalog and locked_version >= migrations[-1].version:
                        connection.rollback()
                        break
                    expected_version = 1 if not locked_catalog else locked_version + 1
                    if migration.version != expected_version:
                        connection.rollback()
                        continue
                    started = time.monotonic()
                    connection.set_authorizer(_deny_transaction_control)
                    try:
                        migration.upgrade(connection)
                    except Exception as exc:
                        raise MigrationExecutionError(
                            f"migration v{migration.version:04d} {migration.name!r} failed"
                        ) from exc
                    finally:
                        connection.set_authorizer(None)
                    if not connection.in_transaction:
                        raise MigrationExecutionError(
                            f"migration v{migration.version:04d} ended its manager transaction"
                        )
                    elapsed_ms = max(0, int((time.monotonic() - started) * 1000))
                    connection.execute(
                        """
                        INSERT INTO schema_migrations
                            (version, name, checksum, applied_at, duration_ms)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (
                            migration.version,
                            migration.name,
                            migration.checksum,
                            datetime.now(UTC).isoformat(),
                            elapsed_ms,
                        ),
                    )
                    migrated_version, _ = _current_version(
                        connection,
                        database_kind,
                        migrations,
                        allow_empty=False,
                    )
                    _validate_database_integrity(connection, database_kind)
                    _validate_schema_structure(
                        connection, database_kind, schema_version=migrated_version
                    )
                    connection.commit()
                    initialized_from_empty = False
                except Exception:
                    if connection.in_transaction:
                        connection.rollback()
                    raise

            current_version, _ = _current_version(
                connection, database_kind, migrations, allow_empty=False
            )
            _validate_database_integrity(connection, database_kind)
            _validate_schema_structure(connection, database_kind, schema_version=current_version)
            return connection
        except Exception:
            connection.close()
            if created and _is_empty_sqlite_file(path):
                path.unlink(missing_ok=True)
            raise


def read_schema_status(
    database_path: Path | str,
    expected_kind: DatabaseKind,
    *,
    trusted_root: Path | str,
) -> SchemaStatus:
    """Read compatibility without creating a database or applying migrations."""
    path = _prepare_database_path(database_path, trusted_root, create_parent=False)
    migrations = _package_migrations(expected_kind)
    target_version = migrations[-1].version
    if not path.exists():
        return SchemaStatus(
            exists=False,
            database_kind=None,
            current_version=0,
            target_version=target_version,
            pending_versions=[migration.version for migration in migrations],
            compatible=False,
            reason="database does not exist",
        )
    try:
        if not path.is_file() or path.stat().st_size == 0:
            raise UnknownDatabaseError("existing file is not a recognized SQLite database")
        uri = f"file:{quote(str(path), safe='/')}?mode=ro"
        connection = sqlite3.connect(uri, uri=True, timeout=DEFAULT_LOCK_TIMEOUT_SECONDS)
        try:
            actual_kind = _read_database_kind(connection)
            if actual_kind is not expected_kind:
                return SchemaStatus(
                    exists=True,
                    database_kind=actual_kind,
                    current_version=_read_raw_version(connection),
                    target_version=target_version,
                    pending_versions=[],
                    compatible=False,
                    reason=f"database kind is {actual_kind.value}, expected {expected_kind.value}",
                )
            current, _ = _current_version(connection, expected_kind, migrations, allow_empty=False)
            pending = [migration.version for migration in migrations if migration.version > current]
            _validate_database_integrity(connection, expected_kind)
            _validate_schema_structure(connection, expected_kind, schema_version=current)
            return SchemaStatus(
                exists=True,
                database_kind=actual_kind,
                current_version=current,
                target_version=target_version,
                pending_versions=pending,
                compatible=not pending,
                reason="migrations pending" if pending else None,
            )
        finally:
            connection.close()
    except (sqlite3.Error, StorageError) as exc:
        try:
            current = _read_raw_version_from_path(path)
        except (sqlite3.Error, OSError):
            current = 0
        return SchemaStatus(
            exists=True,
            database_kind=None,
            current_version=current,
            target_version=target_version,
            pending_versions=[],
            compatible=False,
            reason=str(exc),
        )


def validate_existing_connection(
    connection: sqlite3.Connection, expected_kind: DatabaseKind
) -> None:
    """Validate a caller-owned snapshot without opening, creating, or migrating a file."""
    migrations = _package_migrations(expected_kind)
    current, _ = _current_version(connection, expected_kind, migrations, allow_empty=False)
    if current != migrations[-1].version:
        raise MigrationHistoryError("migrations pending")
    _validate_database_integrity(connection, expected_kind)
    _validate_schema_structure(connection, expected_kind, schema_version=current)


def validate_connection_identity(
    connection: sqlite3.Connection,
    kind: DatabaseKind,
    expected: tuple[str, str, str | None],
) -> None:
    """Check logical identity on the same locked connection used for a service write."""
    _validate_identity_before_migration(connection, kind, expected)


def _validate_identity_before_migration(
    connection: sqlite3.Connection,
    kind: DatabaseKind,
    expected: tuple[str, str, str | None],
) -> None:
    tables = {
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )
    }
    identity_table = "workflow_control" if kind is DatabaseKind.WORKFLOW else "worker_identity"
    identity = None
    if identity_table in tables:
        identity = connection.execute(
            f"SELECT project_id, root_session_id"
            f"{', worker_session_id' if kind is DatabaseKind.WORKER else ''} "
            f"FROM {identity_table} WHERE singleton=1"
        ).fetchone()
    if identity is not None:
        expected_values = expected if kind is DatabaseKind.WORKER else expected[:2]
        if tuple(identity) != expected_values:
            raise DatabaseIdentityMismatchError(
                "database logical identity does not match trusted host binding"
            )
        return

    metadata = {"schema_migrations", "database_info", "workflow_epochs"}
    if kind is DatabaseKind.WORKFLOW and "workflow_session_metadata" in tables:
        empty_metadata = connection.execute(
            "SELECT session_audit_json,capability_snapshot_json,"
            "capability_snapshot_hash,capability_observed_revision "
            "FROM workflow_session_metadata WHERE singleton=1"
        ).fetchone()
        if empty_metadata is not None and all(value is None for value in empty_metadata):
            metadata.add("workflow_session_metadata")
    if kind is DatabaseKind.WORKFLOW and "native_reconciliations" in tables:
        native_identities = connection.execute(
            "SELECT DISTINCT project_id,root_session_id FROM native_reconciliations"
        ).fetchall()
        if any(tuple(item) != expected[:2] for item in native_identities):
            raise DatabaseIdentityMismatchError(
                "pending Native references belong to another project or Root"
            )
        metadata.update(
            {
                "native_reconciliations",
                "native_reconcile_preimages",
                "native_reconcile_resolutions",
                "native_reconcile_resolution_targets",
                "native_reconcile_confirmations",
            }
        )
        if "operation_receipts" in tables:
            native_receipts = connection.execute(
                "SELECT COUNT(*) FROM operation_receipts WHERE operation!='workflow_reconcile'"
            ).fetchone()
            if native_receipts is not None and native_receipts[0] == 0:
                metadata.add("operation_receipts")
    has_business_records = False
    for table in sorted(tables - metadata):
        # Table names originate from sqlite_master, then are quoted as identifiers.
        quoted = '"' + table.replace('"', '""') + '"'
        if connection.execute(f"SELECT 1 FROM {quoted} LIMIT 1").fetchone() is not None:
            has_business_records = True
            break
    if has_business_records:
        raise DatabaseIdentityMismatchError(
            "existing business records have no verifiable logical identity"
        )


def restore_backup(
    database_path: Path | str,
    backup_path: Path | str,
    expected_kind: DatabaseKind,
    *,
    trusted_root: Path | str,
    lock_timeout_seconds: float = DEFAULT_LOCK_TIMEOUT_SECONDS,
) -> None:
    """Restore after an authorized caller has stopped all business writes.

    The migration lock serializes migration/recovery work; it does not prove that
    business writers have stopped. A state service must coordinate this boundary
    before calling this function. Backup paths are constrained to this database's
    generated sibling backup directory.
    """
    target = _prepare_database_path(database_path, trusted_root, create_parent=False)
    backup = _prepare_database_path(backup_path, trusted_root, create_parent=False)
    if backup.parent != target.parent / "backups" or not backup.name.startswith(
        target.name + ".backup-"
    ):
        raise UnsafeDatabasePathError("backup must be a generated backup for this database")
    if not backup.is_file():
        raise FileNotFoundError(backup)

    with _migration_lock(target, trusted_root, lock_timeout_seconds):
        temporary = target.with_name(f".{target.name}.restore-{uuid.uuid4().hex}.tmp")
        _create_empty_file(temporary)
        try:
            source = sqlite3.connect(f"file:{quote(str(backup), safe='/')}?mode=ro", uri=True)
            destination = sqlite3.connect(temporary)
            try:
                source.backup(destination)
                _validate_database_integrity(destination, expected_kind)
                migrations = _package_migrations(expected_kind)
                version, _ = _current_version(
                    destination, expected_kind, migrations, allow_empty=False
                )
                _validate_schema_structure(destination, expected_kind, schema_version=version)
            finally:
                destination.close()
                source.close()
            os.replace(temporary, target)
        except Exception:
            temporary.unlink(missing_ok=True)
            raise


@contextmanager
def _migration_lock(
    database_path: Path,
    trusted_root: Path | str,
    timeout_seconds: float,
) -> Generator[None, None, None]:
    lock_path = database_path.with_name(database_path.name + ".migration.lock")
    _prepare_database_path(lock_path, trusted_root, create_parent=True)
    flags = os.O_CREAT | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(lock_path, flags, 0o600)
    deadline = time.monotonic() + timeout_seconds
    try:
        while True:
            try:
                fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    raise MigrationLockTimeoutError(
                        f"timed out waiting for migration lock: {lock_path}"
                    ) from None
                time.sleep(0.02)
        yield
    finally:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_UN)
        finally:
            os.close(descriptor)


def _prepare_database_path(
    candidate_path: Path | str,
    trusted_root: Path | str,
    *,
    create_parent: bool,
) -> Path:
    root = Path(trusted_root).resolve(strict=True)
    candidate = Path(os.path.abspath(candidate_path))
    relative = None
    prefix = Path(candidate.anchor)
    for index, component in enumerate(candidate.parts[1:], start=1):
        prefix /= component
        try:
            aliases_trusted_root = prefix.resolve(strict=False) == root
        except OSError:
            aliases_trusted_root = False
        if aliases_trusted_root:
            relative = Path(*candidate.parts[index + 1 :])
            break
    if relative is None:
        raise UnsafeDatabasePathError("database path is outside trusted_root")
    if not relative.parts or ".." in relative.parts:
        raise UnsafeDatabasePathError("database path must name a child of trusted_root")

    current = root
    for component in relative.parts[:-1]:
        current = current / component
        if current.is_symlink():
            raise UnsafeDatabasePathError(f"symlink in database directory: {current}")
        if not current.exists():
            if not create_parent:
                return candidate
            current.mkdir(mode=0o700)
        if not current.is_dir():
            raise UnsafeDatabasePathError(f"database parent is not a directory: {current}")

    final = root.joinpath(*relative.parts)
    if final.is_symlink():
        raise UnsafeDatabasePathError(f"database path is a symlink: {final}")
    if final.exists() and not final.is_file():
        raise UnsafeDatabasePathError(f"database path is not a regular file: {final}")
    return final


def _create_empty_file(path: Path) -> None:
    flags = os.O_CREAT | os.O_EXCL | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags, 0o600)
    os.close(descriptor)


def _current_version(
    connection: sqlite3.Connection,
    expected_kind: DatabaseKind,
    migrations: Sequence[_Migration],
    *,
    allow_empty: bool,
) -> tuple[int, bool]:
    tables = {
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )
    }
    if not tables:
        if allow_empty:
            return 0, False
        raise UnknownDatabaseError("existing database has no recognized application tables")
    if "schema_migrations" not in tables or "database_info" not in tables:
        raise MigrationHistoryError("database migration history or database-kind record is missing")

    actual_kind = _read_database_kind(connection)
    if actual_kind is not expected_kind:
        raise DatabaseKindMismatchError(
            f"database kind is {actual_kind.value}, expected {expected_kind.value}"
        )

    rows = connection.execute(
        "SELECT version, name, checksum FROM schema_migrations ORDER BY version"
    ).fetchall()
    if not rows:
        raise MigrationHistoryError("migration history is missing (no applied versions recorded)")
    if [row[0] for row in rows] != list(range(1, len(rows) + 1)):
        raise MigrationHistoryError("migration history is missing or discontinuous")
    known = {migration.version: migration for migration in migrations}
    for version, name, checksum in rows:
        migration = known.get(version)
        if migration is None:
            if version > migrations[-1].version:
                raise FutureSchemaError(
                    f"database schema v{version:04d} is newer than this package"
                )
            raise MigrationHistoryError(
                f"migration v{version:04d} is not present in package history"
            )
        if name != migration.name:
            raise MigrationHistoryError(f"migration name mismatch at v{version:04d}")
        if checksum != migration.checksum:
            raise MigrationChecksumError(f"migration checksum mismatch at v{version:04d}")
    return (rows[-1][0] if rows else 0), True


def _read_database_kind(connection: sqlite3.Connection) -> DatabaseKind:
    try:
        row = connection.execute(
            "SELECT database_kind FROM database_info WHERE singleton = 1"
        ).fetchone()
        return DatabaseKind(row[0])
    except (sqlite3.Error, ValueError, TypeError, IndexError) as exc:
        raise MigrationHistoryError("database kind record is missing or invalid") from exc


def _read_raw_version(connection: sqlite3.Connection) -> int:
    try:
        row = connection.execute("SELECT MAX(version) FROM schema_migrations").fetchone()
        return int(row[0] or 0)
    except (sqlite3.Error, TypeError, ValueError):
        return 0


def _read_raw_version_from_path(path: Path) -> int:
    uri = f"file:{quote(str(path), safe='/')}?mode=ro"
    connection = sqlite3.connect(uri, uri=True)
    try:
        return _read_raw_version(connection)
    finally:
        connection.close()


def _validate_database_integrity(
    connection: sqlite3.Connection,
    expected_kind: DatabaseKind,
) -> None:
    if _read_database_kind(connection) is not expected_kind:
        raise DatabaseKindMismatchError(f"database is not a {expected_kind.value} database")
    integrity = connection.execute("PRAGMA integrity_check").fetchone()
    if integrity is None or integrity[0] != "ok":
        raise StorageError(
            f"SQLite integrity_check failed: {integrity[0] if integrity else 'no result'}"
        )
    foreign_key_error = connection.execute("PRAGMA foreign_key_check").fetchone()
    if foreign_key_error is not None:
        raise StorageError(f"SQLite foreign_key_check failed: {foreign_key_error}")


def _validate_schema_structure(
    connection: sqlite3.Connection,
    expected_kind: DatabaseKind,
    *,
    schema_version: int,
) -> None:
    expected_v2_name = (
        "control_state" if expected_kind is DatabaseKind.WORKFLOW else "worker_identity"
    )
    applied_v2 = connection.execute("SELECT name FROM schema_migrations WHERE version=2").fetchone()
    if schema_version >= 2 and (applied_v2 is None or applied_v2[0] != expected_v2_name):
        # Tests may inject internal migration objects. Their schemas do not
        # claim the production v0002 contract unless the package-owned name is applied.
        schema_version = 1
    if schema_version >= 3:
        expected_v3_name = (
            "evidence_control" if expected_kind is DatabaseKind.WORKFLOW else "evidence_dispatch"
        )
        applied_v3 = connection.execute(
            "SELECT name FROM schema_migrations WHERE version=3"
        ).fetchone()
        if applied_v3 is None or applied_v3[0] != expected_v3_name:
            schema_version = 2
    if schema_version >= 4:
        applied_v4 = connection.execute(
            "SELECT name FROM schema_migrations WHERE version=4"
        ).fetchone()
        if expected_kind is not DatabaseKind.WORKFLOW or (
            applied_v4 is None or applied_v4[0] != "session_metadata"
        ):
            schema_version = 3
    if schema_version >= 5:
        applied_v5 = connection.execute(
            "SELECT name FROM schema_migrations WHERE version=5"
        ).fetchone()
        if expected_kind is not DatabaseKind.WORKFLOW or (
            applied_v5 is None or applied_v5[0] != "native_resolution"
        ):
            schema_version = 4
    required_columns = {
        "database_info": {"singleton", "database_kind"},
        "schema_migrations": {"version", "name", "checksum", "applied_at", "duration_ms"},
    }
    if expected_kind is DatabaseKind.WORKFLOW:
        required_columns.update(
            {
                "workflow_state": {"state_key", "state_json", "revision"},
                "semantic_refs": {"ref_id", "uri", "content_hash", "indexed_at"},
                "evidence_refs": {"evidence_id", "uri", "content_hash", "captured_at"},
            }
        )
        if schema_version >= 2:
            required_columns.update(
                {
                    "workflow_control": {
                        "singleton",
                        "project_id",
                        "root_session_id",
                        "run_id",
                        "mode",
                        "child_count",
                        "mode_source",
                        "source_uri",
                        "source_hash",
                        "semantic_references_json",
                        "lifecycle",
                        "revision",
                        "created_at",
                    },
                    "allocations": {
                        "allocation_id",
                        "slot",
                        "role",
                        "status",
                        "worker_session_id",
                        "output_class",
                        "worker_event_id",
                        "created_at",
                    },
                    "workflow_slices": {
                        "slice_id",
                        "allocation_id",
                        "output_class",
                        "objective_uri",
                        "objective_hash",
                        "return_conditions_uri",
                        "return_conditions_hash",
                        "unreleased_boundary_uri",
                        "unreleased_boundary_hash",
                        "authorized_paths_json",
                        "change_categories_json",
                        "write_content_memo",
                        "status",
                        "created_revision",
                        "created_at",
                    },
                    "operation_receipts": {
                        "idempotency_key",
                        "operation",
                        "payload_hash",
                        "result_json",
                        "receipt_revision",
                        "created_at",
                    },
                    "root_outbox": {
                        "event_id",
                        "allocation_id",
                        "event_type",
                        "payload_json",
                        "payload_hash",
                        "status",
                        "created_at",
                        "confirmed_at",
                    },
                }
            )
        if schema_version >= 3:
            required_columns.update(
                {
                    "workflow_epochs": {
                        "singleton",
                        "implementation_content",
                        "documentation",
                        "git_metadata",
                    },
                    "root_slices": {
                        "slice_id",
                        "objective_uri",
                        "objective_hash",
                        "return_uri",
                        "return_hash",
                        "boundary_uri",
                        "boundary_hash",
                        "authorized_paths_json",
                        "change_categories_json",
                        "status",
                        "created_revision",
                        "created_at",
                    },
                    "checkpoint_evidence": {
                        "evidence_id",
                        "node_id",
                        "facts_json",
                        "evidence_refs_json",
                        "input_hash",
                        "rule_hash",
                        "coverage_json",
                        "implementation_epoch",
                        "documentation_epoch",
                        "git_metadata_epoch",
                        "basis_revision",
                        "recorded_revision",
                        "created_at",
                    },
                    "checkpoint_evaluations": {
                        "evaluation_id",
                        "node_id",
                        "outcome",
                        "branch",
                        "facts_hash",
                        "input_hash",
                        "rule_hash",
                        "implementation_epoch",
                        "documentation_epoch",
                        "git_metadata_epoch",
                        "basis_revision",
                        "result_revision",
                        "missing_facts_json",
                        "missing_evidence_json",
                        "created_at",
                    },
                    "checkpoint_confirmations": {
                        "confirmation_id",
                        "evaluation_id",
                        "node_id",
                        "from_revision",
                        "to_revision",
                        "created_at",
                    },
                    "control_transitions": {
                        "transition_id",
                        "evaluation_id",
                        "outcome",
                        "from_revision",
                        "to_revision",
                        "created_at",
                    },
                    "native_reconciliations": {
                        "reconcile_id",
                        "snapshot_hash",
                        "native_refs_json",
                        "differences_json",
                        "status",
                        "observed_revision",
                        "result_revision",
                        "created_at",
                        "project_id",
                        "root_session_id",
                        "snapshot_json",
                    },
                    "workflow_dispatch_events": {
                        "event_id",
                        "allocation_id",
                        "slice_id",
                        "sequence",
                        "payload_json",
                        "payload_hash",
                        "status",
                        "created_at",
                        "confirmed_at",
                    },
                }
            )
        if schema_version >= 4:
            required_columns["root_slices"].update({"output_class", "write_content_memo"})
            required_columns["workflow_session_metadata"] = {
                "singleton",
                "session_audit_json",
                "capability_snapshot_json",
                "capability_snapshot_hash",
                "capability_observed_revision",
            }
        if schema_version >= 5:
            required_columns["workflow_control"].add("recovery_revision")
            required_columns["native_reconcile_preimages"] = {
                "reconcile_id",
                "snapshot_hash",
                "root_preimage_json",
                "root_preimage_hash",
                "captured_revision",
                "captured_at",
            }
            required_columns["native_reconcile_resolutions"] = {
                "resolution_id",
                "reconcile_id",
                "reviewed_set_hash",
                "snapshot_hash",
                "choice",
                "selected_source_uri",
                "selected_source_hash",
                "selected_semantic_references_json",
                "native_revision",
                "native_epochs_json",
                "root_decision_ref_json",
                "native_freshness_refs_json",
                "root_quiescence_refs_json",
                "observed_revision",
                "result_revision",
                "recovery_revision",
                "created_at",
            }
            required_columns["native_reconcile_resolution_targets"] = {
                "reconcile_id",
                "resolution_id",
                "snapshot_hash",
            }
            required_columns["native_reconcile_confirmations"] = {
                "awaiting_reconcile_id",
                "matched_reconcile_id",
                "snapshot_hash",
                "confirmed_revision",
                "created_at",
            }
    else:
        required_columns.update(
            {
                "assignment_snapshot": {"singleton", "snapshot_json", "source_revision"},
                "worker_progress": {"progress_key", "progress_json", "updated_at"},
                "worker_evidence": {"evidence_id", "uri", "content_hash", "captured_at"},
                "worker_blockers": {"blocker_id", "blocker_json", "reported_at"},
            }
        )
        if schema_version >= 2:
            required_columns.update(
                {
                    "worker_identity": {
                        "singleton",
                        "project_id",
                        "root_session_id",
                        "worker_session_id",
                        "allocation_id",
                        "role",
                        "output_class",
                        "event_id",
                        "assignment_hash",
                        "revision",
                        "created_at",
                    },
                    "worker_inbox": {
                        "event_id",
                        "payload_hash",
                        "status",
                        "received_at",
                        "confirmed_at",
                    },
                    "worker_operation_receipts": {
                        "idempotency_key",
                        "operation",
                        "payload_hash",
                        "result_json",
                        "receipt_revision",
                        "created_at",
                    },
                }
            )
        if schema_version >= 3:
            required_columns.update(
                {
                    "worker_dispatch_history": {
                        "event_id",
                        "sequence",
                        "snapshot_json",
                        "assignment_hash",
                        "status",
                        "received_at",
                        "confirmed_at",
                    },
                    "worker_active_dispatch": {"singleton", "event_id", "sequence"},
                    "worker_checkpoint_evidence": {
                        "evidence_id",
                        "node_id",
                        "facts_json",
                        "evidence_refs_json",
                        "input_hash",
                        "rule_hash",
                        "coverage_json",
                        "implementation_epoch",
                        "documentation_epoch",
                        "git_metadata_epoch",
                        "basis_revision",
                        "recorded_revision",
                        "created_at",
                    },
                }
            )
    for table, expected in required_columns.items():
        rows = connection.execute(f"PRAGMA table_info({table})").fetchall()
        columns = {row[1] for row in rows}
        if not expected.issubset(columns):
            missing = sorted(expected - columns)
            raise StorageError(f"required table structure missing for {table}: {missing}")
    if connection.execute("SELECT COUNT(*) FROM database_info").fetchone()[0] != 1:
        raise StorageError("database_info must contain exactly one database-kind record")


def _create_backup(
    connection: sqlite3.Connection, database_path: Path, trusted_root: Path | str
) -> Path:
    backup_dir = database_path.parent / "backups"
    _prepare_database_path(backup_dir / "placeholder", trusted_root, create_parent=True)
    backup_dir.mkdir(mode=0o700, exist_ok=True)
    if backup_dir.is_symlink() or not backup_dir.is_dir():
        raise UnsafeDatabasePathError("backup directory is not a safe directory")
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S.%fZ")
    backup_path = backup_dir / f"{database_path.name}.backup-{stamp}-{uuid.uuid4().hex}.sqlite3"
    _create_empty_file(backup_path)
    try:
        destination = sqlite3.connect(backup_path)
        try:
            connection.backup(destination)
            _validate_database_integrity(
                destination,
                DatabaseKind(
                    connection.execute(
                        "SELECT database_kind FROM database_info WHERE singleton=1"
                    ).fetchone()[0]
                ),
            )
        finally:
            destination.close()
    except Exception:
        backup_path.unlink(missing_ok=True)
        raise
    return backup_path


def _is_empty_sqlite_file(path: Path) -> bool:
    try:
        if path.stat().st_size == 0:
            return True
        connection = sqlite3.connect(f"file:{quote(str(path), safe='/')}?mode=ro", uri=True)
        try:
            tables = connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' "
                "AND name NOT LIKE 'sqlite_%' LIMIT 1"
            ).fetchone()
            return tables is None
        finally:
            connection.close()
    except sqlite3.Error:
        return False


def _deny_transaction_control(
    action: int,
    arg1: str | None,
    arg2: str | None,
    database: str | None,
    trigger: str | None,
) -> int:
    del arg1, arg2, database, trigger
    if action in {sqlite3.SQLITE_TRANSACTION, getattr(sqlite3, "SQLITE_SAVEPOINT", -1)}:
        return sqlite3.SQLITE_DENY
    return sqlite3.SQLITE_OK
