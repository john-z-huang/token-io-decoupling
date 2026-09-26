# Control Boundary Checkpoint

[English](control.md) | [简体中文](control_zh_cn.md)

## Actions

1. Consume the compressed Progress Signal from the Stage Feedback owner; append the current `Unreleased boundary` without creating a second progress report.
2. Check whether the next action crosses an interface, schema, compatibility, security, risk, irreversible, scope, or external-effect boundary.
3. If more evidence is required, request Evidence-on-Demand and **pause** release; return to this checkpoint after evidence arrives. This is an intermediate action, not a fourth final authorization outcome.
4. Choose the final `Continue`, `Amend`, or `Stop` outcome. Only an explicit `Continue` releases the next slice within the approved envelope; `Amend` returns through Contract and Decision. In Single-Agent this is a logical pause; in Multi-Agent the parent controls release.

## Pass condition

The next action is either released within the current envelope or is paused with the required amendment, evidence, capability, or authorization named.

## Boundary

This checkpoint controls release and authority. It does not silently approve scope expansion, replace verification, or grant Git or external-effect authorization.

## Related concepts

- [Coding Execution Control](../layer-01-fundamental-concepts/execution-control.md) — locate Interaction Slice and control-boundary ownership.
- [Coding Execution Decision Gate](../layer-01-fundamental-concepts/execution-decision-gate.md) — locate decision and release-condition ownership.
- [Coding Delegation State Record Worker Boundary](../layer-01-fundamental-concepts/delegation-worker-boundary.md) — locate parent-controlled Worker release boundaries.
