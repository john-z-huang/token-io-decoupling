# Execution Mode Checkpoint

[English](mode.md) | [简体中文](mode_zh_cn.md)

## Actions

1. Select **Single-Agent Coding** when the user forbids subagents, child tasks, independent Sessions, or parallel delegation.
2. Select **Multi-Agent Coding** only when the user explicitly requests multiple agents, or a concrete structural, isolation, or capability requirement makes separation necessary and allowed.
3. Select Single-Agent Coding by default when neither condition is present.
4. If the selected mode matches a pre-composed workflow, read only that complete workflow. Otherwise record the mode and continue with the checkpoint composition in the Coding index. If the mode conditions become false, stop the current slice, amend the Contract, and reselect.

## Pass condition

Exactly one mode is recorded, and the mode's required capabilities and prohibitions are satisfied.

## Boundary

This checkpoint chooses the execution route only. It does not decide task architecture, grant delegation authority, or create a Session.
