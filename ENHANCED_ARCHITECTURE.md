# Enhanced Workflow Architecture Contract

[English](ENHANCED_ARCHITECTURE.md) | [简体中文](ENHANCED_ARCHITECTURE_zh_cn.md)

This document owns the component and interface contract for the optional enhanced workflow architecture. It maps stable rule nodes to existing owners without copying their policies. This is a design specification; it does not claim that the MCP service, database, or API integration is implemented or available.

## Components and authoritative data

The design uses an independent Python subproject under `mcp/`, managed with uv and using Pydantic, `sqlite3`, the official MCP SDK v2, and the OpenAI SDK. The local stdio transport targets MCP protocol revision `2026-07-28`. These choices define the intended implementation, not verified runtime capability.

Markdown owner documents remain the sole policy-text authority. The JSON registry at [`mcp/rule-registry.json`](mcp/rule-registry.json) maps stable node IDs to owner headings, facts, evidence, branches, evaluation mode, failure action, and successor checkpoints. It must not duplicate owner prose. At load time, the implementation reads the current owner text and computes its hash; it does not maintain a second hand-authored policy body or stored node hash. Ordinary prose changes become visible through dynamic rereads. A change to node structure, branch enums, or hard constraints requires a compatible implementation and test update under the changed `contract_version`.

SQLite stores structured control state, evidence references, semantic-content references and hashes, and indexes. Full Contract, Decision Brief, Plan, Memo, Capsule, Handoff, and other semantic bodies remain in Markdown or Serena Memory under their existing owners. SQLite indexes do not replace formal messages, visibility requirements, or shared-worktree conflict controls.

## Identity and state boundaries

The Root database is the logical owner of root control state. A Worker database contains only its read-only assignment snapshot and that Worker’s own progress, milestones, local checks, evidence, blockers, and recovery context. Root reads only authorized summaries and evidence, verifies them, and performs root-level transitions; a Worker report does not itself confirm root completion.

The intended layout is `~/.local/state/token-io-decoupling/<project-id>/<root-session-id>/workflow.sqlite3` with worker stores under `subagents/<subagent-session-id>/worker.sqlite3`. Project and session bindings must come from trusted runtime context. A caller-provided identity, path, or `authorized=true` flag is insufficient. A Worker store is initialized only after the real child identity is verified and bound to its reserved allocation. Paths are derived from trusted bindings and must reject traversal and out-of-bound symlinks.

Mode/count, Allocation, state Revision, rule/schema compatibility version, and the implementation/content, documentation, and Git metadata Verification Epochs are separate dimensions. They must never be substituted for one another. Their governing policies remain in their existing owners; see Related concepts.

## Interfaces and transaction contract

The planned MCP interface has public read-only capability, rule-context, and schema-status operations; Parent operations for opening and reading workflow state, reserving/binding allocations, checking/releasing slices, evaluating checkpoints, recording evidence, transitioning state, reading Worker summaries, and reconciling; and Worker operations for reading its assignment/state, recording progress/evidence, reporting blockers, and retrieving recovery context. Inputs use explicit types and enums. Writes include an expected Revision and idempotency key and return the resulting status, reason, rule version, evidence references, current Revision, and follow-up requirements. Arbitrary SQL, shell, or free-form prompt execution is outside this interface.

Root and Worker stores have independent migration sequences, beginning at `v0001`. Each database records its kind and migration version, name, checksum, applied time, and duration. An authorized write open validates identity, permission, path, database kind, migration history, checksum, and program compatibility; takes an exclusive per-database migration lock; backs up before pending migrations; and applies each migration with its history record in one transaction. It validates schema and integrity before enabling business writes. Read-only diagnostics do not trigger migration. Published migrations are immutable; no automatic downgrade is provided. A failure rolls back the current migration and preserves earlier successful migrations and the backup. Missing history, checksum mismatch, future schema, corruption, or incompatibility blocks enhanced writes; it must not silently recreate the database.

Single-database transitions use transactions, constraints, monotonic Revision checks, and idempotency. Cross-database exchange uses event IDs and parent confirmation; it does not assume atomic commit across Root and Worker stores.

## Native and Enhanced operation

Native is the default operation: the Agent reads the authoritative documents and maintains the existing structured records and semantic bodies according to their owners. Enhanced operation is optional and may expose only the capabilities whose trusted host identity and actual permission boundaries have both been verified. If either condition is unknown or fails, block that dependent enhanced read/write and retain Native operation where its own required state is available.

The Decisions API is disabled by default. In this implementation phase, API behavior is exercised only through mocks; no real request is authorized by this architecture contract. When an explicitly enabled API is unavailable, times out, rejects input, or returns invalid/stale output, switch semantic judgment to the document path. If MCP and SQLite remain available, continue maintaining their state. API output never authorizes an action or releases a slice.

When MCP is unavailable, use Native records. If MCP later recovers, Root explicitly reconciles effective Native records, database Revision, lifecycle, and evidence freshness before enhanced writes resume. Reconciliation must preserve valid Native records; last-write-wins overwrite is forbidden. A damaged or incompatible database is not directly written through Native fallback. No fallback bypasses a hard constraint or a required host guard.

## Rule-node mapping

[`mcp/rule-registry.json`](mcp/rule-registry.json) is a machine-readable mapping, not a policy source. Each node has a stable ID, owner path and existing section heading, required facts and evidence, legal branches, evaluation mode (`direct`, `deterministic`, `semantic`, or `hybrid`), failure action, and successor checkpoint IDs. `contract_version` identifies the shape of this mapping. IDs are stable and must not be reassigned to different concepts. Node hashes are computed from loaded owner text and are not maintained in the registry.

Registry consumers should load only the node and direct owner headings needed for the current checkpoint. They should not scan the entire repository. Direct references remain authoritative for interpretation; deterministic checks enforce only explicit structured constraints; semantic classification may assist but cannot authorize; hybrid evaluation combines a semantic result with deterministic hard-constraint checks.

## Related concepts

- [Coding Delegation State Record](references/coding/layer-01-fundamental-concepts/delegation-state-record.md) — root control-record ownership.
- [Coding Execution Control](references/coding/layer-01-fundamental-concepts/execution-control.md) — slice and control-boundary ownership.
- [Verification Epoch Checkpoint](references/coding/layer-02-workflow-concepts/verification-epoch.md) — epoch invalidation ownership.
- [Coding workflow selector](workflows/coding.md) — route navigation.
