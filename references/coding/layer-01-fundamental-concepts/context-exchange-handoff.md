# Coding Context Exchange Handoff

[English](context-exchange-handoff.md) | [简体中文](context-exchange-handoff_zh_cn.md)

This module owns Worker-local context indexes, material context updates, handoff and replacement-state records, and successor exposure. It records context transport for an authorized handoff; it does not authorize child reuse or replacement, define capsule content, or define workspace capabilities.

## General rules

### Worker-local context records

Each Worker-local `INDEX.md` records only its task, scope, status, latest material update, document purposes, and blocker or handoff target. Add specialized documents only when they provide distinct reusable value. Update context files at material state, evidence, or handoff changes—not after every command.

### Handoff and successor exposure

Only an authorized context handoff may assign a new Context ID and directory to the receiver; a Context ID never authorizes creating or replacing an Agent. The receiver reads only predecessor documents explicitly exposed by the parent and never writes to its directory. Prefer exact references to stable facts in an existing [content memo](content-memo.md) instead of duplicating their state; when the memo is disabled or absent, record the minimum facts needed for recovery: achieved state, failed approaches and evidence, current changes and verification, blockers, and next action. The parent updates the root index, names source paths, and exposes only named documents; never reconstruct a complete transcript when the predecessor is unavailable.

## Codex CLI / ChatGPT Desktop optimizations

Use a Git/worktree or thread-transfer tool only when the active Session directly exposes and authorizes it. Such a tool may move a chat or checkout, but that does not make it this Skill's cross-Worker context handoff or deliver a named capsule to another allocated Agent. For a real Worker transfer, use the parent-approved source/import paths and record the receiving child identity. A managed worktree may be cleaned up, so verify source freshness before relying on previously exported files. [OpenAI: worktree behavior and cleanup](https://learn.chatgpt.com/docs/environments/git-worktrees).

## Claude Code CLI / Claude Desktop optimizations

If the original Claude Code child still has a resumable Agent ID, prefer an authorized `SendMessage` follow-up and named read-only source pointers instead of creating a new subagent or copying its transcript. If the original child cannot resume, transfer only the parent-approved handoff documents and current source evidence to an **already authorized** recipient; `/resume` for a parent Session or `/branch` does not itself authorize a child replacement. A local MCP tool exposed by Claude Desktop can provide permitted documents, but it does not create a shared Worker lifecycle. [Anthropic: subagent resume](https://code.claude.com/docs/en/sub-agents), [Anthropic: Desktop MCP tools](https://support.claude.com/en/articles/10949351-getting-started-with-local-mcp-servers-on-claude-desktop).

## Related concepts

- [Coding Context Exchange](context-exchange.md) — locate capsule and freshness ownership.
- [Coding Context Exchange Workspace Boundary](context-exchange-workspace-boundary.md) — locate directory and capability boundaries.
- [Coding Session Context Firewall](session-context-firewall.md) — locate raw-state ingress ownership.
- [Coding Child Reuse and Replacement](delegation-child-reuse-replacement.md) — locate reuse and replacement authorization ownership.
- [Coding Child Lifecycle](delegation-child-lifecycle.md) — locate child state and recovery ownership.
