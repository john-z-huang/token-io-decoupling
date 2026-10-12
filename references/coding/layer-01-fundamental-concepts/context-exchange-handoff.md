# Coding Context Exchange Handoff

[English](context-exchange-handoff.md) | [简体中文](context-exchange-handoff_zh_cn.md)

This owner defines content, updates, and successor exposure for handoff and Worker context-index records persisted as Serena project Memories. It does not authorize child reuse/replacement or define capsule freshness.

## General rules

### Context index and handoff records

Use `context-exchange/INDEX` for the parent-owned routing index and `context-exchange/workers/<worker-context-id>/INDEX` for a Worker's task, scope, status, latest material update, record names, and blocker/handoff target. Handoff records preserve achieved state, failed approaches with evidence, current changes and verification, blockers, next action, and exact authoritative source pointers. Update at material state/evidence/handoff changes, not after every command.

Map former handoff/import names to the same basename and subdirectory intent under `context-exchange/`. A successor reads only Memory names explicitly exposed in its released task; it must not write another Worker's names unless explicitly authorized. This is logical instruction ownership only, not technical isolation; Serena may expose records to any authorized Session. Never reconstruct a full transcript. If Memory tools are unavailable, report and block dependent work; do not fall back to files.

### Authorization boundary

A Context ID or memory name never authorizes creating/replacing an Agent or changing parent live task state. Keep mode/count/allocation/epoch state in its existing owner.

## Codex CLI / ChatGPT Desktop optimizations

Use only exposed, authorized Serena tools. Name the exact records in the released handoff, read only those records, verify source freshness, and confirm any write result. Thread/worktree transfer alone does not create or deliver a Memory handoff.

## Claude Code CLI / Claude Desktop optimizations

Use Serena MCP Memory only when exposed and authorized in the active Session; discover deferred MCP tools before relying on them. Claude resume/branch and auto memory do not authorize or deliver this record. If unavailable, follow the report/block rule.

## Related concepts

- [Coding Context Exchange](context-exchange.md) — locate capsule and freshness rules.
- [Coding Context Exchange Workspace Boundary](context-exchange-workspace-boundary.md) — locate logical naming and authorization.
- [Coding Session Context Firewall](session-context-firewall.md) — locate raw-state ingress.
- [Coding Child Reuse and Replacement](delegation-child-reuse-replacement.md) — locate replacement authorization.
