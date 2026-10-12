# Worker Content Memo Dispatch

[English](content-memo-dispatch.md) | [简体中文](content-memo-dispatch_zh_cn.md)

This owner defines the parent-controlled `write_content_memo` switch for a Worker's Serena Memory memo. It does not define memo content or lifecycle.

## General rules

### Dispatch switch

Every released bundle explicitly includes `write_content_memo: true` or `false`; a Worker never infers a default. `true` enables writes to `context-exchange/workers/<worker-context-id>/content-memo`; `false` disables that memo only. Include the exact memory name in the released bundle. The parent controls the switch and name, but this is logical ownership only: Serena does not enforce per-Worker access or read-only ACLs.

If Memory tools are not exposed and authorized, report the limitation and block the memo-dependent slice; do not materialize the memo as a file. Other independent work may continue.

## Codex CLI / ChatGPT Desktop optimizations

Serialize the switch and exact memory name in the actual released child-task prompt. Use only exposed, authorized Serena Memory tools and confirm the write result. Codex configuration, hooks, local memory, or compaction do not themselves implement this switch.

## Claude Code CLI / Claude Desktop optimizations

When the current Agent Session exposes and authorizes Serena MCP Memory tools, include the switch and name in the released bundle and confirm the write result. Claude auto memory, hooks, or compaction do not replace the named project Memory. If tools are unavailable, follow the general block/report rule.

## Related concepts

- [Worker Content Memo](content-memo.md) — locate the memo content contract.
- [Worker Content Memo Lifecycle](content-memo-lifecycle.md) — locate update rules.
- [Coding Context Exchange Workspace Boundary](context-exchange-workspace-boundary.md) — locate logical memory ownership rules.
