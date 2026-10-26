"""Checkpoint evidence, epochs, Root slices, Control and reconciliation records."""

from __future__ import annotations

import sqlite3

VERSION = 3
NAME = "evidence_control"


def upgrade(connection: sqlite3.Connection) -> None:
    connection.execute(
        """CREATE TABLE workflow_epochs (
            singleton INTEGER PRIMARY KEY CHECK(singleton=1),
            implementation_content INTEGER NOT NULL CHECK(implementation_content>=0),
            documentation INTEGER NOT NULL CHECK(documentation>=0),
            git_metadata INTEGER NOT NULL CHECK(git_metadata>=0)
        )"""
    )
    connection.execute("INSERT INTO workflow_epochs VALUES (1, 0, 0, 0)")
    connection.execute(
        """CREATE TABLE root_slices (
            slice_id TEXT PRIMARY KEY,
            objective_uri TEXT NOT NULL,
            objective_hash TEXT NOT NULL CHECK(length(objective_hash)=64),
            return_uri TEXT NOT NULL, return_hash TEXT NOT NULL CHECK(length(return_hash)=64),
            boundary_uri TEXT NOT NULL, boundary_hash TEXT NOT NULL CHECK(length(boundary_hash)=64),
            authorized_paths_json TEXT NOT NULL, change_categories_json TEXT NOT NULL,
            status TEXT NOT NULL CHECK(status IN ('released','closed')),
            created_revision INTEGER NOT NULL CHECK(created_revision>=0), created_at TEXT NOT NULL
        )"""
    )
    connection.execute(
        "CREATE UNIQUE INDEX root_one_active_slice ON root_slices(status) WHERE status='released'"
    )
    connection.execute(
        """CREATE TABLE checkpoint_evidence (
            evidence_id TEXT PRIMARY KEY, node_id TEXT NOT NULL, facts_json TEXT NOT NULL,
            evidence_refs_json TEXT NOT NULL, input_hash TEXT NOT NULL CHECK(length(input_hash)=64),
            rule_hash TEXT NOT NULL CHECK(length(rule_hash)=64),
            coverage_json TEXT NOT NULL,
            evidence_request_id TEXT,
            implementation_epoch INTEGER NOT NULL CHECK(implementation_epoch>=0),
            documentation_epoch INTEGER NOT NULL CHECK(documentation_epoch>=0),
            git_metadata_epoch INTEGER NOT NULL CHECK(git_metadata_epoch>=0),
            basis_revision INTEGER NOT NULL CHECK(basis_revision>=0),
            recorded_revision INTEGER NOT NULL CHECK(recorded_revision>=1), created_at TEXT NOT NULL
        )"""
    )
    connection.execute(
        "CREATE INDEX checkpoint_evidence_node ON checkpoint_evidence(node_id, recorded_revision)"
    )
    connection.execute(
        """CREATE TABLE checkpoint_evaluations (
            evaluation_id TEXT PRIMARY KEY, node_id TEXT NOT NULL,
            outcome TEXT NOT NULL CHECK(outcome IN (
                'ready','incomplete','blocked','evidence_on_demand'
            )),
            branch TEXT, facts_hash TEXT NOT NULL CHECK(length(facts_hash)=64),
            input_hash TEXT NOT NULL CHECK(length(input_hash)=64),
            rule_hash TEXT NOT NULL CHECK(length(rule_hash)=64),
            implementation_epoch INTEGER NOT NULL CHECK(implementation_epoch>=0),
            documentation_epoch INTEGER NOT NULL CHECK(documentation_epoch>=0),
            git_metadata_epoch INTEGER NOT NULL CHECK(git_metadata_epoch>=0),
            basis_revision INTEGER NOT NULL CHECK(basis_revision>=0),
            result_revision INTEGER NOT NULL CHECK(result_revision>=1),
            missing_facts_json TEXT NOT NULL, missing_evidence_json TEXT NOT NULL,
            slice_ids_json TEXT NOT NULL DEFAULT '[]',
            evidence_request_id TEXT,
            created_at TEXT NOT NULL
        )"""
    )
    connection.execute(
        "CREATE INDEX evaluations_current_node ON checkpoint_evaluations(node_id, result_revision)"
    )
    connection.execute(
        """CREATE TABLE control_evidence_requests (
            request_id TEXT PRIMARY KEY,
            source_evaluation_id TEXT NOT NULL REFERENCES checkpoint_evaluations(evaluation_id),
            created_revision INTEGER NOT NULL CHECK(created_revision>=1),
            status TEXT NOT NULL CHECK(status IN ('pending','returned','resolved')),
            returned_revision INTEGER,
            created_at TEXT NOT NULL
        )"""
    )
    connection.execute(
        """CREATE TABLE checkpoint_confirmations (
            confirmation_id TEXT PRIMARY KEY,
            evaluation_id TEXT NOT NULL UNIQUE REFERENCES checkpoint_evaluations(evaluation_id),
            node_id TEXT NOT NULL, from_revision INTEGER NOT NULL CHECK(from_revision>=0),
            to_revision INTEGER NOT NULL CHECK(to_revision>from_revision), created_at TEXT NOT NULL
        )"""
    )
    connection.execute(
        """CREATE TABLE control_transitions (
            transition_id TEXT PRIMARY KEY,
            evaluation_id TEXT NOT NULL REFERENCES checkpoint_evaluations(evaluation_id),
            outcome TEXT NOT NULL CHECK(outcome IN ('continue','amend','stop')),
            slice_ids_json TEXT NOT NULL DEFAULT '[]',
            from_revision INTEGER NOT NULL CHECK(from_revision>=0),
            to_revision INTEGER NOT NULL CHECK(to_revision>from_revision),
            created_at TEXT NOT NULL
        )"""
    )
    connection.execute(
        """CREATE TABLE native_reconciliations (
            reconcile_id TEXT PRIMARY KEY,
            snapshot_hash TEXT NOT NULL CHECK(length(snapshot_hash)=64),
            native_refs_json TEXT NOT NULL, differences_json TEXT NOT NULL,
            status TEXT NOT NULL CHECK(status IN ('matched','conflict','awaiting_confirmation')),
            observed_revision INTEGER NOT NULL CHECK(observed_revision>=0),
            result_revision INTEGER NOT NULL CHECK(result_revision>=1), created_at TEXT NOT NULL,
            project_id TEXT NOT NULL, root_session_id TEXT NOT NULL, snapshot_json TEXT NOT NULL
        )"""
    )
    connection.execute(
        """CREATE TABLE workflow_dispatch_events (
            event_id TEXT PRIMARY KEY,
            allocation_id TEXT NOT NULL REFERENCES allocations(allocation_id),
            slice_id TEXT NOT NULL REFERENCES workflow_slices(slice_id),
            sequence INTEGER NOT NULL CHECK(sequence>=1),
            payload_json TEXT NOT NULL, payload_hash TEXT NOT NULL CHECK(length(payload_hash)=64),
            status TEXT NOT NULL CHECK(status IN ('pending','confirmed')),
            created_at TEXT NOT NULL, confirmed_at TEXT, UNIQUE(allocation_id, sequence)
        )"""
    )
    connection.execute(
        """INSERT INTO workflow_dispatch_events
           (event_id, allocation_id, slice_id, sequence, payload_json, payload_hash,
            status, created_at, confirmed_at)
           SELECT o.event_id, o.allocation_id,
                  (SELECT s.slice_id FROM workflow_slices s WHERE s.allocation_id=o.allocation_id
                   ORDER BY s.created_revision DESC LIMIT 1), 1, o.payload_json, o.payload_hash,
                  o.status, o.created_at, o.confirmed_at
           FROM root_outbox o"""
    )
