# Coding Child Message Visibility

[English](delegation-child-message-visibility.md) | [简体中文](delegation-child-message-visibility_zh_cn.md)

This module owns only the conversation visibility and body evidence for text messages between the parent conversation and child Agents. It does not define message authorization or content scope.

## General rules

### Show before sending; show before relying

When the parent or a child Agent is the sender, it must display the complete safe outbound body as ordinary text in its current sending conversation before calling a messaging tool, and confirm that the displayed text exactly matches the payload. This applies both to parent-to-child and child-to-parent messages.

After a message arrives, the parent must display its complete safe returned body as ordinary text in the primary parent conversation before relying on, summarizing, or taking dependent action on it. Tool-call cards, activity events, delivery receipts, task status, or notices such as “message sent” are not the message body.

If a body is too long, display it in consecutively numbered parts without summarizing or truncating it; clearly mark any redactions. If the runtime does not expose the body and neither the sender nor the parent can reproduce it from the conversation record, do not use the message for a dependent slice.

### Preserve direction and evidence

Identify each message's direction and, when the runtime exposes identity, its intended or source child. Keep the body distinguishable from commentary. A paraphrase, summary, or claim that content was sent or received is not evidence of the message body.

## Codex CLI / ChatGPT Desktop optimizations

### Use the message tool exposed to the current Session

When `collaboration.send_message` is exposed and authorized for either the parent or child Agent's current Session, the sender must display the complete safe outbound body as ordinary text in that same Session before calling the tool and confirm it matches the payload. After receiving a message, the parent must display the complete safe body in the primary parent conversation before relying on it. Tool-call cards, activity events, receipts, and status do not replace the body; block the dependent slice if the complete body cannot be reproduced from the conversation record.

## Claude Code CLI / Claude Desktop optimizations

### Use the exposed SendMessage tool

Anthropic's [Agent Teams documentation](https://code.claude.com/docs/en/agent-teams) describes `SendMessage` as the tool for sending messages between agents. When the current Session exposes and authorizes it to the parent or child Agent, the sender—whether parent or child—must first display the complete safe outbound body as ordinary text in its own conversation, then call the tool and confirm the displayed text matches the payload. After receiving a message, the parent must display the complete safe body in the primary parent conversation before relying on it. If the current path does not expose `SendMessage`, this tool-specific pre-call check does not apply; the general returned-body visibility rule still applies.

## Related concepts

- [Coding Child Creation](delegation-child-creation.md) — locate the creation boundary for a new child prompt.
- [Coding Child Dispatch](delegation-child-dispatch.md) — locate released-slice and follow-up dispatch requirements.
- [Coding Child Lifecycle](delegation-child-lifecycle.md) — locate child status and return handling.
