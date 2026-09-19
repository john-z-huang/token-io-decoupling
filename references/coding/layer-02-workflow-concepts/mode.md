# Execution Mode Checkpoint

[English](mode.md) | [简体中文](mode_zh_cn.md)

## Actions

1. Load [the state-record reference](../layer-01-fundamental-concepts/delegation-state-record.md) and [the mode/count-gate reference](../layer-01-fundamental-concepts/delegation-mode-count-gate.md). When the released mode allocates children, also load [the child dispatch/lifecycle reference](../layer-01-fundamental-concepts/delegation-child-dispatch-lifecycle.md).
2. Read the parent-controlled task record and validate its current `gate_status`, `mode`, `child_count`, allocations, lifecycle, and unavailable capabilities before route selection. If the record has not released the route, stop at this checkpoint and do not proceed.
3. If a new root directive changes delegation, re-apply the mode/count gate and replace the task record before continuing. This checkpoint composes and validates the references; it does not decide mode, count, creation, allocation, reuse, exceptions, or lifecycle itself.

## Pass condition

The task control record contains exactly one valid released mode outcome and the required delegation state: `child_count: 0` for Single-Agent, or a locked positive count with valid allocations and lifecycle for Multi-Agent. The selected route's required capabilities and prohibitions are satisfied.

## Boundary

This checkpoint composes and validates the state-record, mode/count, and conditional child-dispatch references. It does not independently decide mode, topology, creation, allocation, reuse, exceptions, lifecycle, or count.
