# Verification Reporting Checkpoint

[English](verification-reporting.md) | [简体中文](verification-reporting_zh_cn.md)

This checkpoint owns verification result classification, unresolved-item reporting, and blocking-effect reporting. It does not define independent Sessions, check contents, evidence capture, epoch invalidation, or repair.

## Actions

1. Record passed, failed, unavailable, and assumed checks, together with residual risks.
2. Explicitly report every unresolved verification item and its blocking effect.

## Pass condition

The required result categories, residual risks, unresolved items, and blocking effects are explicit.

## Boundary

This checkpoint does not choose checks, capture final-state fingerprints, define independent verification, invalidate epochs, repair failures, write documentation, or perform Git effects.

## Related concepts

- [Coding Execution Decision Gate](../layer-01-fundamental-concepts/execution-decision-gate.md) — locate acceptance-condition ownership.
- [Coding Execution Control](../layer-01-fundamental-concepts/execution-control.md) — locate report scope and return-boundary ownership.
- [Coding Session Role Ownership](../layer-01-fundamental-concepts/session-role-ownership.md) — locate Change Verification responsibility.
- [Coding Delegation State Record Worker Boundary](../layer-01-fundamental-concepts/delegation-worker-boundary.md) — locate evidence access boundaries.
