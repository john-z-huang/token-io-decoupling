# Planning output selection

[English](planning-output-selection.md) | [简体中文](planning-output-selection_zh_cn.md)

This checkpoint determines the current task's default shared-plan output and its verified persistence result.

## Trigger and inputs

For every Coding task, consume the current user goal, Issue/discussion when present, verified project facts, Decision, and any explicit persistence restriction. Apply [Execution Planning](../layer-01-fundamental-concepts/execution-planning/execution-planning.md) and [Task Plan Memory Lifecycle](../layer-01-fundamental-concepts/execution-planning/task-plan-memory-lifecycle.md).

## Decision and result

1. Preserve the task goal, sources, current facts and proposed solution. With or without an Issue, select a shared plan by default; lack of an explicit planning request is not a skip condition.
2. Confirm the exact project, selected repository storage scope, paired active/archive namespaces, active plan identity, allowed contributions and required access. For shared storage, verify that workspaces of one repository reuse the same plan mapping and other repositories remain separate. Missing or conflicting identity/mapping blocks without silent scope fallback. Create or update the concise plan and verify its stored content before implementation or dependent assignment. Return its identity, storage mapping and readback evidence to the caller.
3. Only an explicit user prohibition or higher-priority persistence restriction permits `Not applicable`, with the exact restriction, source and authorized in-context planning alternative. A conflicting explicit requirement to persist blocks; missing tools, unknown permission, or failed persistence are not skip conditions.
4. On new facts/progress or changed requirements, apply the same owner's update-before-report/action sequence and return current readback evidence before affected work resumes. Archive remains conditional on completed Acceptance.

## Failure boundary

Unavailable required access or failed persistence/readback blocks dependent work. This selection does not authorize implementation, change the user's goal, or weaken naming, update coordination, role boundaries, archive or immutability rules.

## Related concepts

- [Task Plan Memory Lifecycle](../layer-01-fundamental-concepts/execution-planning/task-plan-memory-lifecycle.md)
