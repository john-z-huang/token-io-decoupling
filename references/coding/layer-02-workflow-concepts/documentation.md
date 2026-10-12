# Documentation Checkpoint

[English](documentation.md) | [简体中文](documentation_zh_cn.md)

## Actions

1. Confirm the approved documentation paths, audience, purpose, and source evidence.
2. Change only the approved Markdown or comment scope. Keep English and Simplified Chinese mirrors synchronized when both are maintained.
3. When repository documentation, a code comment, or a project-memory note changes, advance the documentation epoch and run the checks applicable to that changed output, including Markdown, link, whitespace, multilingual, and scope checks where relevant.
4. If a repository documentation, code comment, or project-memory note change alters executable content, the Contract, or acceptance conditions, return to the related implementation and Verification checkpoints. Otherwise, do not rerun unrelated product behavior tests solely because the documentation epoch changed.
5. Do not add new behavior, policy, scope, or Git effects under the label of documentation, and report checks that could not run.
6. If approved output includes reusable Agent project knowledge or a cross-session note the user explicitly requested, write it through the [project-memory and code-structure capability](../layer-01-fundamental-concepts/LSP-MCP-Tools.md), preserving the existing name and subdirectory intent, and confirm the successful write result. If no such output was requested, record `Not applicable` with the reason. If the capability is unavailable or the write fails, report the failure and keep that requested output incomplete. Authoritative repository documents and code comments remain in their approved repository file paths and follow the existing mirror, epoch, check, and return rules above.

## Pass condition

Approved documentation is accurate for the applicable verified state, its current documentation epoch is explicit, its applicable checks pass or have explicit unavailable results, all reusable Agent project knowledge included in approved output and every cross-session note explicitly requested by the user have been successfully saved with their write results confirmed, and any content-affecting change has returned through implementation Verification.

## Boundary

This checkpoint does not replace implementation verification, authorize product decisions, or authorize Git effects.

## Related concepts

- [Coding Content Memo](../layer-01-fundamental-concepts/content-memo.md) — locate reusable memo content-contract ownership.
- [Coding Content Memo Lifecycle](../layer-01-fundamental-concepts/content-memo-lifecycle.md) — locate memo lifecycle ownership.
- [Coding Execution Control](../layer-01-fundamental-concepts/execution-control.md) — locate approved documentation-scope ownership.
