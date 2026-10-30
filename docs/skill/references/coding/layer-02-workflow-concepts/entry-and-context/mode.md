# Execution Mode Checkpoint

[English](mode.md) | [简体中文](mode_zh_cn.md)

## Actions

1. Load the [state record](../../layer-01-fundamental-concepts/delegation/delegation-state-record.md), [mode confirmation](../../layer-01-fundamental-concepts/delegation/delegation-mode-confirmation.md), [count gate](../../layer-01-fundamental-concepts/delegation/delegation-mode-count-gate.md), and [re-entry](../../layer-01-fundamental-concepts/delegation/delegation-mode-reentry.md) owners. Do not eagerly load child creation, dispatch, lifecycle, or reuse policies before their actual route step.
2. Confirm the parent-controlled record contains a selected mode and locked count, with `child_count: 0` and `allocations: []` for Single-Agent or exactly `child_count` reserved, initially unbound/unassigned/pending slots for Multi-Agent. If `mode_source: default`, verify Multi-Agent with `child_count: 1` and exactly one reserved slot. If `mode_source: timeout-default`, accept it only as a legacy readback and verify Single-Agent with `child_count: 0` and `allocations: []`; new conversations never use this source. Releasing this gate does **not** release a concrete Interaction Slice, initialize a store, or authorize child creation. Any first Enhanced Root persistence occurs only later, after Session identity, role, and Context Firewall checks pass, as composed by the route.
3. For a later directive, reuse the locked mode/count; refresh task-specific evidence without reopening the mode/count gate. If required record/capability evidence is missing, block the dependent route. Role allocation and child operations are performed and checked at their designated route steps.

4. Verify that the authorized mode/count and evidence required by this gate are recorded. Advisory output cannot alter locked mode/count or reopen this gate; apply [Decisions Advisory](../../layer-01-fundamental-concepts/execution-planning/decisions-advisory.md) for advisory policy.

## Pass condition

The parent record has exactly one valid released mode, a fixed count, valid reserved allocation shape where applicable, and sufficient entry capabilities. No concrete child or slice is assumed to have been released.

## Boundary

This checkpoint composes and validates the state-record, mode/count, and conditional child-dispatch references. It does not independently decide mode, topology, creation, allocation, reuse, exceptions, lifecycle, or count. A passing Mode gate never initializes or migrates a database; store selection and first-write timing belong to the route and the [Enhanced State Store](../../layer-01-fundamental-concepts/enhanced-native-state/enhanced-state-store.md) owner.

## Related concepts

- [Coding Delegation Mode Confirmation](../../layer-01-fundamental-concepts/delegation/delegation-mode-confirmation.md) — locate root mode confirmation ownership.
- [Coding Delegation Count Gate](../../layer-01-fundamental-concepts/delegation/delegation-mode-count-gate.md) — locate child-count gate ownership.
- [Coding Delegation Re-entry](../../layer-01-fundamental-concepts/delegation/delegation-mode-reentry.md) — locate mode/count re-entry ownership.
- [Coding Delegation State Record](../../layer-01-fundamental-concepts/delegation/delegation-state-record.md) — locate task-control record ownership.
- [Coding Delegation State Record Worker Boundary](../../layer-01-fundamental-concepts/delegation/delegation-worker-boundary.md) — locate released Worker record access boundaries.
