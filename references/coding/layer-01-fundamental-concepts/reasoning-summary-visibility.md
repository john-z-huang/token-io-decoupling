# Coding Agent Reasoning Summary Visibility

[English](reasoning-summary-visibility.md) | [简体中文](reasoning-summary-visibility_zh_cn.md)

This module defines the safe, concise summary an Agent makes visible at the end of a completed reasoning turn. It does not require disclosure of private internal reasoning or replace decision, stage-feedback, verification, or message-visibility owners.

## General rules

### Summary boundary and contents

A completed Agent reasoning turn is a visible conversation boundary where the Agent is about to return to the user or parent, pause, yield control, or hand off work. Internal tool calls and continued work within the same turn do not each require a separate summary.

At each such boundary, provide a concise summary in the current conversation containing the current conclusion or progress, key evidence and its source, brief decision rationale, material assumptions/uncertainties/blockers, and next step. When there is no material change, say so in one sentence and state the next action.

### Fixed visible format

Enclose the summary using these exact ASCII markers, each on its own line: `[[REASONING_SUMMARY_BEGIN]]` and `[[REASONING_SUMMARY_END]]`. Keep ordinary replies, status updates, and all other non-summary content outside the markers; do not place an unmarked reasoning summary outside them. Use the conversation language and fill every field in this fixed order: conclusion/progress; key evidence and source; brief rationale; material assumptions/uncertainty/blockers; next step.

When there is no material change, retain both markers and every field. State “No material change,” say there is no new evidence, decision, or assumption, and give the next step; do not emit an empty block. Do not emit an empty marker block when a reasoning turn has not ended.

English example:

```text
[[REASONING_SUMMARY_BEGIN]]
Conclusion / progress: No material change.
Key evidence and source: No new evidence.
Brief rationale: No new decision.
Material assumptions / uncertainty / blockers: No new assumptions or blockers.
Next step: Continue the released task.
[[REASONING_SUMMARY_END]]
```

Simplified Chinese example:

```text
[[REASONING_SUMMARY_BEGIN]]
结论/进展：无实质变化。
关键证据及来源：无新增证据。
简短依据：无新增决定。
重要假设/不确定性/阻塞：无新增假设或阻塞。
下一步：继续已放行的任务。
[[REASONING_SUMMARY_END]]
```

The markers identify only a safe summary. They do not permit private step-by-step internal reasoning, hidden chain of thought, or raw scratchpad.

Do not include private step-by-step internal reasoning, hidden chain of thought, raw scratchpad, exhaustive internal process, secrets, or unverified claims. Do not present the summary as a complete record of internal reasoning.

### Relationship to other evidence

The summary does not replace a Decision Brief, a Progress Signal at a declared stage boundary, verification evidence, or the complete safe body required by child-message visibility. When a completed turn coincides with a stage boundary, combine the required information into one concise visible summary rather than repeating it. In Multi-Agent Coding, a Worker return body retains its complete safe content; the summary block is only one part of that body, and the parent displays the full body under the child-message-visibility owner before relying on it. If the required summary is not visible or is incomplete, report the limitation and block dependent action; do not claim it was displayed.

## Codex CLI / ChatGPT Desktop optimizations

No provider-specific optimization instructions at present; follow the general rules above using only conversation output available to the current Session.

## Claude Code CLI / Claude Desktop optimizations

No provider-specific optimization instructions at present; follow the general rules above using only conversation output available to the current Session.

## Related concepts

- [Coding Session Role Ownership](session-role-ownership.md) — locate role responsibilities and semantic ownership.
- [Coding Execution Stage Feedback](execution-stage-feedback.md) — locate Progress Signal boundaries.
- [Coding Child Message Visibility](delegation-child-message-visibility.md) — locate complete message-body visibility requirements.
- [Coding Execution Decision Gate](execution-decision-gate.md) — locate Decision Brief and decision ownership.
