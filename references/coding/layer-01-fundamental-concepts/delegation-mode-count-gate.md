# Coding Delegation Count Gate

[English](delegation-mode-count-gate.md) | [简体中文](delegation-mode-count-gate_zh_cn.md)

This module owns Multi-Agent child-count recommendation, confirmation, locking, and count-budget boundaries. It consumes a confirmed mode and the state record; it does not define root mode confirmation, re-entry, child creation, or lifecycle.

## Count recommendation and confirmation

After Multi-Agent confirmation, recommend the exact positive integer child count, ask the user to confirm it, and wait. The count is the total budget for the root directive, not a per-stage or per-role number.

## Count locking

After count confirmation, lock it before the first Dispatch. Create exactly that many children if the runtime can safely do so; otherwise block rather than silently changing the count. Every independently assigned role consumes a slot. Reuse does not create a slot. Replacement, fork, handoff to a new child, or an additional verifier is a new creation and is forbidden after the lock for this directive.

An unavailable capability blocks this count route; it never authorizes silently changing the confirmed count.

## Related concepts

- [Coding Delegation Mode Confirmation](delegation-mode-confirmation.md) — locate root mode confirmation ownership.
- [Coding Delegation Count Gate](delegation-mode-count-gate.md) — locate count locking ownership.
- [Coding Delegation Re-entry](delegation-mode-reentry.md) — locate gate re-entry ownership.
- [Coding Delegation State Record](delegation-state-record.md) — locate state record ownership.
- [Coding Child Creation](delegation-child-creation.md) — locate child creation ownership.
- [Coding Child Lifecycle](delegation-child-lifecycle.md) — locate child lifecycle ownership.
