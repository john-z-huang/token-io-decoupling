# Coding Delegation State Record

[English](delegation-state-record.md) | [简体中文](delegation-state-record_zh_cn.md)

This module owns the task-control record used by Coding delegation. It defines the record's canonical location, ownership, shape, field constraints, and staged presence semantics. It does not decide the mode, define Worker read/write boundaries, create children, allocate roles, or define lifecycle transitions.

## General rules

### Ownership

The root parent owns one conversation-level mode/count decision and updates task-specific slices and lifecycle in the same record. The record is task state; it is not stored by editing a policy file. Use a parent-controlled task panel when available; otherwise maintain an explicit structured record in the parent conversation that can be read back before each route release. Do not treat a transient child-status UI as the canonical record.

### Record shape

Before route release, maintain this canonical record:

```text
owner: <root-parent identity>
gate_status: awaiting-mode | awaiting-count | released | blocked
mode_source: unset | explicit | timeout-default
mode: unset | Single-Agent Coding | Multi-Agent Coding
child_count: unset | 0 | <locked positive integer>
allocations: [{agent: unbound | <created-agent-identity>, role: unassigned | <role>,
               slice_status: pending | released, interaction_slice, scope, mutations,
               return_conditions, lifecycle, write_content_memo}]
lifecycle: pending | running | completed | interrupted
unavailable_capabilities: [<capability names>]
block_reason: <required only when gate_status is blocked>
```

| `gate_status` | Mode and count | Allocations and lifecycle | Additional requirement |
| --- | --- | --- | --- |
| `awaiting-mode` | Unset | `[]`; top-level lifecycle `pending` | Initialize before an unanswered first mode question. |
| `awaiting-count` | Multi-Agent; count unset | `[]`; top-level lifecycle `pending` | Only an invalid explicit count enters this state; an omitted count defaults to one. |
| `released` — Single-Agent | Single-Agent; count `0` | `[]`; top-level lifecycle required | Releases the single route, not an independent Session. |
| `released` — Multi-Agent | Multi-Agent; locked positive count | Exactly `child_count` reserved allocations; each starts `agent: unbound`, `role: unassigned`, `slice_status: pending`, `lifecycle: pending` | Releases the route and count budget, **not** each child or Interaction Slice. |
| `blocked` | Preserve confirmed values | Preserve existing allocations/lifecycle | `unavailable_capabilities` and `block_reason` required; cannot enter a dependent route. |

An allocation's role becomes assigned at Role Allocation. A concrete `slice_status: released` requires `role`, `interaction_slice`, `scope`, `mutations`, `return_conditions`, and an explicit boolean `write_content_memo`; pending slices may leave these fields unset. Before serializing each released Worker bundle, include `write_content_memo: true` or `false`; the Worker never infers a default. Child Creation may bind `agent` and lifecycle only after the target role and slice are released. A later slice may be prepared on the **same** created child without creating or recycling a slot.

`mode_source` records the explicit choice or 15-second default and remains fixed for this conversation. Allocation lifecycle may differ from top-level task lifecycle. Blocking preserves all confirmed values; later directives use the Re-entry owner without changing locked mode/count.

## Codex CLI / ChatGPT Desktop optimizations

No provider-specific optimization instructions at present; follow the general rules above.

## Claude Code CLI / Claude Desktop optimizations

Claude Code has no equivalent durable Codex parent task panel. Maintain the structured mode, count, and slice record in the parent conversation and read it back before route release. `/tasks` is only a temporary subagent status view, not the canonical record.

## Related concepts

- [Coding Delegation State Record Worker Boundary](delegation-worker-boundary.md) — locate Worker snapshot and record access boundaries.
- [Coding Delegation Mode Confirmation](delegation-mode-confirmation.md) — locate root mode confirmation ownership.
- [Coding Delegation Count Gate](delegation-mode-count-gate.md) — locate child-count gate ownership.
- [Coding Delegation Re-entry](delegation-mode-reentry.md) — locate mode/count re-entry ownership.
- [Coding Execution Control](execution-control.md) — locate Interaction Slice field ownership.
- [Coding Child Lifecycle](delegation-child-lifecycle.md) — locate child lifecycle field ownership.
