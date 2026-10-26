"""Worker checkpoint evidence and monotonic follow-up assignment history."""

from __future__ import annotations

import sqlite3

VERSION = 3
NAME = "evidence_dispatch"


def upgrade(connection: sqlite3.Connection) -> None:
    connection.execute(
        """CREATE TABLE worker_dispatch_history (
            event_id TEXT PRIMARY KEY, sequence INTEGER NOT NULL CHECK(sequence>=1),
            snapshot_json TEXT NOT NULL,
            assignment_hash TEXT NOT NULL CHECK(length(assignment_hash)=64),
            status TEXT NOT NULL CHECK(status IN ('pending','confirmed')),
            received_at TEXT NOT NULL, confirmed_at TEXT, UNIQUE(sequence)
        )"""
    )
    connection.execute(
        """INSERT INTO worker_dispatch_history
           (event_id, sequence, snapshot_json, assignment_hash, status, received_at, confirmed_at)
           SELECT i.event_id, 1, a.snapshot_json, i.payload_hash, i.status,
                  i.received_at, i.confirmed_at
           FROM worker_inbox i CROSS JOIN assignment_snapshot a WHERE a.singleton=1"""
    )
    connection.execute(
        """CREATE TABLE worker_active_dispatch (
            singleton INTEGER PRIMARY KEY CHECK(singleton=1),
            event_id TEXT NOT NULL REFERENCES worker_dispatch_history(event_id),
            sequence INTEGER NOT NULL CHECK(sequence>=1)
        )"""
    )
    connection.execute(
        """INSERT INTO worker_active_dispatch
           SELECT 1, event_id, sequence FROM worker_dispatch_history
           WHERE sequence=1 AND status='confirmed'"""
    )
    connection.execute(
        """CREATE TABLE worker_checkpoint_evidence (
            evidence_id TEXT PRIMARY KEY, node_id TEXT NOT NULL, facts_json TEXT NOT NULL,
            evidence_refs_json TEXT NOT NULL, input_hash TEXT NOT NULL CHECK(length(input_hash)=64),
            rule_hash TEXT NOT NULL CHECK(length(rule_hash)=64),
            coverage_json TEXT NOT NULL,
            implementation_epoch INTEGER NOT NULL CHECK(implementation_epoch>=0),
            documentation_epoch INTEGER NOT NULL CHECK(documentation_epoch>=0),
            git_metadata_epoch INTEGER NOT NULL CHECK(git_metadata_epoch>=0),
            basis_revision INTEGER NOT NULL CHECK(basis_revision>=0),
            recorded_revision INTEGER NOT NULL CHECK(recorded_revision>=1), created_at TEXT NOT NULL
        )"""
    )
    connection.execute(
        "CREATE INDEX worker_evidence_node ON worker_checkpoint_evidence("
        "node_id, recorded_revision)"
    )
