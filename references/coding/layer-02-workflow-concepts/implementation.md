# Implementation Checkpoint

[English](implementation.md) | [简体中文](implementation_zh_cn.md)

## Actions

1. Re-read the slice objective, authorized paths, allowed mutations, and return conditions.
2. Inspect only the files needed for this slice, then make the smallest change that satisfies the approved direction.
3. Keep unrelated cleanup, refactoring, generated output, and external effects out of the slice.
4. Run focused provisional checks that can guide repair without treating them as final acceptance.
5. Return changed paths, relevant output, remaining issue, and the boundary that was not released.

## Pass condition

The approved slice is implemented within scope, and its focused checks either pass or provide a concrete issue for the Repair checkpoint.

## Boundary

This checkpoint does not expand scope, change a material decision, perform final verification, write post-verification documentation, or perform unapproved Git effects.

## Related concepts

- [Coding Execution Control](../layer-01-fundamental-concepts/execution-control.md) — locate authorized paths, mutations, and return-boundary ownership.
- [Coding Execution Planning](../layer-01-fundamental-concepts/execution-planning.md) — locate bounded plan and released-slice ownership.
- [Coding Execution Decision Gate](../layer-01-fundamental-concepts/execution-decision-gate.md) — locate direction and implementation-release ownership.
- [Coding Delegation State Record Worker Boundary](../layer-01-fundamental-concepts/delegation-worker-boundary.md) — locate named-path Worker access boundaries.
