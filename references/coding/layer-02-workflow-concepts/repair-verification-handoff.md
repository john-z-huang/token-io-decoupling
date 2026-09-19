# Repair Verification Handoff Checkpoint

[English](repair-verification-handoff.md) | [简体中文](repair-verification-handoff_zh_cn.md)

This checkpoint owns the handoff of a state-changing repair to Verification with a new final-state fingerprint or epoch. It does not authorize the repair, define repair content, or define Verification checks or result reporting.

## Actions

1. For a state-changing repair, capture the resulting final-state fingerprint or epoch.
2. Send that new state back through the Verification checkpoint before dependent work continues.

## Pass condition

The changed state has a new final-state fingerprint or epoch and is explicitly queued for Verification, or the handoff is paused with the missing evidence named.

## Boundary

This checkpoint does not diagnose failures, authorize or execute repairs, define check contents, classify results, write documentation, or perform Git effects.

## Related concepts

- [Coding Execution Control](../layer-01-fundamental-concepts/execution-control.md) — locate material-boundary and return-condition ownership.
- [Coding Execution Decision Gate](../layer-01-fundamental-concepts/execution-decision-gate.md) — locate dependent-release ownership.
- [Coding Delegation State Record Worker Boundary](../layer-01-fundamental-concepts/delegation-state-record-worker-boundary.md) — locate final-state evidence access boundaries.
- [Coding Child Reuse and Replacement](../layer-01-fundamental-concepts/delegation-child-reuse-replacement.md) — locate repaired-epoch reuse ownership.
