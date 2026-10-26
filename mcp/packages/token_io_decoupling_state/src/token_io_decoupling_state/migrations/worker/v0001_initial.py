"""Initial Worker database schema."""

from __future__ import annotations

import sqlite3

from token_io_mcp.models import DatabaseKind

VERSION = 1
NAME = "initial"


def upgrade(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE database_info (
            singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
            database_kind TEXT NOT NULL CHECK (database_kind IN ('workflow', 'worker'))
        )
        """
    )
    connection.execute(
        "INSERT INTO database_info (singleton, database_kind) VALUES (?, ?)",
        (1, DatabaseKind.WORKER.value),
    )
    connection.execute(
        """
        CREATE TABLE schema_migrations (
            version INTEGER PRIMARY KEY CHECK (version > 0),
            name TEXT NOT NULL UNIQUE,
            checksum TEXT NOT NULL CHECK (length(checksum) = 64),
            applied_at TEXT NOT NULL,
            duration_ms INTEGER NOT NULL CHECK (duration_ms >= 0)
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE assignment_snapshot (
            singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
            snapshot_json TEXT NOT NULL,
            source_revision INTEGER NOT NULL CHECK (source_revision >= 0)
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE worker_progress (
            progress_key TEXT PRIMARY KEY,
            progress_json TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE worker_evidence (
            evidence_id TEXT PRIMARY KEY,
            uri TEXT NOT NULL,
            content_hash TEXT NOT NULL CHECK (length(content_hash) = 64),
            captured_at TEXT NOT NULL
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE worker_blockers (
            blocker_id TEXT PRIMARY KEY,
            blocker_json TEXT NOT NULL,
            reported_at TEXT NOT NULL
        )
        """
    )
