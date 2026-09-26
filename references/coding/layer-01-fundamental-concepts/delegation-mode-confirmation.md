# Coding Delegation Mode Confirmation

[English](delegation-mode-confirmation.md) | [简体中文](delegation-mode-confirmation_zh_cn.md)

This module owns the conversation's initial mode question, explicit selection or timed default, pre-selection restrictions, and Single-Agent route restrictions. It consumes and updates the state record; it does not define count locking, re-entry, child creation, or lifecycle.

## General rules

### Session mode selection

On the first Coding directive of a conversation, the root parent must:

1. Check whether the user already explicitly chose Single-Agent or Multi-Agent Coding in that directive. If so, record that choice without asking again.
2. Otherwise ask once: `For this conversation, choose Single-Agent Coding or Multi-Agent Coding. If choosing Multi-Agent, you may specify a positive child count. I will wait 15 seconds; without a clear reply, I will use Multi-Agent Coding with one child.` Recommend a mode with a short reason in the same message.
3. Start a 15-second wall-clock timer when the question is sent. Use a non-blocking input channel if exposed; never use an indefinitely blocking question tool for this gate. During the wait, only mandatory instruction loading and capability checks may proceed; do not create children, release Dispatch, or begin substantive project work.
4. If an unambiguous choice is observable by the deadline, use it. If none is observable, select Multi-Agent Coding with one child. A late reply does not silently change the locked conversation mode.
5. Record the selected mode and its source (`explicit` or `timeout-default`) in the parent-controlled state record. Apply the count owner before route release. Keep the mode fixed for the current conversation.

A timeout selects a workflow mode only; it does not grant missing user authorization, bypass a task-level prohibition, or create a capability. If a higher-priority restriction forbids children, it controls; do not start a child under the timeout default. If the required record capability is absent, block the dependent route rather than pretending it exists.

### Single-Agent Coding

After confirmation, keep all work in the current Session. Do not create, fork, hand off to, message, replace, or otherwise manage a child Agent or additional Session. Structural benefit, verification, documentation/Git needs, bootstrap, recovery, or runtime convenience are not exceptions. Independent verification remains a semantic requirement, but is unavailable on this route.

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
