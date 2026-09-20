# Documentation Checkpoint

[English](documentation.md) | [简体中文](documentation_zh_cn.md)

## Actions

1. Confirm the approved documentation paths, audience, purpose, and source evidence.
2. Change only the approved Markdown or comment scope. Keep English and Simplified Chinese mirrors synchronized when both are maintained.
3. After a documentation or comment change, advance the documentation epoch and run applicable Markdown, link, whitespace, multilingual, and scope checks.
4. If the documentation or comment change alters executable content, the Contract, or acceptance conditions, return to the related implementation and Verification checkpoints. Otherwise, do not rerun unrelated product behavior tests solely because the documentation epoch changed.
5. Do not add new behavior, policy, scope, or Git effects under the label of documentation, and report checks that could not run.

## Pass condition

Approved documentation is accurate for the applicable verified state, its current documentation epoch is explicit, its applicable checks pass or have explicit unavailable results, and any content-affecting change has returned through implementation Verification.

## Boundary

This checkpoint does not replace implementation verification, authorize product decisions, or authorize Git effects.

## Related concepts

- [Coding Content Memo](../layer-01-fundamental-concepts/content-memo.md) — locate reusable memo content-contract ownership.
- [Coding Content Memo Lifecycle](../layer-01-fundamental-concepts/content-memo-lifecycle.md) — locate memo lifecycle ownership.
- [Coding Execution Control](../layer-01-fundamental-concepts/execution-control.md) — locate approved documentation-scope ownership.
