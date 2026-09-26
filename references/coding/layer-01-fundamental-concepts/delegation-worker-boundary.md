# Coding Delegation Worker Boundary

[English](delegation-worker-boundary.md) | [简体中文](delegation-worker-boundary_zh_cn.md)

This module owns released Worker snapshots, Worker read/write boundaries, parent-controlled Dispatch entry, and the block that applies when the task-control record cannot be persisted or returned. It consumes the record defined by [the delegation state record](delegation-state-record.md); it does not define record shape, mode/count policy, child lifecycle, or Dispatch Preview strategy.

## General rules

### Worker snapshot and access boundary

Workers receive only the relevant released snapshot through the parent-controlled Dispatch. They must not infer, mutate, or replace the root record. The Worker may use the snapshot only within the released scope and return the required facts through the parent-controlled path.

### Dispatch entry and persistence block

After release, a Worker enters through the parent-provided Dispatch Preview and does not reopen the root-user mode or count gates. If the runtime cannot persist or return the task-control record, the dependent route is blocked.

## Codex CLI / ChatGPT Desktop optimizations

Codex's configured `PreToolUse` hook can match the local `spawn_agent` tool under its `Agent` alias; where available, use it as a tested guardrail against unauthorized nested delegation, alongside the runtime's actual tool/sandbox restrictions. Some specialized tools bypass hook coverage, so a prompt or hook alone is not proof that recursion or peer messaging is impossible. Keep the parent-controlled spawn/follow-up role separate from Worker permissions. [OpenAI: hook tool coverage](https://learn.chatgpt.com/docs/hooks).

## Claude Code CLI / Claude Desktop optimizations

### Scoped worker tools

For an approved Claude Code custom Worker, restrict the frontmatter `tools` allowlist and/or `disallowedTools` so the Worker cannot call `Agent` or peer-messaging tools. An Agent tool made available to the Worker can create nested subagents in current Claude Code; a prose-only prohibition is not a reliable tool boundary. If an MCP server is needed, grant only the required server/tool scope and deny unrelated MCP tools (for example, supported `mcp__<server>` patterns); this narrows tool availability, not the parent's record ownership. Project/user agent definitions can also scope `mcpServers`, but plugin-shipped agent frontmatter ignores that field. Do not assume the same restrictions are installed in Desktop Chat.

Official reference: [subagent tools, disallowedTools and MCP scope](https://code.claude.com/docs/en/sub-agents).

Before dispatch, check that the **effective**, inherited custom-agent tool pool matches the released role. Keep parent-to-child `SendMessage` and resume controls outside the Worker, and do not treat a narrowed `tools` list as a verified per-path filesystem boundary. [Anthropic: subagent tool scope](https://code.claude.com/docs/en/sub-agents).

## Related concepts

- [Coding Delegation State Record](delegation-state-record.md) — locate record ownership and field constraints.
- [Coding Child Dispatch](delegation-child-dispatch.md) — locate Worker dispatch boundaries.
- [Coding Execution Control](execution-control.md) — locate released Interaction Slice boundaries.
- [Coding Context Exchange](context-exchange.md) — locate named context transport ownership.
