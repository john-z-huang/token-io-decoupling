# Git Checkpoint

[English](git.md) | [简体中文](git_zh_cn.md)

## Actions

1. Confirm the exact repository, worktree, branch or ref, remote, operation, and intended external effect.
2. Inspect status and relevant history before mutating Git state. Do not include unrelated user changes.
3. Keep commit, push, Issue, PR, remote changes, and other external effects separate unless each effect is explicitly authorized.
4. Stop on an ambiguous target, unexpected conflict, missing authorization, or failed prerequisite; do not broaden the operation to recover.

## Pass condition

The authorized Git operation completes against the exact target, or the unavailable authorization, conflict, or prerequisite is reported.

## Boundary

This checkpoint does not grant product decision authority, permit unrequested cleanup, or turn a possible Git effect into an authorized one.
