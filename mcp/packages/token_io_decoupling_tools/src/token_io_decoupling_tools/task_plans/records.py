"""任务计划记录、替代关系与完成证据的校验和重放。"""

from __future__ import annotations

import re
from typing import Any

from .constants import _KINDS, _OUTCOMES, _PLAN_ID, _RECORD_ID, _REVISION, MAX_RECORDS_PER_OPERATION
from .types import TaskPlanFailure


def _validate_plan_id(value: Any) -> str:
    if not isinstance(value, str) or not _PLAN_ID.fullmatch(value):
        raise TaskPlanFailure("invalid_plan_id")
    return value


def _validate_id(value: Any, pattern: re.Pattern[str], reason: str) -> str:
    if not isinstance(value, str) or not pattern.fullmatch(value):
        raise TaskPlanFailure(reason)
    return value


def _validate_revision(value: Any, *, allow_absent: bool = False) -> str | None:
    if allow_absent and value is None:
        return None
    if not isinstance(value, str) or not _REVISION.fullmatch(value):
        raise TaskPlanFailure("invalid_expected_revision")
    return value


def _validate_text(value: Any, maximum: int, reason: str) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise TaskPlanFailure(reason)
    return value


def _validate_record_relationships(
    record: dict[str, Any], kind: str
) -> tuple[str | None, str | None, str | None, str | None]:
    outcome = record["outcome"]
    if kind == "verification":
        if not isinstance(outcome, str) or outcome not in _OUTCOMES:
            raise TaskPlanFailure("verification_outcome_required")
    elif outcome is not None:
        raise TaskPlanFailure("outcome_only_for_verification")
    resolves = record["resolves_blocker_id"]
    if kind == "resolution":
        _validate_id(resolves, _RECORD_ID, "resolution_blocker_required")
    elif resolves is not None:
        raise TaskPlanFailure("blocker_reference_only_for_resolution")
    supersedes = record["supersedes_id"]
    reason = record["supersedes_reason"]
    if supersedes is None:
        if reason is not None:
            raise TaskPlanFailure("supersedes_reason_without_target")
    else:
        _validate_id(supersedes, _RECORD_ID, "invalid_supersedes_id")
        _validate_text(reason, 1000, "supersedes_reason_required")
    return outcome, resolves, supersedes, reason


def _validate_record(record: Any) -> dict[str, Any]:
    if not isinstance(record, dict):
        raise TaskPlanFailure("invalid_record")
    allowed = {
        "record_id",
        "kind",
        "text",
        "sources",
        "outcome",
        "resolves_blocker_id",
        "supersedes_id",
        "supersedes_reason",
    }
    if set(record) != allowed:
        raise TaskPlanFailure("invalid_record_fields")
    record_id = _validate_id(record["record_id"], _RECORD_ID, "invalid_record_id")
    kind = record["kind"]
    if not isinstance(kind, str) or kind not in _KINDS:
        raise TaskPlanFailure("invalid_record_kind")
    text = _validate_text(record["text"], 4000, "invalid_record_text")
    sources = record["sources"]
    if (
        not isinstance(sources, list)
        or not 1 <= len(sources) <= 8
        or any(
            not isinstance(source, str) or not source.strip() or len(source) > 512
            for source in sources
        )
    ):
        raise TaskPlanFailure("invalid_record_sources")
    outcome, resolves, supersedes, reason = _validate_record_relationships(record, kind)
    return {
        "record_id": record_id,
        "kind": kind,
        "text": text,
        "sources": list(sources),
        "outcome": outcome,
        "resolves_blocker_id": resolves,
        "supersedes_id": supersedes,
        "supersedes_reason": reason,
    }


def _apply_record_relationships(
    record: dict[str, Any],
    records: dict[str, dict[str, Any]],
    active_ids: set[str],
    resolved_blockers: set[str],
) -> None:
    supersedes = record["supersedes_id"]
    if supersedes is not None:
        old = records.get(supersedes)
        if old is None or supersedes not in active_ids:
            raise TaskPlanFailure("superseded_record_not_active")
        if old["kind"] != record["kind"]:
            raise TaskPlanFailure("superseded_record_kind_mismatch")
        active_ids.remove(supersedes)
    blocker_id = record["resolves_blocker_id"]
    if blocker_id is not None:
        blocker = records.get(blocker_id)
        if blocker is None or blocker["kind"] != "blocker":
            raise TaskPlanFailure("resolution_blocker_not_found")
        if blocker_id in resolved_blockers:
            raise TaskPlanFailure("blocker_already_resolved")
        resolved_blockers.add(blocker_id)


def _apply_records(
    records: dict[str, dict[str, Any]],
    active_ids: set[str],
    resolved_blockers: set[str],
    additions: list[dict[str, Any]],
    *,
    completion: bool,
) -> None:
    if not isinstance(additions, list) or not 1 <= len(additions) <= MAX_RECORDS_PER_OPERATION:
        raise TaskPlanFailure("invalid_record_count")
    seen: set[str] = set()
    for raw_record in additions:
        record = _validate_record(raw_record)
        record_id = record["record_id"]
        if record_id in seen or record_id in records:
            raise TaskPlanFailure("record_id_conflict")
        seen.add(record_id)
        if completion and record["kind"] not in {"result", "limitation"}:
            raise TaskPlanFailure("completion_record_kind_invalid")
        if not completion and record["kind"] in {"result", "limitation"}:
            raise TaskPlanFailure("result_requires_completion")
        _apply_record_relationships(record, records, active_ids, resolved_blockers)
        records[record_id] = record
        active_ids.add(record_id)


def _validate_evidence_entry(
    entry: Any, mapped: set[str], criteria: set[str], verifications: dict[str, dict[str, Any]]
) -> dict[str, str]:
    if not isinstance(entry, dict) or set(entry) != {"criterion_id", "verification_id"}:
        raise TaskPlanFailure("invalid_criterion_evidence")
    criterion_id = _validate_id(entry["criterion_id"], _RECORD_ID, "invalid_criterion_id")
    verification_id = _validate_id(entry["verification_id"], _RECORD_ID, "invalid_verification_id")
    if criterion_id in mapped:
        raise TaskPlanFailure("duplicate_criterion_mapping")
    if criterion_id not in criteria:
        raise TaskPlanFailure("criterion_not_active")
    verification = verifications.get(verification_id)
    if verification is None:
        raise TaskPlanFailure("verification_not_active")
    if verification["outcome"] != "passed":
        raise TaskPlanFailure("verification_not_passed")
    mapped.add(criterion_id)
    return {"criterion_id": criterion_id, "verification_id": verification_id}


def _validate_evidence(
    records: dict[str, dict[str, Any]],
    active_ids: set[str],
    unresolved: tuple[str, ...],
    evidence: Any,
) -> list[dict[str, str]]:
    if unresolved:
        raise TaskPlanFailure("unresolved_blockers")
    criteria = {record_id for record_id in active_ids if records[record_id]["kind"] == "criterion"}
    if not criteria:
        raise TaskPlanFailure("active_criterion_required")
    verifications = {
        record_id: record
        for record_id, record in records.items()
        if record_id in active_ids and record["kind"] == "verification"
    }
    if not isinstance(evidence, list) or not 1 <= len(evidence) <= MAX_RECORDS_PER_OPERATION:
        raise TaskPlanFailure("criterion_evidence_required")
    normalized: list[dict[str, str]] = []
    mapped: set[str] = set()
    for entry in evidence:
        normalized.append(_validate_evidence_entry(entry, mapped, criteria, verifications))
    if mapped != criteria:
        raise TaskPlanFailure("criterion_evidence_incomplete")
    return normalized
