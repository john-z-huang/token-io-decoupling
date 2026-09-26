# Coding Execution Control

[English](execution-control.md) | [简体中文](execution-control_zh_cn.md)

This module owns Interaction Slice control: slice release fields, boundary behavior, and Control Checkpoint choices. It assumes that planning, decision gates, stage feedback, role/session context, runtime capabilities, context transport, and delegation lifecycle are supplied by their owning concepts. It does not define those policies.

## General rules

### Interaction Slice

Release one **Interaction Slice** at a time for non-simple work. Every slice states:

- `Objective`: the result it must produce;
- `Authorized scope/mutations`: paths, behavior, and writes allowed;
- `Return conditions`: the evidence or milestone that ends it;
- `Unreleased boundary`: the next subsystem, risk domain, semantic choice, or mutation that remains blocked.

A slice is a control unit, not a command-by-command script. The executor may continue through low-decision-density mechanics while the Contract and boundary remain unchanged. It must pause at the return conditions or before crossing the unreleased boundary. A simple fast-path task may remain one slice through implementation and focused checks.

### Slice ordering

Release slices in parallel only when they are independent and non-conflicting. Dependencies, shared write targets, or ordered results require sequential release. Context transport and parent-only feedback follow their respective owner protocols and are not defined here.

### Control Checkpoint

At a material boundary, use a compressed Control Checkpoint with the status, findings, changed scope, verification, issue, need, and unreleased boundary that matter to the next decision. The input-side responsibility chooses `Continue`, `Amend`, or `Stop`; `Continue` releases only the next bounded slice, and `Amend` changes the Contract or boundary before work resumes. In a Single-Agent route, this is an internal reasoning pause rather than a simulated self-message.

## Codex CLI / ChatGPT Desktop optimizations

No provider-specific optimization instructions at present; follow the general rules above.

## Claude Code CLI / Claude Desktop optimizations

No provider-specific optimization instructions at present; follow the general rules above.

## Related concepts

- [Coding Execution Planning](execution-planning.md) — locate bounded planning and reconnaissance-to-implementation relations.
- [Coding Execution Decision Gate](execution-decision-gate.md) — locate Decision Brief and decision-release rules.
- [Coding Execution Stage Feedback](execution-stage-feedback.md) — locate bounded-stage feedback rules.
- [Coding Context Exchange](context-exchange.md) — locate context transport ownership.
- [Coding Child Dispatch and Lifecycle](delegation-child-lifecycle.md) — locate delegation lifecycle ownership for released slices.
