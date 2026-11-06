"""校验同源 Hook/短流程交付，拒绝混合批次与被破坏的规则契约。"""

from __future__ import annotations

import hashlib

import pytest
from support.compiled_resources import CompiledResources

from token_io_decoupling_workflow.rules import RuleLoader, RuleLoadError


@pytest.mark.parametrize("language", ["zh_cn"])
def test_explicit_shared_fragment_does_not_repeat_default_event(language):
    """显式读取共享单元时只交付该单元，避免把默认事件再次拼入。"""
    rules = RuleLoader()
    default = rules.load_context_bundle("contract", language=language)
    shared = rules.load_context_bundle(
        "contract", language=language, fragment_ids=["common.hard_constraints"]
    )
    assert default.complete
    assert shared.complete
    assert default.required_fragment_ids == ["contract.compiled"]
    assert shared.required_fragment_ids == ["common.hard_constraints"]
    assert len(shared.fragments) == 1
    assert "Computer Use" in shared.fragments[0].text
    assert shared.text_characters < default.text_characters


@pytest.mark.parametrize("language", ["zh_cn"])
def test_each_lookup_can_be_used_directly_without_a_prior_event(language):
    """节点查询可独立使用，不依赖服务记录先前事件或持有执行游标。"""
    rules = RuleLoader()
    contract = rules.load_context_bundle("contract", language=language)
    assert contract.complete
    assert contract.text_characters <= 12000
    for node in rules._load_registry().nodes:
        assert node.next_checkpoint_ids == []
        bundle = rules.load_context_bundle(node.node_id, language=language, max_chars=60000)
        assert bundle.complete
        assert bundle.build_id == contract.build_id
    assert not hasattr(rules, "load_stage")


@pytest.mark.parametrize("language", ["zh_cn"])
def test_current_event_and_short_workflow_are_independently_hash_bound(language):
    """事件与短流程共享批次但各自绑定正文，短流程不包含阶段推进字段。"""
    rules = RuleLoader()
    event = rules.load_event("completion_requested", language=language)
    workflow = rules.load_workflow("single-agent", language=language)
    assert event.build_id == workflow.build_id
    for card in (event, workflow):
        assert hashlib.sha256(card.text.encode()).hexdigest() == card.content_sha256
    assert event.instruction_ids == ["common.shared", "event.completion_requested"]
    assert workflow.instruction_ids == ["workflow.single-agent"]
    assert "next_stage" not in workflow.model_dump()


@pytest.mark.parametrize("corruption", ["old_successor", "removed_node", "mixed_contract"])
def test_old_or_mixed_registry_contract_cannot_be_blessed_by_manifest_hash(
    tmp_path, monkeypatch, corruption
):
    """真实清单已重新绑定后，旧版本或混合注册表仍须被消费者拒绝。"""
    staged = CompiledResources(tmp_path, monkeypatch)
    nodes = staged.document["registry"]["nodes"]
    if corruption == "old_successor":
        nodes[0]["next_checkpoint_ids"] = ["contract"]
    elif corruption == "removed_node":
        nodes.pop()
    else:
        nodes[0]["required_facts"].append(
            {"key": "injected", "description": "unknown", "required": True}
        )
    staged.save()
    with pytest.raises((RuleLoadError, ValueError)):
        RuleLoader().load_context_bundle("contract")
