# Coding Delegation Re-entry

[English](delegation-mode-reentry.md) | [简体中文](delegation-mode-reentry_zh_cn.md)

This module owns re-entry into the mode and count gates and the blocking boundary for higher-priority constraints or unavailable capabilities. It consumes the mode-confirmation and count-gate outcomes; it does not repeat their confirmation or count-locking policies, and it does not define child creation or lifecycle.

## General rules

### Gate re-entry

A later root directive in the same host-identified Session lifetime reuses the locked mode and current child-count budget; it does not reopen mode selection or replace the session decision. A later turn, compaction, or same-Session resume does not reset these gates. The only same-Session count change is the exact one-slot increase authorized by the [Delegation Count Gate](delegation-mode-count-gate.md) after actual explicit user approval for a different unoccupied role. That transaction changes the count only; it does not reselect the mode, release a slice, or create a child. Other requested count or topology changes block dependent work until a new Session. Refresh task-specific Contract, slices, allocations' current lifecycle, and capability evidence as needed.

A Fork starts a new conversation with a new Session identity. Before any dependent work, perform fresh mode confirmation, count selection, and state-record initialization even if the source conversation used Single-Agent mode. Treat inherited child identities as foreign to the new Session: do not adopt them as created, reserved, resumable, or eligible current-session candidates. Build the new record from this conversation's current user direction and state; do not carry over the source conversation's locked mode/count decision as if it were newly selected.

### Higher-priority constraints and capability blocks

Higher-priority user, permission, security, product, runtime, capability, repository, and safety constraints always apply. An unavailable capability blocks the route; it never authorizes silently changing mode or count.

## Codex CLI / ChatGPT Desktop optimizations

No provider-specific optimization instructions at present; follow the general rules above.

## Claude Code CLI / Claude Desktop optimizations

No provider-specific optimization instructions at present; follow the general rules above.

## Related concepts

- [Coding Delegation Mode Confirmation](delegation-mode-confirmation.md) — locate mode confirmation ownership.
- [Coding Delegation Count Gate](delegation-mode-count-gate.md) — locate count locking ownership.
- [Coding Delegation State Record](delegation-state-record.md) — locate state record ownership.
- [Coding Session Model](session-model.md) — locate Session identity and Fork boundaries.
- [Coding Child Creation](delegation-child-creation.md) — locate child creation ownership.
- [Coding Child Lifecycle](delegation-child-lifecycle.md) — locate child lifecycle ownership.
