# Enhanced State Store

[English](enhanced-state-store.md) | [简体中文](enhanced-state-store_zh_cn.md)

This owner defines persistence authority and access boundaries for the optional Enhanced Root and Worker state stores. It does not redefine task-record fields, Mode/Count, Slice/Control policy, audit semantics, or Worker lifecycle.

## General rules

### Authority and first write

In Native operation, the parent-context record remains canonical under the [delegation state record](delegation-state-record.md). After an authorized Enhanced Root store is initialized and its identity/schema are validated, that Root store is the canonical Enhanced record; parent context keeps a readable snapshot or reference and must not become a competing writable authority. Switching from Native to Enhanced follows [Native Reconciliation](native-reconciliation.md); switching back follows [Native Authority Transfer](native-authority-transfer.md). This store owner supplies persistence and access boundaries, not either transition procedure.

The first authorized Root write is allowed only after the Mode gate has passed and the current Root Session identity, role, and Context Firewall boundary are established. Opening the Root store creates pending workflow state and reserved slots as defined by the existing owners; it does not itself release Mode, Session, audit, Allocation role, or Slice authority. If audit resolution is pending, persist the actual `pending` state when available; an open that succeeded before the audit transition failed is a recoverable intermediate state. Do not infer a reply, default, completed audit, or permission to advance dependent work.

Session Audit values, prompt wording, timing, resolution, and Root-only ownership remain with [Session Audit Visibility](session-audit-visibility.md) and the [delegation state record](delegation-state-record.md). Persist the Root record by the approved typed transition. Never copy the complete Root audit object or prompt history into Worker-controlled state. The audit configuration grants no Mode, Allocation, Slice, lifecycle, or other authority.

### Root and Worker boundaries

Root alone owns workflow control state and Root-only metadata. A Worker store may be initialized only after a real child has been created, its identity verified, and its released allocation bound. A Worker reads its own immutable assignment snapshot and may write only its own progress, evidence, and blocker records. It cannot choose another Worker/path, write Root control state, change its assignment, or read another Worker’s store. Existing record shape and child lifecycle policies remain authoritative.

Store only structured state, semantic references and hashes, evidence references, and bounded recovery indexes. Keep full semantic bodies in their existing document or memory owners. Trusted capability snapshots are evidence about the observed binding, not authority by themselves.

### Reads, writes, and recovery indexes

Read-only state and schema diagnostics must not create files, apply migrations, refresh snapshots, advance Revision, or mutate receipts. An unbound status query performs no state-path I/O. A bound Root or Worker can inspect only its own authorized store; callers never supply arbitrary database paths.

State writes use the existing typed operations, expected Revision, and idempotency key. Same-key/same-operation/same-payload replay returns the prior receipt without repeating effects; conflicting reuse is rejected. A replay or read must not silently update state. State Revision, schema version, rule hash, and each Verification Epoch remain separate.

Recovery indexes are bounded and ordered. A page cursor is bound to its collection and observed Revision; a stale cursor is rejected without writes. The returned page metadata must make omitted items retrievable through the next cursor. Indexes contain references and hashes, not copied semantic bodies. For legacy Root records that lack `output_class` or `write_content_memo`, preserve the value as unknown with an explicit missing-field reason; do not infer a current value or use the unknown field to authorize or release an action. Opening a store never discards or overwrites a valid Native record; use the explicit Native transition owners before dependent writes.

## Codex CLI / ChatGPT Desktop optimizations

Use the state service only when the current Session exposes a trusted binding with the operation’s required guards. Production defaults deny protected state operations without that provider. An SDK or fake-binding test demonstrates only the tested service/protocol contract, not a real host’s identity or OS isolation. Use the existing Native record when Enhanced state is not selected or unavailable and Native prerequisites remain satisfied.

## Claude Code CLI / Claude Desktop optimizations

There is currently no Claude-specific state-store optimization. Follow the general rules and require directly exposed trusted identity and guards before protected access.

## Related concepts

- [Enhanced Schema Migrations](enhanced-schema-migrations.md) — owns schema status, migration, backup, and restore boundaries.
- [Native Reconciliation](native-reconciliation.md) — owns the Native-to-Enhanced authority transition.
- [Native Authority Transfer](native-authority-transfer.md) — owns the Enhanced-to-Native authority transition.
- [Coding Delegation State Record](delegation-state-record.md) — owns the record fields and Native parent-context authority.
- [Coding Delegation Worker Boundary](delegation-worker-boundary.md) — owns Worker snapshot and write-scope boundaries.
- [Coding Execution Control](execution-control.md) — owns Slice and Control policy.
