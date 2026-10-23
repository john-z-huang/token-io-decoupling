"""Migration lifecycle functions for authorized callers and read-only diagnostics."""

from token_io_mcp.migrations.runner import (
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
