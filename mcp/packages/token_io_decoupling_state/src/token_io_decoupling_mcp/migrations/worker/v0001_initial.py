from token_io_decoupling_state.migrations.runner import _import_migration_module

_migration = _import_migration_module("token_io_decoupling_state.migrations.worker.v0001_initial")

NAME = _migration.NAME
VERSION = _migration.VERSION
upgrade = _migration.upgrade

__all__ = ["VERSION", "NAME", "upgrade"]
