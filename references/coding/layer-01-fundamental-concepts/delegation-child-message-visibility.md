# Coding Child Message Visibility

[English](delegation-child-message-visibility.md) | [简体中文](delegation-child-message-visibility_zh_cn.md)

This module owns the parent-conversation visibility and evidence requirements for text exchanged between a parent Session and its child Agents. It does not authorize delegation, define message content scope, or replace child creation, dispatch, lifecycle, or context-transport owners.

## General rules

### Show the complete user-shareable body

For every parent-to-child or child-to-parent text message, make the complete user-shareable body visible as ordinary text in the primary parent conversation. Before sending, show the exact outbound body; after receiving, show the complete returned body before relying on it, summarizing it, or taking dependent action. The displayed outbound body must match the actual payload. If a returned body needs redaction, mark each redaction and use only the displayed safe representation downstream. Tool-call cards, activity events, delivery receipts, task status, and notices such as “message sent” do not satisfy this requirement unless they expose the complete body as readable conversation text.

If a message is too long for one turn, show it in numbered consecutive parts without summarizing, truncating, or omitting user-shareable content. Do not expose credentials, secrets, private chain-of-thought, or other content that is not user-shareable. Sanitize outbound payloads before sending and display the exact sanitized payload. For returned content, explicitly mark redactions, preserve all user-shareable content, and do not act on hidden content. If decision-relevant content cannot be safely represented, the full safe body cannot be displayed, or the runtime exposes only a status notice and the parent cannot reproduce the payload, block the dependent slice and keep it with the parent.

### Preserve direction and evidence

Identify whether each displayed body is outgoing or returned, and identify its intended child or source child when that identity is available. Keep the text distinguishable from the parent's commentary. A paraphrase, summary, or claim that content was sent or received is not evidence of the message body.

## Codex CLI / ChatGPT Desktop optimizations

### Use the exposed parent-controlled tools

Use `collaboration.spawn_agent`, `collaboration.send_message`, and `collaboration.followup_task` only when the active Session exposes and authorizes them. Use `spawn_agent` only after the child slot, role, and slice are released, and include the complete task body in the actual child prompt. Use `send_message` to queue an authorized message; use `followup_task` when queued input must trigger a child turn.

Before each call, display the complete safe outbound body as ordinary text in the parent conversation, and make sure it matches the payload. After receiving a child response, display its complete safe body there before relying on it. A successful call, activity event, receipt, child identity, or status does not count as the message body. If a result omits the body, reproduce the complete body as ordinary text; if the complete safe text cannot be recovered or displayed, block the dependent slice. Use only directly exposed messaging and result tools; do not use desktop UI interaction to recover content.

## Claude Code CLI / Claude Desktop optimizations

### Use the exposed Agent prompt and returned messages

Use the parent-controlled `Agent` task prompt for initial dispatch and `SendMessage` addressed by child ID or name for an authorized follow-up, only when each tool is exposed and authorized. Before calling either tool, display the complete safe message body as ordinary text in the parent conversation. After receiving a response, display its complete safe body there before relying on it. Do not treat a short Agent label, task status, delivery notice, or tool receipt as the message body. If `SendMessage` is unavailable, record it as `Not applicable`; use the ordinary Agent prompt/result path only when the full bodies can be displayed. Otherwise block the dependent slice.

## Related concepts

- [Coding Child Creation](delegation-child-creation.md) — locate authorization and creation boundaries.
- [Coding Child Dispatch](delegation-child-dispatch.md) — locate released-slice and dispatch requirements.
- [Coding Child Lifecycle](delegation-child-lifecycle.md) — locate child state and return lifecycle.
- [Coding Context Exchange](context-exchange.md) — locate file-based context transport ownership.
