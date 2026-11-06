# Workflow Navigation Selection

[English](workflow-navigation-selection.md) | [简体中文](workflow-navigation-selection_zh_cn.md)

This checkpoint selects the current compiled instruction delivery surface and any useful optional structural input check. Delivery and structural results remain separate from independently judging task facts and completion.

## Trigger and inputs

Use current [Environment](../layer-02-workflow-concepts/entry-and-context/environment.md) and [capability inventory](../layer-02-workflow-concepts/entry-and-context/environment-capability-inventory.md) results. Consult [Workflow Navigation Availability](../layer-01-fundamental-concepts/workflow-navigation/navigation-availability.md) and [Workflow Rule Context](../layer-01-fundamental-concepts/workflow-navigation/rule-context.md) when optional navigation may help. If a structural check of supplied checkpoint facts may help, apply [Checkpoint Structural Checks](../layer-01-fundamental-concepts/workflow-navigation/checkpoint-structure-checks.md). Both aids are optional unless the task independently requires their result.

## Decision and result

1. Identify the current instruction unit and any explicitly named continuation needed by this action; retain the exact suspended position and completed effects.
2. If optional navigation is useful and available, consume its current complete instruction text. Verify language, resource/build identity and completeness; none establishes identity, permission, semantic truth, checkpoint completion, sequencing or acceptance.
3. If structural checking is useful, compare its result with supplied input and current compiled instructions, then judge evidence meaning independently. A structural result never establishes authorization or semantic truth.
4. When an optional aid is unnecessary, record `Not applicable` with a reason. Consume the corresponding delivered instruction directly, without looking up author documents.
5. If optional navigation is unavailable, an actually available, authorized same-build generated document-only instruction surface may provide the explicit current unit. Missing, incomplete or incompatible required resources block dependent judgment; resource errors never authorize author-source fallback.
6. Return the selected source and any requested structural result for review. This decision does not change workflow state, authorize an action, or establish a checkpoint result.

## Failure boundary

| Result | Required action |
| --- | --- |
| Optional navigation is not needed | Record `Not applicable`; consume the required delivered instruction directly. |
| Bounded navigation is available | Review current complete text and exact continuations; independently judge facts. |
| Optional structural checking is not needed or unavailable | Record `Not applicable` with the reason; continue from current compiled instructions unless the task independently requires that result. |
| Structural check is available and selected | Compare its result with current instructions and supplied input; judge evidence independently. |
| Navigation is unavailable but same-build generated instructions are accessible | Consume the exact delivered unit and record the limitation. |
| Required instruction resources are unavailable, incomplete or incompatible | Block dependent judgment; do not infer policy, skip guards or read author sources. |

## Related concepts

- [Workflow Navigation Availability](../layer-01-fundamental-concepts/workflow-navigation/navigation-availability.md)
- [Workflow Rule Context](../layer-01-fundamental-concepts/workflow-navigation/rule-context.md)
- [Environment Capability Inventory](../layer-02-workflow-concepts/entry-and-context/environment-capability-inventory.md)
