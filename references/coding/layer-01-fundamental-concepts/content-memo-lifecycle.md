# Worker Content Memo Lifecycle

[English](content-memo-lifecycle.md) | [简体中文](content-memo-lifecycle_zh_cn.md)

This owner defines creation, update, cleanup, and discoverability for a Worker's Serena Memory memo. It does not define memo content, dispatch, handoff authorization, or acceptance.

## General rules

### Creation, update, and discovery

When `write_content_memo` is true, use `list_memories` to check the named entry and `write_memory` to create or update `context-exchange/workers/<worker-context-id>/content-memo` when reusable state first appears and at material milestones, blockers, handoff, replacement, or normal exit. Update only when state/evidence materially changes, not after every command. A parent or successor may read it only when the released instructions name or authorize it; Serena itself does not enforce that ownership rule. Do not create a local file index for these records; the name is discoverable through Serena's memory listing.

Memory capability failure must be reported and blocks dependent record use; never fall back to writing the record as a file. Preserve the content contract and do not turn it into a command journal.

## Codex CLI / ChatGPT Desktop optimizations

Hooks may signal a compaction or exit boundary but do not write or validate the named Memory. Use exposed, authorized Serena tools and confirm the write result; do not write another Worker's memory name unless the parent explicitly authorizes that record.

## Claude Code CLI / Claude Desktop optimizations

Only when Serena MCP Memory tools are exposed and authorized, use the named memory and verify the write result. Hooks or auto memory do not replace it. If unavailable, report the limitation and block dependent work.

## Related concepts

- [Worker Content Memo](content-memo.md) — locate the memo content contract.
- [Worker Content Memo Dispatch](content-memo-dispatch.md) — locate the memo switch.
