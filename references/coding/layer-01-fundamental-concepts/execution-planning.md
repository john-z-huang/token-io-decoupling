# Coding Execution Planning

[English](execution-planning.md) | [简体中文](execution-planning_zh_cn.md)

This module owns two-level execution planning: converting an approved direction into a bounded plan and stage outline, and ordering reconnaissance before implementation release. It does not define decision-gate policy, Interaction Slice fields, stage feedback, role/session semantics, context transport, or delegation lifecycle.

## General rules

### Two-level planning

Translate an approved direction into bounded inspection, implementation, and focused-check steps. The plan records the stage outline and the evidence each stage is expected to produce without turning stages into a command list.

### Reconnaissance to implementation release

When project facts are needed before a material decision, plan a bounded reconnaissance slice that returns compressed facts, evidence-backed options, and unresolved questions. The decision gate then confirms or rejects the direction before implementation is released. Planning does not approve a new semantic or architecture direction.

## Codex CLI / ChatGPT Desktop optimizations

In an interactive Codex CLI or an Agent Session that exposes the direct `/plan` command, invoke `/plan` to enter Plan mode; optionally append the first planning request, for example `/plan Propose a migration plan for this service`. Codex uses that prompt to draft an execution plan before implementation. The command is unavailable while Codex is already working; when no direct `/plan` control is exposed, use the general bounded planning process. Keep the final stage outline in the parent task record or approved plan artifact rather than relying on the plan-mode transcript as a second policy owner. [OpenAI: slash commands](https://learn.chatgpt.com/docs/developer-commands).

## Claude Code CLI / Claude Desktop optimizations

In an existing Claude Code Session, use Plan mode for read-only stage drafting only when that Session directly exposes and authorizes the control; the launch-only flag and Session-identity boundary are owned by [Runtime and Model Provider Support](runtime-provider-support.md). Otherwise use the general bounded planning process. Preserve the stage/evidence outline in the approved plan artifact or parent task record rather than turning a Plan-mode transcript into another policy owner. Before editing, confirm both the released Interaction Slice and effective tool permissions. `/tasks` reports running/background Agent work; it is not a durable plan record or a substitute for stage checkpoints. [Anthropic: workflows](https://code.claude.com/docs/en/common-workflows), [Anthropic: background agents](https://code.claude.com/docs/en/sub-agents).

## Related concepts

- [Coding Execution Control](execution-control.md) — locate Interaction Slice release and boundary control.
- [Coding Execution Decision Gate](execution-decision-gate.md) — locate Decision Brief and implementation-release decisions.
- [Coding Execution Stage Feedback](execution-stage-feedback.md) — locate bounded-stage feedback.
- [Coding Session Model](session-model.md) — locate role and Session ownership.
- [Coding Context Exchange](context-exchange.md) — locate context transport ownership.
- [Coding Child Lifecycle](delegation-child-lifecycle.md) — locate delegation lifecycle ownership.
