from __future__ import annotations

import hashlib
import json
from collections.abc import Callable

import pytest
from pydantic import ValidationError

from token_io_decoupling_core.workflow_models import (
    CheckpointEvidenceRef,
    CheckpointFact,
    CheckpointNode,
    EvidenceKind,
    EvidenceSubmission,
    FactDetermined,
    FactKey,
    FactUnknown,
    LegalBranch,
    TypedEvidenceReference,
    checkpoint_submission_source_input_hash,
)
from token_io_decoupling_workflow.checkpoint_evaluation import evaluate_checkpoint
from token_io_decoupling_workflow.decisions import (
    DecisionAdvice,
    DecisionAdvisoryInput,
    DecisionsAdvisor,
    DecisionsRuntimeConfig,
)
from token_io_decoupling_workflow.payloads import EvaluatePayload
from token_io_decoupling_workflow.rules import RuleLoader


def _submission(
    node: CheckpointNode = CheckpointNode.CONTRACT, *, include_hash: bool = True
) -> EvidenceSubmission:
    """提供一个事实未知的最小输入，可选择附上真实计算的来源 Hash。"""
    submission = EvidenceSubmission(
        node_id=node,
        facts=[
            CheckpointFact(
                fact_key=FactKey.TASK_OBJECTIVE,
                judgment=FactUnknown(status="unknown"),
            )
        ],
    )
    if include_hash:
        return submission.model_copy(
            update={"input_hash": checkpoint_submission_source_input_hash(submission)}
        )
    return submission


def _rules() -> RuleLoader:
    return RuleLoader()


def _complete_submission(node: CheckpointNode) -> EvidenceSubmission:
    """按真实当前规则补齐声明结构；这些合成引用只用于结构检查，不证明事实。"""
    rules = _rules()
    context = rules.load_context(node.value)
    facts = []
    for key_text in context.required_facts:
        key = FactKey(key_text)
        if key is FactKey.PROGRESS_SIGNAL:
            judgment = FactDetermined.model_validate(
                {
                    "status": "determined",
                    "value": {"kind": "enum", "value": LegalBranch.CONTINUE},
                }
            )
        elif key is FactKey.TASK_TYPE:
            judgment = FactDetermined.model_validate(
                {"status": "determined", "value": {"kind": "enum", "value": LegalBranch.CODING}}
            )
        else:
            judgment = FactDetermined.model_validate(
                {
                    "status": "determined",
                    "value": {
                        "kind": "semantic_ref",
                        "value": {"uri": "memory://fact", "content_hash": "a" * 64},
                    },
                }
            )
        facts.append(CheckpointFact(fact_key=key, judgment=judgment))
    evidence_refs = [
        TypedEvidenceReference(
            kind=EvidenceKind(evidence),
            reference=CheckpointEvidenceRef(
                uri=f"memory://{index}", content_hash="b" * 64, evidence_id=f"e{index}"
            ),
        )
        for index, evidence in enumerate(context.required_evidence)
    ]
    return EvidenceSubmission(
        node_id=node,
        facts=facts,
        evidence_refs=evidence_refs,
    )


def test_evaluation_reports_missing_requirements_without_claiming_authority() -> None:
    """未知事实应产生缺口报告，同时明确结构检查不认证调用方事实。"""
    result = evaluate_checkpoint(_submission(), rules=_rules())

    assert result.status == "incomplete_for_agent_review"
    assert result.authority == "structural_check_only"
    assert result.missing_facts
    assert "caller supplied facts and evidence are not authenticated" in result.limitations
    assert result.source_input_hash != "0" * 64


def test_evaluation_blocks_input_hash_and_rule_hash_mismatch() -> None:
    """来源输入或当前规则任一指纹不匹配时都应阻止，不能沿用旧结论。"""
    submission = _submission()
    rules = _rules()

    bad_input = submission.model_copy(update={"input_hash": "f" * 64})
    assert evaluate_checkpoint(bad_input, rules=rules).reason == "source_input_hash_mismatch"
    assert (
        evaluate_checkpoint(submission, rules=rules, expected_rule_hash="e" * 64).reason
        == "stale_rule_hash"
    )


def test_evaluation_rejects_duplicate_fact_keys() -> None:
    """即使输入 Hash 已重新计算，重复事实仍是冲突，不能靠完整性标记洗白。"""
    submission = _submission()
    duplicate = submission.model_copy(update={"facts": [*submission.facts, submission.facts[0]]})
    data = duplicate.model_dump(mode="json", exclude={"input_hash"})
    digest = hashlib.sha256(
        json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()
    duplicate = duplicate.model_copy(update={"input_hash": digest})

    result = evaluate_checkpoint(duplicate, rules=_rules())

    assert result.status == "blocked_input"
    assert result.reason == "conflicting_duplicate_facts"


def test_evaluation_accepts_absent_hash_and_returns_computed_hash() -> None:
    """省略调用方 Hash 时服务应自行计算并返回；结构就绪仍只是待 Agent 审阅。"""
    submission = _complete_submission(CheckpointNode.TASK_INTENT)

    result = evaluate_checkpoint(submission, rules=_rules())

    assert result.status == "ready_for_agent_review"
    assert result.source_input_hash == checkpoint_submission_source_input_hash(submission)


def test_control_evaluation_accepts_legal_branch() -> None:
    """完整 Control 声明可返回合法分支，但不会自动放行下一步执行。"""
    submission = _complete_submission(CheckpointNode.CONTROL)

    result = evaluate_checkpoint(submission, rules=_rules())

    assert result.status == "ready_for_agent_review"
    assert result.selected_branch == "continue"


def test_evaluation_uses_chinese_rule_hash_and_rejects_retired_language() -> None:
    """中文规则必须使用当前指纹；陈旧指纹和原始 JSON 中的英文语言值均要拒绝。"""
    rules = _rules()
    submission = _complete_submission(CheckpointNode.TASK_INTENT)
    context = rules.load_context(CheckpointNode.TASK_INTENT.value)
    result = evaluate_checkpoint(
        submission, rules=rules, language="zh_cn", expected_rule_hash=context.context_hash
    )
    assert result.status == "ready_for_agent_review"
    stale = evaluate_checkpoint(
        submission, rules=rules, language="zh_cn", expected_rule_hash="0" * 64
    )
    assert stale.reason == "stale_rule_hash"
    invalid_language = json.loads('{"language":"en"}')["language"]
    with pytest.raises(ValueError, match="unsupported checkpoint evaluation language"):
        evaluate_checkpoint(submission, rules=rules, language=invalid_language)


def test_default_compiled_bundle_hash_is_checkpoint_rule_hash() -> None:
    """外部默认 bundle 的指纹应能直接用于检查点，正文也必须完全一致。"""
    rules = _rules()
    node_id = CheckpointNode.TASK_INTENT.value
    submission = _complete_submission(CheckpointNode.TASK_INTENT)
    full_context = rules.load_context(node_id, language="zh_cn")
    fragment_bundle = rules.load_context_bundle(node_id, language="zh_cn")

    assert fragment_bundle.context_hash == full_context.context_hash
    result = evaluate_checkpoint(
        submission, rules=rules, language="zh_cn", expected_rule_hash=fragment_bundle.context_hash
    )
    assert result.status == "ready_for_agent_review"
    assert result.instructions is not None
    assert result.instructions.owner_text == fragment_bundle.fragments[0].text


def test_evaluation_payload_bounds_current_facts_and_language() -> None:
    """数量、类型、单值长度和完整请求字节各有边界，不能只限制局部字段。"""
    base = {
        "node_id": CheckpointNode.CONTRACT.value,
        "submission": json.loads(_submission(include_hash=False).model_dump_json()),
    }
    EvaluatePayload.model_validate_json(
        json.dumps({**base, "language": "zh_cn", "current_facts": {}})
    )

    with pytest.raises(ValidationError):
        EvaluatePayload.model_validate_json(
            json.dumps(
                {
                    **base,
                    "current_facts": {f"key-{index}": "x" for index in range(17)},
                }
            )
        )
    with pytest.raises(ValidationError):
        EvaluatePayload.model_validate_json(
            json.dumps({**base, "current_facts": {"key": {"nested": "value"}}})
        )
    with pytest.raises(ValidationError):
        EvaluatePayload.model_validate_json(
            json.dumps({**base, "current_facts": {"key": "x" * 1025}})
        )
    with pytest.raises(ValidationError):
        EvaluatePayload.model_validate_json(
            json.dumps(
                {
                    **base,
                    "submission": {
                        **base["submission"],
                        "evidence_refs": [
                            {
                                "kind": EvidenceKind.READ_ONLY_GIT_STATE.value,
                                "reference": {
                                    "uri": "x" * 512,
                                    "content_hash": "a" * 64,
                                    "evidence_id": "e" * 128,
                                },
                            }
                            for _ in range(48)
                        ],
                    },
                    "current_facts": {f"key-{index}": "x" * 1024 for index in range(8)},
                }
            )
        )


def test_submission_rejects_too_many_top_level_facts() -> None:
    """事实条目超过 128 时拒绝整个请求，避免截断后误报完整。"""
    base = _submission(include_hash=False).model_dump(mode="json")
    with pytest.raises(ValidationError):
        EvidenceSubmission.model_validate_json(json.dumps({**base, "facts": base["facts"] * 129}))


def test_submission_rejects_too_many_top_level_evidence_references() -> None:
    """顶层证据引用最多 128 项，超限不能静默丢失证据。"""
    base = _submission(include_hash=False).model_dump(mode="json")
    reference = TypedEvidenceReference(
        kind=EvidenceKind.READ_ONLY_GIT_STATE,
        reference=CheckpointEvidenceRef(
            uri="memory://evidence", content_hash="a" * 64, evidence_id="evidence"
        ),
    ).model_dump(mode="json")
    with pytest.raises(ValidationError):
        EvidenceSubmission.model_validate_json(
            json.dumps({**base, "evidence_refs": [reference] * 129})
        )


def test_submission_rejects_more_than_three_coverage_dimensions() -> None:
    """覆盖只包含三个已定义维度，重复扩充列表也不能超过容量限制。"""
    base = _submission(include_hash=False).model_dump(mode="json")
    dimensions = [
        "implementation_content",
        "documentation",
        "git_metadata",
        "implementation_content",
    ]
    with pytest.raises(ValidationError):
        EvidenceSubmission.model_validate_json(
            json.dumps({**base, "coverage_dimensions": dimensions})
        )


def test_submission_rejects_too_many_evidence_references_inside_one_fact() -> None:
    """单项事实内部引用最多 16 项，防止绕过顶层集合限制。"""
    base = _submission(include_hash=False).model_dump(mode="json")
    reference = TypedEvidenceReference(
        kind=EvidenceKind.READ_ONLY_GIT_STATE,
        reference=CheckpointEvidenceRef(uri="memory://evidence", content_hash="b" * 64),
    ).model_dump(mode="json")
    fact = {
        "fact_key": FactKey.TASK_OBJECTIVE.value,
        "judgment": {
            "status": "determined",
            "value": {
                "kind": "semantic_ref",
                "value": {"uri": "memory://fact", "content_hash": "a" * 64},
            },
            "evidence": [reference] * 17,
        },
    }
    with pytest.raises(ValidationError):
        EvidenceSubmission.model_validate_json(json.dumps({**base, "facts": [fact]}))


def _registered_callbacks(
    rules: RuleLoader, advisor: DecisionsAdvisor, monkeypatch: pytest.MonkeyPatch
) -> dict[str, Callable[..., object]]:
    """使用真实注册器与建议对象，只截获注册结果，不用 Any 伪装生产类型。"""
    from mcp.server import MCPServer

    from token_io_decoupling_core.binding import DenyingBindingProvider
    from token_io_decoupling_transport.tool import ToolDefinition, ToolRegistrar
    from token_io_decoupling_workflow.events.advice import EventAdvisor
    from token_io_decoupling_workflow.tool import register_tools

    callbacks: dict[str, Callable[..., object]] = {}

    def collect(_registrar: ToolRegistrar, definitions: tuple[ToolDefinition, ...]) -> None:
        callbacks.update((definition.name, definition.callback) for definition in definitions)

    monkeypatch.setattr(ToolRegistrar, "register_all", collect)
    provider = DenyingBindingProvider()
    registrar = ToolRegistrar(
        MCPServer("test"),
        provider=provider,
        state_provider=provider,
        allowed_tools=frozenset(),
        require_codex_context=False,
        bound_role_for=lambda _provider: None,
        description_for=lambda name: name,
    )
    register_tools(
        registrar,
        rules=rules,
        advisor=advisor,
        event_advisor=EventAdvisor(rules, DecisionsRuntimeConfig()),
        capability_callback=lambda: {},
    )
    return callbacks


def test_evaluation_callback_preserves_language_and_source_hash(monkeypatch) -> None:
    """局部观察建议边界，确认回调传递同一中文、当前规则 Hash 与来源输入 Hash。"""
    rules = _rules()
    advisor = DecisionsAdvisor(rules, DecisionsRuntimeConfig())
    calls: list[dict[str, object]] = []

    def record(advisory_input: DecisionAdvisoryInput, **kwargs: object) -> DecisionAdvice:
        calls.append(kwargs)
        return DecisionAdvice(status="fallback", reason="disabled", node_id=advisory_input.node_id)

    monkeypatch.setattr(advisor, "advise", record)
    callbacks = _registered_callbacks(rules, advisor, monkeypatch)
    expected = rules.load_context(CheckpointNode.TASK_INTENT.value)
    payload = EvaluatePayload.model_validate_json(
        json.dumps(
            {
                "node_id": CheckpointNode.TASK_INTENT.value,
                "language": "zh_cn",
                "submission": _submission(
                    CheckpointNode.TASK_INTENT, include_hash=False
                ).model_dump(mode="json"),
                "semantic_input": {
                    "node_id": "task_intent",
                    "requested_outcome": "检查当前任务目标",
                    "task_signal": "coding",
                },
            }
        )
    )
    output = callbacks["workflow_evaluate"](payload)
    assert isinstance(output, dict)
    assert output["language"] == "zh_cn"
    assert len(calls) == 1
    assert calls[0]["language"] == "zh_cn"
    assert calls[0]["expected_rule_hash"] == expected.context_hash
    assert calls[0]["checkpoint_source_input_hash"] == output["source_input_hash"]
