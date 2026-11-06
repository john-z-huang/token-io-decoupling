"""检查事件只交付规则和建议，不替 Agent 保存或推进任务。"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
from pydantic import ValidationError
from support.compiled_resources import CompiledResources
from support.event_cases import EVENT_REQUIREMENTS, checker, request, request_data

from token_io_decoupling_workflow.events.models import EventCheckPayload, canonical_event_json
from token_io_decoupling_workflow.rules import RuleLoader, RuleLoadError


def forbidden_client(_key, _url):
    """静态测试若越过网络建议边界立即失败，防止默认路径偷偷请求模型。"""
    raise AssertionError("static rule delivery must never create an API client")


@pytest.mark.parametrize("event", EVENT_REQUIREMENTS)
@pytest.mark.parametrize("language", ["zh_cn"])
def test_each_event_delivers_shared_and_current_instructions_without_api(event, language):
    """六类事件都必须交付共享与当前政策，并在默认静态路径完全避开模型。"""
    result = checker(factory=forbidden_client).check(request(event, language=language))
    facts, evidence = EVENT_REQUIREMENTS[event]
    assert result.status == "checked"
    assert result.instructions.complete
    assert result.instructions.workflow is None
    current = result.instructions.event
    assert set(current.instruction_ids) == {"common.shared", f"event.{event}"}
    assert current.required_facts == facts
    assert current.required_evidence == evidence
    assert result.structural_check.status == "ready_for_agent_review"
    assert result.structural_check.authority == "structural_check_only"
    assert result.advice.status == "not_requested"
    assert result.authority == "advisory_only"


@pytest.mark.parametrize("mode", ["single-agent", "multi-agent"])
@pytest.mark.parametrize("event", EVENT_REQUIREMENTS)
def test_selected_short_workflow_uses_the_same_build_and_shared_budget(event, mode):
    """两个模式的短流程均来自同批资源，并与事件共享完整交付容量。"""
    result = checker().check(request(event, mode=mode, include_workflow=True))
    instructions = result.instructions
    assert result.status == "checked"
    assert instructions.complete
    assert instructions.event.build_id == instructions.workflow.build_id
    assert instructions.workflow.mode == mode
    assert instructions.text_characters == (
        len(instructions.event.text) + len(instructions.workflow.text)
    )
    assert instructions.text_characters <= instructions.text_budget


def test_workflow_requires_an_explicit_mode_and_never_guesses_from_context():
    """上下文文字不能替代明确模式；请求流程而不选模式必须拒绝。"""
    with pytest.raises(ValidationError, match="requires an explicit mode"):
        request(include_workflow=True, context_summary="This is a multi-agent task.")
    result = checker().check(request(context_summary="This is a multi-agent task."))
    assert result.mode is None
    assert result.instructions.workflow is None


@pytest.mark.parametrize("budget", [256, 1200])
def test_insufficient_budget_delivers_no_partial_instruction_or_model_call(budget):
    """容量低于完整政策时两份正文均为空，语义请求也不能发生。"""
    result = checker(enabled=True, outbound=True, factory=forbidden_client).check(
        request(
            "boundary_requested",
            max_chars=budget,
            mode="multi-agent",
            include_workflow=True,
            semantic_input={"outbound_data_permitted": True},
        )
    )
    assert result.status == "instructions_incomplete"
    assert result.instructions.complete is False
    assert result.instructions.text_characters == 0
    assert result.instructions.event.text == ""
    assert result.instructions.workflow.text == ""
    assert result.structural_check.status == "not_evaluated"
    assert result.advice.status == "unavailable"
    assert result.advice.suggested_outcome is None


def test_missing_completion_evidence_cannot_become_success_from_other_event_results():
    """其他事件的就绪状态不能替代当前完成证据，服务也不能宣布任务完成。"""
    service = checker()
    service.check(request("action_observed"))
    result = service.check(request("completion_requested", evidence_refs=[]))
    assert result.structural_check.status == "incomplete_for_agent_review"
    assert result.structural_check.missing_evidence == ["verification_result", "final_state"]
    assert result.advice.suggested_outcome is None
    assert "acceptance" in result.instructions.event.required_facts
    assert "服务不宣布任务完成" in result.instructions.event.text


@pytest.mark.parametrize("fact_status", ["unknown", "not_applicable"])
def test_missing_resume_context_remains_unresolved_even_with_an_explanation(fact_status):
    """unknown 或不适用解释仍需 Agent 复核，不能据此恢复丢失的会话状态。"""
    data = request_data("session_resumed")
    data["facts"]["retained_context"] = {"status": fact_status, "value": "lost context"}
    result = checker().check(request(**data))
    assert result.structural_check.status == "incomplete_for_agent_review"
    assert result.structural_check.missing_facts == ["retained_context"]
    assert result.structural_check.unresolved_fact_statuses == {"retained_context": fact_status}


@pytest.mark.parametrize("expected", ["expected_build_id", "expected_rule_hash"])
def test_stale_requested_instruction_identity_blocks_judgment_and_api(expected):
    """调用方钉住的 build 或规则已过期时，既不作结构判断也不请求建议。"""
    result = checker(enabled=True, outbound=True, factory=forbidden_client).check(
        request(**{expected: "0" * 64, "semantic_input": {"outbound_data_permitted": True}})
    )
    assert result.status == "stale"
    assert result.structural_check.status == "not_evaluated"
    assert result.advice.status == "stale"
    assert result.advice.suggested_outcome is None


def test_missing_or_mixed_rules_are_unavailable_without_author_source_fallback(monkeypatch):
    """缺失事件或混批短流程均不可执行，不能从作者目录补回内容。"""
    rules = RuleLoader(repository_root=Path("/missing-author-tree"))
    original = rules.load_workflow

    def mixed(*args, **kwargs):
        return original(*args, **kwargs).model_copy(update={"build_id": "0" * 64})

    monkeypatch.setattr(rules, "load_workflow", mixed)
    result = checker(rules=rules).check(request(mode="single-agent", include_workflow=True))
    assert result.status == "rules_unavailable"
    assert result.instructions is None
    assert result.structural_check.status == "not_evaluated"

    def missing(*_args, **_kwargs):
        raise RuleLoadError("required event unavailable")

    monkeypatch.setattr(rules, "load_event", missing)
    result = checker(rules=rules).check(request())
    assert result.status == "rules_unavailable"
    assert result.instructions is None


def test_repeated_checks_are_stateless_and_do_not_write_files(monkeypatch, tmp_path):
    """重复相同事件必须得到相同结果，临时工作目录也不能出现运行记录。"""
    service = checker()
    first = service.check(request())
    monkeypatch.chdir(tmp_path)

    def no_write(*_args, **_kwargs):
        raise AssertionError("event checks cannot persist workflow state")

    monkeypatch.setattr(Path, "write_bytes", no_write)
    monkeypatch.setattr(Path, "write_text", no_write)
    monkeypatch.setattr(Path, "mkdir", no_write)
    service.check(request("completion_requested", facts={}, evidence_refs=[]))
    second = service.check(request())
    assert first == second
    assert list(tmp_path.iterdir()) == []
    encoded = canonical_event_json(request().model_dump(mode="json"))
    assert first.input_hash == hashlib.sha256(encoded.encode()).hexdigest()


@pytest.mark.parametrize("corruption", ["missing_event", "invalid_outcome", "missing_shared"])
def test_corrupt_packaged_event_is_not_delivered_as_executable_rules(
    tmp_path, monkeypatch, corruption
):
    """固定元数据、允许结果或共享依赖被破坏时，不得交付可执行事件。"""
    staged = CompiledResources(tmp_path, monkeypatch)
    if corruption == "missing_event":
        del staged.document["events"]["task_received"]
    elif corruption == "invalid_outcome":
        staged.document["events"]["task_received"]["allowed_outcomes"] = ["allow"]
    else:
        staged.document["events"]["task_received"]["instruction_ids"] = ["event.task_received"]
    staged.save()
    result = checker().check(request())
    assert result.status == "rules_unavailable"
    assert result.structural_check.status == "not_evaluated"


@pytest.mark.parametrize(
    "changes",
    [
        {"stage": "execution"},
        {"next_stage": "completion"},
        {"session_id": "persist-me"},
        {"event": "implementation"},
        {"mode": "auto"},
        {"max_chars": True},
        {"semantic_input": {"outbound_data_permitted": "yes"}},
        {"facts": {"task": {"value": "  "}}},
        {"facts": {"task": {"status": "not_applicable"}}},
        {"facts": {"Task": {"value": "bad key"}}},
    ],
)
def test_request_rejects_stage_controls_coercion_and_ambiguous_facts(changes):
    """拒绝阶段控制、隐式类型转换和含糊事实，避免请求变成状态机命令。"""
    with pytest.raises(ValidationError):
        EventCheckPayload.model_validate({"request": {**request_data(), **changes}})


def test_request_byte_budget_and_collection_bounds_are_strict():
    """完整 UTF-8 字节、事实数和证据数均独立受限，任一超限都拒绝整包。"""
    with pytest.raises(ValidationError, match="32_kib"):
        request(facts={"a": {"value": "文" * 16000}})
    with pytest.raises(ValidationError):
        request(facts={f"f{i}": {"value": "x"} for i in range(65)})
