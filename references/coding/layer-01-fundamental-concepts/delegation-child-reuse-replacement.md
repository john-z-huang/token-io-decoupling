# Coding Child Reuse and Replacement

[English](delegation-child-reuse-replacement.md) | [简体中文](delegation-child-reuse-replacement_zh_cn.md)

This module owns authorized follow-up, repaired epochs, and reuse or replacement relations for created children. It does not define child creation, role allocation, Dispatch Preview, Worker boundaries, lifecycle states, or context transport.

## General rules

### Authorized reuse

For authorized follow-ups, repaired epochs, and interruptions, reuse the same created child when safe. First attempt an authorized repair through that child; if it cannot safely continue, report the blocker and set dependent Multi-Agent work to `blocked`. Reuse must not create a recursive hierarchy or peer coordination. Retain the created child's identity and evidence according to the lifecycle owner.

### Replacement relation

A plan-level revision is allowed for an `agent: unbound` reserved allocation after count locking and before that slot's child is created. It may adjust an unbound role or pending slice only within the locked count and with parent authorization. Before count locking the awaiting-count record has no allocation to replace. A created child's slot cannot be recycled, and after locking no additional or replacement child may be created. Do not reopen the count question, fork, or hand off to a new child. Context handoff is owned by [Coding Context Exchange Handoff](context-exchange-handoff.md) and does not grant an Agent-creation capability.

## Codex CLI / ChatGPT Desktop optimizations

No provider-specific optimization instructions at present; follow the general rules above.

## Claude Code CLI / Claude Desktop optimizations

Use `SendMessage` with the returned Agent ID for an authorized follow-up or repair of the same child. Calling `Agent` again creates another child and consumes another slot; do not use it for reuse after count locking.

### Resume identity, do not respawn

Resume an authorized persistent `general-purpose` or custom subagent with `SendMessage` addressed to its returned `agent_id` (or the supported agent name) and a narrow repair/follow-up prompt. A fresh `Agent` invocation creates a distinct instance even if its type and prompt match; never use it as a hidden replacement under the locked budget. Built-in `Explore` and `Plan` are one-shot and return no resumable ID; do not assign them to a slot that requires later follow-up. If resume fails, preserve the error and block dependent work rather than trying another child. Claude Desktop Chat connector invocations or side chats are not a substitute for this persistent identity.

Official reference: [resume subagents](https://code.claude.com/docs/en/sub-agents).

An agent-team message, `/branch`, or a separate Desktop pane cannot substitute for resuming the recorded Agent identity. If the original child ID is no longer resumable, keep its evidence and block the dependent slice; do not spend an unapproved replacement slot. [Anthropic: subagent resume](https://code.claude.com/docs/en/sub-agents).

## Related concepts

- [Coding Child Creation](delegation-child-creation.md) — locate child creation capability.
- [Coding Child Role Allocation](delegation-child-role-allocation.md) — locate slot and role allocation.
- [Coding Child Dispatch](delegation-child-dispatch.md) — locate material dispatch boundaries.
- [Coding Child Lifecycle](delegation-child-lifecycle.md) — locate child state and recovery ownership.
- [Coding Context Exchange](context-exchange.md) — locate handoff and context transport ownership.
