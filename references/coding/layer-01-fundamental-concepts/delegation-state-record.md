# Coding Delegation State Record

This module owns the task-control record used by Coding delegation. It defines state shape, ownership, and Worker read/write boundaries. It does not decide the mode, create children, allocate roles, or define lifecycle transitions.

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

## Worker boundary

Workers receive only the relevant released snapshot in the parent Dispatch. They must not infer, mutate, or replace the root record. After release, a Worker enters through the parent-provided Dispatch Preview; it does not reopen the root-user mode or count gates. If the runtime cannot persist or return the record, the dependent route is blocked.
