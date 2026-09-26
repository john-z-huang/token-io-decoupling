# Coding Child Lifecycle

[English](delegation-child-lifecycle.md) | [简体中文](delegation-child-lifecycle_zh_cn.md)

This module owns persistence and lifecycle states for created Multi-Agent children. It consumes a child whose creation, allocation, and dispatch have already been handled by their owner concepts; it does not define creation, role allocation, Dispatch Preview, Worker boundaries, reuse/replacement, or context transport.

## General rules

### Lifecycle states

Keep each created child's identity and lifecycle persistent in the parent record. On runtimes with a durable task panel, do not close, shut down, archive, delete, or remove a child merely as cleanup. If a runtime status view is temporary, retain the child ID and status in the parent record after its UI row disappears. While pending or running, wait or send only authorized input. A child may become completed only after returning its final result and evidence.

### Error and interruption

On error or interruption, preserve the original child's identity, explicit lifecycle state, and available evidence. Do not close it as cleanup without authorization. The reuse/replacement owner decides whether an authorized follow-up through that same child is possible and what to do if it is not; the lifecycle owner only records the resulting state and blocker. Do not infer permission to create a successor or to recycle an allocation from a lifecycle transition.

## Codex CLI / ChatGPT Desktop optimizations

Codex can also expose configured `SubagentStart`/`SubagentStop` hooks for child IDs and observed lifecycle; `SubagentStart` with `continue: false` does **not** block spawning. Preserve the actual child ID and final evidence in the parent record even if the task UI or hook report disappears. These events are observational and do not authorize replacement or prove verification passed. [OpenAI: lifecycle hooks](https://learn.chatgpt.com/docs/hooks).

### Codex thread observation

When the active Agent Session exposes `/agent` or a direct subagent-status/result tool, use it to obtain active work and returned summaries without moving whole transcripts into the parent context. The Desktop Codex thread/activity panel is human-facing UI; never inspect it through Computer Use or infer the Agent can read it without a session-exposed tool. An approval for an inactive CLI child can surface over the current thread and identifies the originating thread; resolve it only after checking the source and authorized operation. If a non-interactive host cannot surface a fresh approval, the action fails and the parent must record the blocked slice. A `SubagentStop` hook is observational; neither a Done label nor an empty activity panel supersedes final evidence or grants cleanup/replacement authority. [OpenAI: subagent thread controls and approvals](https://learn.chatgpt.com/docs/agent-configuration/subagents), [OpenAI: hooks](https://learn.chatgpt.com/docs/hooks).

## Claude Code CLI / Claude Desktop optimizations

Use the `Agent` result and `/tasks` when available to observe a running child; use a bounded runtime wait for its result. `/tasks` is temporary, so retain the returned Agent ID and completed or error state in the parent record after its entry disappears.

### Event-assisted observation

In a Claude Code session that actually exposes Hooks, an optional `SubagentStart` hook can record the emitted `agent_id`/`agent_type`; an optional `SubagentStop` hook can observe `agent_id`, `agent_transcript_path`, and `last_assistant_message` without copying the full transcript into the parent context. Reconcile those signals with the actual `Agent` result and parent state record; a hook event alone does not prove successful completion or grant permission to close, replace, or create a child. Record failures and partial output distinctly. `/tasks` is a convenience view, not the durable source of truth; retain ID and evidence when a row disappears. Hooks require actual Claude Code runtime support and are not assumed for Desktop Chat or Cowork.

Official references: [SubagentStart/SubagentStop event inputs](https://code.claude.com/docs/en/hooks), [subagent lifecycle and resume](https://code.claude.com/docs/en/sub-agents).

An exhausted `maxTurns`, failed `Agent` call or incomplete/background result is partial or interrupted until the parent verifies actual output and return conditions. Disappearance from `/tasks` is not completion evidence. [Anthropic: subagent execution limits](https://code.claude.com/docs/en/sub-agents).

## Related concepts

- [Coding Child Creation](delegation-child-creation.md) — locate child creation capability.
- [Coding Child Role Allocation](delegation-child-role-allocation.md) — locate slot and role allocation.
- [Coding Child Dispatch](delegation-child-dispatch.md) — locate Dispatch Preview and Worker boundary.
- [Coding Child Reuse and Replacement](delegation-child-reuse-replacement.md) — locate authorized repair and replacement relations.
- [Coding Context Exchange](context-exchange.md) — locate context transport ownership.
