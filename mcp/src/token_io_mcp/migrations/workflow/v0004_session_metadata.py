"""Root-owned session audit and trusted capability metadata."""

from __future__ import annotations

import sqlite3

VERSION = 4
NAME = "session_metadata"


def upgrade(connection: sqlite3.Connection) -> None:
    connection.execute(
        "ALTER TABLE root_slices ADD COLUMN output_class TEXT "
        "CHECK(output_class IS NULL OR output_class IN "
        "('code_configuration','skill_instructions','ordinary_documentation','other','unknown'))"
    )
    connection.execute(
        "ALTER TABLE root_slices ADD COLUMN write_content_memo INTEGER "
        "CHECK(write_content_memo IS NULL OR write_content_memo IN (0,1))"
    )
    connection.execute(
        """CREATE TABLE workflow_session_metadata (
            singleton INTEGER PRIMARY KEY CHECK(singleton=1),
            session_audit_json TEXT,
            capability_snapshot_json TEXT,
            capability_snapshot_hash TEXT
                CHECK(capability_snapshot_hash IS NULL OR length(capability_snapshot_hash)=64),
            capability_observed_revision INTEGER
                CHECK(capability_observed_revision IS NULL OR capability_observed_revision>=0),
            CHECK((capability_snapshot_json IS NULL AND capability_snapshot_hash IS NULL
                   AND capability_observed_revision IS NULL)
               OR (capability_snapshot_json IS NOT NULL AND capability_snapshot_hash IS NOT NULL
                   AND capability_observed_revision IS NOT NULL))
        )"""
    )
    connection.execute("INSERT INTO workflow_session_metadata(singleton) VALUES (1)")
