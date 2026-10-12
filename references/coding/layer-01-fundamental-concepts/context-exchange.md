# Coding Context Exchange

[English](context-exchange.md) | [简体中文](context-exchange_zh_cn.md)

This owner defines content and freshness rules for context capsules persisted as Serena project Memories for already-assigned Coding Workers. It does not define memory naming/authorization, handoff records, task meaning, Agent topology, or acceptance.

## General rules

### Capsule content and authoritative sources

Persist a capsule only when an authorized handoff or context bootstrap needs a durable record. Use concise neutral facts, exact pointers to authoritative sources, hashes, freshness/invalidation data, and narrow evidence pointers. Do not copy the full source documents into Memory; authoritative repository files remain binding. Receiving Workers read only capsule memories named in their released task, then verify needed facts against named approved sources.

Use these bootstrap Memory names, preserving former filenames: `context-exchange/context-bootstrap/MANIFEST`, `context-exchange/context-bootstrap/project-context`, and `context-exchange/context-bootstrap/policy-context`. `MANIFEST` records snapshot identity, hashes, and freshness rules; the other memories hold neutral project facts/pointers and policy-routing pointers. Other exchange/import records use their existing basename and subdirectory intent under `context-exchange/`.

Check freshness against `HEAD`/tree, tracked-delta fingerprint, listed source hashes, relevant untracked state, and active task/scope. Refresh only affected entries when material fields change; otherwise read named authoritative sources directly. A capsule never replaces Contract or independent final-state verification. Memory listing/read/write capability unavailable means report the limitation and block dependent work; do not use file-backed fallback.

## Codex CLI / ChatGPT Desktop optimizations

Use only exposed, authorized Serena Memory tools. Name the exact capsule Memory in the released task, read it before use, verify source pointers/freshness, and confirm writes. Do not broaden source or tool access just to make a capsule available.

## Claude Code CLI / Claude Desktop optimizations

Use Serena Memory only when the current Agent Session exposes and authorizes its MCP tools. Claude Code MCP Tool Search may defer definitions; discover and verify the tools before relying on them. Claude auto memory or compaction is not a replacement for a named exchange capsule.

## Related concepts

- [Coding Context Exchange Workspace Boundary](context-exchange-workspace-boundary.md) — locate logical naming and authorization.
- [Coding Context Exchange Handoff](context-exchange-handoff.md) — locate handoff record content.
- [Coding Session Context Firewall](session-context-firewall.md) — locate bounded ingress rules.
- [Coding Child Dispatch](delegation-child-dispatch.md) — locate released-task authorization.
