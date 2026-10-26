# Native Reconciliation

[English](native-reconciliation.md) | [简体中文](native-reconciliation_zh_cn.md)

This owner defines explicit Native-to-Enhanced Root reconciliation after Mode and Session boundaries pass. It does not own record fields, Mode/Count, Session Audit policy, Worker lifecycle, schema migration mechanics, or Enhanced availability selection.

## General rules

### Read and compare before dependent Root writes

When Native parent context is canonical and Enhanced is selected, verify the current Root identity, operation guards, and schema before reconciling. A new Enhanced workflow with no Native history records this check as `Not applicable`; it must not invent prior state. For an existing Native record or unresolved comparison history, read the complete bounded set, following every current cursor, before ordinary dependent Root writes. Read-only status inspection does not authorize a write. A comparison is itself a revisioned, idempotent Root mutation and must be authorized and read back.

Compare exact current Native snapshots with the Enhanced Root record. An exact two-phase confirmation applies only to its reviewed comparison and does not dismiss any other unresolved entry. For material differences, review the complete current unresolved set, its digest, the latest target snapshot, and all exposed source, reference, revision, and epoch details. Bind the Root decision and quiescence/freshness evidence to that exact reviewed set. References identify evidence; a hash or caller assertion alone does not establish semantic truth or authority.

### Supported resolution and blockers

For supported material differences, the Root explicitly chooses either the Native Contract source and semantic references together, or retains both SQLite values. Preserve the original Native and SQLite records, every comparison, and the chosen resolution with its evidence references. Do not merge fields selectively, rewrite old comparisons, or let a newer matching snapshot hide an older valid conflict.

Resolution is blocked if any reviewed snapshot changes immutable project, Root, Run, Mode/Count, mode source, allocation identity, lifecycle, or dispatch history; if the record contains a bound or initialized Worker, pending dispatch, active Worker Slice, unknown essential history, malformed data, or an unsupported oversized legacy item; or if the complete set cannot be reviewed. Do not reconstruct identities, import a progressed Native-only workflow without its Root history, resurrect terminal state, or manufacture historical preimages. A stale or ambiguous legacy comparison remains unresolved until a fresh supported comparison and explicit review establish a valid basis.

### Recovery floor and fresh release

Apply a successful resolution atomically against the current Root Revision and the complete reviewed comparison set. Preserve identities and the current Root audit record; Native audit state is not imported, reset, or treated as a replacement for the current [Session Audit Visibility](session-audit-visibility.md) owner. Set the resulting Revision to `max(current SQLite Revision, every reviewed Native Revision) + 1`. For each of the three Verification Epochs, use `max(current SQLite Epoch for that dimension, every reviewed Native Epoch for that dimension) + 1`. Refuse overflow or stale CAS without partial resolution.

Retain prior evidence, evaluations, Control outcomes, receipts, and pending/returned Evidence-on-Demand requests as history. A recovery Revision floor makes every pre-floor result stale, including facts with empty epoch coverage. Do not delete old evidence or reinterpret it as fresh. Pending Evidence-on-Demand remains pending; Continue requires genuinely fresh returned evidence associated with the request. After resolution, recheck the current authorized task envelope and relevant facts before further release. Do not reopen locked Mode or repeat a completed Session Audit question/resolution; re-read and confirm the current canonical audit record before leaving the Session boundary.

Before the next Slice release, require a new explicit Control `Continue` recorded after the recovery floor and current for the Control rule and relevant Epochs. Apply [Coding Execution Control](execution-control.md) for Slice and Control ownership. A prior Continue, an API suggestion, or successful comparison is insufficient. If the state or applicable Epoch/rule changes, obtain a new current Control result. `Amend` returns through the existing Contract and Decision checks and must pass Control again before release; `Stop` does not release. Normal Control after implementation still follows its ordinary route to current-state Verification.

### Root-only authority and effects

Only the trusted Root may compare, confirm, or resolve. While any unresolved comparison or confirmation remains, reject dependent Root writes before side effects, including dispatch completion or Worker initialization. Permit only read-only inspection, authorized comparison/resolution, and genuinely effect-free receipt replay. Keep all state changes CAS- and idempotency-bound. This process does not grant Mode, Count, Allocation, Worker, Slice, verification, or external-effect authority.

## Codex CLI / ChatGPT Desktop optimizations

Use only the authorized Root state operations and bounded pages exposed to the current Session. Review all unresolved pages and the actual referenced sources before resolution; do not use raw database access, fabricated snapshots, or GUI interaction. A fake binding or SDK protocol test proves only its test boundary, not real-host identity or semantic truth.

## Claude Code CLI / Claude Desktop optimizations

There is currently no Claude-specific reconciliation optimization. Follow the general rules and use only actually exposed, authorized Root operations.

## Related concepts

- [Enhanced State Store](enhanced-state-store.md) — owns Root persistence, typed operations, and bounded recovery indexes.
- [Enhanced Workflow Availability](enhanced-workflow-availability.md) — owns selection and unavailable-capability disposition.
- [Coding Delegation State Record](delegation-state-record.md) — owns canonical record fields and Native authority.
- [Coding Execution Control](execution-control.md) — owns Slice and Control policy.
- [Native Authority Transfer](native-authority-transfer.md) — owns the reverse Enhanced-to-Native transition.
