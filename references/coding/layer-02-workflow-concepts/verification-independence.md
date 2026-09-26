# Verification Independence Checkpoint

[English](verification-independence.md) | [简体中文](verification-independence_zh_cn.md)

This checkpoint owns the distinction between an independent Change Verification Session and same-Session logical verification. It does not define check contents, evidence collection, result classification, or repair.

## Actions

1. For material changes, use an independent Change Verification Session when the Contract requires it.
2. Label same-Session checks as logical verification; do not call them independent verification.

## Pass condition

Independence status is explicitly classified: the required independent Session has verified the change, or same-Session checks are labeled logical and independence unavailable. The latter is a recorded limitation, **not** satisfaction of a Contract that requires independent verification; dependent effects remain blocked.

## Boundary

This checkpoint does not choose holistic or targeted checks, capture fingerprints, classify results, invalidate epochs, repair failures, or perform Git effects.

## Related concepts

- [Coding Session Role Ownership](../layer-01-fundamental-concepts/session-role-ownership.md) — locate Change Verification role ownership.
- [Coding Session Context Firewall](../layer-01-fundamental-concepts/session-context-firewall.md) — locate Session state-ingress boundaries.
- [Coding Delegation State Record Worker Boundary](../layer-01-fundamental-concepts/delegation-worker-boundary.md) — locate verifier evidence access boundaries.
- [Coding Execution Decision Gate](../layer-01-fundamental-concepts/execution-decision-gate.md) — locate Contract-dependent verification conditions.
