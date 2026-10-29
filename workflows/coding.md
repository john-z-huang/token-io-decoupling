# Coding Workflow

[English](coding.md) | [简体中文](coding_zh_cn.md)

Use this workflow when repository text, developer-tool output, implementation, tests, documentation, or Git state is the main work state. This file is only the Coding route selector and completion index. Layer-03 decision checkpoints determine task-specific applicability and branches; the selected Layer-04 route orders those decisions and composes the Layer-01 concepts and Layer-02 checkpoint actions needed for execution. Root-directive mode and delegation rules are owned by the atomic delegation references composed by the Mode checkpoint; the parent-controlled record stores the conversation-wide mode/count decision and current task state.

## Entry

1. Complete the Contract checkpoint before route selection.
2. Identify the actual runtime environment, complete the Environment checkpoint, and establish or load the [Environment capability inventory](../references/coding/layer-02-workflow-concepts/entry-and-context/environment-capability-inventory.md) for capability checks.
3. Pass the Mode checkpoint, which consumes the already established Environment capability inventory and composes the delegation references needed for the root-directive mode gate.
4. Call [Route Entry](../references/coding/layer-03-workflow-checkpoints/route-entry.md) with current evidence that Contract, Environment, capability inventory, and Mode passed. Select exactly its authorized complete route, then pass released mode/count evidence to its first module checkpoint SM01/MM01. Each route composes [Entry Readiness](../references/coding/layer-04-workflows/modules/entry-readiness.md), [Session Readiness](../references/coding/layer-04-workflows/modules/session-readiness.md), [Work Definition](../references/coding/layer-04-workflows/modules/work-definition.md), its mode-specific execution module, [Verification and Repair](../references/coding/layer-04-workflows/modules/verification-repair.md), [Documentation](../references/coding/layer-04-workflows/modules/documentation.md), and [Delivery and Acceptance](../references/coding/layer-04-workflows/modules/delivery-acceptance.md) in order. Load only the selected route and modules as reached.

## Routes

- [Single-Agent Coding](../references/coding/layer-04-workflows/coding-single-agent.md): use when the released Mode selects `mode: Single-Agent Coding`; directive-related work stays in the current Session.
- [Multi-Agent Coding](../references/coding/layer-04-workflows/coding-multi-agent.md): use when the released Mode selects Multi-Agent Coding with a locked positive `child_count`. The Mode checkpoint owns the four-option menu, default, and invalid-input handling; locking the budget does not initialize a child.

Do not load both routes. If a later material fact invalidates the selected route, stop the current slice, amend the Contract as needed, and return to Route Entry.

## Document layers

These layers define composition direction, not policy ownership. Each document may keep its language-switch link; dependency links must remain same-language.

| Layer | Role | Allowed dependency targets |
| --- | --- | --- |
| [`layer-01-fundamental-concepts`](../references/coding/layer-01-fundamental-concepts/) | Foundational atomic concepts | Same-language layer-01 concepts and its language mirror |
| [`layer-02-workflow-concepts`](../references/coding/layer-02-workflow-concepts/) | Generic workflow checkpoint actions and evidence | `layer-01-fundamental-concepts`; never layer-03/04 |
| [`layer-03-workflow-checkpoints`](../references/coding/layer-03-workflow-checkpoints/) | Task-specific applicability, branches, and composition decisions | layer-01 and layer-02; never layer-04 |
| [`layer-04-workflows`](../references/coding/layer-04-workflows/) | Complete executable routes | shared protocols, layer-01, layer-02, and layer-03; routes may also call only their exact approved same-language Layer-04 modules, while modules depend only on shared protocols and Layers 01–03 and never call sibling modules |
| `workflows/coding.md` | Route selector and four-layer index | All four layers; owns navigation, not policy |

If a lower layer needs a concept owned by a higher layer, treat that upward dependency as an atomicity failure: split the lower document and move the composition to the higher layer. Root entry documents such as `SKILL.md`, `README.md`, and `docs/` may link downward to entry points. Validate the boundaries with `python3 scripts/check-doc-layer-links.py`; language-switch links are the only intentional cross-language links.

## Checkpoint catalog

The selected layer-04 route orders the [layer-02 checkpoint actions](../references/coding/layer-02-workflow-concepts/) and [layer-03 task-specific decisions](../references/coding/layer-03-workflow-checkpoints/) that apply:

`contract` → `environment` (+ capability inventory) → `mode` → `context` → `decision` → `implementation` → `control` → `verification` → `repair` → `documentation` → `git` → `acceptance`

The catalog is navigation only. A checkpoint does not route to another checkpoint; the selected route defines the actual sequence and records why a conditional checkpoint is skipped.

## Completion

Return `COMPLETE` only after the selected route reaches Acceptance with current evidence. Report unavailable checks, assumptions, residual risks, authorized effects, and the recorded delegation state. Do not cause external effects without explicit authorization.
