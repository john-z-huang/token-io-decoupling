# Coding Delegation State Record

[English](delegation-state-record.md) | [简体中文](delegation-state-record_zh_cn.md)

This module owns the task-control record used by Coding delegation. It defines the record's canonical location, ownership, shape, and field constraints. It does not decide the mode, define Worker read/write boundaries, create children, allocate roles, or define lifecycle transitions.

## Ownership

The root parent owns the record for the current root user directive. The record is task state; it is not stored by editing a policy file. The parent-controlled task panel or equivalent runtime control record is the canonical location.

## Record shape

Before route release, record:

```text
owner: <root-parent identity>
gate_status: awaiting-mode | awaiting-count | released | blocked
mode: Single-Agent Coding | Multi-Agent Coding
child_count: 0 | <positive integer>
allocations: [{agent, role, interaction_slice, scope, mutations, return_conditions, lifecycle}]
lifecycle: pending | running | completed | interrupted
unavailable_capabilities: [<capability names>]
```

`child_count` is zero for Single-Agent Coding and a locked positive integer for Multi-Agent Coding. Allocation lifecycle values may differ from the top-level record while children progress.

## Related concepts

- [Coding Delegation State Record Worker Boundary](delegation-worker-boundary.md) — locate Worker snapshot and record access boundaries.
- [Coding Delegation Mode Confirmation](delegation-mode-confirmation.md) — locate root mode confirmation ownership.
- [Coding Delegation Count Gate](delegation-mode-count-gate.md) — locate child-count gate ownership.
- [Coding Delegation Re-entry](delegation-mode-reentry.md) — locate mode/count re-entry ownership.
- [Coding Execution Control](execution-control.md) — locate Interaction Slice field ownership.
- [Coding Child Lifecycle](delegation-child-lifecycle.md) — locate child lifecycle field ownership.
