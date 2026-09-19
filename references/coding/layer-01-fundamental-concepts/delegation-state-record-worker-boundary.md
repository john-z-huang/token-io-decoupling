# Coding Delegation State Record Worker Boundary

[English](delegation-state-record-worker-boundary.md) | [简体中文](delegation-state-record-worker-boundary_zh_cn.md)

This module owns released Worker snapshots, Worker read/write boundaries, parent-controlled Dispatch entry, and the block that applies when the task-control record cannot be persisted or returned. It consumes the record defined by [the delegation state record](delegation-state-record.md); it does not define record shape, mode/count policy, child lifecycle, or Dispatch Preview strategy.

## Worker snapshot and access boundary

Workers receive only the relevant released snapshot through the parent-controlled Dispatch. They must not infer, mutate, or replace the root record. The Worker may use the snapshot only within the released scope and return the required facts through the parent-controlled path.

## Dispatch entry and persistence block

After release, a Worker enters through the parent-provided Dispatch Preview and does not reopen the root-user mode or count gates. If the runtime cannot persist or return the task-control record, the dependent route is blocked.

## Related concepts

- [Coding Delegation State Record](delegation-state-record.md) — locate record ownership and field constraints.
- [Coding Child Dispatch](delegation-child-dispatch.md) — locate Worker dispatch boundaries.
- [Coding Execution Control](execution-control.md) — locate released Interaction Slice boundaries.
- [Coding Context Exchange](context-exchange.md) — locate named context transport ownership.
