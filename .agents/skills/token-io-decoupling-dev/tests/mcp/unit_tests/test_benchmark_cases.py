"""Current service regressions and explicit retirement of historical measurements."""

from __future__ import annotations

import hashlib

import pytest
from support import benchmark_cases as cases
from support.event_cases import checker, request

from token_io_decoupling_tools.compliance_preflight import (
    CompliancePreflightService,
    validate_decoupling_compliance,
)
from token_io_decoupling_workflow.rules import RuleLoader


class _ForbiddenRecorder:
    def make_client(self, **_kwargs):
        raise AssertionError("retired cases cannot create a client")


def test_historical_dataset_and_reports_remain_read_only_and_explicitly_retired(tmp_path):
    archives = list(cases.DATASET_PATH.parent.rglob("*.json"))
    before = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in archives}
    assert cases.PROTOCOL_STATUS == "retired"
    assert ".agents/skills/token-io-decoupling-dev/benchmarks" in str(cases.DATASET_PATH)
    assert len(cases.CASE_IDS) == 5
    for case_id in cases.CASE_IDS:
        for arm in ("baseline", "assisted"):
            result = cases.run_case(
                case_id, arm, _ForbiddenRecorder(), tmp_path, tmp_path / "unused"
            )
            assert result["execution_status"] == "not_applicable"
            assert result["reason"] == "retired_benchmark_protocol"
            assert result["semantic_success"] is None
            assert result["api_calls"] == []
            assert result["http_attempts"] == 0
            assert result["token_comparison_valid"] is False
    assert before == {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in archives}
    assert not (tmp_path / "unused").exists()


@pytest.mark.parametrize("case_id", sorted(cases.REMOVED_PRODUCT_CASES))
def test_removed_project_skill_cases_never_become_product_measurements(tmp_path, case_id):
    result = cases.run_case(case_id, "assisted", _ForbiddenRecorder(), tmp_path, tmp_path)
    assert result["product_capability_removed"] is True
    assert result["workflow_completed"] is None
    with pytest.raises(ValueError, match="unknown historical"):
        cases.run_case("invented-case", "assisted", _ForbiddenRecorder(), tmp_path, tmp_path)


def test_current_rule_lookup_returns_complete_compiled_instructions_without_source_access(tmp_path):
    bundle = RuleLoader(repository_root=tmp_path / "absent-author-tree").load_context_bundle(
        "verification"
    )
    assert bundle.complete and bundle.schema_version == 2
    assert bundle.fragments and bundle.fragments[0].text
    assert bundle.remaining_owner_refs == []
    assert bundle.node_metadata.owner_path.startswith("compiled:")


def test_current_event_returns_current_instructions_without_api_or_owner_lookup(monkeypatch):
    """基准入口直接返回当前编译事件，不请求模型或要求跟读作者文件。"""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    result = checker().check(request("action_observed"))
    assert result.status == "checked"
    assert result.instructions is not None and result.instructions.complete
    assert result.instructions.event.text
    assert result.advice.status == "not_requested"
    assert result.authority == "advisory_only"


def test_current_generic_preflight_is_read_only_and_retired_scope_is_rejected(tmp_path):
    service = CompliancePreflightService(tmp_path, {"generic_project"})
    request = {
        "policy_scope": "generic_project",
        "candidates": [
            {
                "path": "summary.txt",
                "operation": "create",
                "baseline": {"state": "absent"},
                "content": "current generic candidate\n",
            }
        ],
    }
    try:
        result = validate_decoupling_compliance(service, request)
        assert result["status"] == "pass"
        assert not (tmp_path / "summary.txt").exists()
        with pytest.raises(ValueError):
            validate_decoupling_compliance(
                service, {**request, "policy_scope": "skill_maintenance"}
            )
    finally:
        service.close()
