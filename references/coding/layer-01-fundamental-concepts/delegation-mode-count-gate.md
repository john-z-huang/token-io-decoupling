# Coding Delegation Count Gate

[English](delegation-mode-count-gate.md) | [简体中文](delegation-mode-count-gate_zh_cn.md)

This module owns Multi-Agent child-count selection, locking, and count-budget boundaries. It consumes the selected mode and the state record; it does not define mode selection, re-entry, child creation, or lifecycle.

## General rules

### Count selection and lock

For a selected Multi-Agent conversation, take the explicit positive child count supplied by the user, if any. Otherwise lock a budget of one child. This default also applies when Multi-Agent is selected as the first Coding directive's default. If the user selected the custom-count menu option but omitted or supplied an invalid count, ask one focused follow-up and keep the Mode gate unreleased; never substitute one. Do not ask an additional count question when the count is valid. Reject any other invalid explicit count and keep the route unreleased until the user supplies a valid positive integer; do not reinterpret it as consent to a different count. The count is a conversation-wide total child budget, not a per-task, per-stage, or per-role number.

Lock the count before route release and reserve exactly that many planned allocation slots in the parent record. Each reserved slot starts with `agent: unbound`, `role: unassigned`, `slice_status: pending`, and `lifecycle: pending`; it does not assert that Context, Decision, or a concrete slice is released, and does not initialize a child. The role-allocation owner assigns roles within those slots after bounded parent fact confirmation. No child may be created until its role and current slice are released and the output is code/configuration implementation or authorship/editing of this Skill's instructions or reference documents. Ordinary non-Skill documentation never triggers or consumes a reserved slot; the root parent authors it, including when code changes are also present. Every independently assigned role consumes one reserved slot; reuse consumes none. Locking the count fixes the total budget, not the contents of an unbound slot.

After count locking, never create a replacement, fork, handoff successor, extra verifier, or other child beyond the budget. A slot whose child was already created cannot be recycled for a different child. If a required slot or capability is unavailable, block the dependent work instead of silently changing the count.

## Codex CLI / ChatGPT Desktop optimizations

No provider-specific optimization instructions at present; follow the general rules above.

## Claude Code CLI / Claude Desktop optimizations

No provider-specific optimization instructions at present; follow the general rules above.

## Related concepts

- [Coding Delegation Mode Confirmation](delegation-mode-confirmation.md) — locate root mode confirmation ownership.
- [Coding Delegation Re-entry](delegation-mode-reentry.md) — locate gate re-entry ownership.
- [Coding Delegation State Record](delegation-state-record.md) — locate state record ownership.
- [Coding Child Creation](delegation-child-creation.md) — locate child creation ownership.
- [Coding Child Lifecycle](delegation-child-lifecycle.md) — locate child lifecycle ownership.
