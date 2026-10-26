"""Compatibility imports for the former migration runner module."""

from token_io_decoupling_state.migrations.runner import (
    DEFAULT_LOCK_TIMEOUT_SECONDS,
    DatabaseIdentityMismatchError,
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
    validate_connection_identity,
    validate_existing_connection,
)

__all__ = [
    "DEFAULT_LOCK_TIMEOUT_SECONDS",
    "DatabaseIdentityMismatchError",
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
    "validate_connection_identity",
    "validate_existing_connection",
]
