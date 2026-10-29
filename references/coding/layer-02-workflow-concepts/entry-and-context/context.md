# Context Checkpoint

[English](context.md) | [简体中文](context_zh_cn.md)

## Actions

1. Define the smallest question the next slice must answer.
2. Read only the files, metadata, history, or generated evidence needed for that question.
3. Before reusing cached or file-backed context, check its scope, owner, source paths, freshness, and final-state epoch.
4. Treat stale, incomplete, or conflicting context as unusable. Refresh only the affected context and record what changed.
5. Keep context factual and routing-oriented; do not use it as a replacement for the Contract, source documents, or verification.
6. For a rule lookup selected by the applicable workflow decision node, apply [Enhanced Rule Context](../../layer-01-fundamental-concepts/enhanced-native-state/enhanced-rule-context.md): verify the requested node, owner, language, and source/hash, then read any necessary direct owner that the excerpt does not include. Keep the returned context bounded and confirm required owner content before relying on it.
7. When a released Worker must persist a memo or exchange record, require the named persistent-memory capability and confirm its availability; memo and cross-Worker exchange remain independent triggers. Apply the linked Layer-01 owner for logical ownership. If the capability is unavailable, report it and block dependent work; do not fall back to file storage.
8. When a released task requires reusable Agent project knowledge from prior work, use the [project-memory and code-structure capability](../../layer-01-fundamental-concepts/session-runtime/LSP-MCP-Tools.md) to access authorized Memory and check its source pointers and freshness against authoritative project files. Report unavailable capability; return to approved authoritative project files and pause only when an essential fact cannot be confirmed another approved way. A memory does not replace an authoritative project file in the approved paths.

## Pass condition

The next slice has bounded, current context, or the exact missing context is recorded and the slice is paused.

## Boundary

This checkpoint gathers and qualifies context. It does not make material decisions, authorize implementation, or declare verification complete.

## Related concepts

- [Coding Context Exchange](../../layer-01-fundamental-concepts/context-exchange/context-exchange.md) — locate Memory capsule and freshness ownership.
- [Coding Session Context Firewall](../../layer-01-fundamental-concepts/session-runtime/session-context-firewall.md) — locate raw-state ingress and fact-return ownership.
- [Project-memory and code-structure capability](../../layer-01-fundamental-concepts/session-runtime/LSP-MCP-Tools.md) — locate reusable project knowledge and structured code navigation.
