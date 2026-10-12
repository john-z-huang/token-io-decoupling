# Worker Content Memo

[English](content-memo.md) | [简体中文](content-memo_zh_cn.md)

This owner defines the content contract for a Worker execution memo persisted as a Serena project Memory. It does not define the dispatch switch or lifecycle.

## General rules

### Purpose and content

Use the memory name `context-exchange/workers/<worker-context-id>/content-memo`, which Serena maps to `.serena/memories/context-exchange/workers/<worker-context-id>/content-memo.md` under its default project data directory. Serena configuration may change that directory. The name identifies logical ownership only: Serena does not enforce Worker-specific visibility, read-only access, or filesystem isolation, and any Session with the relevant tools may see or change the Memory. Follow the released task's ownership instructions and never claim technical isolation.

Worker-authored prose uses Chinese. Preserve paths, filenames, commands, symbols, keys, hashes, exact errors, and log fragments in original form. Record only stable, reusable execution state: completed results, findings, changed paths/symbols, verification evidence, failed approaches, remaining work, blockers, and handoff needs. Keep accurate pointers to authoritative sources; do not store their full text as an authoritative copy.

### Prohibited material and unavailable capability

Do not write a per-command journal, full logs/diffs, large source copies, secrets, private reasoning, complete transcripts, unrelated history, or live parent mode/count/allocation/epoch state. If Serena Memory read/write is unavailable, report the limitation and block work that depends on this record; do not write the record to a file as fallback. Independent work may continue.

## Codex CLI / ChatGPT Desktop optimizations

Use only Serena Memory tools actually exposed and authorized in the current Session. Codex-local memories and `/compact` do not replace the named Serena Memory. Confirm a successful write result and verify the stored entry with `read_memory` when the active workflow requires it.

## Claude Code CLI / Claude Desktop optimizations

Use Serena Memory only if the current Session exposes and authorizes the relevant Serena MCP tools. Claude auto memory and compaction do not replace this named project Memory. Confirm the actual tool availability and write result; Serena Memory access is not shared or isolated by assumption.

## Related concepts

- [Worker Content Memo Dispatch](content-memo-dispatch.md) — locate the memory-write switch.
- [Worker Content Memo Lifecycle](content-memo-lifecycle.md) — locate update and discovery rules.
