"""Initial Root workflow database schema."""

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
        (1, DatabaseKind.WORKFLOW.value),
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
        CREATE TABLE workflow_state (
            state_key TEXT PRIMARY KEY,
            state_json TEXT NOT NULL,
            revision INTEGER NOT NULL CHECK (revision >= 0)
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE semantic_refs (
            ref_id TEXT PRIMARY KEY,
            uri TEXT NOT NULL,
            content_hash TEXT NOT NULL CHECK (length(content_hash) = 64),
            indexed_at TEXT NOT NULL
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE evidence_refs (
            evidence_id TEXT PRIMARY KEY,
            uri TEXT NOT NULL,
            content_hash TEXT NOT NULL CHECK (length(content_hash) = 64),
            captured_at TEXT NOT NULL
        )
        """
    )
