"""Fixed diagnostic scenarios for the distinct repair checkpoint contracts."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

from token_io_decoupling_core.registry_contract import (
    UnsupportedRegistryShapeError,
    validate_supported_registry_shape,
)
from token_io_decoupling_core.workflow_models import EvidenceSubmission
from token_io_decoupling_workflow.checkpoint_evaluation import evaluate_checkpoint
from token_io_decoupling_workflow.rules import RuleLoader


def _submission(payload: dict[str, Any]) -> EvidenceSubmission:
    return EvidenceSubmission.model_validate_json(json.dumps(payload))


def _reference(value: object) -> dict[str, str]:
    encoded = json.dumps(value, sort_keys=True).encode()
    return {"uri": "memory://dedupe-diagnosis", "content_hash": hashlib.sha256(encoded).hexdigest()}


def _fact(key: str, value: object) -> dict[str, Any]:
    return {
        "fact_key": key,
        "judgment": {
            "status": "determined",
            "value": {"kind": "semantic_ref", "value": _reference(value)},
        },
    }


def _evidence(kind: str) -> dict[str, Any]:
    return {"kind": kind, "reference": {**_reference(kind), "evidence_id": kind}}


def _diagnosis(*, blocker: bool = False) -> dict[str, Any]:
    return {
        "node_id": "repair",
        "facts": [
            _fact("classified failure", "[3,1,3,2] incorrectly produces [1,2,3]"),
            _fact("affected repair paths", ["dedupe.py"]),
            _fact(
                "repair diagnosis or blocker",
                {"missing_decision": "confirm hashable-input contract"}
                if blocker
                else {"candidate": "return list(dict.fromkeys(values))"},
            ),
        ],
        "evidence_refs": [_evidence("failure evidence"), _evidence("repair diagnosis or blocker")],
    }


@pytest.mark.parametrize("language", ["zh_cn"])
@pytest.mark.parametrize("blocker", [False, True])
def test_diagnosis_is_reviewable_without_future_repair_effects(
    language: str, blocker: bool
) -> None:
    """有无 blocker 都不应要求尚未发生的修复效果；诊断就绪不授予执行权限。"""
    result = evaluate_checkpoint(
        _submission(_diagnosis(blocker=blocker)),
        rules=RuleLoader(),
        language=language,
    )
    assert result.status == "ready_for_agent_review"
    assert result.authority == "structural_check_only"
    assert result.next_checkpoint_ids == []
    assert result.missing_evidence == []
    assert "caller supplied facts and evidence are not authenticated" in result.limitations


@pytest.mark.parametrize(
    "key", ["classified failure", "affected repair paths", "repair diagnosis or blocker"]
)
def test_diagnosis_reports_each_missing_fact(key: str) -> None:
    """逐项删除当前诊断必需事实，缺口必须准确指回被删事实。"""
    payload = _diagnosis()
    payload["facts"] = [fact for fact in payload["facts"] if fact["fact_key"] != key]
    result = evaluate_checkpoint(_submission(payload), rules=RuleLoader())
    assert result.status == "incomplete_for_agent_review"
    assert result.missing_facts == [key]


@pytest.mark.parametrize("kind", ["failure evidence", "repair diagnosis or blocker"])
def test_future_repair_evidence_cannot_replace_diagnostic_evidence(kind: str) -> None:
    """未来修复结果不能替代当次诊断所需证据，避免循环完成条件。"""
    payload = _diagnosis()
    payload["evidence_refs"] = [ref for ref in payload["evidence_refs"] if ref["kind"] != kind]
    payload["evidence_refs"] += [
        _evidence("repair result"),
        _evidence("re-verification for changed coverage"),
    ]
    result = evaluate_checkpoint(_submission(payload), rules=RuleLoader())
    assert result.status == "incomplete_for_agent_review"
    assert result.missing_evidence == [kind]


def test_diagnostic_readiness_does_not_satisfy_scope_authorization() -> None:
    """诊断材料齐全仍不能满足独立的范围授权检查。"""
    payload = {
        "node_id": "repair_scope",
        "facts": [
            _fact("repair diagnosis or blocker", "candidate"),
            {"fact_key": "authorized repair scope", "judgment": {"status": "unknown"}},
        ],
        "evidence_refs": [_evidence("repair diagnosis or blocker")],
    }
    result = evaluate_checkpoint(_submission(payload), rules=RuleLoader())
    assert result.status == "incomplete_for_agent_review"
    assert result.missing_facts == ["authorized repair scope"]
    assert result.missing_evidence == ["repair authorization"]
    assert result.next_checkpoint_ids == []
    assert result.authority == "structural_check_only"


def test_repair_handoff_queues_verification_without_requiring_its_future_result() -> None:
    """修复交接只需当前结果和待验证范围，不能要求未来验证结果先存在。"""
    payload = {
        "node_id": "repair_handoff",
        "facts": [
            _fact("affected repair paths", ["dedupe.py"]),
            {
                "fact_key": "affected verification epoch",
                "judgment": {"status": "determined", "value": {"kind": "count", "value": 2}},
            },
        ],
        "evidence_refs": [_evidence("repair result"), _evidence("repair verification handoff")],
    }
    result = evaluate_checkpoint(_submission(payload), rules=RuleLoader())
    assert result.status == "ready_for_agent_review"
    assert result.next_checkpoint_ids == []
    assert result.authority == "structural_check_only"


def test_repair_lookups_have_no_successor_and_old_hash_is_rejected() -> None:
    """修复查询只返回当前政策，后继为空；原有指纹失效时不能继续使用。"""
    rules = RuleLoader()
    for node in ("repair", "repair_scope", "repair_execution", "repair_handoff"):
        assert rules.load_context(node).next_checkpoint_ids == []
    result = evaluate_checkpoint(
        _submission(_diagnosis()), rules=rules, expected_rule_hash="e" * 64
    )
    assert result.reason == "stale_rule_hash"


@pytest.mark.parametrize("target", ["verification", "nonexistent_checkpoint"])
def test_supported_contract_rejects_repair_successor_drift(target: str) -> None:
    """即使资源重算 Hash，增加修复后继边仍违反无固定推进链的消费者契约。"""
    root = next(
        path
        for path in Path(__file__).resolve().parents
        if (path / "instruction-compiler/sources/rule-registry.json").is_file()
    )
    registry = json.loads((root / "instruction-compiler/sources/rule-registry.json").read_text())
    changed = copy.deepcopy(registry)
    next(node for node in changed["nodes"] if node["node_id"] == "repair")[
        "next_checkpoint_ids"
    ] = [target]
    with pytest.raises(UnsupportedRegistryShapeError):
        validate_supported_registry_shape(changed)
