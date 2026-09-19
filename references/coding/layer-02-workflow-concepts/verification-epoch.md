# Verification Epoch Checkpoint

[English](verification-epoch.md) | [简体中文](verification-epoch_zh_cn.md)

This checkpoint owns final-state epoch invalidation: a later change makes an earlier verification result stale and requires re-verification. It does not define check contents, independent Sessions, result classification, or repair.

## Actions

1. Treat any later change as a new final-state epoch.
2. Do not use an earlier verification result as evidence for the new state; require Verification for the new epoch.

## Pass condition

The current final-state epoch is explicit and any required re-verification is queued or complete.

## Boundary

This checkpoint does not capture fingerprints, choose checks, define independent verification, classify results, authorize repairs, write documentation, or perform Git effects.

## Related concepts

- [Coding Execution Control](../layer-01-fundamental-concepts/execution-control.md) — locate material state-boundary ownership.
- [Coding Delegation State Record Worker Boundary](../layer-01-fundamental-concepts/delegation-state-record-worker-boundary.md) — locate final-state evidence access.
- [Coding Child Reuse and Replacement](../layer-01-fundamental-concepts/delegation-child-reuse-replacement.md) — locate repaired-epoch reuse ownership.
- [Coding Execution Decision Gate](../layer-01-fundamental-concepts/execution-decision-gate.md) — locate dependent-release conditions.
