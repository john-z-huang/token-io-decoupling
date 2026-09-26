# Coding Execution Planning

[English](execution-planning.md) | [简体中文](execution-planning_zh_cn.md)

This module owns two-level execution planning: converting an approved direction into a bounded plan and stage outline, and ordering reconnaissance before implementation release. It does not define decision-gate policy, Interaction Slice fields, stage feedback, role/session semantics, context transport, or delegation lifecycle.

## General rules

### Two-level planning

Translate an approved direction into bounded inspection, implementation, and focused-check steps. The plan records the stage outline and the evidence each stage is expected to produce without turning stages into a command list.

### Reconnaissance to implementation release

When project facts are needed before a material decision, plan a bounded reconnaissance slice that returns compressed facts, evidence-backed options, and unresolved questions. The decision gate then confirms or rejects the direction before implementation is released. Planning does not approve a new semantic or architecture direction.

## Codex CLI / ChatGPT Desktop optimizations

No provider-specific optimization instructions at present; follow the general rules above.

## Claude Code CLI / Claude Desktop optimizations

No provider-specific optimization instructions at present; follow the general rules above.

## Related concepts

- [Coding Execution Control](execution-control.md) — locate Interaction Slice release and boundary control.
- [Coding Execution Decision Gate](execution-decision-gate.md) — locate Decision Brief and implementation-release decisions.
- [Coding Execution Stage Feedback](execution-stage-feedback.md) — locate bounded-stage feedback.
- [Coding Session Model](session-model.md) — locate role and Session ownership.
- [Coding Context Exchange](context-exchange.md) — locate context transport ownership.
- [Coding Child Lifecycle](delegation-child-lifecycle.md) — locate delegation lifecycle ownership.
