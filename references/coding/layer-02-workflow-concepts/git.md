# Git Checkpoint

[English](git.md) | [简体中文](git_zh_cn.md)

## Actions

1. Confirm the exact repository, worktree, branch or ref, remote, operation, and intended external effect.
2. Inspect status and relevant history before mutating Git state. Do not include unrelated user changes.
3. Treat commit, branch, index, and history changes as Git metadata operations that do not automatically invalidate the implementation/content or documentation epoch.
4. Confirm that staged or committed content matches the latest verified fingerprints and contains no unverified content. If it differs, return to the corresponding implementation/content or documentation Verification epoch before continuing.
5. Keep commit, push, Issue, PR, remote changes, and other external effects separate unless each effect is explicitly authorized.
6. Record the latest applicable implementation/content and documentation epochs that the Git operation targets.
7. Stop on an ambiguous target, unexpected conflict, missing authorization, or failed prerequisite; do not broaden the operation to recover.

## Pass condition

The authorized Git operation completes against the exact target, records the latest applicable content and documentation epochs, and matches their verified fingerprints; otherwise the unavailable authorization, conflict, prerequisite, or required Verification return is reported.

## Boundary

This checkpoint does not grant product decision authority, permit unrequested cleanup, or turn a possible Git effect into an authorized one.

## Related concepts

- [Coding Context Exchange Workspace Boundary](../layer-01-fundamental-concepts/context-exchange-workspace-boundary.md) — locate worktree, permission, and path boundaries.
- [Coding Session Role Ownership](../layer-01-fundamental-concepts/session-role-ownership.md) — locate Documentation/Comments & Git Operations ownership.
- [Coding Execution Control](../layer-01-fundamental-concepts/execution-control.md) — locate authorized scope and unreleased-boundary ownership.
- [Coding Delegation State Record Worker Boundary](../layer-01-fundamental-concepts/delegation-worker-boundary.md) — locate parent-controlled path and Worker access boundaries.
