# Acceptance Checkpoint

[English](acceptance.md) | [简体中文](acceptance_zh_cn.md)

## Actions

1. Map every Contract acceptance condition to the latest evidence for each applicable implementation/content, documentation, and Git metadata epoch.
2. Check that the changed paths, effects, and documentation stay within the approved scope.
3. Report implementation/content, documentation, and Git metadata status separately, and separate passed, failed, not-run, unavailable, assumed, and user-authorized items.
4. Record residual risks and any follow-up that requires new authority or a new Contract.
5. Do not use evidence from an older epoch as current evidence after a related change. Report `COMPLETE` only when every applicable latest epoch has current evidence and no required item, capability, verification boundary, or authorization remains unresolved.

## Pass condition

The final report maps every acceptance condition to current evidence from the applicable latest epochs, reports the three status dimensions separately, and is scope-accurate and explicit about limitations and authorized effects.

## Boundary

This checkpoint does not hide failures, convert assumptions into facts, or authorize new implementation, documentation, or Git work.

## Related concepts

- [Coding Execution Decision Gate](../layer-01-fundamental-concepts/execution-decision-gate.md) — locate decision and acceptance-condition ownership.
- [Coding Execution Control](../layer-01-fundamental-concepts/execution-control.md) — locate released-scope and return-boundary ownership.
