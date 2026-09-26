# Coding Context Exchange

[English](context-exchange.md) | [简体中文](context-exchange_zh_cn.md)

This module defines the transport capsule for already-assigned Coding Workers: its content restrictions, freshness/invalidation checks, and authoritative-source rules. It does not define workspace layout, directory ownership, capability boundaries, handoff records, task meaning, Agent topology, execution planning, or acceptance.

## General rules

### Transport capsule

Pass only the context needed by the receiving Worker. Prefer a targeted read-only view of the original document. If that is unavailable, the parent or filesystem layer may create and mechanically copy the named documents into the parent-prepared read-only directory `CONTEXT_ROOT/<worker-context-id>/imports/<source-context-id>/`; the Worker may read the import but must not rewrite it. The parent must name the source documents in the concrete handoff or dependency, and the authoritative source remains preferred and binding. Use a compact parent-mediated handoff only when neither filesystem option is safe.

A reusable capsule may contain neutral facts, exact paths and source pointers, hashes, freshness/invalidation data, and narrow evidence pointers. It must not contain implementation reasoning, Contract verdicts, private chain-of-thought, secrets, complete diffs, complete logs, or large source copies. Receiving Workers read the capsule first and then only the named source paths they need; authoritative source files remain binding.

For a capsule under `CONTEXT_ROOT/context-bootstrap/`, use:

```text
MANIFEST.md        snapshot identity, hashes, freshness rules
project-context.md neutral project facts and source pointers
policy-context.md  policy-routing pointers and authoritative sections
```

Check freshness against `HEAD`/tree, tracked-delta fingerprint, listed source hashes, relevant untracked state, and the active task/scope. If a material field changes, refresh only affected sections before relying on the capsule; otherwise read the named authoritative sources directly. A capsule never replaces independent final-state verification.

## Codex CLI / ChatGPT Desktop optimizations

No provider-specific optimization instructions at present; follow the general rules above.

## Claude Code CLI / Claude Desktop optimizations

No provider-specific optimization instructions at present; follow the general rules above.

## Related concepts

- [Coding Context Exchange Workspace Boundary](context-exchange-workspace-boundary.md) — locate workspace and capability boundaries.
- [Coding Context Exchange Handoff](context-exchange-handoff.md) — locate handoff record ownership.
- [Coding Session Context Firewall](session-context-firewall.md) — locate raw-state ingress boundaries.
- [Coding Child Dispatch](delegation-child-dispatch.md) — locate named-path dispatch boundaries.
