"""Deterministic workflow, allocation, slice, receipt, and outbox state."""

from __future__ import annotations

import sqlite3

VERSION = 2
NAME = "control_state"


def upgrade(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE workflow_control (
            singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
            project_id TEXT NOT NULL,
            root_session_id TEXT NOT NULL,
            run_id TEXT NOT NULL UNIQUE,
            mode TEXT NOT NULL CHECK (mode IN ('Single-Agent Coding', 'Multi-Agent Coding')),
            child_count INTEGER NOT NULL CHECK (child_count >= 0),
            mode_source TEXT NOT NULL CHECK (mode_source IN ('explicit', 'default')),
            source_uri TEXT NOT NULL,
            source_hash TEXT NOT NULL CHECK (length(source_hash) = 64),
            semantic_references_json TEXT NOT NULL,
            lifecycle TEXT NOT NULL CHECK (
                lifecycle IN ('pending', 'running', 'completed', 'interrupted')
            ),
            revision INTEGER NOT NULL CHECK (revision >= 0),
            created_at TEXT NOT NULL,
            CHECK (
                (mode = 'Single-Agent Coding' AND child_count = 0)
                OR (mode = 'Multi-Agent Coding' AND child_count > 0)
            ),
            CHECK (mode_source != 'default' OR (mode = 'Multi-Agent Coding' AND child_count = 1))
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE allocations (
            allocation_id TEXT PRIMARY KEY,
            slot INTEGER NOT NULL UNIQUE CHECK (slot >= 0),
            role TEXT,
            status TEXT NOT NULL CHECK (
                status IN ('unassigned', 'reserved', 'bound', 'initialized')
            ),
            worker_session_id TEXT UNIQUE,
            output_class TEXT CHECK (output_class IN ('code_configuration', 'skill_instructions')),
            worker_event_id TEXT UNIQUE,
            created_at TEXT NOT NULL,
            CHECK (
                (status IN ('unassigned', 'reserved') AND worker_session_id IS NULL)
                OR (status IN ('bound', 'initialized') AND worker_session_id IS NOT NULL)
            ),
            CHECK (
                (status = 'unassigned' AND role IS NULL)
                OR (status != 'unassigned' AND role IS NOT NULL)
            )
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE workflow_slices (
            slice_id TEXT PRIMARY KEY,
            allocation_id TEXT NOT NULL REFERENCES allocations(allocation_id),
            output_class TEXT NOT NULL CHECK (
                output_class IN ('code_configuration', 'skill_instructions')
            ),
            objective_uri TEXT NOT NULL,
            objective_hash TEXT NOT NULL CHECK (length(objective_hash) = 64),
            return_conditions_uri TEXT NOT NULL,
            return_conditions_hash TEXT NOT NULL CHECK (length(return_conditions_hash) = 64),
            unreleased_boundary_uri TEXT NOT NULL,
            unreleased_boundary_hash TEXT NOT NULL CHECK (length(unreleased_boundary_hash) = 64),
            authorized_paths_json TEXT NOT NULL,
            change_categories_json TEXT NOT NULL,
            write_content_memo INTEGER NOT NULL CHECK (write_content_memo IN (0, 1)),
            status TEXT NOT NULL CHECK (status IN ('released', 'closed')),
            created_revision INTEGER NOT NULL CHECK (created_revision >= 0),
            created_at TEXT NOT NULL
        )
        """
    )
    connection.execute(
        "CREATE UNIQUE INDEX workflow_one_active_slice_per_allocation "
        "ON workflow_slices(allocation_id) WHERE status = 'released'"
    )
    connection.execute(
        """
        CREATE TABLE operation_receipts (
            idempotency_key TEXT PRIMARY KEY,
            operation TEXT NOT NULL,
            payload_hash TEXT NOT NULL CHECK (length(payload_hash) = 64),
            result_json TEXT NOT NULL,
            receipt_revision INTEGER NOT NULL CHECK (receipt_revision >= 0),
            created_at TEXT NOT NULL
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE root_outbox (
            event_id TEXT PRIMARY KEY,
            allocation_id TEXT NOT NULL UNIQUE REFERENCES allocations(allocation_id),
            event_type TEXT NOT NULL CHECK (event_type = 'worker_assignment'),
            payload_json TEXT NOT NULL,
            payload_hash TEXT NOT NULL CHECK (length(payload_hash) = 64),
            status TEXT NOT NULL CHECK (status IN ('pending', 'confirmed')),
            created_at TEXT NOT NULL,
            confirmed_at TEXT
        )
        """
    )
