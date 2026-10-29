# Enhanced path selection

[English](enhanced-path-selection.md) | [简体中文](enhanced-path-selection_zh_cn.md)

This checkpoint owns the task-specific choice to use the optional Enhanced path.
## Trigger and inputs

At S02/M02, use current [Environment](../layer-02-workflow-concepts/entry-and-context/environment.md) and [capability inventory](../layer-02-workflow-concepts/entry-and-context/environment-capability-inventory.md) results to decide whether this task needs optional Enhanced operations. Apply [Enhanced Workflow Availability](../layer-01-fundamental-concepts/enhanced-native-state/enhanced-workflow-availability.md) and [Enhanced Host Binding](../layer-01-fundamental-concepts/enhanced-native-state/enhanced-host-binding.md) when the Enhanced branch is needed.

## Decision and result

1. Compare the task's required operation with the optional Enhanced operations supported by the current Environment and capability inventory.
2. If no required operation needs Enhanced state, record Native and `Not applicable` with the reason; continue without opening or initializing Enhanced state.
3. If an Enhanced operation is needed, verify that this Session meets the availability owner's eligibility conditions, that the current host identity is trusted and bound, and that every required guard/capability is available. Preserve the evidence source for each check.
4. Return `Enhanced eligible` with the verified operation, identity, and guard evidence, or return `blocked` with the missing/unknown requirement. The route's subsequent state-resolution action consumes the selected result; path selection alone never opens or initializes state.

## Failure boundary

| Result | Required route action |
| --- | --- |
| No Enhanced operation is required | Continue on Native and record `Not applicable` with why. |
| Enhanced operation and all eligibility, identity, and guard facts are verified | Return the evidence for the route's state-resolution action; do not open state here. |
| Required operation is unclear, or identity, capability, eligibility, or guard is unknown/unavailable | Block the dependent Enhanced branch. Preserve any Native candidate; do not infer eligibility or initialize state. |

Native candidacy does not decide which backend is canonical when prior Enhanced authority may exist; the route's state-resolution action establishes that under the reconciliation and authority-transfer owners.

## Related concepts

- [Enhanced Workflow Availability](../layer-01-fundamental-concepts/enhanced-native-state/enhanced-workflow-availability.md)
