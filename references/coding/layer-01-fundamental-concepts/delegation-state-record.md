# Coding Delegation State Record

[English](delegation-state-record.md) | [简体中文](delegation-state-record_zh_cn.md)

This module owns the task-control record used by Coding delegation. It defines the record's canonical location, ownership, shape, field constraints, and staged presence semantics. It does not decide the mode, define Worker read/write boundaries, create children, allocate roles, or define lifecycle transitions.

## Ownership

The root parent owns the record for the current root user directive. The record is task state; it is not stored by editing a policy file. The parent-controlled task panel or equivalent runtime control record is the canonical location.

## Record shape

Before route release, initialize and maintain:

```text
owner: <root-parent identity>
gate_status: awaiting-mode | awaiting-count | released | blocked
mode: unset | Single-Agent Coding | Multi-Agent Coding
child_count: unset | 0 | <locked positive integer>
allocations: [{agent: unbound | <created-agent-identity>, role, interaction_slice, scope, mutations, return_conditions, lifecycle, write_content_memo}]
lifecycle: pending | running | completed | interrupted
unavailable_capabilities: [<capability names>]
block_reason: <required only when gate_status is blocked>
```

The staged field contract is:

| `gate_status` | `mode` | `child_count` | `allocations` | `lifecycle` | Additional requirement |
| --- | --- | --- | --- | --- | --- |
| `awaiting-mode` | Unset | Unset | Must be `[]` | Must be `pending` | Initialize this state before asking for mode confirmation. |
| `awaiting-count` | Must be `Multi-Agent Coding` | Unset; not yet locked | Must be `[]` | Must be `pending` | Enter only after Multi-Agent mode is explicitly confirmed. |
| `released` — Single-Agent | Must be `Single-Agent Coding` | Must be `0` | Must be `[]` | Required; records root-task state | Route is released only after its release conditions are satisfied. |
| `released` — Multi-Agent | Must be `Multi-Agent Coding` | Must be a locked positive integer | Must contain exactly `child_count` locked planned allocations; before creation, each may have `agent: unbound` and `lifecycle: pending` | Required at record level; each allocation must have its own lifecycle | Every allocation must include explicit `write_content_memo: true` or `false`. This state releases the route for child creation; it does not claim that children have been created or dispatched. |
| `blocked` | Preserve any confirmed value; otherwise unset | Preserve any confirmed value; otherwise unset | Preserve the current value | Preserve the current value | `unavailable_capabilities` and `block_reason` are required. This state is not `released`. |

For `awaiting-mode`, `mode` and `child_count` are absent or explicitly `unset`; all other required fields are present as shown. For `awaiting-count`, `mode` is present, while `child_count` remains absent or explicitly `unset` until count locking. For every `released` record, the fields shown as required must be present; `write_content_memo` is a per-Worker released-slice dispatch field, not an inferred Worker default. A released Multi-Agent record contains exactly the locked number of planned allocations; before child creation, an allocation may use `agent: unbound` with `lifecycle: pending`. The released state means that the route release gate has passed and the next step may be child creation; it does not claim that children have been created or dispatched. After successful creation, the child-creation owner writes back the created agent identity and actual lifecycle. Allocation lifecycle values may differ from the top-level record while children progress. Transition from `awaiting-mode` to `awaiting-count` occurs only after explicit Multi-Agent confirmation; Single-Agent confirmation sets `child_count: 0` before route release and retains `allocations: []`. Blocking preserves the confirmed state and does not release the route; any later gate re-entry follows its owner concept.

## Related concepts

- [Coding Delegation State Record Worker Boundary](delegation-worker-boundary.md) — locate Worker snapshot and record access boundaries.
- [Coding Delegation Mode Confirmation](delegation-mode-confirmation.md) — locate root mode confirmation ownership.
- [Coding Delegation Count Gate](delegation-mode-count-gate.md) — locate child-count gate ownership.
- [Coding Delegation Re-entry](delegation-mode-reentry.md) — locate mode/count re-entry ownership.
- [Coding Execution Control](execution-control.md) — locate Interaction Slice field ownership.
- [Coding Child Lifecycle](delegation-child-lifecycle.md) — locate child lifecycle field ownership.
