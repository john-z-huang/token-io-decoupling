# Bootstrap selection

[English](bootstrap-selection.md) | [简体中文](bootstrap-selection_zh_cn.md)

This checkpoint owns whether the current Multi-Agent task consumes Bootstrap/Refresh.


## Trigger and inputs

After current facts are established and Root has authorized the current task scope, consider whether that task triggers Bootstrap/Refresh. Use this authorized scope as the evaluation input. If Bootstrap/Refresh proposes a specific auxiliary task, Root must separately review and authorize that task before Executor Selection or role reservation. Read [Child Role Allocation](../layer-01-fundamental-concepts/delegation/delegation-child-role-allocation.md) for its existing trigger, threshold, skip conditions, and role/slot authorization.

## Decision and result

1. List the Root-authorized current task scope, proposed role, role occupancy/slot, and relevant Memory facts with their sources.
2. Apply the original Child Role Allocation trigger, threshold, and skip conditions item by item; record the matched condition or missing fact and explicit `Not applicable` reason.
3. When triggered, return the proposed Bootstrap/Refresh task and basis to later Executor Selection and Role Reservation; otherwise return `Not applicable`.
4. Return the decision evidence to the caller for the subsequent task and role decisions. This step does not reserve role/capacity, create a child, or release an Interaction Slice.

## Failure boundary

Unclear trigger facts or authorization block this branch. Do not copy/redefine the owner’s thresholds, infer a new role, reserve capacity early, or bypass the later Slice and creation gates.

## Related concepts

- [Child Role Allocation](../layer-01-fundamental-concepts/delegation/delegation-child-role-allocation.md)
