# Coding Delegation Count Gate

[English](delegation-mode-count-gate.md) | [简体中文](delegation-mode-count-gate_zh_cn.md)

This module owns Multi-Agent child-count selection, locking, and count-budget boundaries. It consumes the selected mode and the state record; it does not define mode selection, re-entry, child creation, or lifecycle.

## General rules

### Count selection and lock

For a selected Multi-Agent Session, take the explicit positive child count supplied by the user, if any. Otherwise lock a budget of one child. This default also applies when Multi-Agent is selected as the first Coding directive's default. The Skill sets no maximum for this initial positive count. If the user selected the custom-count menu option but omitted or supplied an invalid count, ask one focused follow-up and keep the Mode gate unreleased; never substitute one. Do not ask an additional count question when the count is valid. Reject any other invalid explicit count and keep the route unreleased until the user supplies a valid positive integer; do not reinterpret it as consent to a different count. The count is a total child budget for the host Session lifetime, not a per-turn, per-task, per-stage, or per-role number.

Lock the count before route release and reserve exactly that many planned allocation slots in the parent record. Each reserved slot starts with `agent: unbound`, `role: unassigned`, `slice_status: pending`, and `lifecycle: pending`; it does not assert that Context, Decision, or a concrete slice is released, and does not initialize a child. Reservation does not select a role or make Primary Output the automatic role for a one-child budget. After current task context and Decision are reviewed, [Child Role Selection](child-role-selection.md) selects a role and the allocation owner records it in an unassigned slot. No child may be created until its role and current slice are released and the output is code/configuration implementation or authorship/editing of this Skill's instructions or reference documents. Ordinary non-Skill documentation never triggers or consumes a reserved slot; the root parent authors it, including when code changes are also present. Every independently assigned role consumes one reserved slot; reuse consumes none. Locking the count fixes the total budget, not the contents of an unbound slot.

### Explicit one-slot increase

If no unassigned slot remains and current facts establish a need for one additional child with a different, unoccupied role, Root may ask the user for explicit approval to increase the locked count by exactly one. No model advice, inferred intent, prior approval for another change, or API result is user approval. Root must review the actual user instruction and supply its `SemanticRef` or `EvidenceRef` in the guarded reservation transaction. The transaction accepts the increase only when the requested count equals the current count plus one, preserves the prior count source in the canonical semantic references, records the new approval as the current source, and atomically adds and reserves the unoccupied role in one new slot. Its mutation receipt records the approval evidence and the old/new counts. If any fact is missing, approval is unclear, the new role is already reserved or created, or the exact count cannot be represented by the existing approval contract (which accepts approved counts through four), preserve the state and stop; do not coerce or split the request. An explicit initial count is not capped by that approval-field limit.

An increase does not choose a role from the budget alone, release a slice, or create a child. A remaining unassigned slot is used under the existing count and normal release gates; it does not require budget approval. A role assignment on an unbound, not-yet-created slot may be revised only as a parent-authorized plan update within the current count, and the replacement role must be unoccupied. Once a child is created, its identity, slot, and role are permanent in this Session: never recycle or replace them, including through a fork or handoff successor. Only an additional child above the current count requires the exact one-slot user approval above, and that approval is for a different unoccupied role, never a replacement. If all maintained roles are occupied, approval cannot authorize a repeated role. If a required slot or capability is unavailable, block dependent work instead of silently changing the count.

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
- [Coding Child Role Selection](child-role-selection.md) — locate the selection that uses approved capacity.
