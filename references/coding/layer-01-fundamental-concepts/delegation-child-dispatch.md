# Coding Child Dispatch

[English](delegation-child-dispatch.md) | [简体中文](delegation-child-dispatch_zh_cn.md)

This module owns material Dispatch Preview and the Worker boundary. It consumes an already authorized child and slice; it does not define child creation, role allocation, reuse or replacement, lifecycle, or Interaction Slice fields.

## General rules

### Dispatch Preview and return boundary

Before assigning or materially dispatching to a child, the parent must itself analyze the instructions, confirm the project environment, and verify the code details needed to define the task. Record the supporting paths and facts, then issue a concise preview of the already authorized slice with a precise objective, mutations, and return conditions. Do not assign a child to perform these prerequisite confirmations. If a needed fact remains unconfirmed, keep the slice with the parent until it is confirmed. A Worker returns only to its direct parent; it must not create, fork, hand off to, message, replace, or coordinate another Agent or Session, or contact arbitrary threads. Worker findings that contradict a confirmed premise return to the parent for a new decision; they cannot change the root mode or count.

### Named paths and slice release

Keep each Worker's context-exchange directory separate and grant only named paths. Release one Interaction Slice at a time unless independent, non-conflicting parallel work is explicitly allowed. Interaction Slice fields and boundary controls are owned by [execution control](execution-control.md).

## Codex CLI / ChatGPT Desktop optimizations

No provider-specific optimization instructions at present; follow the general rules above.

## Claude Code CLI / Claude Desktop optimizations

No provider-specific optimization instructions at present; follow the general rules above.

## Related concepts

- [Coding Child Creation](delegation-child-creation.md) — locate child creation capability.
- [Coding Child Role Allocation](delegation-child-role-allocation.md) — locate slot and role allocation.
- [Coding Child Lifecycle](delegation-child-lifecycle.md) — locate child state and recovery ownership.
- [Coding Child Reuse and Replacement](delegation-child-reuse-replacement.md) — locate authorized reuse and replacement.
- [Coding Context Exchange](context-exchange.md) — locate named-path context transport ownership.
- [Coding Execution Control](execution-control.md) — locate Interaction Slice boundary controls.
