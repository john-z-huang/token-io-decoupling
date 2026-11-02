from __future__ import annotations

import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import ValidationError
from token_io_decoupling_core.materialization_models import FactOrderingPlan

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "support"))
import benchmark_cases as cases  # ty: ignore[unresolved-import]


class _FakeRecorder:
    def __init__(
        self,
        outcomes: dict[str, list[str]] | None = None,
        contents: dict[str, str | list[str]] | None = None,
        fail_caller: bool = False,
    ) -> None:
        self.outcomes = outcomes or {}
        self.contents = contents or {}
        self.fail_caller = fail_caller
        self.calls: list[dict[str, object]] = []
        self.response_schemas: list[str] = []
        self.decision_choices: list[str] = []
        self.http_attempts = 0

    def make_client(self, *, case_id: str, arm: str, component: str, timeout: float):
        del timeout
        owner = self

        class Responses:
            def parse(self, **kwargs):
                if component == "caller" and owner.fail_caller:
                    from openai import OpenAIError

                    raise OpenAIError("fake caller API failure")
                text_format = kwargs["text_format"]
                owner.response_schemas.append(getattr(text_format, "__name__", str(text_format)))
                if text_format is cases._case_judgment_model(case_id):
                    assert kwargs["max_output_tokens"] == 4_000
                    sequence = owner.outcomes.get(case_id, [cases._CASES[case_id]["expected"]])
                    index = sum(
                        1
                        for call in owner.calls
                        if call.get("case_id") == case_id and call.get("component") == component
                    )
                    outcome = sequence[min(index, len(sequence) - 1)]
                    configured_content = owner.contents.get(case_id, "## Facts\n\n- source fact\n")
                    if isinstance(configured_content, list):
                        final_content = configured_content[min(index, len(configured_content) - 1)]
                    else:
                        final_content = configured_content
                    if case_id != "primary_skill_fact_markdown_apply":
                        final_content = ""
                    response = SimpleNamespace(
                        status="completed",
                        output_parsed=text_format(
                            outcome=outcome,
                            final_content=final_content,
                            rationale="bounded fake response",
                        ),
                    )
                elif text_format is FactOrderingPlan:
                    parsed = FactOrderingPlan(files=[{"file_index": 0, "fact_ids": ["fact-1"]}])
                    response = SimpleNamespace(
                        status="completed",
                        model="gpt-6-luna",
                        error=None,
                        incomplete_details=None,
                        output_parsed=parsed,
                    )
                else:
                    response = SimpleNamespace(
                        status="completed",
                        model="gpt-6-luna",
                        error=None,
                        incomplete_details=None,
                        output_parsed=text_format(
                            files=[{"file_index": 0, "fact_ids": ["fact-1"]}]
                        ),
                    )
                owner.calls.append(
                    {"case_id": case_id, "arm": arm, "component": component, "status": "success"}
                )
                return response

        class Decisions:
            def create(self, **_kwargs):
                owner.decision_choices.append("work_definition")
                owner.calls.append(
                    {"case_id": case_id, "arm": arm, "component": component, "status": "success"}
                )
                answer = SimpleNamespace(
                    type="choice", name="workflow_stage", choice="work_definition"
                )
                return SimpleNamespace(model="gpt-6-luna", answers=[answer])

        class Client:
            responses = Responses()
            decisions = Decisions()

            def close(self):
                return None

        return Client()


def _fake_rule(*_args):
    return {"status": "complete", "full_or_bounded": "verified owner context"}, {}


def _fake_route(_case_id, arm, _repo_root, _recorder):
    return {
        "request": {"stage": "auto"},
        "result": {"status": "available", "module_id": "MM03", "arm": arm},
    }, {"service": 0.001}


def _fake_materialization(_case_id, arm, root, _repo_root, _recorder, component_calls=None):
    content = "## Facts\n\n- source fact\n"
    output = root / "project" / "docs" / "skill-output.md"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(content.encode("utf-8"))
    result = {
        "prepare": {"status": "prepared"},
        "inspect": {"status": "inspected"},
        "apply": {"status": "applied"},
        "actual_content": content,
    }
    call = cases._component_call(
        "materialize_decoupled_output",
        {"request": {"action": "prepare"}},
        {"status": "prepared"},
        0.001,
        "prepared",
    )
    result["component_calls"] = [call]
    if component_calls is not None:
        component_calls.append(call)
    return result, {"service": 0.001, "apply": 0.001}, content


@pytest.mark.parametrize("case_id", cases.CASE_IDS)
@pytest.mark.parametrize("arm", ["baseline", "assisted"])
def test_all_fixed_cases_have_oracle_checked_fake_arms(tmp_path, monkeypatch, case_id, arm):
    repo_root = Path(__file__).resolve().parents[3]
    temporary_root = tmp_path / "isolated"
    temporary_root.mkdir()
    recorder = _FakeRecorder()
    monkeypatch.setattr(cases, "_rule_service", _fake_rule)
    monkeypatch.setattr(cases, "_routing_service", _fake_route)
    monkeypatch.setattr(cases, "_materialization_service", _fake_materialization)

    row = cases.run_case(case_id, arm, recorder, repo_root, temporary_root)

    assert row["case_id"] == case_id
    assert row["arm"] == arm
    assert row["semantic_success"] is True, (
        row["observed"],
        row["workflow_completed"],
        cases._CASES[case_id]["expected"],
        cases._CASES[case_id]["workflow_completed_on_correct_answer"],
        [
            key
            for key in row["source_hashes"]["before"]["hashes"]
            if row["source_hashes"]["before"]["hashes"][key]
            != row["source_hashes"]["after"]["hashes"].get(key)
        ],
        row["service_status"],
    )
    assert row["first_attempt_success"] is True
    assert (
        row["workflow_completed"] is cases._CASES[case_id]["workflow_completed_on_correct_answer"]
    )
    assert row["source_hashes"]
    assert row["source_hashes"]["stable"] is True
    assert "elapsed" in row["timings"]
    assert row["http_attempts"] == 0
    if case_id == "primary_skill_fact_markdown_apply":
        expected_state_service = "not_used" if arm == "baseline" else "real_test_instance"
        assert row["execution_context"] == {
            "state_service": expected_state_service,
            "host_binding": (
                "synthetic_fixture_not_used" if arm == "baseline" else "synthetic_test_fixture"
            ),
            "operator_grant": (
                "synthetic_fixture_not_used" if arm == "baseline" else "synthetic_test_fixture"
            ),
            "effect_executor": "isolated_harness"
            if arm == "baseline"
            else "materialization_service",
            "temporary_root": "isolated_per_case_arm",
            "production_authorization": False,
        }
    if case_id == "generic_create_preflight_pass" and arm == "assisted":
        assert row["service_status"] == "pass"
    if case_id == "skill_cross_language_preflight_fail" and arm == "assisted":
        assert row["service_status"] == "fail"
        assert row["workflow_completed"] is False


def test_caller_repair_is_bounded_to_one_semantic_attempt(tmp_path):
    recorder = _FakeRecorder(
        {
            "rules_current_verification": [
                "verification_not_required",
                "verification_required",
                "verification_not_required",
            ]
        }
    )
    case = cases._CASES["rules_current_verification"]
    judgment, repair_count, _prompt_hash, _elapsed = cases._call_judge(
        recorder, "rules_current_verification", "baseline", case, {"evidence": "same"}
    )
    assert judgment.outcome == "verification_required"
    assert repair_count == 1
    assert len(recorder.calls) == 2


def test_wrong_answer_after_one_repair_fails_frozen_oracle(tmp_path, monkeypatch):
    repo_root = Path(__file__).resolve().parents[3]
    temporary_root = tmp_path / "isolated"
    temporary_root.mkdir()
    monkeypatch.setattr(cases, "_rule_service", _fake_rule)
    recorder = _FakeRecorder({"rules_current_verification": ["verification_not_required"] * 2})
    row = cases.run_case(
        "rules_current_verification", "baseline", recorder, repo_root, temporary_root
    )
    assert row["semantic_success"] is False
    assert row["first_attempt_success"] is False
    assert row["repair_count"] == 1


def test_case_schema_rejects_valid_outcomes_from_other_cases_and_repairs_valid_wrong_choice():
    verification_model = cases._case_judgment_model("rules_current_verification")
    preflight_model = cases._case_judgment_model("generic_create_preflight_pass")
    with pytest.raises(ValidationError):
        preflight_model(
            outcome="verification_required",
            rationale="cross-case outcome",
        )

    recorder = _FakeRecorder({"generic_create_preflight_pass": ["fail", "pass"]})
    judgment, repair_count, _prompt_hashes, _elapsed = cases._call_judge(
        recorder,
        "generic_create_preflight_pass",
        "baseline",
        cases._CASES["generic_create_preflight_pass"],
        {"evidence": "structural rule result"},
    )

    assert (
        "verification_required"
        in verification_model.model_json_schema()["properties"]["outcome"]["enum"]
    )
    assert (
        "verification_required"
        not in preflight_model.model_json_schema()["properties"]["outcome"]["enum"]
    )
    assert judgment.outcome == "pass"
    assert repair_count == 1


def test_each_case_arm_uses_a_fresh_temporary_root(tmp_path, monkeypatch):
    repo_root = Path(__file__).resolve().parents[3]
    temporary_root = tmp_path / "isolated"
    temporary_root.mkdir()
    monkeypatch.setattr(cases, "_rule_service", _fake_rule)
    recorder = _FakeRecorder()
    first = cases.run_case(
        "rules_current_verification", "baseline", recorder, repo_root, temporary_root
    )
    assert first["semantic_success"] is True
    with pytest.raises(FileExistsError):
        cases.run_case(
            "rules_current_verification", "baseline", recorder, repo_root, temporary_root
        )
    other_arm = cases.run_case(
        "rules_current_verification", "assisted", recorder, repo_root, temporary_root
    )
    assert other_arm["semantic_success"] is True


def test_materialization_case_uses_real_service_prepare_inspect_apply(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-only-canary")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://benchmark.invalid/v1")
    repo_root = Path(__file__).resolve().parents[3]
    recorder = _FakeRecorder()
    with tempfile.TemporaryDirectory(dir="/private/tmp") as safe_tmp:
        case_root = Path(safe_tmp) / "case-root"
        case_root.mkdir()
        result, timings, expected = cases._materialization_service(
            "primary_skill_fact_markdown_apply",
            "assisted",
            case_root,
            repo_root,
            recorder,
        )
    assert result["prepare"]["status"] == "prepared"
    assert result["inspect"]["content"] == expected
    assert result["apply"]["status"] == "applied"
    assert result["actual_content"] == expected
    assert timings["apply"] >= 0
    assert any(call["component"] == "inner" for call in recorder.calls)


def test_multi_agent_routing_service_uses_current_locked_route(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-only-canary")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://benchmark.invalid/v1")
    repo_root = Path(__file__).resolve().parents[3]
    recorder = _FakeRecorder()
    result, timings = cases._routing_service(
        "multi_auto_work_definition", "assisted", repo_root, recorder
    )
    assert result["request"]["mode_locked"] is True
    assert result["request"]["mode_count"] == {"mode": "Multi-Agent Coding", "child_count": 1}
    assert result["request"]["stage"] == "auto"
    assert result["result"]["module_id"] == "MM03", (
        result["result"]["status"],
        result["result"]["reason"],
        recorder.calls,
    )
    assert [fact["statement"] for fact in result["request"]["source_facts"]] == cases._CASES[
        "multi_auto_work_definition"
    ]["facts"]
    assert timings["service"] >= 0
    assert recorder.calls == [
        {
            "case_id": "multi_auto_work_definition",
            "arm": "assisted",
            "component": "inner",
            "status": "success",
        }
    ]


def test_routing_baseline_loads_complete_l4_sources():
    repo_root = Path(__file__).resolve().parents[3]
    result, timings = cases._routing_service(
        "multi_auto_work_definition", "baseline", repo_root, _FakeRecorder()
    )
    sources = result["full_l4_source"]
    expected_paths = {
        "docs/skill/references/coding/layer-04-workflows/coding-multi-agent.md",
        "docs/skill/references/coding/layer-04-workflows/modules/work-definition.md",
    }

    assert set(sources) == expected_paths
    assert all(sources[path] == (repo_root / path).read_text(encoding="utf-8") for path in sources)
    assert timings["service"] >= 0


def test_rule_service_returns_verification_owner_and_complete_requested_closure():
    repo_root = Path(__file__).resolve().parents[3]
    full, _ = cases._rule_service(
        "rules_current_verification", "baseline", repo_root, _FakeRecorder()
    )
    bundle, _ = cases._rule_service(
        "rules_current_verification", "assisted", repo_root, _FakeRecorder()
    )
    assert full.node_id == "verification"
    assert full.owner_path.endswith("verification.md")
    assert bundle.complete is True
    assert {item.fragment_id for item in bundle.fragments} >= {
        "verification.actions",
        "verification.pass",
        "verification.boundary",
    }


def test_baseline_materialization_wrong_content_fails_same_frozen_oracle(tmp_path):
    repo_root = Path(__file__).resolve().parents[3]
    temporary_root = tmp_path / "isolated"
    temporary_root.mkdir()
    recorder = _FakeRecorder(contents={"primary_skill_fact_markdown_apply": "wrong bytes\n"})
    row = cases.run_case(
        "primary_skill_fact_markdown_apply", "baseline", recorder, repo_root, temporary_root
    )
    assert row["observed"] == "exact_content"
    assert row["semantic_success"] is False
    assert row["workflow_completed"] is False
    assert row["workflow_completion_status"] == "not_applied"
    assert row["workflow_completion_reason"] == "target_file_absent"
    assert row["expected_content_sha256"] == cases._EXPECTED_CONTENT_SHA256
    assert row["observed_content_sha256"] is None
    assert not (
        temporary_root
        / "primary_skill_fact_markdown_apply"
        / "baseline"
        / "project"
        / "docs"
        / "skill-output.md"
    ).exists()


def test_materialization_same_outcome_repairs_exact_content(tmp_path, monkeypatch):
    repo_root = Path(__file__).resolve().parents[3]
    temporary_root = tmp_path / "isolated"
    temporary_root.mkdir()
    monkeypatch.setattr(cases, "_rule_service", _fake_rule)
    recorder = _FakeRecorder(
        outcomes={"primary_skill_fact_markdown_apply": ["exact_content"] * 2},
        contents={"primary_skill_fact_markdown_apply": ["wrong bytes\n", cases._EXPECTED_CONTENT]},
    )

    row = cases.run_case(
        "primary_skill_fact_markdown_apply", "baseline", recorder, repo_root, temporary_root
    )

    assert row["observed"] == "exact_content"
    assert row["repair_count"] == 1
    assert row["semantic_success"] is True
    assert row["workflow_completed"] is True
    assert row["observed_content_sha256"] == cases._EXPECTED_CONTENT_SHA256


def test_materialization_oracle_is_independent_of_dataset_content():
    case = cases._CASES["primary_skill_fact_markdown_apply"]
    assert case["expected_content_utf8"].encode("utf-8") == cases._EXPECTED_CONTENT_BYTES
    assert cases._sha(cases._EXPECTED_CONTENT_BYTES) == cases._EXPECTED_CONTENT_SHA256
    assert case["expected_content_sha256"] == cases._EXPECTED_CONTENT_SHA256
    assert case["template_contract"]["facts"] == [
        {"id": "fact-1", "heading_id": "facts", "text": "source fact"}
    ]


def test_baseline_completion_is_derived_after_exact_harness_write(tmp_path):
    repo_root = Path(__file__).resolve().parents[3]
    temporary_root = tmp_path / "isolated"
    temporary_root.mkdir()
    case_id = "primary_skill_fact_markdown_apply"
    recorder = _FakeRecorder()

    row = cases.run_case(case_id, "baseline", recorder, repo_root, temporary_root)

    output = temporary_root / case_id / "baseline" / "project" / "docs" / "skill-output.md"
    assert row["semantic_success"] is True
    assert row["workflow_completed"] is True
    assert row["workflow_completion_status"] == "complete"
    assert output.read_bytes() == cases._EXPECTED_CONTENT_BYTES


def test_assisted_apply_survives_caller_failure_as_filesystem_effect(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-only-canary")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://benchmark.invalid/v1")
    repo_root = Path(__file__).resolve().parents[3]
    temporary_root = tmp_path / "isolated"
    temporary_root.mkdir()
    case_id = "primary_skill_fact_markdown_apply"
    recorder = _FakeRecorder(fail_caller=True)

    row = cases.run_case(case_id, "assisted", recorder, repo_root, temporary_root)

    output = temporary_root / case_id / "assisted" / "project" / "docs" / "skill-output.md"
    assert output.read_bytes() == cases._EXPECTED_CONTENT_BYTES
    assert row["semantic_success"] is False
    assert row["failure_category"] == "caller_provider_error"
    assert row["workflow_completed"] is True
    assert row["workflow_completion_status"] == "complete"
    assert row["observed_content_sha256"] == cases._EXPECTED_CONTENT_SHA256
    assert [call["status"] for call in row["component_calls"]] == [
        "prepared",
        "inspected",
        "applied",
    ]
    assert row["api_calls"]
    assert all(call["component"] == "inner" for call in row["api_calls"])


def test_unreadable_materialization_effect_is_unknown_not_false(tmp_path, monkeypatch):
    root = tmp_path / "isolated"
    output = root / "project" / "docs" / "skill-output.md"
    output.parent.mkdir(parents=True)
    output.write_bytes(cases._EXPECTED_CONTENT_BYTES)
    original_read_bytes = Path.read_bytes

    def unreadable_target(path):
        if path == output:
            raise PermissionError("simulated unreadable target")
        return original_read_bytes(path)

    monkeypatch.setattr(Path, "read_bytes", unreadable_target)
    effect = cases._file_effect(root, "primary_skill_fact_markdown_apply")

    assert effect["workflow_completed"] is None
    assert effect["workflow_completion_status"] == "unknown"
    assert effect["workflow_completion_reason"] == "target_file_unreadable"
    assert effect["observed_content_sha256"] is None


def test_workflow_completion_is_not_a_model_judgment_field():
    model = cases._case_judgment_model("primary_skill_fact_markdown_apply")
    assert "workflow_completed" not in model.model_json_schema()["properties"]
    with pytest.raises(ValidationError):
        model(
            outcome="exact_content",
            workflow_completed=True,
            rationale="completion is derived from the filesystem",
        )


def test_repository_internal_temporary_root_is_rejected_before_directory_creation():
    repo_root = Path(__file__).resolve().parents[3]
    target_root = repo_root / "primary_skill_fact_markdown_apply" / "baseline"
    assert not target_root.exists()

    with pytest.raises(ValueError, match="benchmark_temporary_root_must_be_isolated"):
        cases.run_case(
            "primary_skill_fact_markdown_apply",
            "baseline",
            _FakeRecorder(),
            repo_root,
            repo_root,
        )

    assert not target_root.exists()


def test_service_call_metrics_survive_caller_failure(tmp_path, monkeypatch):
    repo_root = Path(__file__).resolve().parents[3]
    temporary_root = tmp_path / "isolated"
    temporary_root.mkdir()
    monkeypatch.setattr(cases, "_routing_service", _fake_route)
    monkeypatch.setattr(
        cases,
        "_call_judge",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("caller_provider_error")),
    )

    row = cases.run_case(
        "multi_auto_work_definition",
        "assisted",
        _FakeRecorder(),
        repo_root,
        temporary_root,
    )

    assert row["failure_category"] == "caller_provider_error"
    assert len(row["component_calls"]) == 1
    call = row["component_calls"][0]
    assert call["arguments_utf8_bytes"] > 0
    assert call["result_utf8_bytes"] > 0
    assert row["source_hashes"]["before"]["status"] == "readable"
    assert row["source_hashes"]["after"]["status"] == "readable"
    assert set(row["source_hashes"]["before"]["hashes"]) == set(
        row["source_hashes"]["after"]["hashes"]
    )


def test_blocked_materialization_prepare_retains_nonzero_call_metrics(tmp_path, monkeypatch):
    repo_root = Path(__file__).resolve().parents[3]
    temporary_root = tmp_path / "isolated"
    temporary_root.mkdir()

    def blocked_prepare(_case_id, _arm, _root, _repo_root, _recorder, component_calls):
        request = {"action": "prepare"}
        result = {"status": "blocked", "reason_code": "preflight_blocked"}
        component_calls.append(
            cases._component_call(
                "materialize_decoupled_output",
                {"request": request},
                result,
                0.001,
                "blocked",
            )
        )
        return (
            {"prepare": result, "apply": {"status": "blocked"}},
            {"service": 0.001, "apply": 0.0},
            "",
        )

    monkeypatch.setattr(cases, "_materialization_service", blocked_prepare)
    row = cases.run_case(
        "primary_skill_fact_markdown_apply",
        "assisted",
        _FakeRecorder(),
        repo_root,
        temporary_root,
    )

    assert row["service_status"] == "blocked"
    assert len(row["component_calls"]) == 1
    assert row["component_calls"][0]["arguments_utf8_bytes"] > 0
    assert row["component_calls"][0]["result_utf8_bytes"] > 0
    assert row["component_calls"][0]["status"] == "blocked"
    assert row["workflow_completed"] is False


def test_source_fingerprint_read_failure_is_explicit_and_never_stable(tmp_path, monkeypatch):
    repo_root = Path(__file__).resolve().parents[3]
    temporary_root = tmp_path / "isolated"
    temporary_root.mkdir()
    monkeypatch.setattr(cases, "_rule_service", _fake_rule)
    original_sha = cases._sha
    failed = False

    def fail_first_fingerprint(data):
        nonlocal failed
        if not failed:
            failed = True
            raise OSError("simulated unreadable source")
        return original_sha(data)

    monkeypatch.setattr(cases, "_sha", fail_first_fingerprint)
    row = cases.run_case(
        "rules_current_verification",
        "baseline",
        _FakeRecorder(),
        repo_root,
        temporary_root,
    )

    before = row["source_hashes"]["before"]
    after = row["source_hashes"]["after"]
    assert before["status"] == "unreadable"
    assert before["unreadable_paths"]
    assert before["hashes"]
    assert after["status"] == "readable"
    assert row["source_hashes"]["stable"] is False
    assert row["semantic_success"] is False


def test_full_fixed_matrix_with_real_services_and_fake_api_only(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-only-canary")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://benchmark.invalid/v1")
    repo_root = Path(__file__).resolve().parents[3]
    temporary_root = tmp_path / "integrated"
    temporary_root.mkdir()
    recorder = _FakeRecorder()
    rows = {}

    for case_id in cases.CASE_IDS:
        for arm in ("baseline", "assisted"):
            rows[(case_id, arm)] = cases.run_case(case_id, arm, recorder, repo_root, temporary_root)

    assert len(rows) == 10
    for (case_id, arm), row in rows.items():
        assert row["semantic_success"] is True, (case_id, arm, row)
        assert row["first_attempt_success"] is True
        assert row["observed"] == row["expected"]
        assert row["source_hashes"]["stable"] is True
        assert row["source_hashes"]["before"]["status"] == "readable"
        assert row["source_hashes"]["after"]["status"] == "readable"
        assert row["http_attempts"] == 0
        if arm == "assisted":
            assert row["component_calls"]

    materialization_id = "primary_skill_fact_markdown_apply"
    for arm in ("baseline", "assisted"):
        row = rows[(materialization_id, arm)]
        if arm == "assisted":
            assert [call["status"] for call in row["component_calls"]] == [
                "prepared",
                "inspected",
                "applied",
            ]
        output = temporary_root / materialization_id / arm / "project" / "docs" / "skill-output.md"
        assert output.read_bytes() == cases._EXPECTED_CONTENT_BYTES
        assert row["observed_content_sha256"] == cases._EXPECTED_CONTENT_SHA256

    assert "FactOrderingPlan" in recorder.response_schemas
    assert any(schema.startswith("CaseJudgment_") for schema in recorder.response_schemas)
    assert "work_definition" in recorder.decision_choices
