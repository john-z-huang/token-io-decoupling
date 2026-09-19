# Coding Workflow

[English](coding.md) | [简体中文](coding_zh_cn.md)

Use this workflow when repository text, developer-tool output, implementation, tests, documentation, or Git state is the main work state. This file is only the Coding route selector and completion index. The selected `exist-workflow` document composes the references and checkpoints needed for execution. Root-directive mode and delegation rules are owned exclusively by the delegation policy; the task control record stores the current state.

## Entry

1. Load the delegation authority needed for the root-directive mode gate.
2. Identify the actual runtime environment and complete the Environment checkpoint.
3. Select exactly one complete route after the mode gate and environment check. That route loads its own references and checkpoints.

## Routes

- [Single-Agent Coding](exist-workflow/coding-single-agent.md): use only when the task record says `mode: Single-Agent Coding`.
- [Multi-Agent Coding](exist-workflow/coding-multi-agent.md): use only when it says `mode: Multi-Agent Coding` with a locked positive `child_count`.

Do not load both routes. If a later material fact invalidates the selected route, stop the current slice, amend the Contract as needed, and return to route selection.

## Document layers

These layers define composition direction, not policy ownership. Each document may keep its language-switch link; dependency links must remain same-language.

| Layer | Role | Allowed dependency targets |
| --- | --- | --- |
| `references/` | Atomic policy modules | Its language mirror only; never `workflows/` |
| `workflows/checkpoint/` | Execution checkpoints | `references/`; never `workflows/exist-workflow/` |
| `workflows/exist-workflow/` | Final composed routes | `references/` and `workflows/checkpoint/`; never the selector |
| `workflows/coding.md` | Route selector and checkpoint catalog | `workflows/exist-workflow/`; owns navigation, not policy |

If a lower layer needs a concept owned by a higher layer, treat that upward dependency as an atomicity failure: split the lower document and move the composition to the higher layer. Root entry documents such as `SKILL.md`, `README.md`, and `docs/` may link downward to entry points. Validate the boundaries with `python3 scripts/check-doc-layer-links.py`; language-switch links are the only intentional cross-language links.

## Checkpoint catalog

The route may compose these independent action boundaries as conditions require:

`contract` → `environment` → `mode` → `context` → `decision` → `implementation` → `control` → `verification` → `repair` → `documentation` → `git` → `acceptance`

The catalog is navigation only. A checkpoint does not route to another checkpoint; the selected route defines the actual sequence and records why a conditional checkpoint is skipped.

## Completion

Return `COMPLETE` only after the selected route reaches Acceptance with current evidence. Report unavailable checks, assumptions, residual risks, authorized effects, and the recorded delegation state. Do not cause external effects without explicit authorization.
