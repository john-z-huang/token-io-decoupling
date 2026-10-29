# Context source selection

[English](context-source-selection.md) | [简体中文](context-source-selection_zh_cn.md)

This checkpoint owns the route-level procedure for selecting and qualifying active-plan, bounded-rule, reusable project-memory, and persistent-exchange context.

## Trigger and inputs

After Session resolution, use current verified facts and task scope. Apply [Context](../layer-02-workflow-concepts/entry-and-context/context.md), [Session Context Firewall](../layer-01-fundamental-concepts/session-runtime/session-context-firewall.md), [project-memory and code-structure capability](../layer-01-fundamental-concepts/session-runtime/LSP-MCP-Tools.md), [Enhanced Rule Context](../layer-01-fundamental-concepts/enhanced-native-state/enhanced-rule-context.md), and the context-exchange owners when their triggers apply.

## Decision and result

1. Define the smallest current Context question, its task scope, and which source class can answer it. Apply the Context owner; do not read unrelated project state.
2. Always list active plan Memories under `plans/` and read every match for this task. Compare each match with current instructions, task match, source pointers, and freshness; current instructions take precedence, and a plan never grants authorization. If there is no matching active plan, record `Not applicable` and why. If listing or reading a relevant active plan fails, block work depending on it; do not substitute filesystem files for that plan.
3. For reusable project knowledge from prior work, list project Memories and read relevant entries; verify source pointers and freshness against authoritative project files. If there is no relevant entry or cross-session knowledge is unnecessary, record `Not applicable` and why. If Memory is unavailable, return to approved authoritative project files; block only if an essential fact cannot otherwise be established. This fallback applies to ordinary reusable project knowledge, not the required active-plan listing/read in step 2.
4. If the current question needs a registered rule node, use Enhanced Rule Context to read only that node and mapped owner heading from one current source/language. Verify owner, language, source, and hash; separately read each necessary direct owner omitted from the excerpt. If bounded lookup is unnecessary, record `Not applicable` and still confirm required direct owners. If lookup fails but the direct authoritative owner is available, read that authoritative owner directly and record the limitation; block only if required authoritative content cannot be confirmed.
5. Apply Session Context Firewall to source scope and ingress. If Worker memo or memo dispatch is needed, use [Content Memo Dispatch](../layer-01-fundamental-concepts/context-exchange/content-memo-dispatch.md) and its [Content Memo Lifecycle](../layer-01-fundamental-concepts/context-exchange/content-memo-lifecycle.md), confirm required Memory capability and evidence, and retain it as evidence for any later authorized Worker memo dispatch; when the trigger is absent, record `Not applicable` and why. If a Worker requires cross-Worker exchange/bootstrap, use [Coding Context Exchange](../layer-01-fundamental-concepts/context-exchange/context-exchange.md) and [Workspace Boundary](../layer-01-fundamental-concepts/context-exchange/context-exchange-workspace-boundary.md). Use [Context Exchange Handoff](../layer-01-fundamental-concepts/context-exchange/context-exchange-handoff.md) only for a concrete handoff or recovery. Evaluate each independent trigger under its named owner; confirm required persistent-memory capability and evidence. Do not create exchange records merely because Context is being gathered. If a required exchange capability is unavailable, block dependent work; never use filesystem fallback for an owner-required persistent record.
6. Return the minimal current facts with source pointers, provenance, freshness/epoch, and any limitation. Stale, incomplete, or conflicting essential context blocks dependent decisions. Memo eligibility, consent, and persistence remain with their owners.

## Failure boundary

Stale, inaccessible, or conflicting essential context blocks dependent decisions. Do not broaden source scope, infer authorization from memory, or bypass required Memory capability.

## Related concepts

- [Context](../layer-02-workflow-concepts/entry-and-context/context.md)
