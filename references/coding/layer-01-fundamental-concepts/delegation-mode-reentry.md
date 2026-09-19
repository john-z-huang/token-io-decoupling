# Coding Delegation Re-entry

[English](delegation-mode-reentry.md) | [简体中文](delegation-mode-reentry_zh_cn.md)

This module owns re-entry into the mode and count gates and the blocking boundary for higher-priority constraints or unavailable capabilities. It consumes the mode-confirmation and count-gate outcomes; it does not repeat their confirmation or count-locking policies, and it does not define child creation or lifecycle.

## Gate re-entry

Every new root directive reopens the mode and count gates, including when work continues in the same project. A later directive that materially changes delegation must re-apply those gates before changing topology or continuing the changed route.

## Higher-priority constraints and capability blocks

Higher-priority user, permission, security, product, runtime, capability, repository, and safety constraints always apply. An unavailable capability blocks the route; it never authorizes silently changing mode or count.

## Related concepts

- [Coding Delegation Mode Confirmation](delegation-mode-confirmation.md) — locate mode confirmation ownership.
- [Coding Delegation Count Gate](delegation-mode-count-gate.md) — locate count locking ownership.
- [Coding Delegation Re-entry](delegation-mode-reentry.md) — locate gate re-entry ownership.
- [Coding Delegation State Record](delegation-state-record.md) — locate state record ownership.
- [Coding Child Creation](delegation-child-creation.md) — locate child creation ownership.
- [Coding Child Lifecycle](delegation-child-dispatch-lifecycle.md) — locate child lifecycle ownership.
