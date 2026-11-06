from __future__ import annotations

import json
from pathlib import Path

import pytest
from support.compiled_resources import CompiledResources

from token_io_decoupling_workflow.rules import (
    IncompatibleRuleContractError,
    RuleLoader,
    RuleLoadError,
    UnknownRuleNodeError,
)


def test_chinese_context_has_one_build_identity_and_inline_instructions() -> None:
    """默认与显式中文必须读取同一完整节点；旧英文输入和未知节点均不能被接受。"""
    loader = RuleLoader()
    context = loader.load_context("contract")
    assert context == loader.load_context("contract", language="zh_cn")
    assert context.schema_version == 2
    assert context.owner_path == "compiled:contract"
    assert context.owner_text
    assert context.required_facts
    assert context.next_checkpoint_ids == []
    invalid_language = json.loads('{"language":"en"}')["language"]
    with pytest.raises(RuleLoadError, match="unsupported instruction language"):
        loader.load_context("contract", language=invalid_language)
    with pytest.raises(UnknownRuleNodeError):
        loader.load_context("environment")


def test_repository_argument_cannot_select_author_documents(tmp_path: Path) -> None:
    """即使传入不存在的作者目录，规则仍只来自批准包资源，不能改变执行来源。"""
    before = RuleLoader().load_context("contract")
    nonexistent = tmp_path / "no-author-tree"
    assert RuleLoader(repository_root=nonexistent).load_context("contract") == before


def test_missing_compiled_resource_does_not_fall_back_to_sources(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """删除实际编译资源后必须失败，传入仓库路径不能启用作者源回退。"""
    staged = CompiledResources(tmp_path, monkeypatch)
    (staged.resources / "instructions.json").unlink()
    with pytest.raises(RuleLoadError, match="compiled instruction"):
        RuleLoader(repository_root=tmp_path).load_context("contract")


@pytest.mark.parametrize("field", ["schema", "build", "manifest_hash", "text_hash"])
def test_corrupt_or_incompatible_resources_fail_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, field: str
) -> None:
    """分别破坏版本、批次、清单或正文；任一完整性层失败都不得返回可执行规则。"""
    staged = CompiledResources(tmp_path, monkeypatch)
    if field == "schema":
        staged.document["schema_version"] = 1
    elif field == "build":
        staged.document["build_id"] = "0" * 64
    elif field == "text_hash":
        staged.document["nodes"]["contract"]["text"] += " changed"
    staged.save()
    if field == "manifest_hash":
        (staged.resources / "instructions.json").write_text("{}", encoding="utf-8")
    with pytest.raises(RuleLoadError):
        RuleLoader().load_context("contract")


def test_registry_semantics_cannot_change_without_consumer_contract_update(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """即使重新计算资源清单，未审阅的新需求也不能绕过固定消费者契约。"""
    staged = CompiledResources(tmp_path, monkeypatch)
    staged.document["registry"]["nodes"][0]["required_facts"] = ["invented_requirement"]
    staged.save()
    with pytest.raises(IncompatibleRuleContractError):
        RuleLoader().load_context("contract")


@pytest.mark.parametrize("target", ["document", "manifest"])
@pytest.mark.parametrize("version", [2, "3", True])
def test_reader_rejects_old_or_noninteger_resource_versions(tmp_path, monkeypatch, target, version):
    """两类资源都只接受整数 3；旧版本、数字字符串和布尔值必须被拒绝。"""
    staged = CompiledResources(tmp_path, monkeypatch)
    resource = staged.document if target == "document" else staged.manifest
    resource["schema_version"] = version
    staged.save()
    with pytest.raises(RuleLoadError):
        RuleLoader().load_context("contract")


@pytest.mark.parametrize(
    "collection,field,version",
    [("registry", "contract_version", 2), ("context_index", "schema_version", 1)],
)
def test_reader_rejects_old_internal_contract_versions(
    tmp_path, monkeypatch, collection, field, version
):
    """外层 Hash 合法也不能替代 registry 与 context index 各自的版本守卫。"""
    staged = CompiledResources(tmp_path, monkeypatch)
    staged.document[collection][field] = version
    staged.save()
    with pytest.raises(RuleLoadError):
        RuleLoader().load_context("contract")


@pytest.mark.parametrize("target", ["document", "manifest"])
def test_reader_rejects_nonchinese_resource_identity(tmp_path, monkeypatch, target):
    """正文与清单分别声明英文时都应失败，防止以混合语言身份加载当前资源。"""
    staged = CompiledResources(tmp_path, monkeypatch)
    resource = staged.document if target == "document" else staged.manifest
    resource["language"] = "en"
    staged.save()
    with pytest.raises(RuleLoadError):
        RuleLoader().load_context("contract")


@pytest.mark.parametrize("collection", ["nodes", "fragments", "events", "policies", "workflows"])
def test_reader_rejects_language_mirrors_in_every_instruction_collection(
    tmp_path, monkeypatch, collection
):
    """五类集合都必须按 ID 直达单项，不能继续执行旧双语言镜像结构。"""
    staged = CompiledResources(tmp_path, monkeypatch)
    identity = next(iter(staged.document[collection]))
    entry = staged.document[collection][identity]
    staged.document[collection][identity] = {"en": entry, "zh_cn": entry}
    staged.save()
    with pytest.raises(RuleLoadError):
        RuleLoader().load_context("contract")


@pytest.mark.parametrize("collection", ["nodes", "fragments", "events", "policies", "workflows"])
def test_reader_rejects_language_fields_mixed_into_current_entries(
    tmp_path, monkeypatch, collection
):
    """当前字段与旧语言子项混合时也要拒绝，不能仅检查版本号。"""
    staged = CompiledResources(tmp_path, monkeypatch)
    identity = next(iter(staged.document[collection]))
    staged.document[collection][identity]["en"] = {"text": "retired mirror"}
    staged.save()
    with pytest.raises(RuleLoadError):
        RuleLoader().load_context("contract")


@pytest.mark.parametrize("field", ["owner_mirrors", "resource_paths"])
def test_registry_rejects_retired_mirror_fields(tmp_path, monkeypatch, field):
    """旧 owner 镜像与资源路径即使为空也不再是合法执行入口。"""
    staged = CompiledResources(tmp_path, monkeypatch)
    staged.document["registry"]["nodes"][0][field] = []
    staged.save()
    with pytest.raises(IncompatibleRuleContractError):
        RuleLoader().load_context("contract")


@pytest.mark.parametrize("field", ["section_en", "section_zh_cn", "source_path"])
def test_context_index_rejects_retired_language_and_source_fields(tmp_path, monkeypatch, field):
    """章节只保留单中文定位；旧语言字段或作者路径不能藏在合法外层清单中。"""
    staged = CompiledResources(tmp_path, monkeypatch)
    fragment = staged.document["context_index"]["fragments"][0]
    fragment[field] = "retired value"
    staged.save()
    with pytest.raises(RuleLoadError):
        RuleLoader().load_context("contract")


def test_event_and_workflow_loaders_reject_explicit_retired_language():
    """从原始 JSON 进入的非法语言仍须被 Reader 拒绝，两个入口默认均为中文。"""
    loader = RuleLoader()
    invalid_language = json.loads('{"language":"en"}')["language"]
    assert loader.load_event("task_received").language == "zh_cn"
    assert loader.load_workflow("single-agent").language == "zh_cn"
    with pytest.raises(RuleLoadError, match="unsupported instruction language"):
        loader.load_event("task_received", language=invalid_language)
    with pytest.raises(RuleLoadError, match="unsupported instruction language"):
        loader.load_workflow("single-agent", language=invalid_language)


def test_policy_sections_and_choices_are_compiled_data_and_hash_bound(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """修改政策语义索引后 Hash 必须变化，证明建议不能只钉住未变化的正文。"""
    staged = CompiledResources(tmp_path, monkeypatch)
    before = RuleLoader().load_delegation_policy("task-assignment")
    heading = "Executor Decisions instructions"
    staged.document["policies"]["task-assignment"]["sections"][heading] = (
        "Use this compiled instruction directly."
    )
    staged.save()
    after = RuleLoader().load_delegation_policy("task-assignment")
    assert after.text == before.text
    assert after.content_sha256 != before.content_sha256
    assert after.sections[heading] == "Use this compiled instruction directly."
    assert after.choices["Executor choice descriptions"]
