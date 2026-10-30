# Session state resolution

[English](session-state-resolution.md) | [简体中文](session-state-resolution_zh_cn.md)

This checkpoint owns the route-level sequence for establishing and reading the current canonical Root state before audit configuration is resolved. It does not own audit prompts, audit fields, or migration mechanics.

## Trigger and inputs

Consume the selected Native or Enhanced path, the released Mode/count, and current Session identity, role, and Context Firewall facts. Apply [Session Model](../layer-01-fundamental-concepts/session-runtime/session-model.md), [Session Role Ownership](../layer-01-fundamental-concepts/session-runtime/session-role-ownership.md), [Session Context Firewall](../layer-01-fundamental-concepts/session-runtime/session-context-firewall.md), and [Delegation State Record](../layer-01-fundamental-concepts/delegation/delegation-state-record.md). For Enhanced state, also apply [Enhanced State Store](../layer-01-fundamental-concepts/enhanced-native-state/enhanced-state-store.md), [Enhanced Schema Migrations](../layer-01-fundamental-concepts/enhanced-native-state/enhanced-schema-migrations.md), [Native Reconciliation](../layer-01-fundamental-concepts/enhanced-native-state/native-reconciliation.md), and [Native Authority Transfer](../layer-01-fundamental-concepts/enhanced-native-state/native-authority-transfer.md) only on their stated triggers.

## Decision and result

1. Confirm the selected backend and released Session facts. If Mode, identity, role, Context Firewall, or required schema evidence is missing or conflicting, stop before opening or writing Root state.
2. Establish which record is canonical. When Enhanced is selected but Native may still hold the current canonical record, complete Native Reconciliation before an ordinary Enhanced open or dependent write. If an established Enhanced record is being returned to Native, use Native Authority Transfer only under that owner's transfer conditions. An outage alone never changes authority. If Native is selected and no prior Enhanced authority exists, record Enhanced-store/schema and transfer checks as `Not applicable` with the observed reason.
3. For Enhanced state, before the first open verify the bound host identity, Root-only access, paths, read-only identity/status guards, and compatible schema/history. If migration is required, follow the migration owner's backup, version, transaction, and integrity procedure; this checkpoint only confirms its evidence. A new Enhanced Root with no Native history records reconciliation as `Not applicable`. Never recreate a missing or inaccessible record as a recovery shortcut.
4. Open or resume the Root record only after the applicable authority, identity, role, firewall, and schema checks pass. Use the Native canonical parent-context record when Native is selected; use the bound Enhanced Root record when Enhanced is selected. Preserve the existing record and pending state.
5. Read back the current canonical record, identity, revision, and applicable allocation/state evidence. Return that verified result to the route so its subsequent audit-resolution action can consume it; this checkpoint does not own audit-record configuration or its prompt/resume procedure.

| Observed result | Required route action |
| --- | --- |
| Canonical authority and record are verified; guarded open/resume and readback succeed | Return the record and readback evidence to the route for its next action. |
| No prior Enhanced authority applies to a Native route, or reconciliation is not triggered for a new Enhanced Root with no Native history | Record `Not applicable` and why; continue only after the applicable canonical record is identified. |
| Authority, identity, role, firewall, schema, migration result, required guard, open/resume, or readback is unknown or fails | Mark the dependent operation unavailable and block state-dependent work. Preserve recoverable state; do not infer authority or create a replacement record. |
| Reconciliation materially changes current facts or the authorized decision | Return to current Context and Decision, then re-establish and read back canonical state before continuing. Do not reopen Mode or repeat a completed audit prompt. |

## Failure boundary

Do not open or write state before applicable owners' guards pass. Do not treat a failed Enhanced operation as permission to transfer authority or reset state. A failed readback blocks audit resolution and dependent work.

## Related concepts

- [Session Model](../layer-01-fundamental-concepts/session-runtime/session-model.md)
- [Enhanced State Store](../layer-01-fundamental-concepts/enhanced-native-state/enhanced-state-store.md)
