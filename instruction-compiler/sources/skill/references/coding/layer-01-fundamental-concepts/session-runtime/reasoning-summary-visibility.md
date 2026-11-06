# Coding Agent Reasoning Summary Visibility

[English](reasoning-summary-visibility.md) | [简体中文](reasoning-summary-visibility_zh_cn.md)

This module defines the safe, concise summary an Agent makes visible at the end of a completed reasoning turn. It does not require disclosure of private internal reasoning or replace decision, stage-feedback, verification, or message-visibility owners.

## General rules

### Summary boundary and contents

A completed Agent reasoning turn is a visible conversation boundary where the Agent is about to return to the user or parent, pause, yield control, or hand off work. Internal tool calls and continued work within the same turn do not each require a separate summary.

At such boundaries, follow the configured cadence in [session audit visibility](session-audit-visibility.md). `full` uses the summary below at every completed boundary. `milestone_only` uses it at material decisions, authorization changes, verification failures, blockers, and stage acceptance; ordinary unchanged waits and mechanics do not create repeated summary blocks. `off` suppresses this optional block. Required Progress Signals, evidence, control deltas, verification reports, and higher-level periodic updates remain required.

### Fixed visible format

Enclose the summary using these exact ASCII markers, each on its own line: `[[REASONING_SUMMARY_BEGIN]]` and `[[REASONING_SUMMARY_END]]`. Keep ordinary replies, status updates, and all other non-summary content outside the markers; do not place an unmarked reasoning summary outside them. Use the conversation language and fill every field in this fixed order: conclusion/progress; key evidence and source; brief rationale; material assumptions/uncertainty/blockers; next step.

When cadence requires a summary and there is no material change, retain both markers and every field. State “No material change,” say there is no new evidence, decision, or assumption, and give the next step; do not emit an empty block. Do not emit an empty marker block when a reasoning turn has not ended.

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

The summary does not replace a Decision Brief, a Progress Signal at a declared stage boundary, verification evidence, or message-body evidence. When a completed turn coincides with a stage boundary, combine the required information into one concise visible summary rather than repeating it. A Worker final result that is already complete in its conversation is the outbound copy; do not duplicate it. Root still reads the complete actual return before relying on it, while the visible Root copy follows the configured message preset. If required evidence is unavailable, report the limitation and block dependent action.

## Codex CLI / ChatGPT Desktop optimizations

Apply the configured Root or Worker cadence from [session audit visibility](session-audit-visibility.md). This Skill setting is not a native parameter and never permits private reasoning disclosure.

## Claude Code CLI / Claude Desktop optimizations

No provider-specific optimization instructions at present; follow the general rules above using only conversation output available to the current Session.

## Related concepts

- [Coding Session Role Ownership](session-role-ownership.md) — locate role responsibilities and semantic ownership.
- [Coding Execution Stage Feedback](../execution-control/execution-stage-feedback.md) — locate Progress Signal boundaries.
- [Coding Child Message Visibility](../delegation/delegation-child-message-visibility.md) — locate complete message-body visibility requirements.
- [Coding Session Audit Visibility](session-audit-visibility.md) — locate configured cadence and defaults.
- [Coding Execution Decision Gate](../execution-planning/execution-decision-gate.md) — locate Decision Brief and decision ownership.
