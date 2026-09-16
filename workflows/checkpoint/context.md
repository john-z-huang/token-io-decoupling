# Context Checkpoint

[English](context.md) | [简体中文](context_zh_cn.md)

## Actions

1. Define the smallest question the next slice must answer.
2. Read only the files, metadata, history, or generated evidence needed for that question.
3. Before reusing cached or file-backed context, check its scope, owner, source paths, freshness, and final-state epoch.
4. Treat stale, incomplete, or conflicting context as unusable. Refresh only the affected context and record what changed.
5. Keep context factual and routing-oriented; do not use it as a replacement for the Contract, source documents, or verification.

## Pass condition

The next slice has bounded, current context, or the exact missing context is recorded and the slice is paused.

## Boundary

This checkpoint gathers and qualifies context. It does not make material decisions, authorize implementation, or declare verification complete.
