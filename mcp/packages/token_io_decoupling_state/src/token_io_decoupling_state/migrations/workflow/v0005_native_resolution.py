"""Append-only Native comparison and explicit recovery records."""

from __future__ import annotations

import hashlib
import json
import sqlite3

VERSION = 5
NAME = "native_resolution"


def upgrade(connection: sqlite3.Connection) -> None:
    connection.execute(
        "ALTER TABLE workflow_control ADD COLUMN recovery_revision INTEGER "
        "NOT NULL DEFAULT 0 CHECK(recovery_revision>=0)"
    )
    connection.execute(
        """CREATE TABLE native_reconcile_preimages (
            reconcile_id TEXT PRIMARY KEY,
            snapshot_hash TEXT NOT NULL CHECK(length(snapshot_hash)=64),
            root_preimage_json TEXT NOT NULL,
            root_preimage_hash TEXT NOT NULL CHECK(length(root_preimage_hash)=64),
            captured_revision INTEGER NOT NULL CHECK(captured_revision>=0),
            captured_at TEXT NOT NULL,
            FOREIGN KEY(reconcile_id) REFERENCES native_reconciliations(reconcile_id)
        )"""
    )
    connection.execute(
        """CREATE TABLE native_reconcile_resolutions (
            resolution_id TEXT PRIMARY KEY,
            reconcile_id TEXT NOT NULL,
            reviewed_set_hash TEXT NOT NULL CHECK(length(reviewed_set_hash)=64),
            snapshot_hash TEXT NOT NULL CHECK(length(snapshot_hash)=64),
            choice TEXT NOT NULL CHECK(choice IN ('adopt_native_pair','retain_sqlite_pair')),
            selected_source_uri TEXT NOT NULL,
            selected_source_hash TEXT NOT NULL CHECK(length(selected_source_hash)=64),
            selected_semantic_references_json TEXT NOT NULL,
            native_revision INTEGER NOT NULL CHECK(native_revision>=0),
            native_epochs_json TEXT NOT NULL,
            root_decision_ref_json TEXT NOT NULL,
            native_freshness_refs_json TEXT NOT NULL,
            root_quiescence_refs_json TEXT NOT NULL,
            observed_revision INTEGER NOT NULL CHECK(observed_revision>=0),
            result_revision INTEGER NOT NULL CHECK(result_revision>=1),
            recovery_revision INTEGER NOT NULL CHECK(recovery_revision>=1),
            created_at TEXT NOT NULL,
            FOREIGN KEY(reconcile_id) REFERENCES native_reconciliations(reconcile_id)
        )"""
    )
    connection.execute(
        "CREATE INDEX native_reconcile_resolutions_order "
        "ON native_reconcile_resolutions(result_revision,resolution_id)"
    )
    connection.execute(
        """CREATE TABLE native_reconcile_resolution_targets (
            reconcile_id TEXT PRIMARY KEY,
            resolution_id TEXT NOT NULL,
            snapshot_hash TEXT NOT NULL CHECK(length(snapshot_hash)=64),
            FOREIGN KEY(reconcile_id) REFERENCES native_reconciliations(reconcile_id),
            FOREIGN KEY(resolution_id) REFERENCES native_reconcile_resolutions(resolution_id)
        )"""
    )
    connection.execute(
        "CREATE INDEX native_resolution_targets_by_resolution "
        "ON native_reconcile_resolution_targets(resolution_id,reconcile_id)"
    )
    connection.execute(
        """CREATE TABLE native_reconcile_confirmations (
            awaiting_reconcile_id TEXT PRIMARY KEY,
            matched_reconcile_id TEXT NOT NULL UNIQUE,
            snapshot_hash TEXT NOT NULL CHECK(length(snapshot_hash)=64),
            confirmed_revision INTEGER NOT NULL CHECK(confirmed_revision>=1),
            created_at TEXT NOT NULL,
            CHECK(awaiting_reconcile_id<>matched_reconcile_id),
            FOREIGN KEY(awaiting_reconcile_id) REFERENCES native_reconciliations(reconcile_id),
            FOREIGN KEY(matched_reconcile_id) REFERENCES native_reconciliations(reconcile_id)
        )"""
    )
    connection.execute(
        "CREATE INDEX native_confirmations_by_match "
        "ON native_reconcile_confirmations(matched_reconcile_id)"
    )
    _backfill_proven_confirmations(connection)


def _backfill_proven_confirmations(connection: sqlite3.Connection) -> None:
    """Link only exact, adjacent legacy compare/confirm pairs with unique provenance."""
    awaiting = connection.execute(
        "SELECT reconcile_id,snapshot_hash,observed_revision,result_revision,project_id,"
        "root_session_id,native_refs_json,snapshot_json "
        "FROM native_reconciliations WHERE status='awaiting_confirmation'"
    ).fetchall()
    matched = connection.execute(
        "SELECT reconcile_id,snapshot_hash,observed_revision,result_revision,project_id,"
        "root_session_id,native_refs_json,snapshot_json "
        "FROM native_reconciliations WHERE status='matched'"
    ).fetchall()
    candidates: dict[str, list[str]] = {}
    reverse: dict[str, list[str]] = {}
    for pending in awaiting:
        (
            pending_id,
            snapshot_hash,
            observed_revision,
            result_revision,
            project_id,
            root_session_id,
            native_refs_json,
            snapshot_json,
        ) = pending
        pending_snapshot = _verified_legacy_snapshot(
            snapshot_json,
            snapshot_hash,
            project_id,
            root_session_id,
            native_refs_json,
        )
        if pending_snapshot is None or result_revision != observed_revision + 1:
            continue
        if json.loads(pending_snapshot)["revision"] != observed_revision:
            continue
        for confirmed in matched:
            (
                match_id,
                match_hash,
                match_observed_revision,
                final_revision,
                match_project,
                match_root,
                match_native_refs_json,
                match_snapshot_json,
            ) = confirmed
            match_snapshot = _verified_legacy_snapshot(
                match_snapshot_json,
                match_hash,
                match_project,
                match_root,
                match_native_refs_json,
            )
            if (
                match_snapshot is not None
                and snapshot_hash == match_hash
                and project_id == match_project
                and root_session_id == match_root
                and match_observed_revision == result_revision
                and final_revision == match_observed_revision + 1
                and match_snapshot == pending_snapshot
            ):
                candidates.setdefault(pending_id, []).append(match_id)
                reverse.setdefault(match_id, []).append(pending_id)
    for pending_id, matches in candidates.items():
        if len(matches) != 1 or len(reverse[matches[0]]) != 1:
            continue
        match_id = matches[0]
        match = next(row for row in matched if row[0] == match_id)
        connection.execute(
            "INSERT INTO native_reconcile_confirmations VALUES (?,?,?,?,CURRENT_TIMESTAMP)",
            (pending_id, match_id, match[1], match[3]),
        )


def _verified_legacy_snapshot(
    snapshot_json: str,
    stored_hash: str,
    project_id: str,
    root_session_id: str,
    native_refs_json: str,
) -> str | None:
    """Return canonical payload only when the legacy row matches its stored content hash."""
    try:
        payload = json.loads(snapshot_json)
        native_refs = json.loads(native_refs_json)
    except (TypeError, json.JSONDecodeError):
        return None
    required_keys = {
        "project_id",
        "root_session_id",
        "run_id",
        "mode_count",
        "mode_source",
        "lifecycle",
        "source",
        "semantic_references",
        "revision",
        "allocations",
        "epochs",
        "evidence_refs",
    }
    if not isinstance(payload, dict) or set(payload) != required_keys:
        return None
    if payload.get("project_id") != project_id or payload.get("root_session_id") != root_session_id:
        return None
    revision = payload.get("revision")
    if type(revision) is not int or revision < 0:
        return None
    mode_count = payload.get("mode_count")
    source = payload.get("source")
    epochs = payload.get("epochs")
    if (
        not isinstance(mode_count, dict)
        or set(mode_count) != {"mode", "child_count"}
        or mode_count.get("mode") not in {"Single-Agent Coding", "Multi-Agent Coding"}
        or type(mode_count.get("child_count")) is not int
        or mode_count["child_count"] < 0
        or (mode_count["mode"] == "Single-Agent Coding" and mode_count["child_count"] != 0)
        or (mode_count["mode"] == "Multi-Agent Coding" and mode_count["child_count"] < 1)
        or not isinstance(source, dict)
        or not _valid_semantic_ref(source)
        or not _valid_ref_list(payload.get("semantic_references"))
        or not _valid_ref_list(payload.get("evidence_refs"))
        or not isinstance(epochs, dict)
        or set(epochs) != {"implementation_content", "documentation", "git_metadata"}
        or any(type(value) is not int or value < 0 for value in epochs.values())
        or payload.get("mode_source") not in {"explicit", "default", "timeout-default"}
        or payload.get("lifecycle") not in {"pending", "running", "completed", "interrupted"}
        or (payload.get("run_id") is not None and not isinstance(payload.get("run_id"), str))
        or not _valid_allocation_list(payload.get("allocations"))
    ):
        return None
    evidence_refs = payload.get("evidence_refs")
    if not isinstance(evidence_refs, list) or evidence_refs != native_refs:
        return None
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    actual_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    if actual_hash != stored_hash:
        return None
    return canonical


def _valid_semantic_ref(value: object) -> bool:
    if not isinstance(value, dict) or set(value) != {"uri", "content_hash"}:
        return False
    return (
        isinstance(value.get("uri"), str)
        and bool(value["uri"].strip())
        and isinstance(value.get("content_hash"), str)
        and len(value["content_hash"]) == 64
        and all(character in "0123456789abcdef" for character in value["content_hash"])
    )


def _valid_ref_list(value: object) -> bool:
    return (
        isinstance(value, list)
        and len(value) <= 256
        and all(_valid_semantic_ref(item) for item in value)
    )


def _valid_allocation_list(value: object) -> bool:
    if not isinstance(value, list) or len(value) > 256:
        return False
    for item in value:
        if not isinstance(item, dict) or set(item) != {
            "allocation_id",
            "role",
            "worker_session_id",
            "status",
        }:
            return False
        if not isinstance(item.get("allocation_id"), str) or not item["allocation_id"].strip():
            return False
        if item.get("role") is not None and not isinstance(item.get("role"), str):
            return False
        if item.get("worker_session_id") is not None and not isinstance(
            item.get("worker_session_id"), str
        ):
            return False
        if item.get("status") not in {"reserved", "bound", "initialized"}:
            return False
    return True
