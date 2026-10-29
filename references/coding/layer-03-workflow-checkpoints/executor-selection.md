# Executor selection

[English](executor-selection.md) | [简体中文](executor-selection_zh_cn.md)

This checkpoint owns executor routing at S06/M07. [Task Assignment](../layer-01-fundamental-concepts/execution-planning/task-assignment.md) remains authoritative for executor and candidate selection policy.

## Trigger and inputs

Run after current facts, explicit user direction, locked mode, and an authorized proposed task are established. Read the Task Assignment owner and current verified Session allocation, identity, capability, permission, and availability facts. Executor selection does not settle output size or release a child Slice.

## Decision and result

1. Check explicit direction first. Honor an explicit executor/candidate subject to mode, permission, current identity, capability, scope, and availability; skip only the corresponding advice. Under locked Single-Agent mode, explicit `sub_agent` conflicts and returns for Root review; explicit `root` is valid. With no executor instruction, the Single-Agent route is deterministic Root and makes no executor-advice request.
2. In Multi-Agent mode, compare current task facts and authorized scope. If Root is appropriate under permissions and capability, return `root`; if a child is required, examine only verified, eligible current-Session children. After a Fork, first complete fresh mode/count re-entry for the new Session; inherited children never become candidates for that new Session through re-entry.
3. Apply the owner’s candidate filter. Select a single eligible candidate directly. When multiple candidates remain, prefer eligible idle candidates; if exactly one idle candidate remains after filtering, select it. If two or more eligible idle candidates remain, compare them using the current task-context procedure in Task Assignment, including its suitable idle Primary branch. Do not select by transcript size or invented thresholds. If no suitable existing child exists but child execution is required, record the route disposition `new-executor-needed` from the verified `sub_agent` direction and empty eligible-candidate result, with authorization, task facts, and candidate-filter evidence. This is not a new registration decision or tool-return enum and does not authorize creation. If suitable children exist but are busy, pass the busy state to the route for independent output assessment before waiting.
4. For busy candidates, route each requested direct Root output under Output Token Routing before waiting. A `no` returns to remaining Root gates; a `yes` requires a suitable idle child or hold/wait; insufficient/failure stays unresolved unless verified direct facts suffice. Recheck identity, authority, role, capability, permission, scope, and latest availability immediately before dispatch.
5. Return `root`, selected candidate, `new-executor-needed`, `hold`, or `insufficient_evidence` with current evidence, policy/input/context hashes when advice was used, and rationale. Advice failure never defaults to Root. This checkpoint does not reserve a new role, release a Slice, create, or dispatch.

## Failure boundary

Missing or stale facts, conflicting direction, unknown mode/permission/capability, unavailable candidate identity, unresolved selection, or advice/hash failure without sufficient direct evidence returns unresolved and blocks downstream release. Never assume Root or candidate availability.

## Related concepts

- [Task Assignment](../layer-01-fundamental-concepts/execution-planning/task-assignment.md)
- [Output Token Routing](../layer-01-fundamental-concepts/execution-planning/output-token-routing.md)
- [Session Model](../layer-01-fundamental-concepts/session-runtime/session-model.md)
- [Delegation State Record](../layer-01-fundamental-concepts/delegation/delegation-state-record.md)
