"""Current service regressions and explicit retirement of historical measurements."""

from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path

import pytest
from support import benchmark_cases as cases

from token_io_decoupling_core.materialization_models import MaterializationInspectRequest
from token_io_decoupling_core.models import CodingMode
from token_io_decoupling_core.rules import RuleLoader
from token_io_decoupling_workflow.compliance_preflight import (
    CompliancePreflightService,
    validate_decoupling_compliance,
)
from token_io_decoupling_workflow.workflow_routing import (
    DecouplingWorkflowRequest,
    WorkflowRouter,
    source_facts_hash,
)


class _ForbiddenRecorder:
    def make_client(self, **_kwargs):
        raise AssertionError("retired cases cannot create a client")


def _materialization_fixture():
    fixture = Path(__file__).with_name("test_output_materialization.py")
    spec = importlib.util.spec_from_file_location(
        "_current_generic_materialization_fixture", fixture
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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


def test_current_explicit_routing_returns_current_step_without_api_or_owner_lookup(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    request = DecouplingWorkflowRequest.model_validate(
        {
            "task_id": "synthetic-current-routing-regression",
            "task_summary": "Inspect the explicitly requested current stage.",
            "stage": "execution",
            "language": "en",
            "mode_locked": True,
            "mode_count": {"mode": CodingMode.SINGLE_AGENT, "child_count": 0},
            "capabilities": [],
            "hard_constraints": [],
            "source_facts": [],
            "source_facts_hash": source_facts_hash([]),
            "outbound_data_permitted": False,
        }
    )
    result = WorkflowRouter(RuleLoader(), None).decide(request)
    assert result.status == "available"
    assert result.instructions is not None
    assert result.instructions["module_id"] == "SM04"
    assert result.instructions["text"]
    assert result.advisory_only is True


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


def test_current_generic_code_materialization_keeps_prepare_inspect_preflight_apply_guards(
    tmp_path,
):
    fixture = _materialization_fixture()
    project, _artifacts, _binding, _provider, preflight, _grant, _config, materializer = (
        fixture._workspace(tmp_path, ["src/current.txt"])
    )
    try:
        prepared = materializer.execute(
            fixture._literal_prepare("src/current.txt", "current code output\n")
        )
        assert prepared["status"] == "prepared"
        assert not (project / "src/current.txt").exists()
        inspected = materializer.execute(
            MaterializationInspectRequest(
                action="inspect",
                prepared_id=prepared["prepared_id"],
                expected_manifest_hash=prepared["manifest_sha256"],
                file_index=0,
                max_chars=8192,
            )
        )
        assert inspected["complete"] is True
        assert inspected["content"] == "current code output\n"
        applied = fixture._apply(materializer, prepared)
        assert applied["status"] == "applied"
        assert applied["fresh_preflight"] == "pass"
        assert (project / "src/current.txt").read_text() == "current code output\n"
    finally:
        materializer.close()
        preflight.close()
