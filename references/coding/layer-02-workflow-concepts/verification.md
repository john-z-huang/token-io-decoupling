# Verification Checkpoint

[English](verification.md) | [简体中文](verification_zh_cn.md)

This checkpoint captures the current final-state evidence, binds acceptance conditions, runs applicable holistic and targeted checks, and determines whether the required evidence is complete. It does not define independent Sessions, result classifications, or invalidation rules for later epochs.

## Actions

1. Capture the current final-state fingerprint or epoch and the acceptance conditions.
2. Run the strongest applicable holistic and targeted checks against that exact state.

## Pass condition

Every required verification item has current evidence, or the evidence gap is explicit and prevents completion.

## Boundary

This checkpoint does not define independent verification Sessions, classify or report results, invalidate later epochs, repair failures, write documentation, perform Git effects, or declare overall acceptance by itself.

## Related concepts

- [Coding Execution Decision Gate](../layer-01-fundamental-concepts/execution-decision-gate.md) — locate acceptance-condition and release-decision ownership.
- [Coding Execution Control](../layer-01-fundamental-concepts/execution-control.md) — locate released scope and return-boundary ownership.
- [Coding Session Role Ownership](../layer-01-fundamental-concepts/session-role-ownership.md) — locate Change Verification role ownership.
- [Coding Delegation State Record Worker Boundary](../layer-01-fundamental-concepts/delegation-worker-boundary.md) — locate final-state evidence access boundaries.
