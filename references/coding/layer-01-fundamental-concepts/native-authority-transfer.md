# Native Authority Transfer

[English](native-authority-transfer.md) | [简体中文](native-authority-transfer_zh_cn.md)

This owner defines the safe transfer of canonical Root workflow authority from an established Enhanced store back to Native parent context. It does not define workflow fields, Mode/Count, audit policy, Worker lifecycle, or a product-specific export capability.

## General rules

### When transfer applies

Native parent context is canonical when Enhanced persistence has never been initialized for this workflow. Record transfer as `Not applicable` with that reason; do not invent an Enhanced history. Once an authorized Enhanced Root store has been initialized and validated, it remains canonical until this transfer protocol has completed. An outage, missing guard, route preference, or public rule access does not switch authority.

This is a safety protocol, not a claim that every host or service implements export, writer-stop, or transfer operations. Use it only when the current authorized environment exposes the required operations and evidence. Failure of an optional advice API alone does not make a healthy Enhanced state service unavailable and does not trigger a transfer.

### Freeze, settle, and verify before switching

Before writing the Native canonical record, verify the same project, Root, Run, Mode/Count, schema, and current canonical Root record. Stop accepting new dependent writes and actually freeze every writer to that authority. Resolve the final outcome of every in-flight operation and pending cross-store effect. A timeout, disconnected client, missing response, or claimed server stop is not evidence of rollback or quiescence. If any writer or operation may still commit, keep dependent writes blocked and preserve the uncertain state for recovery.

Transfer only a complete, verified canonical record that Native can represent. Preserve stable identities, allocations, lifecycle, current state, references, audit state and its unknown or pending values, and the evidence needed to understand the record. The [Session Audit Visibility](session-audit-visibility.md) and [Coding Delegation State Record](delegation-state-record.md) owners remain authoritative for audit fields and timing; transfer does not answer, reset, default, or copy audit policy into Worker state. Do not reconstruct missing historical fields or replace unknown values with current defaults.

Write the verified record into the Native canonical context and read it back. Confirm that the full supported structured record and its identity match the frozen Enhanced record before treating Native as canonical. Keep the prior Enhanced record and transfer evidence available as history; never use last-write-wins, overwrite a valid record, or discard an unresolved comparison. If Native cannot preserve an essential field, reference, or lifecycle fact, block dependent work rather than claiming a complete transfer.

If transfer stops before readback and confirmation, its outcome is indeterminate. Do not resume writes to either authority or infer that a partial Native write succeeded or rolled back. Preserve both records and the exact boundary reached; continue only after an authorized operation resolves which record is complete and canonical. A freeze without verified transfer is not permission to continue Native writes.

### Authority boundary

This protocol changes only which existing Root record is canonical. It does not authorize a Mode/Count change, new Run or allocation, Worker creation, Slice release, lifecycle transition, verification pass, or external effect. Preserve existing Worker identity and state boundaries; this owner does not transfer or merge Worker stores. Apply the Native Reconciliation owner separately when the direction is Native to Enhanced.

## Codex CLI / ChatGPT Desktop optimizations

Use only a directly exposed and authorized operation that can freeze Enhanced writers, settle in-flight effects, write the Native parent record, and verify readback. Do not infer these capabilities from a CLI, SDK, fake binding, protocol test, or unavailable host. If any required operation is absent or unverified, keep dependent writes blocked. Never use Computer Use to establish the transfer.

## Claude Code CLI / Claude Desktop optimizations

There is currently no Claude-specific authority-transfer optimization. Follow the general rules and require actually exposed, authorized operations and evidence.

## Related concepts

- [Enhanced Workflow Availability](enhanced-workflow-availability.md) — owns path selection and unavailable-capability disposition.
- [Enhanced State Store](enhanced-state-store.md) — owns Enhanced persistence authority and access boundaries.
- [Coding Delegation State Record](delegation-state-record.md) — owns canonical record fields and Native parent-context authority.
- [Native Reconciliation](native-reconciliation.md) — owns the reverse Native-to-Enhanced transition.
