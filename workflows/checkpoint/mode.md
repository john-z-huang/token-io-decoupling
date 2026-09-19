# Execution Mode Checkpoint

[English](mode.md) | [简体中文](mode_zh_cn.md)

## Actions

1. Load and follow [delegation policy](../../references/coding/agent-delegation-control.md), the sole authority for mode confirmation and delegation rules.
2. Read the parent-controlled task record and confirm its current `gate_status`, `mode`, `child_count`, allocations, lifecycle, and unavailable capabilities before route selection. If the record has not released the route, stop at this checkpoint and do not proceed.
3. If a new root directive changes delegation, apply the policy again and replace the task record before continuing. This checkpoint does not restate or replace the policy's creation, allocation, reuse, exception, or count rules.

## Pass condition

The task control record contains exactly one valid mode outcome and any required delegation state; the selected route's required capabilities and prohibitions are satisfied.

## Boundary

This checkpoint only reads and validates the task record against the delegation policy. It does not independently decide mode, topology, creation, allocation, reuse, exceptions, or count.
