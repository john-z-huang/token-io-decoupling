"""Compatibility imports for the former storage module."""

from token_io_decoupling_state.storage import (
    DEFAULT_LOCK_TIMEOUT_SECONDS,
    DatabaseKindMismatchError,
    FutureSchemaError,
    MigrationChecksumError,
    MigrationExecutionError,
    MigrationHistoryError,
    MigrationLockTimeoutError,
    StorageError,
    UnknownDatabaseError,
    UnsafeDatabasePathError,
    open_database_for_authorized_write,
    read_schema_status,
    restore_backup,
)

__all__ = [
    "DEFAULT_LOCK_TIMEOUT_SECONDS",
    "DatabaseKindMismatchError",
    "FutureSchemaError",
    "MigrationChecksumError",
    "MigrationExecutionError",
    "MigrationHistoryError",
    "MigrationLockTimeoutError",
    "StorageError",
    "UnknownDatabaseError",
    "UnsafeDatabasePathError",
    "open_database_for_authorized_write",
    "read_schema_status",
    "restore_backup",
]
