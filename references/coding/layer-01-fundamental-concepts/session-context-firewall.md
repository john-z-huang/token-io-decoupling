# Coding Session Context Firewall

[English](session-context-firewall.md) | [简体中文](session-context-firewall_zh_cn.md)

This module owns the Context Firewall: raw-state ingress limits, bounded inspection, fact-return boundaries, and ephemeral project localization. It does not define role responsibilities, Session semantics, file-backed context transport, or workflow acceptance.

## General rules

### Raw-state ingress

In a multi-Session Coding run, the input-side Session directly inspects the bounded project-environment and code evidence required to confirm a child's task before dispatch; it does not perform open-ended project inspection. Primary Output consumes further source/configuration state only within the parent's confirmed and released scope; Change Verification consumes final-state evidence; Documentation/Comments & Git Operations consumes Git state and approved documentation scope. Each returns only the facts needed for the next decision.

The input-side Session may directly inspect bounded, read-only source/configuration excerpts and environment evidence needed for its prerequisite fact confirmation. It records exact source pointers and conclusions before child assignment. Potential output volume and repository-state impact determine the boundary, not the command name. A single Session has no cross-Session firewall, but still reads progressively and compresses raw state.

### Semantic ownership and ephemeral localization

The firewall limits raw-state ingress, not semantic reasoning. The input-side role retains ownership of meaning, trade-offs, release decisions, and acceptance. Ephemeral UI/project localization belongs to the Session that observes it and is not promoted to long-lived Contract state.

## Codex CLI / ChatGPT Desktop optimizations

No provider-specific optimization instructions at present; follow the general rules above.

## Claude Code CLI / Claude Desktop optimizations

No provider-specific optimization instructions at present; follow the general rules above.

## Related concepts

- [Coding Session Model](session-model.md) — locate Session semantics and affinity.
- [Coding Session Role Ownership](session-role-ownership.md) — locate role responsibility ownership.
- [Coding Context Exchange](context-exchange.md) — locate file-backed context transport.
- [Coding Delegation State Record](delegation-state-record.md) — locate task-control state ownership.
- [Coding Execution Control](execution-control.md) — locate bounded stage and slice ownership.
