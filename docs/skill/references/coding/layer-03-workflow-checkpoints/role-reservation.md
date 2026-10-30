# Role reservation

[English](role-reservation.md) | [简体中文](role-reservation_zh_cn.md)

This checkpoint owns role-reservation decisions for an authorized Multi-Agent task. [Child Role Selection](../layer-01-fundamental-concepts/delegation/child-role-selection.md), the [Count Gate](../layer-01-fundamental-concepts/delegation/delegation-mode-count-gate.md), the [State Record](../layer-01-fundamental-concepts/delegation/delegation-state-record.md), and [Child Role Allocation](../layer-01-fundamental-concepts/delegation/delegation-child-role-allocation.md) remain authoritative for role choice, capacity, identity/state, and reservation.

## Trigger and inputs

Run only after Executor Selection returns `new-executor-needed` for an authorized proposed task and Output Route Selection has independently dispositioned direct Root output. Read the four linked L1 owners and current Session role/allocation/capacity facts.

## Decision and result

1. Apply Child Role Selection to match the actual authorized proposed task to one maintained role. Honor explicit user role direction; use its conditional Primary fallback only when the owner’s trigger is met. Suggestions or a Primary preference do not authorize creation.
2. Read the entire current-Session role ledger from the State Record and Role Allocation owner. Any role already reserved or created by any Session member is occupied. Do not count inherited agents from another Session.
3. If a different unoccupied role fits, record its unique reservation in the current allocation within locked capacity. If capacity alone is insufficient, and only if that role remains unoccupied, request explicit approval for exactly `+1` through the Count Gate. Never increase automatically.
4. If all four roles are occupied, block without requesting more capacity. Return the reservation, `Not applicable` with evidence/reason, or block to the caller for task orchestration. Slice release and child creation remain later, separate gates.

## Failure boundary

Missing authorized task, stale or uncertain Session state, role conflict, unavailable role, insufficient capacity without exact approval, or unresolved role fit blocks Slice release. This checkpoint does not release a Slice, create, or dispatch.

## Related concepts

- [Child Role Selection](../layer-01-fundamental-concepts/delegation/child-role-selection.md)
- [Delegation Count Gate](../layer-01-fundamental-concepts/delegation/delegation-mode-count-gate.md)
- [Delegation State Record](../layer-01-fundamental-concepts/delegation/delegation-state-record.md)
- [Child Role Allocation](../layer-01-fundamental-concepts/delegation/delegation-child-role-allocation.md)
