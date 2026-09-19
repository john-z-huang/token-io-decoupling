# Acceptance Checkpoint

[English](acceptance.md) | [简体中文](acceptance_zh_cn.md)

## Actions

1. Map every Contract acceptance condition to current evidence from the final state.
2. Check that the changed paths, effects, and documentation stay within the approved scope.
3. Separate passed, failed, not-run, unavailable, assumed, and user-authorized items.
4. Record residual risks and any follow-up that requires new authority or a new Contract.
5. Report `COMPLETE` only when no required item, capability, verification boundary, or authorization remains unresolved.

## Pass condition

The final report is evidence-backed, scope-accurate, and explicit about limitations and authorized effects.

## Boundary

This checkpoint does not hide failures, convert assumptions into facts, or authorize new implementation, documentation, or Git work.

## Related concepts

- [Coding Execution Decision Gate](../layer-01-fundamental-concepts/execution-decision-gate.md) — locate decision and acceptance-condition ownership.
- [Coding Execution Control](../layer-01-fundamental-concepts/execution-control.md) — locate released-scope and return-boundary ownership.
