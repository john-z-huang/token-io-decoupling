"""Verified Worker identity, event receipt, and local idempotency state."""

from __future__ import annotations

import sqlite3

VERSION = 2
NAME = "worker_identity"


def upgrade(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE worker_identity (
            singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
            project_id TEXT NOT NULL,
            root_session_id TEXT NOT NULL,
            worker_session_id TEXT NOT NULL UNIQUE,
            allocation_id TEXT NOT NULL UNIQUE,
            role TEXT NOT NULL,
            output_class TEXT NOT NULL CHECK (
                output_class IN ('code_configuration', 'skill_instructions')
            ),
            event_id TEXT NOT NULL UNIQUE,
            assignment_hash TEXT NOT NULL CHECK (length(assignment_hash) = 64),
            revision INTEGER NOT NULL CHECK (revision >= 0),
            created_at TEXT NOT NULL
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE worker_inbox (
            event_id TEXT PRIMARY KEY,
            payload_hash TEXT NOT NULL CHECK (length(payload_hash) = 64),
            status TEXT NOT NULL CHECK (status IN ('pending', 'confirmed')),
            received_at TEXT NOT NULL,
            confirmed_at TEXT
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE worker_operation_receipts (
            idempotency_key TEXT PRIMARY KEY,
            operation TEXT NOT NULL,
            payload_hash TEXT NOT NULL CHECK (length(payload_hash) = 64),
            result_json TEXT NOT NULL,
            receipt_revision INTEGER NOT NULL CHECK (receipt_revision >= 0),
            created_at TEXT NOT NULL
        )
        """
    )
