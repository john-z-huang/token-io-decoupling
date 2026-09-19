# Execution Mode Checkpoint

[English](mode.md) | [简体中文](mode_zh_cn.md)

## Actions

1. Load [the state-record reference](../layer-01-fundamental-concepts/delegation-state-record.md), [the mode-confirmation reference](../layer-01-fundamental-concepts/delegation-mode-confirmation.md), [the mode/count-gate reference](../layer-01-fundamental-concepts/delegation-mode-count-gate.md), and [the mode-reentry reference](../layer-01-fundamental-concepts/delegation-mode-reentry.md). When the released mode allocates children, also load [child creation](../layer-01-fundamental-concepts/delegation-child-creation.md), [child role allocation](../layer-01-fundamental-concepts/delegation-child-role-allocation.md), [child dispatch](../layer-01-fundamental-concepts/delegation-child-dispatch.md), [child reuse/replacement](../layer-01-fundamental-concepts/delegation-child-reuse-replacement.md), and [child lifecycle](../layer-01-fundamental-concepts/delegation-child-lifecycle.md).
2. Read the parent-controlled task record and validate its current `gate_status`, `mode`, `child_count`, allocations, lifecycle, and unavailable capabilities before route selection. If the record has not released the route, stop at this checkpoint and do not proceed.
3. If a new root directive changes delegation, re-apply the mode/count gate and replace the task record before continuing. This checkpoint composes and validates the references; it does not decide mode, count, creation, allocation, reuse, exceptions, or lifecycle itself.

## Pass condition

The task control record contains exactly one valid released mode outcome and the required delegation state: `child_count: 0` for Single-Agent, or a locked positive count with valid allocations and lifecycle for Multi-Agent. The selected route's required capabilities and prohibitions are satisfied.

## Boundary

This checkpoint composes and validates the state-record, mode/count, and conditional child-dispatch references. It does not independently decide mode, topology, creation, allocation, reuse, exceptions, lifecycle, or count.

## Related concepts

- [Coding Delegation Mode Confirmation](../layer-01-fundamental-concepts/delegation-mode-confirmation.md) — locate root mode confirmation ownership.
- [Coding Delegation Count Gate](../layer-01-fundamental-concepts/delegation-mode-count-gate.md) — locate child-count gate ownership.
- [Coding Delegation Re-entry](../layer-01-fundamental-concepts/delegation-mode-reentry.md) — locate mode/count re-entry ownership.
- [Coding Delegation State Record](../layer-01-fundamental-concepts/delegation-state-record.md) — locate task-control record ownership.
- [Coding Delegation State Record Worker Boundary](../layer-01-fundamental-concepts/delegation-worker-boundary.md) — locate released Worker record access boundaries.
