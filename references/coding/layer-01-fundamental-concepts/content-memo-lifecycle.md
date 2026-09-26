# Worker Content Memo Lifecycle

[English](content-memo-lifecycle.md) | [简体中文](content-memo-lifecycle_zh_cn.md)

This module defines creation, update, cleanup, and local-index discoverability for a Worker's file-backed execution memo. It does not define memo content, the dispatch switch, handoff or replacement strategy, or task acceptance.

## General rules

### Creation and update

Create or update `content-memo.md`, or an existing equivalent document identified as the memo, when reusable execution state first appears and at material milestones, a blocking boundary, handoff, replacement, or normal exit.

### Cleanup and discoverability

Cleanup and compaction must preserve the `content-memo.md` content contract rather than turn the memo into a command journal. The memo must remain discoverable from the Worker's local index.

## Codex CLI / ChatGPT Desktop optimizations

No provider-specific optimization instructions at present; follow the general rules above.

## Claude Code CLI / Claude Desktop optimizations

No provider-specific optimization instructions at present; follow the general rules above.

## Related concepts

- [Worker Content Memo](content-memo.md) — locate the memo content contract.
- [Worker Content Memo Dispatch](content-memo-dispatch.md) — locate the memo dispatch switch.
