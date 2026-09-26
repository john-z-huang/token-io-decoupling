# Coding Child Dispatch

[English](delegation-child-dispatch.md) | [简体中文](delegation-child-dispatch_zh_cn.md)

This module owns material Dispatch Preview and the Worker boundary. It consumes an already authorized child and slice; it does not define child creation, role allocation, reuse or replacement, lifecycle, or Interaction Slice fields.

## General rules

### Dispatch Preview and return boundary

Before assigning or materially dispatching to a child, verify that Input-side Reasoning has completed its prerequisite instruction, environment, and task-defining code-fact confirmations with source pointers, and that a concrete Interaction Slice was released. The parent shows a concise Dispatch Preview of the authorized objective, mutations, and return conditions; a missing prerequisite keeps the slice with the parent. A Worker returns only to its direct parent and cannot create, fork, hand off to, message, replace, or coordinate another Agent or Session, or contact arbitrary threads. Contradictory findings return to the parent for a new decision, not a new mode or count.

### Named paths and slice release

Check each Worker's named-path and directory permissions under [context workspace boundary](context-exchange-workspace-boundary.md); consume the released Interaction Slice under [execution control](execution-control.md). Dispatch one slice at a time unless independent, non-conflicting parallel work is explicitly allowed. Do not redefine directory layout or slice fields here.

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
