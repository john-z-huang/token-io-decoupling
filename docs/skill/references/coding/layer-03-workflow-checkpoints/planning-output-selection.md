# Planning output selection

[English](planning-output-selection.md) | [简体中文](planning-output-selection_zh_cn.md)

This checkpoint determines the current task's default shared-plan output and its persistence/verification evidence under the lifecycle owner.

## Trigger and inputs

For every Coding task, consume the current user goal, Issue/discussion when present, verified project facts, Decision, and any explicit persistence restriction. Apply [Execution Planning](../layer-01-fundamental-concepts/execution-planning/execution-planning.md) and [Task Plan Memory Lifecycle](../layer-01-fundamental-concepts/execution-planning/task-plan-memory-lifecycle.md).

## Decision and result

1. Preserve the task goal, sources, current facts and proposed solution. With or without an Issue, select a shared plan by default; lack of an explicit planning request is not a skip condition.
2. Confirm the exact project, selected repository storage scope, paired active/archive namespaces, active plan identity, allowed contributions and required access. For shared storage, verify that workspaces of one repository reuse the same plan mapping and other repositories remain separate. Missing or conflicting identity/mapping blocks without silent scope fallback. Create or update the concise plan, confirm the authorized persistence operation, and perform content verification only when the lifecycle owner requires it. Return its identity, storage mapping, persistence confirmation, and any required verification evidence to the caller.
3. Only an explicit user prohibition or higher-priority persistence restriction permits `Not applicable`, with the exact restriction, source and authorized in-context planning alternative. A conflicting explicit requirement to persist blocks; missing tools, unknown permission, or failed persistence are not skip conditions.
4. Record material updates at the lifecycle owner's applicable phase, handoff, pause, or completion boundaries. Record and analyze changes affecting authorization, scope, acceptance, direction, or dependent actions before those actions. Ordinary progress reports do not independently trigger a plan write. Archive remains conditional on completed Acceptance.

## Failure boundary

Unavailable required access, failed persistence, or failed owner-required verification blocks dependent work. This selection does not authorize implementation, change the user's goal, or weaken naming, update coordination, role boundaries, archive or immutability rules.

## Related concepts

- [Task Plan Memory Lifecycle](../layer-01-fundamental-concepts/execution-planning/task-plan-memory-lifecycle.md)
