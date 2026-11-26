from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, cast

import pytest
from pydantic import TypeAdapter, ValidationError
from token_io_decoupling_core.compliance_core import (
    MAX_BATCH_UTF8_BYTES,
    MAX_DIRECT_TARGETS,
    MAX_OUTPUT_CHECKS,
    ComplianceInputError,
    evaluate_candidate_checks,
    validate_candidate_list,
)
from token_io_decoupling_tools.compliance_preflight import (
    CompliancePreflightService,
    validate_decoupling_compliance,
)
from token_io_decoupling_tools.payloads import _COMPLIANCE_PREFLIGHT


def _candidate(
    path: str,
    content: str,
    *,
    operation: str = "create",
    baseline: dict[str, str] | None = None,
) -> dict[str, object]:
    return {
        "path": path,
        "operation": operation,
        "baseline": baseline or {"state": "absent"},
        "content": content,
    }


def _request(*candidates: dict[str, object], scope: str = "skill_maintenance") -> dict[str, object]:
    return {"policy_scope": scope, "candidates": list(candidates)}


def _content(language: str, peer: str) -> str:
    return (
        "## 通用规范\n规范。\n"
        "## Pi Coding Agent 优化指令\n暂无。\n"
        "## 相关概念\n导航。\n"
    )


def _checks_for(result: dict[str, object], rule: str) -> list[dict[str, object]]:
    checks = cast(list[dict[str, Any]], result["checks"])
    return [item for item in checks if item["rule_id"] == rule]


def test_candidate_contract_rejects_noncanonical_paths_and_budget_overflow() -> None:
    with pytest.raises(ComplianceInputError, match="candidate_path_not_canonical"):
        validate_candidate_list([_candidate("docs/../unsafe.md", "x")])
    with pytest.raises(ComplianceInputError, match="create_requires_absent_baseline"):
        validate_candidate_list(
            [_candidate("docs/a.md", "x", baseline={"state": "sha256", "value": "a" * 64})]
        )

    candidates = [_candidate(f"src/file-{index}.md", "界" * 90_000) for index in range(6)]
    assert MAX_BATCH_UTF8_BYTES == 524_288
    with pytest.raises(ComplianceInputError, match="candidate_batch_byte_limit_exceeded"):
        validate_candidate_list(candidates)


def test_wire_schema_enforces_strict_candidate_envelope() -> None:
    adapter = TypeAdapter(_COMPLIANCE_PREFLIGHT)
    good = {
        "request": {
            "policy_scope": "skill_maintenance",
            "candidates": [_candidate("docs/a.md", "text")],
        }
    }
    parsed = adapter.validate_json(json.dumps(good)).model_dump()
    request = cast(dict[str, Any], parsed["request"])
    candidates = cast(list[dict[str, Any]], request["candidates"])
    assert candidates[0]["path"] == "docs/a.md"

    for path, operation, baseline, content in (
        ("/absolute.md", "create", {"state": "absent"}, "text"),
        ("a/../b.md", "create", {"state": "absent"}, "text"),
        ("docs/a.md", "replace", {"state": "absent"}, "text"),
        ("docs/a.md", "delete", {"state": "sha256", "value": "0" * 64}, "text"),
    ):
        bad = {
            "request": {
                "policy_scope": "skill_maintenance",
                "candidates": [
                    {"path": path, "operation": operation, "baseline": baseline, "content": content}
                ],
            }
        }
        with pytest.raises(ValidationError):
            adapter.validate_json(json.dumps(bad))


def test_no_reader_reports_unknown_without_probing_and_keeps_static_evidence_unknown_overall() -> (
    None
):
    result = validate_decoupling_compliance(
        None,
        _request(
            _candidate("skill/example.md", "# candidate\n"),
        ),
    )
    assert result["status"] == "unknown"
    baseline = _checks_for(result, "candidate_baseline")
    assert baseline[0]["reason_code"] == "compliance_backend_unavailable"
    message = cast(str, baseline[0]["message"])
    assert "no candidate path was probed" in message
    assert result["not_evaluated"] == [
        "reverse inbound-link scans across unchanged documents",
        "中文指令的语义准确性与完整性",
        "full repository CI and final integration acceptance",
    ]


def test_skill_overlay_checks_bilingual_links_and_layer01_structure() -> None:
    en_path = "skill/references/coding/layer-01-fundamental-concepts/example.md"
    zh_path = en_path.removesuffix(".md") + "_zh_cn.md"
    result = validate_decoupling_compliance(
        None,
        _request(
            _candidate(en_path, _content("en", Path(zh_path).name)),
            _candidate(zh_path, _content("zh", Path(en_path).name)),
        ),
    )
    assert result["status"] == "unknown"  # static content passes; disk baselines remain unknown
    assert all(check["status"] == "pass" for check in _checks_for(result, "layer01_structure"))
    assert all(
        check["status"] == "not_applicable" for check in _checks_for(result, "bilingual_mirror")
    )
    assert not any(
        check["status"] == "fail"
        for check in result["checks"]
        if check["rule_id"].startswith("markdown_link_")
    )

    malformed = validate_decoupling_compliance(
        None,
        _request(_candidate(en_path, "## General rules\nonly one section\n")),
    )
    assert malformed["status"] == "fail"
    assert any(check["status"] == "fail" for check in _checks_for(malformed, "layer01_structure"))


def test_generic_scope_marks_every_skill_rule_not_applicable() -> None:
    result = validate_decoupling_compliance(
        None,
        _request(_candidate("src/example.py", "print('not executed')\n"), scope="generic_project"),
    )
    skill_checks = [check for check in result["checks"] if check["rule_id"] != "candidate_baseline"]
    assert skill_checks
    assert {check["status"] for check in skill_checks} == {"not_applicable"}
    assert result["status"] == "unknown"  # baseline requires a trusted disk reader


def test_service_checks_real_baseline_and_never_writes_candidates(tmp_path: Path) -> None:
    original = b"original file\n"
    path = tmp_path / "src" / "file.md"
    path.parent.mkdir()
    path.write_bytes(original)
    service = CompliancePreflightService(tmp_path, {"skill_maintenance"})
    try:
        matching = validate_decoupling_compliance(
            service,
            _request(
                _candidate(
                    "src/file.md",
                    "updated file\n",
                    operation="replace",
                    baseline={"state": "sha256", "value": hashlib.sha256(original).hexdigest()},
                )
            ),
        )
        assert matching["status"] == "pass"
        assert _checks_for(matching, "candidate_baseline")[0]["status"] == "pass"
        assert path.read_bytes() == original

        stale = validate_decoupling_compliance(
            service,
            _request(
                _candidate(
                    "src/file.md",
                    "updated file\n",
                    operation="replace",
                    baseline={"state": "sha256", "value": "0" * 64},
                )
            ),
        )
        assert stale["status"] == "fail"
        assert _checks_for(stale, "candidate_baseline")[0]["reason_code"] == "baseline_mismatch"
        assert path.read_bytes() == original
    finally:
        service.close()


@pytest.mark.parametrize("mutation", ["in_place", "replace_path"])
def test_unstable_baseline_read_returns_unknown(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mutation: str
) -> None:
    original = b"original bytes\n"
    path = tmp_path / "src" / "file.md"
    path.parent.mkdir()
    path.write_bytes(original)
    service = CompliancePreflightService(tmp_path, {"skill_maintenance"})
    real_read = os.read
    mutated = False

    def mutate_after_read(file_descriptor: int, count: int) -> bytes:
        nonlocal mutated
        data = real_read(file_descriptor, count)
        if not mutated:
            mutated = True
            if mutation == "in_place":
                path.write_bytes(b"replacement with different size\n")
            else:
                replacement = tmp_path / "src" / "replacement.md"
                replacement.write_bytes(b"new inode content\n")
                replacement.replace(path)
        return data

    monkeypatch.setattr(os, "read", mutate_after_read)
    try:
        result = validate_decoupling_compliance(
            service,
            _request(
                _candidate(
                    "src/file.md",
                    "next\n",
                    operation="replace",
                    baseline={"state": "sha256", "value": hashlib.sha256(original).hexdigest()},
                )
            ),
        )
        assert result["status"] == "unknown"
        baseline = _checks_for(result, "candidate_baseline")[0]
        assert baseline["reason_code"] == "baseline_unavailable"
        assert baseline["evidence_missing"]
    finally:
        service.close()


def test_operator_scope_and_symlink_targets_fail_closed(tmp_path: Path) -> None:
    outside = tmp_path.parent / f"{tmp_path.name}-outside.md"
    outside.write_text("outside\n", encoding="utf-8")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "target.md").symlink_to(outside)
    service = CompliancePreflightService(tmp_path, {"skill_maintenance"})
    try:
        disallowed = validate_decoupling_compliance(
            service,
            _request(_candidate("src/new.md", "content\n"), scope="generic_project"),
        )
        assert disallowed["status"] == "unknown"
        assert (
            _checks_for(disallowed, "policy_scope")[0]["reason_code"] == "policy_scope_not_allowed"
        )

        symlink = validate_decoupling_compliance(
            service,
            _request(_candidate("src/new.md", "[target](target.md)\n")),
        )
        assert symlink["status"] == "unknown"
        assert any(
            check["status"] == "unknown" and check.get("target_path") == "src/target.md"
            for check in _checks_for(symlink, "markdown_link_target")
        )
        assert outside.read_text(encoding="utf-8") == "outside\n"
    finally:
        service.close()
        outside.unlink()


def test_direct_target_budget_exhaustion_is_unknown_not_pass(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    for index in range(MAX_DIRECT_TARGETS):
        (tmp_path / "src" / f"target-{index}.md").write_text("target\n", encoding="utf-8")
    links = " ".join(
        f"[target]({target})"
        for target in [f"target-{index}.md" for index in range(MAX_DIRECT_TARGETS + 1)]
    )
    service = CompliancePreflightService(tmp_path, {"skill_maintenance"})
    try:
        result = validate_decoupling_compliance(service, _request(_candidate("src/new.md", links)))
        assert result["status"] == "unknown"
        assert result["limits"]["direct_targets_read"] == MAX_DIRECT_TARGETS
        assert result["limits"]["direct_target_limit_exceeded"] is True
        assert any(
            check.get("reason_code") == "direct_target_budget_exceeded"
            for check in result["checks"]
        )
    finally:
        service.close()


def test_output_check_budget_is_bounded_and_truncation_is_unknown() -> None:
    candidates = [
        _candidate(
            f"src/doc-{index}.md",
            " ".join(f"[target](missing-{index}-{link}.md)" for link in range(10)),
        )
        for index in range(64)
    ]
    normalized = validate_candidate_list(candidates)
    baseline = [
        {"rule_id": "candidate_baseline", "status": "pass", "path": item["path"]}
        for item in normalized
    ]
    result = evaluate_candidate_checks(
        "skill_maintenance", normalized, baseline, lambda _path: False, allowed_scope=True
    )
    assert result["status"] == "fail"
    assert len(result["checks"]) == MAX_OUTPUT_CHECKS
    assert result["limits"]["checks_truncated"] is True
    assert result["checks"][-1]["reason_code"] == "output_check_budget_exceeded"


def test_result_exposes_policy_version_and_rule_id() -> None:
    result = validate_decoupling_compliance(
        None,
        _request(_candidate("docs/example.md", "## General rules\nBody\n")),
    )
    assert result["policy_version"] == 1
    assert result["checks"]
    assert all("rule_id" in check and "rule" not in check for check in result["checks"])


@pytest.mark.parametrize(
    ("candidate_path", "mirror_path"),
    [
        (
            "docs/mcp/CANDIDATE_COMPLIANCE.md",
            "docs/mcp/CANDIDATE_COMPLIANCE_zh_cn.md",
        ),
        (
            "docs/mcp/OUTPUT_MATERIALIZATION.md",
            "docs/mcp/OUTPUT_MATERIALIZATION_zh_cn.md",
        ),
        (
            "docs/mcp/DEVELOPMENT.md",
            "docs/mcp/DEVELOPMENT_zh_cn.md",
        ),
    ],
)
def test_new_mcp_owner_candidate_does_not_require_a_mirror(
    tmp_path: Path,
    candidate_path: str,
    mirror_path: str,
) -> None:
    service = CompliancePreflightService(tmp_path, {"skill_maintenance"})
    try:
        result = validate_decoupling_compliance(
            service,
            _request(_candidate(candidate_path, "Candidate text\n")),
        )
        mirror = _checks_for(result, "bilingual_mirror")[0]
        assert mirror["status"] == "not_applicable"
        assert mirror.get("target_path") is None
    finally:
        service.close()


def _delete_candidate(path: str, current: bytes) -> dict[str, object]:
    return {
        "path": path,
        "operation": "delete",
        "baseline": {"state": "sha256", "value": hashlib.sha256(current).hexdigest()},
        "content": None,
    }


@pytest.mark.parametrize(
    ("deleted_paths", "expected_status"),
    [
        (["docs/mcp/CANDIDATE_COMPLIANCE.md"], "fail"),
        (["docs/mcp/CANDIDATE_COMPLIANCE_zh_cn.md"], "fail"),
        (
            [
                "docs/mcp/CANDIDATE_COMPLIANCE.md",
                "docs/mcp/CANDIDATE_COMPLIANCE_zh_cn.md",
            ],
            "pass",
        ),
    ],
)
def test_delete_has_no_bilingual_pair_requirement(
    tmp_path: Path, deleted_paths: list[str], expected_status: str
) -> None:
    en_path = "docs/mcp/CANDIDATE_COMPLIANCE.md"
    zh_path = "docs/mcp/CANDIDATE_COMPLIANCE_zh_cn.md"
    contents = {en_path: b"English\n", zh_path: "中文\n".encode()}
    for path, data in contents.items():
        target = tmp_path / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    service = CompliancePreflightService(tmp_path, {"skill_maintenance"})
    try:
        result = validate_decoupling_compliance(
            service,
            _request(*(_delete_candidate(path, contents[path]) for path in deleted_paths)),
        )
        assert _checks_for(result, "bilingual_mirror")[0]["status"] == "not_applicable"
    finally:
        service.close()


def test_delete_does_not_probe_absent_or_unsafe_legacy_peer(tmp_path: Path) -> None:
    en_path = "docs/mcp/CANDIDATE_COMPLIANCE.md"
    content = b"English\n"
    target = tmp_path / en_path
    target.parent.mkdir(parents=True)
    target.write_bytes(content)
    service = CompliancePreflightService(tmp_path, {"skill_maintenance"})
    try:
        absent = validate_decoupling_compliance(
            service, _request(_delete_candidate(en_path, content))
        )
        assert _checks_for(absent, "bilingual_mirror")[0]["status"] == "not_applicable"
    finally:
        service.close()

    unknown_root = tmp_path / "unknown-root"
    unknown_root.mkdir()
    unknown_project_mcp = unknown_root / "docs/mcp"
    unknown_project_mcp.mkdir(parents=True)
    unknown_en = unknown_root / en_path
    unknown_en.write_bytes(content)
    outside = tmp_path / "outside-mirror.md"
    outside.write_bytes(b"Chinese\n")
    (unknown_project_mcp / "CANDIDATE_COMPLIANCE_zh_cn.md").symlink_to(outside)
    unknown_service = CompliancePreflightService(unknown_root, {"skill_maintenance"})
    try:
        unknown = validate_decoupling_compliance(
            unknown_service, _request(_delete_candidate(en_path, content))
        )
        mirror = _checks_for(unknown, "bilingual_mirror")[0]
        assert mirror["status"] == "not_applicable"
        assert not mirror["evidence_missing"]
    finally:
        unknown_service.close()


def test_closed_service_does_not_apply_disallowed_skill_scope(tmp_path: Path) -> None:
    service = CompliancePreflightService(tmp_path, {"generic_project"})
    service.close()
    result = validate_decoupling_compliance(
        service,
        _request(
            _candidate(
                "docs/mcp/CANDIDATE_COMPLIANCE.md",
                "Candidate\n",
            ),
            scope="skill_maintenance",
        ),
    )
    assert result["status"] == "unknown"
    assert _checks_for(result, "policy_scope")[0]["reason_code"] == "policy_scope_not_allowed"
    assert not any(
        check["rule_id"]
        in {
            "bilingual_mirror",
            "markdown_link_language",
            "markdown_link_layer",
            "markdown_link_target",
            "layer01_structure",
        }
        for check in result["checks"]
    )


def test_service_create_and_delete_baselines_are_checked_without_writes(tmp_path: Path) -> None:
    service = CompliancePreflightService(tmp_path, {"skill_maintenance"})
    existing = tmp_path / "src" / "existing.md"
    existing.parent.mkdir()
    original = b"original\n"
    existing.write_bytes(original)
    try:
        absent_create = validate_decoupling_compliance(
            service, _request(_candidate("src/new.md", "candidate\n"))
        )
        assert _checks_for(absent_create, "candidate_baseline")[0]["status"] == "pass"

        occupied_create = validate_decoupling_compliance(
            service, _request(_candidate("src/existing.md", "candidate\n"))
        )
        assert (
            _checks_for(occupied_create, "candidate_baseline")[0]["reason_code"]
            == "create_target_exists"
        )

        valid_delete = validate_decoupling_compliance(
            service, _request(_delete_candidate("src/existing.md", original))
        )
        assert _checks_for(valid_delete, "candidate_baseline")[0]["status"] == "pass"

        stale_delete = validate_decoupling_compliance(
            service,
            _request(
                {
                    **_delete_candidate("src/existing.md", original),
                    "baseline": {"state": "sha256", "value": "0" * 64},
                }
            ),
        )
        assert (
            _checks_for(stale_delete, "candidate_baseline")[0]["reason_code"] == "baseline_mismatch"
        )
        assert existing.read_bytes() == original
    finally:
        service.close()


def test_candidate_and_intermediate_directory_symlinks_fail_closed(tmp_path: Path) -> None:
    outside = tmp_path.parent / f"{tmp_path.name}-outside"
    outside.mkdir()
    (outside / "existing.md").write_text("outside\n", encoding="utf-8")
    (tmp_path / "file-link.md").symlink_to(outside / "existing.md")
    (tmp_path / "dir-link").symlink_to(outside, target_is_directory=True)
    service = CompliancePreflightService(tmp_path, {"skill_maintenance"})
    try:
        for candidate_path in ("file-link.md", "dir-link/new.md"):
            result = validate_decoupling_compliance(
                service, _request(_candidate(candidate_path, "candidate\n"))
            )
            baseline = _checks_for(result, "candidate_baseline")[0]
            assert baseline["status"] == "unknown"
            assert baseline["evidence_missing"]
        assert (outside / "existing.md").read_text(encoding="utf-8") == "outside\n"
    finally:
        service.close()


def test_oversized_baseline_and_link_target_are_unknown_with_missing_evidence(
    tmp_path: Path,
) -> None:
    (tmp_path / "src").mkdir()
    oversized = b"x" * (MAX_BATCH_UTF8_BYTES + 1)
    baseline_path = tmp_path / "src" / "baseline.md"
    baseline_path.write_bytes(oversized)
    (tmp_path / "src" / "large-target.md").write_bytes(oversized)
    service = CompliancePreflightService(tmp_path, {"skill_maintenance"})
    try:
        baseline = validate_decoupling_compliance(
            service,
            _request(
                _candidate(
                    "src/baseline.md",
                    "replacement\n",
                    operation="replace",
                    baseline={"state": "sha256", "value": hashlib.sha256(oversized).hexdigest()},
                )
            ),
        )
        baseline_check = _checks_for(baseline, "candidate_baseline")[0]
        assert baseline_check["status"] == "unknown"
        assert baseline_check["evidence_missing"]

        linked = validate_decoupling_compliance(
            service, _request(_candidate("src/new.md", "[large](large-target.md)\n"))
        )
        target_check = next(
            check
            for check in _checks_for(linked, "markdown_link_target")
            if check.get("target_path") == "src/large-target.md"
        )
        assert target_check["status"] == "unknown"
        assert target_check["evidence_missing"]
    finally:
        service.close()
