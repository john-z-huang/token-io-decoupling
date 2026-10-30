# Coding Context Exchange Workspace Boundary

[English](context-exchange-workspace-boundary.md) | [简体中文](context-exchange-workspace-boundary_zh_cn.md)

This owner defines logical naming and authorization for Agent-facing context records persisted as Serena project Memories. It does not define code-workspace filesystem permissions, capsule content, freshness, or handoff authorization.

## General rules

### Memory names and logical ownership

Use Serena project Memory names for context records. Under the default project data directory, names map beneath `.serena/memories/`, slash segments create subdirectories, and Serena adds `.md`; follow configured overrides. Preserve the former record layout in names: `context-exchange/INDEX`; `context-exchange/workers/<worker-context-id>/INDEX`; `context-exchange/workers/<worker-context-id>/content-memo`; and `context-exchange/context-bootstrap/MANIFEST`, `.../project-context`, and `.../policy-context`. Map other handoff/import records using their existing basenames and subdirectory intent.

A memory name expresses logical ownership only. Serena does not provide Worker-level visibility isolation, read-only ACLs, or OS/RW/RO/DENY enforcement for Memory records. The tool may expose listed memories to any authorized Session. Agents must follow the released task's instructions about which names they may read or write, but neither the namespace nor Serena's project-wide patterns technically enforce that rule. Do not claim these records are protected by directories, `.gitignore`, worktrees, or filesystem permissions.

Keep source-code and authoritative repository-file access within their separately approved filesystem/tool boundaries. A Memory capsule may contain concise facts, exact authoritative source pointers, hashes, freshness, and scope; do not store full source documents as authoritative copies. Parent live mode/count/allocation/epoch state remains in its existing owner, not these memories. Secrets, full transcripts, and private reasoning remain prohibited.

If Serena Memory tools are unavailable, report the limitation and block work that depends on reading or writing the context record. Do not fall back to a file-backed copy. Independent work may continue.

## Codex CLI / ChatGPT Desktop optimizations

Use only Serena Memory tools exposed and authorized to the active Session. List and read named records before relying on them; write only the names authorized in the released task and confirm the result. Codex filesystem sandbox or worktree settings still govern source files, but do not create or imply per-Worker Memory isolation.

## Claude Code CLI / Claude Desktop optimizations

Use Serena Memory only when the active Agent Session exposes and authorizes the relevant MCP tools. Claude Code MCP Tool Search may defer tool definitions, so discover and verify the actual tools first. Claude auto memory, worktree isolation, and filesystem rules do not provide Serena Memory isolation. If unavailable, follow the general report/block rule.

## Related concepts

- [Coding Context Exchange](context-exchange.md) — locate capsule content and freshness rules.
- [Coding Context Exchange Handoff](context-exchange-handoff.md) — locate handoff record content.
- [Coding Session Context Firewall](../session-runtime/session-context-firewall.md) — locate bounded ingress rules.
- [Coding Child Dispatch](../delegation/delegation-child-dispatch.md) — locate released-task authorization.
