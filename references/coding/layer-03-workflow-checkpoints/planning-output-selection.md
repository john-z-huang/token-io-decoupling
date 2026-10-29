# Planning output selection

[English](planning-output-selection.md) | [简体中文](planning-output-selection_zh_cn.md)

This checkpoint owns whether the current task consumes the plan-memory output lifecycle.


## Trigger and inputs

Once current facts and Decision inputs are established, evaluate whether the user’s goal requests planning, exploration, or producing/updating a plan. Apply [Execution Planning](../layer-01-fundamental-concepts/execution-planning/execution-planning.md) and, only when triggered, [Planning Intent Plan Memory Lifecycle](../layer-01-fundamental-concepts/execution-planning/planning-intent-plan-memory-lifecycle.md).

## Decision and result

1. Preserve the user’s planning intent and the Decision evidence that triggers the branch.
2. For triggered intent, use the plan-memory lifecycle owner to create or update the concise plan, then read back the stored item and compare it with the intended result before dependent work.
3. If intent is absent, record `Not applicable` with the observed goal evidence; continue ordinary Decision planning and its execution plan.
4. Return verified plan/readback evidence, `Not applicable`, or a block to route scheduling. Archive is owned only by Acceptance.

## Failure boundary

Unavailable required persistence or failed write/readback blocks dependent work. This selection does not authorize extra effects, change the user’s goal, or weaken the plan-memory owner’s naming, immutability, archive, and failure rules.

## Related concepts

- [Planning Intent Plan Memory Lifecycle](../layer-01-fundamental-concepts/execution-planning/planning-intent-plan-memory-lifecycle.md)
