# Repair Execution Checkpoint

[English](repair-execution.md) | [简体中文](repair-execution_zh_cn.md)

This checkpoint owns execution of an authorized narrow repair and its focused checks. It consumes the scope-gate authorization; it does not diagnose failures, define authorization criteria, or create Verification epochs.

## Actions

1. Apply only the authorized repair within the released paths and mutations.
2. Run focused checks that directly exercise or inform that repair.
3. Return the changed paths, relevant check output, and any remaining issue to the parent boundary.

## Pass condition

The authorized narrow repair has been applied and its focused checks have passed or produced a concrete issue for the next owner.

## Boundary

This checkpoint does not diagnose failures, authorize scope changes, define final-state fingerprints or epochs, perform final Verification, write documentation, or perform Git effects.

## Related concepts

- [Coding Execution Control](../layer-01-fundamental-concepts/execution-control.md) — locate released paths and mutation boundaries.
- [Coding Execution Planning](../layer-01-fundamental-concepts/execution-planning.md) — locate bounded implementation-slice ownership.
- [Coding Delegation State Record Worker Boundary](../layer-01-fundamental-concepts/delegation-worker-boundary.md) — locate named-path Worker access boundaries.
