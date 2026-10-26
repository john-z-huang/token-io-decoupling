# Context Checkpoint

[English](context.md) | [简体中文](context_zh_cn.md)

## Actions

1. Define the smallest question the next slice must answer.
2. Read only the files, metadata, history, or generated evidence needed for that question.
3. Before reusing cached or file-backed context, check its scope, owner, source paths, freshness, and final-state epoch.
4. Treat stale, incomplete, or conflicting context as unusable. Refresh only the affected context and record what changed.
5. Keep context factual and routing-oriented; do not use it as a replacement for the Contract, source documents, or verification.
6. When a bounded current rule-context lookup is selected for the next question, apply [Enhanced Rule Context](../layer-01-fundamental-concepts/enhanced-rule-context.md): verify the requested node, owner, language, and source/hash, then read any necessary direct owner that the excerpt does not include. If lookup is unnecessary, record `Not applicable` and why while still consulting the required owner directly. If lookup fails, use the authoritative owner when available; block the dependent judgment if required owner content cannot be confirmed.
7. When a released Worker must persist a memo or exchange record, require the named persistent-memory capability and confirm its availability; memo and cross-Worker exchange remain independent triggers. Apply the linked Layer-01 owner for logical ownership. If the capability is unavailable, report it and block dependent work; do not fall back to file storage.
8. When answering the current question requires reusable Agent project knowledge from prior work, use the [project-memory and code-structure capability](../layer-01-fundamental-concepts/LSP-MCP-Tools.md) to list memories and read relevant entries, then check their source pointers and freshness against authoritative project files. If memory listing is available and contains no relevant entry, or cross-session knowledge is unnecessary, record `Not applicable` with the reason. If the capability is unavailable, report it and return to approved authoritative project files; do not infer that no relevant memory exists. Pause only when an essential fact cannot be confirmed from another approved source. A memory does not replace an authoritative project file in the approved paths.

## Pass condition

The next slice has bounded, current context, or the exact missing context is recorded and the slice is paused.

## Boundary

This checkpoint gathers and qualifies context. It does not make material decisions, authorize implementation, or declare verification complete.

## Related concepts

- [Coding Context Exchange](../layer-01-fundamental-concepts/context-exchange.md) — locate Memory capsule and freshness ownership.
- [Coding Session Context Firewall](../layer-01-fundamental-concepts/session-context-firewall.md) — locate raw-state ingress and fact-return ownership.
- [Project-memory and code-structure capability](../layer-01-fundamental-concepts/LSP-MCP-Tools.md) — locate reusable project knowledge and structured code navigation.
