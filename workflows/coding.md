# Coding Workflow

[English](coding.md) | [简体中文](coding_zh_cn.md)

Use this workflow when repository text, developer-tool output, implementation, tests, documentation, or Git state is the main work state. This file is only the Coding route selector and completion index. The selected `exist-workflow` document composes the references and checkpoints needed for execution. Root-directive mode and delegation decisions are owned exclusively by `references/coding/agent-delegation-control.md`.

## Entry

1. Load the delegation authority needed for the root-directive mode gate.
2. Identify the actual runtime environment and complete the Environment checkpoint.
3. Select exactly one complete route after the mode gate and environment check. That route loads its own references and checkpoints.

## Routes

- [Single-Agent Coding](exist-workflow/coding-single-agent.md): use only for the recorded Single-Agent outcome.
- [Multi-Agent Coding](exist-workflow/coding-multi-agent.md): use only for the recorded Multi-Agent outcome and available delegation state.

Do not load both routes. If a later material fact invalidates the selected route, stop the current slice, amend the Contract as needed, and return to route selection.

## Checkpoint catalog

The route may compose these independent action boundaries as conditions require:

`contract` → `environment` → `mode` → `context` → `decision` → `implementation` → `control` → `verification` → `repair` → `documentation` → `git` → `acceptance`

The catalog is navigation only. A checkpoint does not route to another checkpoint; the selected route defines the actual sequence and records why a conditional checkpoint is skipped.

## Completion

Return `COMPLETE` only after the selected route reaches Acceptance with current evidence. Report unavailable checks, assumptions, residual risks, authorized effects, and the recorded delegation state. Do not cause external effects without explicit authorization.
