# Worker Content Memo Dispatch

[English](content-memo-dispatch.md) | [简体中文](content-memo-dispatch_zh_cn.md)

This module defines the parent-controlled `write_content_memo` dispatch switch for a Worker's file-backed execution memo. It does not define memo content, memo lifecycle, context transport, or child lifecycle.

## General rules

### Dispatch switch

The parent sets:

```text
write_content_memo: true
```

`true` is the default, including when the field is omitted. It enables the file-backed memo for the dispatch. `false` suppresses only the file-backed memo and is appropriate only when memo cost clearly exceeds likely reuse, recovery, or handoff value.

Internal dispatch configuration may omit the field and use this `true` default. Before the parent serializes a released task bundle, it must write `write_content_memo: true` or `write_content_memo: false` explicitly. A Worker consumes only the explicit value in its released bundle; if the released bundle omits the field, the dispatch is incomplete and the Worker must not infer a default.

### Parent authority

The Worker cannot change or reinterpret the switch. Only the parent may choose a value for a later slice. This authority controls memo file materialization only; it does not grant any other scope or capability.

## Codex CLI / ChatGPT Desktop optimizations

No provider-specific optimization instructions at present; follow the general rules above.

## Claude Code CLI / Claude Desktop optimizations

Claude Code's `Agent` prompt and custom subagent definition do not automatically implement this Skill's `write_content_memo` switch. Before invoking an authorized Worker, serialize `write_content_memo: true` or `false` in that Worker's released task bundle and ensure its writable memo directory exists when enabled. Do not rely on a default implicit in `Agent`, a `SubagentStop` hook, or the parent's auto memory to create the file-backed memo. When disabled, omit the memo write but retain the separately required return evidence. [Anthropic: subagent configuration](https://code.claude.com/docs/en/sub-agents), [Anthropic: memory](https://code.claude.com/docs/en/memory).

## Related concepts

- [Worker Content Memo](content-memo.md) — locate the memo content contract.
- [Worker Content Memo Lifecycle](content-memo-lifecycle.md) — locate memo lifecycle rules.
