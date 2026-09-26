# Coding Execution Planning

[English](execution-planning.md) | [简体中文](execution-planning_zh_cn.md)

This module owns two-level execution planning: converting an approved direction into a bounded plan and stage outline, and ordering reconnaissance before implementation release. It does not define decision-gate policy, Interaction Slice fields, stage feedback, role/session semantics, context transport, or delegation lifecycle.

## General rules

### Two-level planning

Translate an approved direction into bounded inspection, implementation, and focused-check steps. The plan records the stage outline and the evidence each stage is expected to produce without turning stages into a command list.

### Reconnaissance to implementation release

When project facts are needed before a material decision, plan a bounded reconnaissance slice that returns compressed facts, evidence-backed options, and unresolved questions. The decision gate then confirms or rejects the direction before implementation is released. Planning does not approve a new semantic or architecture direction.

## Codex CLI / ChatGPT Desktop optimizations

In an interactive Codex CLI or supported Desktop Codex chat, `/plan` can organize the approved direction as short stages and expected evidence before edits. Keep the final stage outline in the parent task record or approved plan artifact rather than relying on the plan-mode transcript as a second policy owner. A Desktop local environment's setup scripts and reusable actions apply to the selected project/worktree only; they prepare execution but do not authorize new stages, agents or mutations. [OpenAI: slash commands](https://learn.chatgpt.com/docs/developer-commands), [OpenAI: local environments](https://learn.chatgpt.com/docs/environments/local-environment).

## Claude Code CLI / Claude Desktop optimizations

In Claude Code, Plan mode may help draft the approved direction without making repository changes; use the stage/evidence outline from the general rules rather than converting a `/plan` transcript into another policy owner. After planning, confirm the permitted interaction slice and executable tool permissions before any edit. `/tasks` is a view of running/background Agent work, not a durable plan database or a substitute for stage checkpoints. In Desktop Code, the graphical plan/permission selector is a human-facing control for that Code session; an Agent may change planning or permissions only through direct Session-exposed controls, never through Desktop GUI automation. [Anthropic: workflows](https://code.claude.com/docs/en/common-workflows), [Anthropic: background agents](https://code.claude.com/docs/en/sub-agents), [Anthropic: desktop mode selector](https://code.claude.com/docs/en/desktop).

## Related concepts

- [Coding Execution Control](execution-control.md) — locate Interaction Slice release and boundary control.
- [Coding Execution Decision Gate](execution-decision-gate.md) — locate Decision Brief and implementation-release decisions.
- [Coding Execution Stage Feedback](execution-stage-feedback.md) — locate bounded-stage feedback.
- [Coding Session Model](session-model.md) — locate role and Session ownership.
- [Coding Context Exchange](context-exchange.md) — locate context transport ownership.
- [Coding Child Lifecycle](delegation-child-lifecycle.md) — locate delegation lifecycle ownership.
