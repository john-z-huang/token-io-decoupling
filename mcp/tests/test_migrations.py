from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from token_io_decoupling_core.models import DatabaseKind
from token_io_decoupling_state.migrations.runner import (
    _Migration,
    _migration_lock,
    _open_with_migrations,
    _package_migrations,
    read_schema_status,
    restore_backup,
)
from token_io_decoupling_state.storage import (
    DatabaseKindMismatchError,
    FutureSchemaError,
    MigrationChecksumError,
    MigrationExecutionError,
    MigrationHistoryError,
    MigrationLockTimeoutError,
    StorageError,
    UnsafeDatabasePathError,
    open_database_for_authorized_write,
)


def _v2_add_index(connection: sqlite3.Connection) -> None:
    connection.execute("CREATE INDEX workflow_state_revision_idx ON workflow_state(revision)")


def _v2_failing(connection: sqlite3.Connection) -> None:
    connection.execute("CREATE TABLE should_rollback (id INTEGER PRIMARY KEY)")
    raise RuntimeError("injected migration failure")


def _v2_break_required_structure(connection: sqlite3.Connection) -> None:
    connection.execute("DROP TABLE workflow_state")


def _v2_deferred_foreign_key_failure(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE deferred_child (
            child_id TEXT PRIMARY KEY,
            parent_id TEXT,
            FOREIGN KEY (parent_id) REFERENCES workflow_state(state_key)
                DEFERRABLE INITIALLY DEFERRED
        )
        """
    )
    connection.execute(
        "INSERT INTO deferred_child(child_id, parent_id) VALUES ('child', 'missing-parent')"
    )


def _migration_v2(upgrade=_v2_add_index) -> _Migration:
    return _Migration(
        version=2,
        name="add_index",
        checksum=hashlib.sha256(b"migration-v2-test").hexdigest(),
        upgrade=upgrade,
    )


def _v3_add_index(connection: sqlite3.Connection) -> None:
    connection.execute("CREATE INDEX workflow_state_key_idx ON workflow_state(state_key)")


def _open(root: Path, name: str = "workflow.sqlite3") -> sqlite3.Connection:
    return open_database_for_authorized_write(root / name, DatabaseKind.WORKFLOW, trusted_root=root)


def _open_v1(root: Path, name: str = "workflow.sqlite3") -> sqlite3.Connection:
    return _open_with_migrations(
        root / name,
        DatabaseKind.WORKFLOW,
        trusted_root=root,
        migrations=_package_migrations(DatabaseKind.WORKFLOW)[:1],
    )


def test_empty_database_initializes_each_kind_with_supported_schema(tmp_path: Path) -> None:
    workflow = open_database_for_authorized_write(
        tmp_path / "workflow.sqlite3", DatabaseKind.WORKFLOW, trusted_root=tmp_path
    )
    worker = open_database_for_authorized_write(
        tmp_path / "worker.sqlite3", DatabaseKind.WORKER, trusted_root=tmp_path
    )
    try:
        assert workflow.execute("SELECT database_kind FROM database_info").fetchone() == (
            "workflow",
        )
        assert worker.execute("SELECT database_kind FROM database_info").fetchone() == ("worker",)
        assert workflow.execute(
            "SELECT version, name FROM schema_migrations ORDER BY version"
        ).fetchall()[-1] == (5, "native_resolution")
        assert worker.execute(
            "SELECT version, name FROM schema_migrations ORDER BY version"
        ).fetchall()[-1] == (3, "evidence_dispatch")
    finally:
        workflow.close()
        worker.close()


def test_v4_to_v5_preserves_native_history_and_adds_resolution_journal(tmp_path: Path) -> None:
    database = tmp_path / "workflow.sqlite3"
    migrations = _package_migrations(DatabaseKind.WORKFLOW)
    connection = _open_with_migrations(
        database,
        DatabaseKind.WORKFLOW,
        trusted_root=tmp_path,
        migrations=migrations[:4],
    )
    refs = [{"uri": "test://native", "content_hash": "b" * 64}]
    snapshot = {
        "project_id": "project-a",
        "root_session_id": "root-a",
        "run_id": "run-a",
        "mode_count": {"mode": "Single-Agent Coding", "child_count": 0},
        "mode_source": "explicit",
        "lifecycle": "pending",
        "source": {"uri": "test://plan", "content_hash": "c" * 64},
        "semantic_references": [],
        "revision": 10,
        "allocations": [],
        "epochs": {"implementation_content": 0, "documentation": 0, "git_metadata": 0},
        "evidence_refs": refs,
    }
    snapshot_json = json.dumps(snapshot, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    snapshot_hash = hashlib.sha256(snapshot_json.encode("utf-8")).hexdigest()
    refs_json = json.dumps(refs, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

    def legacy_row(
        reconcile_id: str,
        status: str,
        observed_revision: int,
        result_revision: int,
        *,
        stored_snapshot: str = snapshot_json,
        stored_hash: str = snapshot_hash,
    ) -> tuple[object, ...]:
        return (
            reconcile_id,
            stored_hash,
            refs_json,
            '["Contract source"]',
            status,
            observed_revision,
            result_revision,
            "2026-10-25T00:00:00+00:00",
            "project-a",
            "root-a",
            stored_snapshot,
        )

    original = legacy_row("native-v4-row", "conflict", 8, 9)
    connection.execute(
        "INSERT INTO native_reconciliations VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        original,
    )
    awaiting = legacy_row("native-v4-awaiting", "awaiting_confirmation", 10, 11)
    matched = legacy_row("native-v4-matched", "matched", 11, 12)
    malformed_awaiting = legacy_row(
        "native-v4-malformed-awaiting",
        "awaiting_confirmation",
        20,
        21,
        stored_snapshot='{"prior":"snapshot"}',
        stored_hash="d" * 64,
    )
    malformed_matched = legacy_row(
        "native-v4-malformed-matched",
        "matched",
        21,
        22,
        stored_snapshot='{"prior":"snapshot"}',
        stored_hash="d" * 64,
    )
    nonadjacent_awaiting = legacy_row(
        "native-v4-nonadjacent-awaiting", "awaiting_confirmation", 30, 32
    )
    nonadjacent_matched = legacy_row("native-v4-nonadjacent-matched", "matched", 32, 33)
    connection.executemany(
        "INSERT INTO native_reconciliations VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        [
            awaiting,
            matched,
            malformed_awaiting,
            malformed_matched,
            nonadjacent_awaiting,
            nonadjacent_matched,
        ],
    )
    connection.commit()
    connection.close()

    upgraded = _open_with_migrations(
        database,
        DatabaseKind.WORKFLOW,
        trusted_root=tmp_path,
        migrations=migrations,
    )
    try:
        assert (
            upgraded.execute(
                "SELECT * FROM native_reconciliations WHERE reconcile_id='native-v4-row'"
            ).fetchone()
            == original
        )
        columns = {row[1] for row in upgraded.execute("PRAGMA table_info(workflow_control)")}
        assert "recovery_revision" in columns
        assert upgraded.execute(
            "SELECT COUNT(*) FROM native_reconcile_resolution_targets"
        ).fetchone() == (0,)
        assert upgraded.execute(
            "SELECT awaiting_reconcile_id,matched_reconcile_id,snapshot_hash,confirmed_revision "
            "FROM native_reconcile_confirmations"
        ).fetchall() == [("native-v4-awaiting", "native-v4-matched", snapshot_hash, 12)]
        assert upgraded.execute("SELECT MAX(version) FROM schema_migrations").fetchone() == (5,)
    finally:
        upgraded.close()


def test_read_only_status_does_not_create_or_migrate(tmp_path: Path) -> None:
    missing_path = tmp_path / "missing.sqlite3"
    status = read_schema_status(missing_path, DatabaseKind.WORKFLOW, trusted_root=tmp_path)
    assert not status.exists
    assert not missing_path.exists()
    assert not list(tmp_path.iterdir())

    connection = _open_v1(tmp_path)
    connection.close()
    connection = sqlite3.connect(tmp_path / "workflow.sqlite3")
    connection.execute("DELETE FROM schema_migrations")
    connection.commit()
    connection.close()
    before = (tmp_path / "workflow.sqlite3").read_bytes()
    status = read_schema_status(
        tmp_path / "workflow.sqlite3", DatabaseKind.WORKFLOW, trusted_root=tmp_path
    )
    assert not status.compatible
    assert "migration history is missing" in (status.reason or "")
    assert (tmp_path / "workflow.sqlite3").read_bytes() == before
    with pytest.raises(MigrationHistoryError):
        open_database_for_authorized_write(
            tmp_path / "workflow.sqlite3", DatabaseKind.WORKFLOW, trusted_root=tmp_path
        )
    assert (tmp_path / "workflow.sqlite3").read_bytes() == before


def test_middle_missing_migration_history_is_never_upgraded(tmp_path: Path) -> None:
    path = tmp_path / "workflow.sqlite3"
    migrations = (
        *_package_migrations(DatabaseKind.WORKFLOW)[:1],
        _migration_v2(),
        _Migration(
            version=3,
            name="add_second_index",
            checksum=hashlib.sha256(b"migration-v3-test").hexdigest(),
            upgrade=_v3_add_index,
        ),
    )
    _open_with_migrations(
        path, DatabaseKind.WORKFLOW, trusted_root=tmp_path, migrations=migrations
    ).close()
    with sqlite3.connect(path) as connection:
        connection.execute("DELETE FROM schema_migrations WHERE version=2")
    before = path.read_bytes()

    status = read_schema_status(path, DatabaseKind.WORKFLOW, trusted_root=tmp_path)
    assert not status.compatible
    assert "missing or discontinuous" in (status.reason or "")
    with pytest.raises(MigrationHistoryError):
        _open_with_migrations(
            path, DatabaseKind.WORKFLOW, trusted_root=tmp_path, migrations=migrations
        )
    assert path.read_bytes() == before


def test_existing_unknown_and_wrong_kind_databases_are_rejected(tmp_path: Path) -> None:
    unknown = tmp_path / "unknown.sqlite3"
    connection = sqlite3.connect(unknown)
    connection.execute("CREATE TABLE user_data (id INTEGER PRIMARY KEY)")
    connection.commit()
    connection.close()
    before = unknown.read_bytes()
    with pytest.raises(MigrationHistoryError):
        open_database_for_authorized_write(unknown, DatabaseKind.WORKFLOW, trusted_root=tmp_path)
    assert unknown.read_bytes() == before

    connection = _open(tmp_path, "workflow.sqlite3")
    connection.close()
    with pytest.raises(DatabaseKindMismatchError):
        open_database_for_authorized_write(
            tmp_path / "workflow.sqlite3", DatabaseKind.WORKER, trusted_root=tmp_path
        )


def test_history_checksum_missing_and_future_versions_are_rejected(tmp_path: Path) -> None:
    path = tmp_path / "workflow.sqlite3"
    connection = _open_v1(tmp_path)
    connection.execute("UPDATE schema_migrations SET checksum = ?", ("0" * 64,))
    connection.close()
    with pytest.raises(MigrationChecksumError):
        open_database_for_authorized_write(path, DatabaseKind.WORKFLOW, trusted_root=tmp_path)

    path_missing = tmp_path / "history-missing.sqlite3"
    connection = open_database_for_authorized_write(
        path_missing, DatabaseKind.WORKFLOW, trusted_root=tmp_path
    )
    connection.execute("DROP TABLE schema_migrations")
    connection.close()
    with pytest.raises(MigrationHistoryError):
        open_database_for_authorized_write(
            path_missing, DatabaseKind.WORKFLOW, trusted_root=tmp_path
        )

    path_future = tmp_path / "future.sqlite3"
    connection = open_database_for_authorized_write(
        path_future, DatabaseKind.WORKFLOW, trusted_root=tmp_path
    )
    connection.execute(
        "INSERT INTO schema_migrations VALUES (6, 'future', ?, 'now', 0)", ("b" * 64,)
    )
    connection.close()
    with pytest.raises(FutureSchemaError):
        open_database_for_authorized_write(
            path_future, DatabaseKind.WORKFLOW, trusted_root=tmp_path
        )
    status = read_schema_status(path_future, DatabaseKind.WORKFLOW, trusted_root=tmp_path)
    assert not status.compatible


def test_later_migration_preserves_data_and_index_and_can_restore_backup(tmp_path: Path) -> None:
    path = tmp_path / "workflow.sqlite3"
    connection = _open_v1(tmp_path)
    connection.execute(
        "INSERT INTO workflow_state(state_key, state_json, revision) VALUES ('mode', '{}', 7)"
    )
    connection.close()
    migrations = (*_package_migrations(DatabaseKind.WORKFLOW)[:1], _migration_v2())
    connection = _open_with_migrations(
        path, DatabaseKind.WORKFLOW, trusted_root=tmp_path, migrations=migrations
    )
    assert connection.execute(
        "SELECT revision FROM workflow_state WHERE state_key='mode'"
    ).fetchone() == (7,)
    assert connection.execute(
        "SELECT name FROM sqlite_master WHERE type='index' AND name='workflow_state_revision_idx'"
    ).fetchone() == ("workflow_state_revision_idx",)
    connection.close()
    backups = list((tmp_path / "backups").glob("workflow.sqlite3.backup-*.sqlite3"))
    assert len(backups) == 1

    restore_backup(path, backups[0], DatabaseKind.WORKFLOW, trusted_root=tmp_path)
    restored = sqlite3.connect(path)
    try:
        assert restored.execute(
            "SELECT revision FROM workflow_state WHERE state_key='mode'"
        ).fetchone() == (7,)
        assert restored.execute("SELECT MAX(version) FROM schema_migrations").fetchone() == (1,)
        assert (
            restored.execute(
                "SELECT 1 FROM sqlite_master WHERE type='index' "
                "AND name='workflow_state_revision_idx'"
            ).fetchone()
            is None
        )
    finally:
        restored.close()


@pytest.mark.parametrize("tamper", ["checksum", "future_schema"])
def test_restore_rejects_incompatible_backup_and_preserves_target(
    tmp_path: Path, tamper: str
) -> None:
    path = tmp_path / "workflow.sqlite3"
    connection = _open_v1(tmp_path)
    connection.close()
    _open_with_migrations(
        path,
        DatabaseKind.WORKFLOW,
        trusted_root=tmp_path,
        migrations=(*_package_migrations(DatabaseKind.WORKFLOW)[:1], _migration_v2()),
    ).close()
    backup = next((tmp_path / "backups").glob("workflow.sqlite3.backup-*.sqlite3"))

    tampered_backup = tmp_path / "backups" / "workflow.sqlite3.backup-tampered.sqlite3"
    with sqlite3.connect(backup) as source, sqlite3.connect(tampered_backup) as copy:
        source.backup(copy)
    with sqlite3.connect(tampered_backup) as connection:
        if tamper == "checksum":
            connection.execute("UPDATE schema_migrations SET checksum = ?", ("0" * 64,))
        else:
            connection.execute(
                "INSERT INTO schema_migrations VALUES (5, 'future', ?, 'now', 0)",
                ("f" * 64,),
            )

    with pytest.raises(StorageError):
        restore_backup(path, tampered_backup, DatabaseKind.WORKFLOW, trusted_root=tmp_path)

    with sqlite3.connect(path) as target:
        assert target.execute("SELECT MAX(version) FROM schema_migrations").fetchone() == (2,)
        assert target.execute(
            "SELECT 1 FROM sqlite_master WHERE type='index' AND name='workflow_state_revision_idx'"
        ).fetchone() == (1,)


def test_failed_migration_rolls_back_current_version_and_keeps_backup(tmp_path: Path) -> None:
    path = tmp_path / "workflow.sqlite3"
    connection = _open_v1(tmp_path)
    connection.execute(
        "INSERT INTO workflow_state(state_key, state_json, revision) VALUES ('plan', '{}', 3)"
    )
    connection.close()
    migrations = (*_package_migrations(DatabaseKind.WORKFLOW)[:1], _migration_v2(_v2_failing))
    with pytest.raises(MigrationExecutionError):
        _open_with_migrations(
            path, DatabaseKind.WORKFLOW, trusted_root=tmp_path, migrations=migrations
        )
    connection = sqlite3.connect(path)
    try:
        assert connection.execute("SELECT MAX(version) FROM schema_migrations").fetchone() == (1,)
        assert (
            connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='should_rollback'"
            ).fetchone()
            is None
        )
        assert connection.execute(
            "SELECT revision FROM workflow_state WHERE state_key='plan'"
        ).fetchone() == (3,)
    finally:
        connection.close()
    assert len(list((tmp_path / "backups").glob("workflow.sqlite3.backup-*.sqlite3"))) == 1


@pytest.mark.parametrize(
    ("upgrade", "failure_type"),
    [
        (_v2_break_required_structure, StorageError),
        (_v2_deferred_foreign_key_failure, StorageError),
    ],
)
def test_precommit_validation_rolls_back_invalid_schema_and_deferred_fk(
    tmp_path: Path,
    upgrade,
    failure_type: type[Exception],
) -> None:
    path = tmp_path / "workflow.sqlite3"
    connection = _open_v1(tmp_path)
    connection.execute(
        "INSERT INTO workflow_state(state_key, state_json, revision) VALUES ('mode', '{}', 2)"
    )
    connection.close()
    migrations = (*_package_migrations(DatabaseKind.WORKFLOW)[:1], _migration_v2(upgrade))
    with pytest.raises(failure_type):
        _open_with_migrations(
            path, DatabaseKind.WORKFLOW, trusted_root=tmp_path, migrations=migrations
        )
    connection = sqlite3.connect(path)
    try:
        assert connection.execute("SELECT MAX(version) FROM schema_migrations").fetchone() == (1,)
        assert connection.execute(
            "SELECT revision FROM workflow_state WHERE state_key='mode'"
        ).fetchone() == (2,)
        assert connection.execute(
            "SELECT name FROM sqlite_master WHERE name IN ('deferred_child', 'workflow_state') "
            "AND type='table'"
        ).fetchall() == [("workflow_state",)]
    finally:
        connection.close()


def test_concurrent_initial_migrations_are_serialized(tmp_path: Path) -> None:
    path = tmp_path / "workflow.sqlite3"
    _open_v1(tmp_path).close()
    migrations = (*_package_migrations(DatabaseKind.WORKFLOW)[:1], _migration_v2())
    barrier = threading.Barrier(4)

    def open_and_close() -> int:
        barrier.wait(timeout=3)
        connection = _open_with_migrations(
            path,
            DatabaseKind.WORKFLOW,
            trusted_root=tmp_path,
            migrations=migrations,
            lock_timeout_seconds=3,
        )
        try:
            return connection.execute("SELECT COUNT(*) FROM schema_migrations").fetchone()[0]
        finally:
            connection.close()

    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda _: open_and_close(), range(4)))
    assert results == [2, 2, 2, 2]


def test_migration_lock_wait_is_bounded(tmp_path: Path) -> None:
    path = tmp_path / "workflow.sqlite3"
    connection = _open(tmp_path)
    connection.close()
    migrations = _package_migrations(DatabaseKind.WORKFLOW)
    with _migration_lock(path, tmp_path, 1):
        with pytest.raises(MigrationLockTimeoutError):
            _open_with_migrations(
                path,
                DatabaseKind.WORKFLOW,
                trusted_root=tmp_path,
                migrations=migrations,
                lock_timeout_seconds=0.05,
            )


def test_paths_reject_escape_and_symlink_components(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    root_alias = tmp_path / "root-alias"
    root_alias.symlink_to(root, target_is_directory=True)
    alias_connection = open_database_for_authorized_write(
        root_alias / "alias.sqlite3", DatabaseKind.WORKFLOW, trusted_root=root
    )
    alias_connection.close()
    assert (root / "alias.sqlite3").is_file()

    outside = tmp_path / "outside"
    outside.mkdir()
    with pytest.raises(UnsafeDatabasePathError):
        open_database_for_authorized_write(
            outside / "db.sqlite3", DatabaseKind.WORKFLOW, trusted_root=root
        )
    (root / "link").symlink_to(outside, target_is_directory=True)
    with pytest.raises(UnsafeDatabasePathError):
        open_database_for_authorized_write(
            root / "link" / "db.sqlite3", DatabaseKind.WORKFLOW, trusted_root=root
        )
