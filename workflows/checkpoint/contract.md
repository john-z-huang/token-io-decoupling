# Contract Checkpoint

[English](contract.md) | [简体中文](contract_zh_cn.md)

## Actions

1. State the requested outcome in one sentence.
2. Record hard limits: user prohibitions, allowed runtime environments, repository and worktree scope, permitted tools and paths, safety limits, and explicitly authorized external effects.
3. Record material decisions already made, unresolved questions, and acceptance conditions.
4. Separate facts observed from assumptions. Keep unresolved material questions out of the implementation release.

## Pass condition

The goal, constraints, decisions, and acceptance conditions are explicit. If required information is missing, stop the dependent slice and ask for or report the exact missing input.

## Boundary

This checkpoint does not choose an execution mode, inspect the whole repository, implement changes, verify results, write documentation, or perform Git operations.
