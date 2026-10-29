# Decision Checkpoint

[English](decision.md) | [简体中文](decision_zh_cn.md)

## Actions

1. State the decision the next slice depends on.
2. List the relevant facts, constraints, options, chosen direction, and rejected alternatives.
3. Confirm that the chosen direction stays within the Contract and named paths or mutations.
4. Release only one concrete Development slice. If a new fact changes the decision, amend the Contract and make a new decision before continuing.

5. When a route supplies advisory output for this decision, re-read the applicable direct owner and decide from current facts; advice does not choose the Core branch or release the Slice. Continue from the direct owner only when required evidence remains available. Apply [Decisions Advisory](../../layer-01-fundamental-concepts/execution-planning/decisions-advisory.md) for advisory policy.

## Pass condition

The next slice has one approved direction, an explicit scope, and a stated boundary beyond which work must pause.

## Boundary

This checkpoint decides what may be done next. It does not implement, perform final verification, write post-verification documentation, or perform Git effects.

## Related concepts

- [Coding Execution Decision Gate](../../layer-01-fundamental-concepts/execution-planning/execution-decision-gate.md) — locate decision-brief and release-condition ownership.
- [Coding Execution Planning](../../layer-01-fundamental-concepts/execution-planning/execution-planning.md) — locate bounded planning ownership.
- [Coding Execution Control](../../layer-01-fundamental-concepts/execution-control/execution-control.md) — locate released-slice boundary ownership.
