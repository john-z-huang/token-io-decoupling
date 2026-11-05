# Workflow Navigation Selection

[English](workflow-navigation-selection.md) | [简体中文](workflow-navigation-selection_zh_cn.md)

This checkpoint decides whether bounded workflow navigation or structural input checking is useful for the current task. These are stateless aids; caller-supplied facts and authoritative owner documents remain the source for judging policy and results.

## Trigger and inputs

Use current [Environment](../layer-02-workflow-concepts/entry-and-context/environment.md) and [capability inventory](../layer-02-workflow-concepts/entry-and-context/environment-capability-inventory.md) results. Consult [Workflow Navigation Availability](../layer-01-fundamental-concepts/workflow-navigation/navigation-availability.md) and [Workflow Rule Context](../layer-01-fundamental-concepts/workflow-navigation/rule-context.md) when optional navigation may help. If a structural check of supplied checkpoint facts may help, apply [Checkpoint Structural Checks](../layer-01-fundamental-concepts/workflow-navigation/checkpoint-structure-checks.md). Both aids are optional unless the task independently requires their result.

## Decision and result

1. Identify the authoritative owner documents needed for the current judgment.
2. If optional navigation is useful and available, use only the bounded current context it returns. Treat source/hash/status as navigation evidence; it does not establish identity, permission, semantic truth, checkpoint completion, sequencing, or acceptance.
3. If structural checking is useful, compare its structural result with the supplied input and current owner, then independently judge what the facts and evidence mean. The check does not establish identity, permission, semantic truth, checkpoint completion, sequencing, or acceptance.
4. When either optional aid is not useful, record `Not applicable` with a reason; do not make an extra lookup or check merely to produce a result. Read the required authoritative owners directly.
5. If an aid is unavailable or incomplete, use direct authoritative documents when accessible through current authorized capabilities and record the limitation. If a required owner cannot be obtained, block the dependent judgment.
6. Return the selected source and any requested structural result for review. This decision does not change workflow state, authorize an action, or establish a checkpoint result.

## Failure boundary

| Result | Required action |
| --- | --- |
| Optional navigation is not needed | Record `Not applicable`; read required authoritative owners directly. |
| Bounded navigation is available | Review current returned source and read any uncovered direct owner; independently judge the task facts. |
| Optional structural checking is not needed or unavailable | Record `Not applicable` with the reason; continue from the authoritative owner unless the task independently requires the structural result. |
| Structural check is available and selected | Review its result against the current owner and caller-supplied input; decide evidence meaning independently. |
| Navigation is unavailable/incomplete but direct owner is accessible | Read the owner directly and record the limitation. |
| Required authoritative owner is inaccessible | Block only the judgment that depends on it; do not infer or skip its policy. |

## Related concepts

- [Workflow Navigation Availability](../layer-01-fundamental-concepts/workflow-navigation/navigation-availability.md)
- [Workflow Rule Context](../layer-01-fundamental-concepts/workflow-navigation/rule-context.md)
- [Environment Capability Inventory](../layer-02-workflow-concepts/entry-and-context/environment-capability-inventory.md)
