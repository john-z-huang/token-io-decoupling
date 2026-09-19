# Coding Child Dispatch

[English](delegation-child-dispatch.md) | [简体中文](delegation-child-dispatch_zh_cn.md)

This module owns material Dispatch Preview and the Worker boundary. It consumes an already authorized child and slice; it does not define child creation, role allocation, reuse or replacement, lifecycle, or Interaction Slice fields.

## Dispatch Preview and return boundary

Before each material Dispatch, issue a concise preview of the already authorized slice. A Worker returns only to its direct parent; it must not create, fork, hand off to, message, replace, or coordinate another Agent or Session, or contact arbitrary threads. Worker findings cannot change the root mode or count.

## Named paths and slice release

Keep each Worker's context-exchange directory separate and grant only named paths. Release one Interaction Slice at a time unless independent, non-conflicting parallel work is explicitly allowed. Interaction Slice fields and boundary controls are owned by [execution control](execution-control.md).

## Related concepts

- [Coding Child Creation](delegation-child-creation.md) — locate child creation capability.
- [Coding Child Role Allocation](delegation-child-role-allocation.md) — locate slot and role allocation.
- [Coding Child Lifecycle](delegation-child-dispatch-lifecycle.md) — locate child state and recovery ownership.
- [Coding Child Reuse and Replacement](delegation-child-reuse-replacement.md) — locate authorized reuse and replacement.
- [Coding Context Exchange](context-exchange.md) — locate named-path context transport ownership.
- [Coding Execution Control](execution-control.md) — locate Interaction Slice boundary controls.
