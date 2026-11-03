"""Produce a bounded, explicitly unapproved mapping for human source review."""

from __future__ import annotations

import hashlib
import posixpath
import re
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import unquote, urlsplit

from token_io_decoupling_core.heading_parser import extract_heading

from .compiler import CompileError, _source_path
from .legacy import build_legacy_mapping_draft, read_legacy_sources
from .markdown_refs import extract_markdown_links

_LAYER_ONE = "docs/skill/references/coding/layer-01-fundamental-concepts/"


def _classification(
    unit_id: str,
    reference_index: int,
    aliases: set[str],
    source_path: str,
    source_heading: str,
    target_path: str,
    section: str,
) -> tuple[str, str, str | None]:
    name = PurePosixPath(target_path).name.removesuffix("_zh_cn.md").removesuffix(".md")
    source = PurePosixPath(source_path).name.removesuffix("_zh_cn.md").removesuffix(".md")
    if section.casefold() in {"related concepts", "相关概念"}:
        return "navigation", "Related-concepts locator; no execution edge is inferred.", None
    reviewed: dict[tuple[str, int], tuple[str, str, str | None]] = {
        ("control.checkpoint", 0): (
            "required",
            "Root: stage feedback defines Control evidence.",
            None,
        ),
        ("delegation.record_shape", 0): (
            "required",
            "Root: record shape consumes audit definitions.",
            None,
        ),
        ("owner.child-role-selection", 0): (
            "conditional",
            "Root: generate context when no explicit role instruction applies.",
            "no_explicit_role",
        ),
        ("owner.delegation-mode-count-gate", 0): (
            "navigation",
            "Root: role selection occurs later, after Context and Decision.",
            None,
        ),
        ("owner.delegation-mode-reentry", 0): (
            "conditional",
            "Root: only an actually proposed, approved same-Session one-slot increase.",
            "same_session_count_change",
        ),
        ("owner.delegation-state-record", 0): (
            "conditional",
            "Root: only actual Native-to-Enhanced reconciliation.",
            "native_to_enhanced",
        ),
        ("owner.delegation-state-record", 1): (
            "conditional",
            "Root: only actual Enhanced-to-Native authority transfer.",
            "enhanced_to_native",
        ),
        ("owner.decision-context-generation.codex", 0): (
            "required",
            "Root: Codex API binding and bounded recovery material.",
            None,
        ),
        ("owner.output-materialization.codex", 0): (
            "navigation",
            "Root: model-binding ownership locator; no model selection here.",
            None,
        ),
        ("owner.workflow-routing-advice.codex", 0): (
            "navigation",
            "Root: model-binding ownership locator; no model selection here.",
            None,
        ),
        ("owner.delegation-child-message-visibility", 0): (
            "internal_already_included",
            "Root: audit configuration definition back-reference; "
            "audit must already be in the entry closure.",
            None,
        ),
        ("owner.reasoning-summary-visibility", 0): (
            "internal_already_included",
            "Root: audit configuration definition back-reference; "
            "audit must already be in the entry closure.",
            None,
        ),
        ("owner.reasoning-summary-visibility.codex", 0): (
            "internal_already_included",
            "Root: audit configuration definition back-reference; "
            "audit must already be in the entry closure.",
            None,
        ),
        ("task_intent.scope", 0): (
            "navigation",
            "Root: optional architecture locator; do not initialize state.",
            None,
        ),
    }
    reviewed.update(
        {
            ("owner.child-role-selection", 4): (
                "navigation",
                "Root: locate later role reservation; advice does not reserve.",
                None,
            ),
            ("owner.delegation-child-role-allocation", 0): (
                "required",
                "Root: identify a role before reserving it.",
                None,
            ),
            ("owner.execution-stage-feedback", 0): (
                "required",
                "Root: feedback requires audit field definitions.",
                None,
            ),
            ("owner.execution-stage-feedback", 1): (
                "required",
                "Root: feedback requires the task-plan lifecycle.",
                None,
            ),
            ("owner.execution-control", 0): (
                "required",
                "Root: the Control Progress Signal consumes execution-stage feedback.",
                None,
            ),
            ("owner.native-authority-transfer", 0): (
                "internal_already_included",
                "Root: transfer retains the already included audit definition.",
                None,
            ),
            ("owner.native-authority-transfer", 1): (
                "internal_already_included",
                "Root: transfer retains the already included state-record definition.",
                None,
            ),
            ("owner.native-reconciliation", 0): (
                "internal_already_included",
                "Root: reconciliation retains the already included audit definition.",
                None,
            ),
            ("owner.native-reconciliation", 1): (
                "required",
                "Root: current Control Continue is required before the next release.",
                None,
            ),
            ("owner.session-model", 2): (
                "navigation",
                "Root: workspace ownership locator does not trigger worktree creation.",
                None,
            ),
        }
    )
    if unit_id == "owner.child-role-selection" and reference_index in {1, 2, 3}:
        return (
            "required",
            "Root: authoritative gate or field material, without replaying actions.",
            None,
        )
    if unit_id == "owner.session-context-firewall" and reference_index in range(4):
        if reference_index < 2:
            return (
                "required",
                "Root: session role ownership defines the firewall's authority.",
                None,
            )
        return (
            "conditional",
            "Root: authorized reusable-context record persistence only.",
            "authorized_context_persistence",
        )
    if unit_id == "owner.session-model" and reference_index in {0, 1}:
        return (
            "conditional",
            "Root: Fork starts a new Coding Session and record.",
            "fork_new_session",
        )
    if unit_id == "owner.lsp-mcp-tools" and reference_index in range(5):
        condition = (
            "authorized_worker_memo",
            "authorized_context_exchange",
            "exchange_workspace",
            "exchange_handoff",
            "durable_context_firewall",
        )[reference_index]
        return (
            "conditional",
            "Root: corresponding authorized durable memo or exchange record only.",
            condition,
        )
    if unit_id == "owner.task-assignment" and reference_index in range(5):
        condition = (
            "fork_new_session",
            "fork_new_session",
            "fork_new_session",
            "new_role_reservation",
            "no_slot_unoccupied_role",
        )[reference_index]
        return (
            "conditional",
            "Root: source-specific Fork, role reservation, or approved count branch.",
            condition,
        )
    if (unit_id, reference_index) in reviewed:
        return reviewed[(unit_id, reference_index)]
    if name == "decisions-advisory" and aliases & {
        "mode.actions",
        "contract.actions",
        "contract_change.actions",
        "decision.actions",
        "verification_impact.actions",
    }:
        return (
            "conditional",
            "Root: advisory policy applies only when advisory output is used.",
            "advisory_used",
        )
    if "mode.actions" in aliases and name in {
        "delegation-state-record",
        "delegation-mode-confirmation",
        "delegation-mode-count-gate",
        "delegation-mode-reentry",
    }:
        return "required", "Root: Mode composes these four owner materials.", None
    if "mode.boundary" in aliases and name == "enhanced-state-store":
        return "navigation", "Root: ownership locator; Mode does not initialize a store.", None
    if "context.actions" in aliases:
        choices = {
            "enhanced-rule-context": ("conditional", "rule_lookup"),
            "LSP-MCP-Tools": ("conditional", "prior_project_knowledge"),
            "task-plan-memory-lifecycle": ("required", None),
        }
        if name in choices:
            kind, condition = choices[name]
            return kind, "Root: Context's explicit source line controls this dependency.", condition
    if "implementation.actions" in aliases:
        if name in {"output-materialization", "candidate-compliance"}:
            return (
                "conditional",
                "Root: controlled-candidate implementation path only.",
                "controlled_candidate",
            )
        if name == "task-plan-memory-lifecycle":
            return "required", "Root: plan lifecycle is required before implementation.", None
    if "documentation.actions" in aliases:
        if name == "candidate-compliance":
            return (
                "conditional",
                "Root: authorized pre-write candidate feedback only.",
                "prewrite_feedback",
            )
        if name == "LSP-MCP-Tools":
            return (
                "conditional",
                "Root: approved reusable knowledge or requested cross-session note.",
                "approved_knowledge",
            )
    if (
        source == "delegation-state-record"
        and name == "session-audit-visibility"
        and section in {"Record shape", "记录结构"}
    ):
        return "required", "Root: record shape consumes the audit field definitions.", None
    if source == "session-audit-visibility":
        if name == "delegation-state-record" and section in {"Configuration values", "配置值"}:
            return (
                "internal_already_included",
                "Root: definition back-reference only when target is in final closure.",
                None,
            )
        if name in {"delegation-child-message-visibility", "reasoning-summary-visibility"}:
            return "required", "Root: audit preset or cadence consumes the linked owner.", None
    if source == "delegation-child-creation" and name in {
        "runtime-provider-support",
        "session-audit-visibility",
    }:
        return "required", "Root: child creation capability requires these owner materials.", None
    if (
        source == "runtime-provider-support"
        and name == "delegation-child-creation"
        and ("optimizations" in source_heading or "特别优化指令" in source_heading)
    ):
        return (
            "internal_already_included",
            "Root: definition back-reference only when child-creation material "
            "is already in closure.",
            None,
        )
    return (
        "unresolved",
        "Source link needs an explicit Root classification and target-range review.",
        None,
    )


def build_review_draft(root: Path) -> dict[str, Any]:
    """Return actual source excerpts, candidates, aliases, and unresolved review questions."""
    root = root.resolve(strict=True)
    legacy = build_legacy_mapping_draft(root)
    sources = read_legacy_sources(root)
    units: dict[str, dict[str, Any]] = {}
    identities: dict[tuple[str, str, str, str], str] = {}
    queue: list[str] = []

    def source(path: str, heading: str, locale: str) -> dict[str, str]:
        raw = _source_path(root, path).read_bytes()
        excerpt = extract_heading(raw.decode("utf-8"), heading).strip()
        return {
            "path": path,
            "heading": heading,
            "locale": locale,
            "source_sha256": hashlib.sha256(raw).hexdigest(),
            "excerpt_sha256": hashlib.sha256(excerpt.encode()).hexdigest(),
        }

    def add_unit(en: dict[str, str], zh: dict[str, str], preferred: str, kind: str) -> str:
        key = (en["path"], en["heading"], zh["path"], zh["heading"])
        if key in identities:
            return identities[key]
        if len(units) >= 256:
            raise ValueError("review draft exceeds the bilingual source-unit bound")
        unit_id = preferred
        if unit_id in units:
            unit_id = "unit." + hashlib.sha256("\0".join(key).encode()).hexdigest()[:20]
        identities[key] = unit_id
        units[unit_id] = {
            "source_unit_id": unit_id,
            "source_kind": kind,
            "legacy_fragment_ids": [],
            "legacy_owner_ids": [],
            "source_en": en,
            "source_zh_cn": zh,
            "references": {"en": [], "zh_cn": []},
            "semantic_dependencies": {"en": [], "zh_cn": []},
        }
        queue.append(unit_id)
        return unit_id

    def add_owner(path: str, *, runtime_provider: bool = False) -> str:
        zh_path = path.removesuffix(".md") + "_zh_cn.md"
        en_heading = (
            "Codex CLI / ChatGPT Desktop optimizations" if runtime_provider else "General rules"
        )
        zh_heading = "Codex CLI / ChatGPT Desktop 特别优化指令" if runtime_provider else "通用规范"
        suffix = ".codex" if runtime_provider else ""
        preferred = "owner." + PurePosixPath(path).stem.lower() + suffix
        return add_unit(
            source(path, en_heading, "en"),
            source(zh_path, zh_heading, "zh_cn"),
            preferred,
            "semantic_owner",
        )

    fragment_bindings: dict[str, str] = {}
    owner_bindings: dict[str, str] = {}
    for fragment in legacy["fragments"]:
        fragment_id = fragment["legacy_fragment_id"]
        unit_id = add_unit(fragment["source_en"], fragment["source_zh_cn"], fragment_id, "fragment")
        fragment_bindings[fragment_id] = unit_id
        units[unit_id]["legacy_fragment_ids"].append(fragment_id)
    for owner in legacy["owner_mappings"]:
        owner_id, path = owner["legacy_owner_id"], owner["source_en"]
        unit_id = add_owner(path)
        owner_bindings[owner_id] = unit_id
        units[unit_id]["legacy_owner_ids"].append(owner_id)
        provider_id = add_owner(path, runtime_provider=True)
        units[unit_id]["codex_optimization_candidate"] = provider_id

    for relative in (
        "delegation/delegation-state-record.md",
        "delegation/delegation-child-role-allocation.md",
        "session-runtime/session-audit-visibility.md",
        "delegation/delegation-child-creation.md",
        "context-exchange/context-exchange.md",
    ):
        unit_id = add_owner(_LAYER_ONE + relative)
        if relative == "delegation/delegation-child-role-allocation.md":
            units[unit_id]["codex_optimization_candidate"] = add_owner(
                _LAYER_ONE + relative, runtime_provider=True
            )
        if relative == "delegation/delegation-child-creation.md":
            units[unit_id]["usage_condition"] = (
                "Only when the authorized route actually creates a new child."
            )
    add_owner(_LAYER_ONE + "session-runtime/runtime-provider-support.md", runtime_provider=True)

    # The mapping is a reviewable projection of existing policy, not another
    # policy owner. Each node is a separate unit so unrelated branches are not
    # pulled into a context response.
    mapping_path = ".agents/skills/token-io-decoupling-dev/references/node-mapping.md"
    mapping_zh = mapping_path.removesuffix(".md") + "_zh_cn.md"
    mapping_units: dict[str, str] = {}
    for node in sources["registry"]["nodes"]:
        node_id = node["node_id"]
        mapping_units[node_id] = add_unit(
            source(mapping_path, "Node: " + node_id, "en"),
            source(mapping_zh, "Node: " + node_id, "zh_cn"),
            "mapping." + node_id,
            "node_mapping",
        )

    verification_units: dict[tuple[str, str], str] = {}
    verification_root = (
        "docs/skill/references/coding/layer-02-workflow-concepts/verification-and-repair/"
    )
    for owner in ("verification-reporting", "verification-independence"):
        for part, en_heading, zh_heading in (
            ("actions", "Actions", "动作"),
            ("pass", "Pass condition", "通过条件"),
        ):
            path = verification_root + owner + ".md"
            verification_units[(owner, part)] = add_unit(
                source(path, en_heading, "en"),
                source(path.removesuffix(".md") + "_zh_cn.md", zh_heading, "zh_cn"),
                owner + "." + part,
                "semantic_owner",
            )

    default_fragments = {
        node["node_id"]: node["default_fragment_ids"][0] for node in sources["index"]["nodes"]
    }
    mapping_targets: dict[str, list[tuple[str, str, str | None]]] = {
        node_id: [(fragment_bindings[fragment_id], "required", None)]
        for node_id, fragment_id in default_fragments.items()
    }
    mapping_targets["delegation"].extend(
        [
            ("owner.delegation-child-role-allocation", "conditional", "multi_agent_allocation"),
            ("owner.delegation-child-creation", "conditional", "new_child_creation"),
        ]
    )
    mapping_targets["output_class"].append(("owner.session-role-ownership", "required", None))
    mapping_targets["decision"].append(
        (fragment_bindings["decision.workflow_routing_advice"], "conditional", "workflow_advice")
    )
    mapping_targets["verification"].extend(
        [
            (verification_units[("verification-reporting", "actions")], "required", None),
            (verification_units[("verification-reporting", "pass")], "required", None),
            (
                verification_units[("verification-independence", "actions")],
                "required",
                None,
            ),
            (
                verification_units[("verification-independence", "pass")],
                "required",
                None,
            ),
        ]
    )

    plan_owner = add_owner(_LAYER_ONE + "execution-planning/task-plan-memory-lifecycle.md")
    amendment_evidence = {
        "contract": {
            "en": (
                "A verified fact or user instruction materially changes the current Contract.",
                "Record and analyze the change and update the Contract, plan and dependent "
                "decision within existing authority.",
            ),
            "zh_cn": (
                "经核实的事实或用户指令实质改变当前 Contract。",
                "记录并分析变化，在既有授权内同步 Contract、计划和依赖决定。",
            ),
        },
        "contract_change": {
            "en": (
                "A material change is confirmed and the required amendment is covered by "
                "existing authority.",
                "Synchronize the Contract, plan and Decision before affected work resumes.",
            ),
            "zh_cn": (
                "已确认实质变化且所需修改属于既有授权范围。",
                "受影响工作恢复前同步 Contract、计划和 Decision。",
            ),
        },
    }
    for node_id, locales in amendment_evidence.items():
        source_id = mapping_units[node_id]
        for locale, (trigger, action) in locales.items():
            trigger_selector = {"source_unit_id": source_id, "quote": trigger, "occurrence": 0}
            action_selector = {"source_unit_id": source_id, "quote": action, "occurrence": 0}
            units[source_id]["semantic_dependencies"][locale].append(
                {
                    "class": "conditional",
                    "target_source_unit_id": plan_owner,
                    "condition_id": "contract_amendment",
                    "trigger_selector": trigger_selector,
                    "provenance": {"kind": "markdown_quote", "selector": action_selector},
                    "review_status": "root_preclassified; confirm amendment closure",
                }
            )

    index = sources["index"]
    for i, fragment in enumerate(index["fragments"]):
        for j, dependency in enumerate(fragment.get("dependencies", [])):
            edge = {
                "class": "required",
                "target_source_unit_id": fragment_bindings[dependency],
                "provenance": {
                    "kind": "legacy_index_dependency",
                    "json_pointer": f"/fragments/{i}/dependencies/{j}",
                    "fragment_id": fragment["fragment_id"],
                    "dependency_fragment_id": dependency,
                    "source_sha256": sources["source_hashes"]["context_index_sha256"],
                },
                "review_status": "root_preclassified; confirm graph and closure",
            }
            unit = units[fragment_bindings[fragment["fragment_id"]]]
            for locale in ("en", "zh_cn"):
                unit["semantic_dependencies"][locale].append(edge)

    context_id = fragment_bindings["context.actions"]
    exchange_id = add_owner(_LAYER_ONE + "context-exchange/context-exchange.md")
    for locale, trigger in (
        ("en", "When a released Worker must persist a memo or exchange record"),
        ("zh_cn", "已放行 Worker 需要持久化 memo 或交换记录时"),
    ):
        for condition in ("worker_memo", "cross_worker_exchange"):
            selector = {"source_unit_id": context_id, "quote": trigger, "occurrence": 0}
            units[context_id]["semantic_dependencies"][locale].append(
                {
                    "class": "conditional",
                    "target_source_unit_id": exchange_id,
                    "condition_id": condition,
                    "trigger_selector": selector,
                    "provenance": {"kind": "markdown_quote", "selector": selector},
                    "review_status": "root_preclassified; independent memo and exchange triggers",
                }
            )

    # The General-rules owner includes the Interaction Slice definition. Its
    # Contract dependency is separately proposed even when the narrow legacy
    # Interaction Slice fragment is not itself selected as a source root.
    control_id = add_owner(_LAYER_ONE + "execution-control/execution-control.md")
    contract_id = fragment_bindings["contract.actions"]
    for locale, quote in (
        (
            "en",
            "The executor may continue through low-decision-density mechanics "
            "while the Contract and boundary remain unchanged.",
        ),
        (
            "zh_cn",
            "只要 Contract 和边界未变，执行者可以继续处理低决策密度的机械步骤；"
            "到达 return conditions 或跨越未放行边界前必须暂停。",
        ),
    ):
        selector = {"source_unit_id": control_id, "quote": quote, "occurrence": 0}
        units[control_id]["semantic_dependencies"][locale].append(
            {
                "class": "required",
                "target_source_unit_id": contract_id,
                "provenance": {"kind": "markdown_quote", "selector": selector},
                "review_status": "root_preclassified; confirm entry closure",
                "reason": "The included Interaction Slice passage depends "
                "on the Contract remaining unchanged.",
            }
        )

    cursor = 0
    while cursor < len(queue):
        unit = units[queue[cursor]]
        cursor += 1
        aliases = set(unit["legacy_fragment_ids"])
        for locale, key in (("en", "source_en"), ("zh_cn", "source_zh_cn")):
            record = unit[key]
            excerpt = extract_heading(
                _source_path(root, record["path"]).read_text(encoding="utf-8"), record["heading"]
            )
            for reference_index, link in enumerate(extract_markdown_links(excerpt)):
                matches = [m.start() for m in re.finditer(re.escape(link.raw), excerpt)]
                position = matches[link.occurrence]
                start = excerpt.rfind("\n", 0, position) + 1
                end = excerpt.find("\n", position)
                line = excerpt[start : end if end >= 0 else len(excerpt)].strip()
                before = excerpt[:position]
                sections = [
                    line[4:].strip() for line in before.splitlines() if line.startswith("### ")
                ]
                section = sections[-1] if sections else ""
                parsed = urlsplit(link.destination or "")
                target = ""
                if not parsed.scheme and not parsed.netloc and parsed.path:
                    target = posixpath.normpath(
                        posixpath.join(
                            PurePosixPath(record["path"]).parent.as_posix(), unquote(parsed.path)
                        )
                    )
                kind, reason, condition = _classification(
                    unit["source_unit_id"],
                    reference_index,
                    aliases,
                    record["path"],
                    record["heading"],
                    target,
                    section,
                )
                mapped_node = next(
                    (
                        node
                        for node, source_id in mapping_units.items()
                        if source_id == unit["source_unit_id"]
                    ),
                    None,
                )
                mapped_target = None
                if mapped_node is not None:
                    candidates = mapping_targets[mapped_node]
                    if reference_index >= len(candidates):
                        raise CompileError(
                            f"unexpected mapping reference: {mapped_node} ({locale})"
                        )
                    mapped_target, kind, condition = candidates[reference_index]
                    if units[mapped_target][key]["path"] != target:
                        raise CompileError(
                            f"mapping authority target changed: {mapped_node} ({locale})"
                        )
                    reason = "Existing policy authority; mapping and target require Root review."
                if parsed.scheme or parsed.netloc:
                    kind, reason, condition = (
                        "navigation",
                        "External reference recorded as data; no network access.",
                        None,
                    )
                item: dict[str, Any] = {
                    "selector": {"raw": link.raw, "occurrence": link.occurrence},
                    "label": link.label,
                    "destination": link.destination,
                    "source_section": section,
                    "candidate_class": kind,
                    "reason": reason,
                    "target_path": target or None,
                    "review_status": "requires_root_review",
                }
                if condition:
                    quote_occurrence = excerpt[:start].count(line)
                    item["condition_id"] = condition
                    item["trigger_selector"] = {
                        "source_unit_id": unit["source_unit_id"],
                        "quote": line,
                        "occurrence": quote_occurrence,
                    }
                if target and kind in {"required", "conditional", "internal_already_included"}:
                    english_target = (
                        target.removesuffix("_zh_cn.md") + ".md" if locale == "zh_cn" else target
                    )
                    try:
                        target_id = mapped_target or add_owner(english_target)
                    except (ValueError, OSError):
                        item["target_binding_unresolved"] = (
                            "Target has no usable bilingual General rules pair."
                        )
                    else:
                        item["target_source_unit_id"] = target_id
                        if english_target.startswith(_LAYER_ONE):
                            try:
                                provider_id = add_owner(english_target, runtime_provider=True)
                            except (ValueError, OSError):
                                item["provider_scope_unresolved"] = (
                                    "Codex optimization section is unavailable."
                                )
                            else:
                                item["codex_optimization_candidate"] = provider_id
                                item["provider_scope_review"] = (
                                    "Root must determine which Codex optimization content "
                                    "is consumed with this execution dependency."
                                )
                        if kind == "internal_already_included":
                            item["included_in_source_unit_id"] = target_id
                            item["closure_check"] = (
                                "must already be present in the final entry closure"
                            )
                unit["references"][locale].append(item)
            if unit["source_unit_id"] in mapping_units.values():
                mapped_node = next(
                    node
                    for node, source_id in mapping_units.items()
                    if source_id == unit["source_unit_id"]
                )
                if len(unit["references"][locale]) != len(mapping_targets[mapped_node]):
                    raise CompileError(
                        f"mapping authority reference missing: {mapped_node} ({locale})"
                    )

    counts: dict[str, int] = {}
    for unit in units.values():
        for references in unit["references"].values():
            for item in references:
                counts[item["candidate_class"]] = counts.get(item["candidate_class"], 0) + 1
    source_chars = {
        locale: sum(
            len(
                extract_heading(
                    _source_path(root, unit[key]["path"]).read_text(encoding="utf-8"),
                    unit[key]["heading"],
                )
            )
            for unit in units.values()
        )
        for locale, key in (("en", "source_en"), ("zh_cn", "source_zh_cn"))
    }
    return {
        "draft_format": "token-io-legacy-mapping-review-draft/v1",
        "review_status": "DRAFT_REQUIRES_ROOT_REVIEW",
        "complete": False,
        "legacy_source_hashes": sources["source_hashes"],
        "legacy_node_metadata": sources["registry"]["nodes"],
        "legacy_context_nodes": index["nodes"],
        "legacy_fragments": index["fragments"],
        "owner_paths": sources["owner_paths"],
        "optional_fragment_owner_bindings": sources["optional_fragment_owner_bindings"],
        "legacy_bindings": {"fragments": fragment_bindings, "owners": owner_bindings},
        "source_units": [units[key] for key in sorted(units)],
        "candidate_reference_counts": counts,
        "budget_diagnostics": {
            "source_unit_records": len(units) * 2,
            "source_unit_record_limit": 512,
            "aggregate_excerpt_unicode_chars_by_locale": source_chars,
            "entry_closure_unicode_char_limit": 262144,
            "artifact_byte_limit": 8388608,
            "entry_closure_status": "unresolved until Root approves the actual dependency graph",
        },
        "provider_scope": (
            "Execution uses the applicable Codex CLI sections; Claude sections remain "
            "documentation-compatibility background and are not consumed by this MCP server."
        ),
        "required_legacy_dependency_records_per_locale": sum(
            len(f.get("dependencies", [])) for f in index["fragments"]
        ),
        "unresolved": [
            "Root must review every candidate reference and unresolved target, including "
            "provider-section coverage and back-reference closures.",
            "Runtime entry actions and legal branch selectors require direct bilingual source "
            "review; this draft is not a compilable manifest.",
            "Actual execution graph cycles and full entry budgets require an approved mapping "
            "and may not be inferred from this inventory.",
        ],
    }
