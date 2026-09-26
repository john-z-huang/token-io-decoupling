# Context Checkpoint

[English](context.md) | [简体中文](context_zh_cn.md)

## Actions

1. Define the smallest question the next slice must answer.
2. Read only the files, metadata, history, or generated evidence needed for that question.
3. Before reusing cached or file-backed context, check its scope, owner, source paths, freshness, and final-state epoch.
4. Treat stale, incomplete, or conflicting context as unusable. Refresh only the affected context and record what changed.
5. Keep context factual and routing-oriented; do not use it as a replacement for the Contract, source documents, or verification.
6. When a released Worker enables a file-backed memo, require its context workspace, permissions, and local index even when no cross-Worker exchange is needed; the file-backed-exchange and memo triggers are independent.

## Pass condition

The next slice has bounded, current context, or the exact missing context is recorded and the slice is paused.

## Boundary

This checkpoint gathers and qualifies context. It does not make material decisions, authorize implementation, or declare verification complete.

## Related concepts

- [Coding Context Exchange](../layer-01-fundamental-concepts/context-exchange.md) — locate file-backed capsule and freshness ownership.
- [Coding Session Context Firewall](../layer-01-fundamental-concepts/session-context-firewall.md) — locate raw-state ingress and fact-return ownership.
