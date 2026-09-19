# Coding Delegation Mode Confirmation

[English](delegation-mode-confirmation.md) | [简体中文](delegation-mode-confirmation_zh_cn.md)

This module owns root-directive mode recommendation and explicit confirmation, pre-confirmation restrictions, and Single-Agent route restrictions. It consumes and updates the state record; it does not define count locking, re-entry, child creation, or lifecycle.

## Root-directive mode confirmation

For every new root user directive, the root parent must:

1. Analyze the task enough to make a useful recommendation.
2. Recommend Single-Agent Coding or Multi-Agent Coding with a concise reason.
3. Ask the user to choose and wait for an unambiguous confirmation.

A mode stated in the directive is input to the recommendation, not a substitute for confirmation. Until confirmation, do not create/manage Agents or Sessions, release Dispatch, or begin substantive reconnaissance, implementation, verification, documentation, or Git work. Mandatory instruction loading and capability checks needed to form the question are allowed.

Record the confirmed mode in the task-control record. Ambiguous or non-responsive input does not release it.

## Single-Agent Coding

After confirmation, keep all work in the current Session. Do not create, fork, hand off to, message, replace, or otherwise manage a child Agent or additional Session. Structural benefit, verification, documentation/Git needs, bootstrap, recovery, or runtime convenience are not exceptions. Independent verification remains a semantic requirement, but is unavailable on this route.

## Related concepts

- [Coding Delegation Mode Confirmation](delegation-mode-confirmation.md) — locate mode confirmation ownership.
- [Coding Delegation Count Gate](delegation-mode-count-gate.md) — locate count locking ownership.
- [Coding Delegation Re-entry](delegation-mode-reentry.md) — locate gate re-entry ownership.
- [Coding Delegation State Record](delegation-state-record.md) — locate state record ownership.
- [Coding Child Creation](delegation-child-creation.md) — locate child creation ownership.
- [Coding Child Lifecycle](delegation-child-dispatch-lifecycle.md) — locate child lifecycle ownership.
