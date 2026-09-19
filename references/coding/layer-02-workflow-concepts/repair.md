# Repair Checkpoint

[English](repair.md) | [简体中文](repair_zh_cn.md)

This checkpoint diagnoses failure evidence, affected paths, and the smallest repair candidate. It reports when the candidate exceeds the approved boundary; it does not authorize or execute repairs and does not define verification epochs.

## Actions

1. Name the failing evidence, affected paths, and smallest repair that can address it.
2. Identify the smallest candidate that could address the failure without assuming authorization.
3. If the candidate changes scope, architecture, security, compatibility, or another material decision, stop the repair path and return that diagnostic result to Contract and Decision.

## Pass condition

The failing evidence, affected paths, and a smallest repair candidate are explicit, or the diagnostic result identifies the missing decision or capability.

## Boundary

This checkpoint does not authorize or execute repairs, run repair checks, define verification epochs, authorize broad cleanup, documentation, Git effects, or external effects.

## Related concepts

- [Coding Execution Decision Gate](../layer-01-fundamental-concepts/execution-decision-gate.md) — locate material decision and release-condition ownership.
- [Coding Execution Control](../layer-01-fundamental-concepts/execution-control.md) — locate approved slice and return-boundary ownership.
- [Coding Delegation State Record Worker Boundary](../layer-01-fundamental-concepts/delegation-worker-boundary.md) — locate named-path Worker access boundaries.
