# Coding Context Exchange

This module defines file-backed context transport for already-assigned Coding Workers: workspace layout, ownership, capability boundaries, freshness, and handoff. It does not define task meaning, Agent topology, execution planning, or acceptance.

## Transport capsule

Pass only the context needed by the receiving Worker. Prefer a targeted read-only view of the original document. If that is unavailable, the filesystem/tool layer may mechanically copy the named documents into the receiver's `imports/<source-context-id>/`; the LLM must not rewrite them for transport. Use a compact parent-mediated handoff only when neither filesystem option is safe.

A reusable capsule may contain neutral facts, exact paths and source pointers, hashes, freshness/invalidation data, and narrow evidence pointers. It must not contain implementation reasoning, Contract verdicts, private chain-of-thought, secrets, complete diffs, complete logs, or large source copies. Receiving Workers read the capsule first and then only the named source paths they need; authoritative source files remain binding.

For a capsule under `CONTEXT_ROOT/context-bootstrap/`, use:

```text
MANIFEST.md        snapshot identity, hashes, freshness rules
project-context.md neutral project facts and source pointers
policy-context.md  policy-routing pointers and authoritative sections
```

Check freshness against `HEAD`/tree, tracked-delta fingerprint, listed source hashes, relevant untracked state, and the active task/scope. If a material field changes, refresh only affected sections before relying on the capsule; otherwise read the named authoritative sources directly. A capsule never replaces independent final-state verification.

## Workspace ownership

- Set `CONTEXT_ROOT=<primary-worktree>/.token-io-decoupling/context/`. The parent exclusively maintains `CONTEXT_ROOT/INDEX.md`, mapping each assigned or historical Context ID to its directory and minimal routing state. The canonical layout is `CONTEXT_ROOT/INDEX.md`, `CONTEXT_ROOT/<worker-context-id>/`, and, when bootstrap is assigned, `CONTEXT_ROOT/context-bootstrap/`.
- Before an assigned Worker uses file-backed exchange, the parent provisions `CONTEXT_ROOT/<worker-context-id>/` and gives the exact path. The Worker may write only inside that directory; it must not access another Worker's directory unless the parent names specific documents for a concrete handoff or dependency.
- Workers normally share the task's primary worktree. An additional worktree requires a concrete isolation need, such as incompatible snapshots/environments, unredirectable validation writes, a distinct permission/security boundary, or an explicitly isolated audit. Worktree separation alone is not a permission boundary.
- An authorized successor receives a new Context ID and directory. It may read only predecessor documents explicitly exposed by the parent and never writes to the predecessor directory.
- The repository `.gitignore` must ignore `/.token-io-decoupling/`. This root is runtime coordination state, not a product artifact; do not delete it automatically.

## Capability boundary

When the runtime supports filesystem capabilities, enforce the smallest set before execution:

- **RW**: only the Worker's released code paths and its own context directory; a verifier may write only named verification assets.
- **RO**: only source paths required for the released slice and specifically named documents from another Worker.
- **DENY**: the root `INDEX.md`, other Worker directories, and every unlisted path.

If several Workers share one OS identity, ordinary Unix ownership is not reliable isolation; use a real sandbox, container/mount namespace, path allowlist, or equivalent. A Worker must stop when the runtime cannot enforce the required boundary.

## Documents and handoff

Each Worker-local `INDEX.md` records only its task, scope, status, latest material update, document purposes, and blocker/handoff target. Add specialized documents only when they provide distinct reusable value. Update context files at material state, evidence, or handoff changes—not after every command.

An authorized replacement handoff should record achieved state, failed approaches and evidence, current changes and verification state, blockers, and the next useful action. The parent updates the root index and exposes only the named predecessor documents. If the predecessor is unavailable, record the smallest fact-supported recovery note; never recreate a full transcript.
