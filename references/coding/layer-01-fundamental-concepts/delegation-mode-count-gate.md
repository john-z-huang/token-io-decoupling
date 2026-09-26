# Coding Delegation Count Gate

[English](delegation-mode-count-gate.md) | [简体中文](delegation-mode-count-gate_zh_cn.md)

This module owns Multi-Agent child-count selection, locking, and count-budget boundaries. It consumes the selected mode and the state record; it does not define mode selection, re-entry, child creation, or lifecycle.

## General rules

### Count selection and lock

For a selected Multi-Agent conversation, take the explicit positive child count supplied with the mode choice, if any. Otherwise use one child, including after the 15-second timeout. Do not ask a second blocking count question. Reject an invalid explicit count and keep the route unreleased until the user supplies a valid positive integer; do not reinterpret it as consent to a different count. The count is a conversation-wide total child budget, not a per-task, per-stage, or per-role number.

Lock the count before the first Dispatch and form exactly that many planned allocations before route release; entries may use `agent: unbound` until creation. With one child, allocate Primary Output; independent Change Verification and documentation/Git child roles remain unallocated, so label same-Session checks as logical and independence unavailable. Every independently assigned role consumes a slot. Reuse does not. After locking, never create a replacement, fork, handoff successor, extra verifier, or other child that would exceed the count. If a required slot or capability is unavailable, block the dependent work instead of changing the count silently.

## Codex CLI / ChatGPT Desktop optimizations

No provider-specific optimization instructions at present; follow the general rules above.

## Claude Code CLI / Claude Desktop optimizations

No provider-specific optimization instructions at present; follow the general rules above.

## Related concepts

- [Coding Delegation Mode Confirmation](delegation-mode-confirmation.md) — locate root mode confirmation ownership.
- [Coding Delegation Count Gate](delegation-mode-count-gate.md) — locate count locking ownership.
- [Coding Delegation Re-entry](delegation-mode-reentry.md) — locate gate re-entry ownership.
- [Coding Delegation State Record](delegation-state-record.md) — locate state record ownership.
- [Coding Child Creation](delegation-child-creation.md) — locate child creation ownership.
- [Coding Child Lifecycle](delegation-child-lifecycle.md) — locate child lifecycle ownership.
