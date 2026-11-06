# Implementation Checkpoint

[English](implementation.md) | [简体中文](implementation_zh_cn.md)

## Actions

1. Re-read the slice objective, authorized paths, allowed mutations, and return conditions.
2. Inspect only the files needed for this slice, then make the smallest change that satisfies the approved direction.
3. When the authorized implementation path uses controlled candidate output, follow [Output Materialization](../../layer-01-fundamental-concepts/execution-planning/output-materialization.md) and [Candidate Compliance Preflight](../../layer-01-fundamental-concepts/execution-planning/candidate-compliance.md) at their owned gates. Review the exact bounded candidate and its current baseline; resolve every selected failed, unknown, omitted, or stale preflight result before applying it. If the optional candidate path is not selected, record `Not applicable` with the reason and continue only under the independently authorized implementation path. Preparation, preflight, and apply receipts are provisional evidence, not a substitute for this checkpoint's focused checks or later final Verification.
4. Keep unrelated cleanup, refactoring, generated output, and external effects out of the slice.
5. Run focused provisional checks that can guide repair without treating them as final acceptance.
6. Return changed paths, relevant output, remaining issue, and the boundary that was not released.

Apply [Task Plan Memory Lifecycle](../../layer-01-fundamental-concepts/execution-planning/task-plan-memory-lifecycle.md) before implementation: require current plan evidence and confirmed persistence, any content verification required by that owner, or its documented restriction exception. Record updates at owner-defined boundaries; facts affecting authorization, scope, acceptance, direction, or dependent implementation must be recorded and analyzed before that work. Only the parent releases affected work.

## Pass condition

The approved slice is implemented within scope, and its focused checks either pass or provide a concrete issue for the Repair checkpoint.

## Boundary

This checkpoint does not expand scope, change a material decision, perform final verification, write post-verification documentation, or perform unapproved Git effects.

## Related concepts

- [Coding Execution Control](../../layer-01-fundamental-concepts/execution-control/execution-control.md) — locate authorized paths, mutations, and return-boundary ownership.
- [Coding Execution Planning](../../layer-01-fundamental-concepts/execution-planning/execution-planning.md) — locate bounded plan and released-slice ownership.
- [Coding Execution Decision Gate](../../layer-01-fundamental-concepts/execution-planning/execution-decision-gate.md) — locate direction and implementation-release ownership.
- [Output Materialization](../../layer-01-fundamental-concepts/execution-planning/output-materialization.md) — locate controlled candidate preparation and application.
- [Candidate Compliance Preflight](../../layer-01-fundamental-concepts/execution-planning/candidate-compliance.md) — locate read-only candidate checks.
- [Coding Delegation State Record Worker Boundary](../../layer-01-fundamental-concepts/delegation/delegation-worker-boundary.md) — locate named-path Worker access boundaries.
