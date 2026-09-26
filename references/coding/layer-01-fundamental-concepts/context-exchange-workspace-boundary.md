# Coding Context Exchange Workspace Boundary

[English](context-exchange-workspace-boundary.md) | [简体中文](context-exchange-workspace-boundary_zh_cn.md)

This module owns the file-backed context workspace layout, directory ownership, filesystem capability boundary, worktree separation, and OS-level isolation requirements. It does not define capsule content, freshness, handoff records, or child reuse/replacement authorization.

## General rules

### Workspace ownership

- Set `CONTEXT_ROOT=<primary-worktree>/.token-io-decoupling/context/`. The parent exclusively maintains `CONTEXT_ROOT/INDEX.md`, mapping each assigned or historical Context ID to its directory and minimal routing state. The canonical layout is `CONTEXT_ROOT/INDEX.md`, `CONTEXT_ROOT/<worker-context-id>/`, `CONTEXT_ROOT/<worker-context-id>/imports/<source-context-id>/` for parent-prepared read-only imports, and, when bootstrap is assigned, `CONTEXT_ROOT/context-bootstrap/`.
- Before an assigned Worker uses file-backed exchange, the parent provisions `CONTEXT_ROOT/<worker-context-id>/` and gives the exact path. For a concrete handoff or dependency, the parent provisions and names the relevant `imports/<source-context-id>/` directory and source documents. Imports are read-only and are not Worker-writable generated context; the Worker may write only other permitted content in its own context directory and must not access another Worker's directory unless the parent names specific documents.
- Workers normally share the task's primary worktree. An additional worktree requires a concrete isolation need, such as incompatible snapshots/environments, unredirectable validation writes, a distinct permission/security boundary, or an explicitly isolated audit. Worktree separation alone is not a permission boundary.
- The repository `.gitignore` must ignore `.token-io-decoupling`. This root is runtime coordination state, not a product artifact; do not delete it automatically.

### Capability boundary

When the runtime supports filesystem capabilities, enforce the smallest set before execution:

- **RW**: only the Worker's released code paths and permitted writable content in its own context directory; `imports/` is excluded, and a verifier may write only named verification assets.
- **RO**: only source paths required for the released slice and specifically named documents or imports from another Worker.
- **DENY**: the root `INDEX.md`, unlisted imports, other Worker directories, and every other unlisted path.

If several Workers share one OS identity, ordinary Unix ownership is not reliable isolation; use a real sandbox, container/mount namespace, path allowlist, or equivalent. A Worker must stop when the runtime cannot enforce the required boundary.

## Codex CLI / ChatGPT Desktop optimizations

No provider-specific optimization instructions at present; follow the general rules above.

## Claude Code CLI / Claude Desktop optimizations

No provider-specific optimization instructions at present; follow the general rules above.

## Related concepts

- [Coding Context Exchange](context-exchange.md) — locate capsule and freshness ownership.
- [Coding Context Exchange Handoff](context-exchange-handoff.md) — locate handoff record ownership.
- [Coding Session Context Firewall](session-context-firewall.md) — locate raw-state ingress ownership.
- [Coding Child Dispatch](delegation-child-dispatch.md) — locate named-path dispatch boundaries.
