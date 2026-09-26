# Worker Content Memo Lifecycle

[English](content-memo-lifecycle.md) | [简体中文](content-memo-lifecycle_zh_cn.md)

This module defines creation, update, cleanup, and local-index discoverability for a Worker's file-backed execution memo. It does not define memo content, the dispatch switch, handoff or replacement strategy, or task acceptance.

## General rules

### Creation and update

Create or update `content-memo.md`, or an existing equivalent document identified as the memo, when reusable execution state first appears and at material milestones, a blocking boundary, handoff, replacement, or normal exit.

### Cleanup and discoverability

Cleanup and compaction must preserve the `content-memo.md` content contract rather than turn the memo into a command journal. The memo must remain discoverable from the Worker's local index.

## Codex CLI / ChatGPT Desktop optimizations

When this Codex runtime has configured `PreCompact` or `SubagentStop` hooks, use the event as an observation that an owned memo may need updating; do not assume the hook serializes the memo, knows every relevant source, or can write to another Worker's directory. The Worker still updates its explicitly authorized memo/index before source evidence is lost. [OpenAI: lifecycle/compaction hooks](https://learn.chatgpt.com/docs/hooks).

A trusted, enabled Codex `PreCompact` or `SubagentStop` hook may identify an imminent context-loss or exit boundary; after compaction, a `SessionStart` hook with `source: compact` can supply small approved context to the continuation. Hooks do not serialize a correct Worker memo automatically, and concurrent hook outputs are not an ordered write transaction. The Worker must update its own allowed memo/index at actual material milestones while evidence is still available, and must not write another Worker's folder. [OpenAI: hook lifecycle, trust and compact restart](https://learn.chatgpt.com/docs/hooks).

## Claude Code CLI / Claude Desktop optimizations

### Compaction- and exit-aware memo checkpoints

Where local Claude Code Hooks are configured and `write_content_memo: true`, an optional `PreCompact` hook can detect impending compaction and check whether the existing, permitted memo/index is current **before** compaction; it cannot be assumed to prompt the Agent to write new state, and `SubagentStop` may surface the final message to the parent for a last memo/index check. These event signals do not themselves write a correct memo, and a generic hook that copies an entire transcript violates the memo content contract. Maintain the memo at ordinary material milestones independently of hooks, keep its exact named path in the Worker index, and never run the hook workflow when memo is explicitly disabled. Hooks require their scripts to be available and trusted in the actual Claude Code session; do not infer they run in Desktop Chat/Cowork.

Official reference: [PreCompact and SubagentStop hooks](https://code.claude.com/docs/en/hooks).

Even after `PreCompact` or `SubagentStop` fires, a hook cannot reconstruct missing source evidence or retroactively satisfy a skipped memo update. Keep ownership and write scope with the Worker rather than copying an incomplete hook transcript to the parent's memo. [Anthropic: compaction and child-stop hooks](https://code.claude.com/docs/en/hooks).

## Related concepts

- [Worker Content Memo](content-memo.md) — locate the memo content contract.
- [Worker Content Memo Dispatch](content-memo-dispatch.md) — locate the memo dispatch switch.
