# Coding Child Message Visibility

[English](delegation-child-message-visibility.md) | [简体中文](delegation-child-message-visibility_zh_cn.md)

This module owns only the conversation visibility and body evidence for text messages between the parent conversation and child Agents. It does not define message authorization or content scope.

## General rules

### Configured display; complete body before reliance

Apply the configured [session audit visibility](session-audit-visibility.md) preset. The Worker must keep the complete safe inbound and outbound bodies visible in its own conversation. For Root messages, show the configured preview, summary, or full body; when full display is required, show the complete safe body before sending and confirm it exactly matches the payload. A Worker final result already visible in full is its outbound copy and must not be duplicated.

After a message arrives, Root must obtain and read the complete actual returned body before relying on it. Root displays the full safe body or configured summary in the primary conversation according to the preset. Tool-call cards, activity events, delivery receipts, task status, or notices such as “message sent” are not the message body and cannot replace it.

When full display is required by role or preset, a long body may be displayed in consecutively numbered parts without summarizing or truncating it; clearly mark any redactions. If the actual body is not exposed and cannot be reproduced from the conversation record, do not use the message for dependent work.

### Preserve direction and evidence

Identify each message's direction and, when the runtime exposes identity, its intended or source child. Keep the body distinguishable from commentary. A paraphrase, summary, or claim that content was sent or received is not evidence of the message body.

## Codex CLI / ChatGPT Desktop optimizations

### Use the message tool exposed to the current Session

When `collaboration.send_message` is exposed and authorized, apply the configured preset. A Worker keeps complete safe inbound and outbound bodies visible; a full Root outbound display must match the payload. Root always reads the complete actual return before reliance, while its visible copy follows the preset. If the actual body cannot be reproduced from the conversation record, block dependent work. A visible copy is not proof of original transport bytes.

## Claude Code CLI / Claude Desktop optimizations

### Use the exposed SendMessage tool

Anthropic's [Agent Teams documentation](https://code.claude.com/docs/en/agent-teams) describes `SendMessage` as the tool for sending messages between agents. When the current Session exposes and authorizes it, follow the general configured preset. A Worker retains complete safe inbound and outbound visibility; Root reads the full actual return before reliance, with display governed by the preset. A visible copy does not prove original transport bytes. If `SendMessage` is unavailable, do not assume it exists; the general evidence requirement still applies.

## Related concepts

- [Coding Child Creation](delegation-child-creation.md) — locate the creation boundary for a new child prompt.
- [Coding Child Dispatch](delegation-child-dispatch.md) — locate released-slice and follow-up dispatch requirements.
- [Coding Child Lifecycle](delegation-child-lifecycle.md) — locate child status and return handling.
- [Coding Session Audit Visibility](session-audit-visibility.md) — locate session visibility presets and their precedence.
