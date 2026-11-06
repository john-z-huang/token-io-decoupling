from __future__ import annotations

import hashlib
import json
import os

import pytest
from pydantic import TypeAdapter, ValidationError

from token_io_decoupling_core.compliance_core import (
    MAX_BATCH_UTF8_BYTES,
    MAX_OUTPUT_CHECKS,
    ComplianceInputError,
    build_result,
    validate_candidate_list,
)
from token_io_decoupling_workflow.compliance_preflight import (
    CompliancePreflightService,
    validate_decoupling_compliance,
)
from token_io_decoupling_workflow.payloads import _COMPLIANCE_PREFLIGHT


def candidate(path="src/new.py", content="print(1)\n", operation="create", baseline=None):
    return {
        "path": path,
        "operation": operation,
        "content": content,
        "baseline": baseline or {"state": "absent"},
    }


def request(*items):
    return {"policy_scope": "generic_project", "candidates": list(items)}


@pytest.mark.parametrize("path", ["/absolute", "../escape", "a/../b", "a//b", "a\\b", "a/./b"])
def test_candidate_paths_remain_canonical_and_relative(path):
    with pytest.raises(ComplianceInputError):
        validate_candidate_list([candidate(path)])


def test_candidate_baselines_and_utf8_budget_remain_strict():
    with pytest.raises(ComplianceInputError, match="create_requires_absent_baseline"):
        validate_candidate_list([candidate(baseline={"state": "sha256", "value": "a" * 64})])
    assert MAX_BATCH_UTF8_BYTES == 524_288
    with pytest.raises(ComplianceInputError, match="candidate_batch_byte_limit_exceeded"):
        validate_candidate_list([candidate(f"src/{i}.py", "界" * 90_000) for i in range(6)])


def test_wire_contract_rejects_project_maintenance_and_extra_fields():
    adapter = TypeAdapter(_COMPLIANCE_PREFLIGHT)
    good = {"request": request(candidate())}
    assert adapter.validate_json(json.dumps(good)).request.policy_scope == "generic_project"
    for invalid in [
        {"request": {**good["request"], "policy_scope": "skill_maintenance"}},
        {"request": {**good["request"], "unexpected": True}},
        {"request": request(candidate("/escape"))},
    ]:
        with pytest.raises(ValidationError):
            adapter.validate_json(json.dumps(invalid))


def test_product_cannot_enable_repository_document_policy(tmp_path):
    with pytest.raises(ValueError, match="allowed_scopes_invalid"):
        CompliancePreflightService(tmp_path, {"skill_maintenance"})


def test_unconfigured_reader_does_not_probe_candidate_paths():
    parsed = TypeAdapter(_COMPLIANCE_PREFLIGHT).validate_python({"request": request(candidate())})
    result = validate_decoupling_compliance(None, parsed.request)
    assert result["status"] == "unknown"
    assert result["limits"]["direct_targets_read"] == 0


def test_generic_service_checks_baselines_without_writing_or_reading_document_links(tmp_path):
    path = tmp_path / "src/existing.py"
    path.parent.mkdir()
    path.write_text("before")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    proposed = candidate(
        "src/existing.py",
        "[missing](no-such-file.md)",
        "replace",
        {"state": "sha256", "value": digest},
    )
    with CompliancePreflightService(tmp_path, {"generic_project"}) as service:
        result = service.validate(request(proposed))
        assert result["status"] == "pass"
        assert result["limits"]["direct_targets_read"] == 0
        assert all(
            item["rule_id"] not in {"bilingual_mirror", "layer01_structure"}
            for item in result["checks"]
        )
        assert path.read_text() == "before"
        path.write_text("concurrent change")
        assert service.validate(request(proposed))["status"] == "fail"


def test_absent_create_and_existing_delete_stay_read_only(tmp_path):
    path = tmp_path / "existing.txt"
    path.write_text("retained")
    deletion = candidate(
        "existing.txt",
        None,
        "delete",
        {"state": "sha256", "value": hashlib.sha256(path.read_bytes()).hexdigest()},
    )
    with CompliancePreflightService(tmp_path, {"generic_project"}) as service:
        assert service.validate(request(candidate("new.txt"), deletion))["status"] == "pass"
    assert path.read_text() == "retained"
    assert not (tmp_path / "new.txt").exists()


@pytest.mark.skipif(not hasattr(os, "symlink"), reason="symlinks unavailable")
def test_intermediate_and_candidate_symlinks_fail_closed(tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "existing").write_text("secret")
    trusted = tmp_path / "trusted"
    trusted.mkdir()
    (trusted / "link").symlink_to(outside, target_is_directory=True)
    (trusted / "file").symlink_to(outside / "existing")
    with CompliancePreflightService(trusted, {"generic_project"}) as service:
        for item in [candidate("link/new"), candidate("file")]:
            assert service.validate(request(item))["status"] != "pass"
    assert not (outside / "new").exists()


def test_closed_and_disallowed_services_remain_unknown(tmp_path):
    service = CompliancePreflightService(tmp_path, {"generic_project"})
    service.close()
    assert service.validate(request(candidate()))["status"] == "unknown"
    with CompliancePreflightService(tmp_path, set()) as disabled:
        assert disabled.validate(request(candidate()))["status"] == "unknown"


def test_output_budget_cannot_report_a_complete_pass():
    checks = [{"rule_id": str(i), "status": "pass"} for i in range(MAX_OUTPUT_CHECKS + 1)]
    result = build_result("generic_project", checks)
    assert result["limits"]["checks_truncated"]
    assert len(result["checks"]) == MAX_OUTPUT_CHECKS
    assert result["status"] == "unknown"
