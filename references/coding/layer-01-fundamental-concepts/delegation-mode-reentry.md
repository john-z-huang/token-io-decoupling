# Coding Delegation Re-entry

[English](delegation-mode-reentry.md) | [简体中文](delegation-mode-reentry_zh_cn.md)

This module owns re-entry into the mode and count gates and the blocking boundary for higher-priority constraints or unavailable capabilities. It consumes the mode-confirmation and count-gate outcomes; it does not repeat their confirmation or count-locking policies, and it does not define child creation or lifecycle.

## General rules

### Gate re-entry

A later root directive in the same conversation reuses the locked mode and child-count budget; it does not reopen the selection timer or replace the session decision. Refresh task-specific Contract, slices, allocations' current lifecycle, and capability evidence as needed. Re-enter mode and count selection only in a new conversation. If a later same-conversation instruction conflicts with the locked topology, stop dependent work and explain that a new conversation is required for a different mode or count.

### Higher-priority constraints and capability blocks

Higher-priority user, permission, security, product, runtime, capability, repository, and safety constraints always apply. An unavailable capability blocks the route; it never authorizes silently changing mode or count.

## Codex CLI / ChatGPT Desktop optimizations

No provider-specific optimization instructions at present; follow the general rules above.

## Claude Code CLI / Claude Desktop optimizations

No provider-specific optimization instructions at present; follow the general rules above.

## Related concepts

- [Coding Delegation Mode Confirmation](delegation-mode-confirmation.md) — locate mode confirmation ownership.
- [Coding Delegation Count Gate](delegation-mode-count-gate.md) — locate count locking ownership.
- [Coding Delegation Re-entry](delegation-mode-reentry.md) — locate gate re-entry ownership.
- [Coding Delegation State Record](delegation-state-record.md) — locate state record ownership.
- [Coding Child Creation](delegation-child-creation.md) — locate child creation ownership.
- [Coding Child Lifecycle](delegation-child-lifecycle.md) — locate child lifecycle ownership.
